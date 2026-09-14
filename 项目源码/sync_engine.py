# -*- coding: utf-8 -*-
"""
双向同步引擎（类 Chrome/Edge 云同步）
========================================

核心原则：
  1) Last Write Wins (LWW)：同一条记录谁的 updated_at 更新，谁赢。绝不"整体覆盖"。
  2) 软删除墓碑：删除操作 = 置 is_deleted=True + 更新 updated_at。两端互相通知。
  3) 增量同步：sync_state.json 记录每类模型上次同步到的最大 updated_at，
     下次只推/拉比这个时间新的差异。
  4) 关系（Post-Tag）同步：把 M2M 表 post_tags 导出为 (post_id, tag_id) 对。

远端存储协议（任何 adapter 都映射到这个语义）：
  <prefix>/sync_state.json                      {version, push_cursors:{entity:ts}, pull_cursors:{entity:ts}}
  <prefix>/sync_data/posts.jsonl                {id,data,is_deleted,updated_at,prov}  (prov=来源节点，便于调试)
  <prefix>/sync_data/tags.jsonl
  <prefix>/sync_data/profile.jsonl
  <prefix>/sync_data/comments.jsonl
  <prefix>/sync_data/likes.jsonl
  <prefix>/sync_data/friend_links.jsonl
  <prefix>/sync_data/post_tags.jsonl            {post_id, tag_id}
  <prefix>/sync_data/site_settings.jsonl        {key,value,updated_at}  (新增：站点配置)
  <prefix>/sync_attachments/<subpath>           (新增：二进制附件，按原始目录结构镜像，如 avatars/x.png bg/y.png)
"""
from __future__ import annotations

import json
import os
import datetime
import hashlib
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ============================================================
# 模型元数据（独立于 app 导入；app.py 没初始化也能用其中纯函数）
# 每个需要同步的模型：
#   name         → 文件名（.jsonl 后缀）
#   pk_field     → 主键字段名（一般是 id）
#   exclude_cols → 不参与同步的列（如反查关系属性 rendered_html 等）
#   relation     → 是否 M2M 关系表（不是 ORM Model）
# ============================================================
SYNCABLE_ENTITY_NAMES: Tuple[str, ...] = (
    'profile', 'posts', 'tags', 'comments', 'likes', 'friend_links', 'post_tags',
    'site_settings',
)


def _entity_to_model_name(entity: str) -> Optional[str]:
    m = {
        'profile': 'Profile',
        'posts': 'Post',
        'tags': 'Tag',
        'comments': 'Comment',
        'likes': 'Like',
        'friend_links': 'FriendLink',
        'site_settings': 'SiteSetting',
    }.get(entity)
    return m


def _get_syncable_models(app_module) -> Dict[str, Any]:
    """返回 {entity_name: ORM_Model}，M2M 关系 post_tags 不在此返回。"""
    mapping = {}
    for entity in SYNCABLE_ENTITY_NAMES:
        mname = _entity_to_model_name(entity)
        if mname is None:
            continue
        mapping[entity] = getattr(app_module, mname, None)
    return mapping


# 不参与"行数据 LWW 比较"的列（不写入 jsonl，也不回写到 DB）
_EXCLUDE_COLUMNS = {'rendered_html'}  # 这个列可以从 content 重新生成

# ============================================================
# 1. 时间工具（确保全链路 ISO 字符串一致）
# ============================================================
def _dt_to_iso(dt: Any) -> str:
    if dt is None:
        return ''
    if isinstance(dt, str):
        return dt
    # datetime
    return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)


def _iso_to_dt(s: str) -> Optional[datetime.datetime]:
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:
        # 兼容旧格式
        for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'):
            try:
                return datetime.datetime.strptime(s, fmt)
            except Exception:
                continue
    return None


def _cmp_iso(a: str, b: str) -> int:
    """比较两个 ISO 时间字符串；认为空串最早。"""
    if not a and not b:
        return 0
    if not a:
        return -1
    if not b:
        return 1
    # 纯字符串比较对标准 ISO 是可靠的（YYYY-MM-DDTHH:MM:SS 字典序=时间序）
    return -1 if a < b else (1 if a > b else 0)


def _model_updated_at(instance_or_cls: Any) -> str:
    """统一获取模型行的 LWW 时间戳（缺 updated_at → created_at → 空串=最早）。
    没有 updated_at/created_at 的模型（如 Tag）返回空串，
    LWW 视为"最旧"，远端有值时自动覆盖本地。"""
    for attr in ('updated_at', 'created_at'):
        v = getattr(instance_or_cls, attr, None)
        if v is not None:
            return _dt_to_iso(v)
    # 没有 updated_at/created_at → 空串（LWW 视为最早，允许远端覆盖）
    return ''


# ============================================================
# 2. ORM 行 → 记录 dict（导出）
# ============================================================
def _row_to_record(row: Any, provenance: str = '') -> Dict[str, Any]:
    """把 ORM 对象转成 {id, data, is_deleted, updated_at, prov} 记录。"""
    mapper = getattr(row, '__mapper__', None)
    if mapper is None:
        raise TypeError('sync_engine 只能处理 ORM 实例')
    data: Dict[str, Any] = {}
    for col_name in mapper.columns.keys():
        if col_name == 'id':
            continue
        if col_name in _EXCLUDE_COLUMNS:
            continue
        v = getattr(row, col_name, None)
        # 日期→ISO 字符串
        if isinstance(v, (datetime.datetime, datetime.date)):
            v = _dt_to_iso(v)
        data[col_name] = v
    rec = {
        'id': row.id,
        'data': data,
        'is_deleted': bool(getattr(row, 'is_deleted', False)),
        'updated_at': _model_updated_at(row),
    }
    if provenance:
        rec['prov'] = provenance
    return rec


def export_all_records(session, entity_name: str,
                       since_iso: str = '',
                       provenance: str = '') -> List[Dict[str, Any]]:
    """
    把某一类模型的所有（或 since 之后有变更的）行 → 记录列表。
    entity_name: 'posts' | 'tags' | ... | 'post_tags' | 'site_settings'
    since_iso 非空时，只返回 updated_at > since_iso 的记录（增量导出）。
    注意：默认 since_iso 为空 = 全量导出（首次同步/容错重置时使用）。
    """
    # M2M 关系单独处理
    if entity_name == 'post_tags':
        return _export_post_tags(session, since_iso, provenance)

    # site_settings KV 表单独处理（模型可能叫 SiteSetting 也可能用简单 KV 结构）
    if entity_name == 'site_settings':
        return _export_site_settings(session, since_iso, provenance)

    # 懒 import app（避免在没 Flask app 上下文时加载失败）
    import app as _app_module
    model = _get_syncable_models(_app_module).get(entity_name)
    if model is None:
        raise ValueError('未知同步实体: %s' % entity_name)

    q = session.query(model)
    # 软删的也要同步出去（它本身就是墓碑）
    if since_iso:
        # since 过滤：严格 >（since 那一刻的都已在上一轮同步出去了，等值不重推）
        since_dt = _iso_to_dt(since_iso)
        if since_dt is not None:
            if hasattr(model, 'updated_at') and model.updated_at is not None:
                q = q.filter(model.updated_at > since_dt)
            elif hasattr(model, 'created_at'):
                q = q.filter(model.created_at > since_dt)
    rows = q.all()
    return [_row_to_record(r, provenance) for r in rows]


def _export_post_tags(session, since_iso: str, provenance: str = '') -> List[Dict[str, Any]]:
    """导出 Post↔Tag 关系。"""
    import app as _app_module
    post_tags = _app_module.post_tags
    # 取所有关联对；updated_at 参考 Post.updated_at（Tag 被挂到某文章上 → Post 的时间就是关联时间）
    pairs = session.query(post_tags).all()
    result = []
    for (post_id, tag_id) in pairs:
        # 取 Post 的 updated_at 作为本条关系的 LWW 时间（没 Post 就算了）
        p = session.query(_app_module.Post).get(post_id)
        ts = _model_updated_at(p) if p is not None else ''
        if since_iso and ts and _cmp_iso(ts, since_iso) <= 0:
            # since_iso 那一刻及之前的都已同步，严格 > 才传
            continue
        rec = {
            'id': 'pt_%d_%d' % (post_id, tag_id),  # 伪主键，便于去重
            'data': {'post_id': post_id, 'tag_id': tag_id},
            'is_deleted': False,
            'updated_at': ts or _dt_to_iso(datetime.datetime.utcnow()),
        }
        if provenance:
            rec['prov'] = provenance
        result.append(rec)
    return result


def _export_site_settings(session, since_iso: str, provenance: str = '') -> List[Dict[str, Any]]:
    """导出站点配置（SiteSetting 模型或 profile.bg_image/nickname 等冗余字段走 profile 实体）。

    注意：这里只负责 SiteSetting ORM 表（如果 app 里定义了的话）。个人资料走 profile 实体。
    """
    import app as _app_module
    model = getattr(_app_module, 'SiteSetting', None)
    if model is None:
        # 没有独立 SiteSetting 模型 → 无记录
        return []
    q = session.query(model)
    if since_iso:
        since_dt = _iso_to_dt(since_iso)
        if since_dt is not None and hasattr(model, 'updated_at') and model.updated_at is not None:
            q = q.filter(model.updated_at > since_dt)
        elif since_dt is not None and hasattr(model, 'created_at'):
            q = q.filter(model.created_at > since_dt)
    rows = q.all()
    return [_row_to_record(r, provenance) for r in rows]


# ============================================================
# 3. 记录 dict → ORM（导入，LWW 合并）
# ============================================================
def import_records(session, entity_name: str,
                   remote_records: Iterable[Dict[str, Any]],
                   only_since_iso: str = '') -> int:
    """
    把远端记录合并到本地 DB（LWW）。返回实际应用（更新/插入/墓碑）的记录数。
    冲突策略：比较 record.updated_at vs 本地对应行的 updated_at，谁更新谁赢。
    only_since_iso: 可选，只处理 updated_at > only_since_iso 的记录（增量拉取）。
    """
    applied = 0
    # 增量 since 预过滤（防止"全量远端 vs 本地已合并"时浪费大量 LWW 比较）
    if only_since_iso:
        kept = []
        for r in remote_records:
            ts = r.get('updated_at', '') or ''
            if ts and _cmp_iso(ts, only_since_iso) > 0:
                kept.append(r)
        remote_records = kept

    if entity_name == 'post_tags':
        return _import_post_tags(session, remote_records)
    if entity_name == 'site_settings':
        return _import_site_settings(session, remote_records)

    import app as _app_module
    model = _get_syncable_models(_app_module).get(entity_name)
    if model is None:
        # 模型不存在（比如 app 还没加 SiteSetting）→ 跳过不报错
        if entity_name == 'site_settings':
            return 0
        raise ValueError('未知同步实体: %s' % entity_name)

    for rec in remote_records:
        try:
            applied += _apply_one_record(session, model, rec)
        except Exception:
            import logging
            logging.getLogger('sync_engine').exception(
                '合并记录失败 entity=%s id=%s', entity_name, rec.get('id'))
    session.flush()
    return applied


def _profile_field_is_default(field_name: str, value) -> bool:
    """判断 Profile 某字段是否处于"用户未编辑过"的默认态。

    用于"记录级 LWW 失败"时的字段级兜底合并：本地仍为默认态 ⇒ 允许远端非空值填入。
    注意：这只是"填空"，绝不会覆盖用户已编辑的非默认值，因此等价于字段级 LWW 的保守实现。
    """
    s = '' if value is None else str(value).strip()
    if field_name == 'nickname':
        DEFAULT_NICKS = ('博主', '默认博主', '', 'Cyber Coder')
        return (s in DEFAULT_NICKS
                or s.startswith('博主') or s.startswith('默认博主')
                or s.startswith('Cyber Coder'))
    # 其他展示字段：空串/空值 = 默认态
    return s == ''


def _apply_one_record(session, model, rec: Dict[str, Any]) -> int:
    """对单条记录应用 LWW。返回 1 表示实际改动了，0 表示跳过。"""
    rid = rec.get('id')
    if rid is None:
        return 0
    remote_updated = rec.get('updated_at', '') or ''
    remote_is_deleted = bool(rec.get('is_deleted', False))
    remote_data = rec.get('data') or {}

    # ---------- 本地现状 ----------
    local = session.query(model).get(rid)
    if local is not None:
        local_updated = _model_updated_at(local)
        # ========== 特殊：默认初始化 Profile 视为 "从未编辑过"，LWW 优先级最低 ==========
        default_profile = False
        try:
            if model.__name__ == 'Profile' and rid == 1:
                nick = str(getattr(local, 'nickname', None) or '').strip()
                title = str(getattr(local, 'title', None) or '').strip()
                bio = str(getattr(local, 'bio', None) or '').strip()
                about = str(getattr(local, 'about', None) or '').strip()
                avatar = str(getattr(local, 'avatar', None) or '').strip()
                bg = str(getattr(local, 'bg_image', None) or '').strip()
                DEFAULT_NICKS = ('博主', '默认博主', '', 'Cyber Coder')
                is_default_name = (nick in DEFAULT_NICKS
                                   or nick.startswith('博主')
                                   or nick.startswith('默认博主')
                                   or nick.startswith('Cyber Coder'))
                is_empty_content = not (title or bio or about or avatar or bg)
                default_profile = is_default_name and is_empty_content
        except Exception:
            default_profile = False

        if default_profile:
            # 本地是默认空壳，直接让远端覆盖（LWW 跳过，远端数据就是用户真实编辑）
            pass
        elif _cmp_iso(remote_updated, local_updated) <= 0:
            # ===== 记录级 LWW：本地更新或持平，远端整行"没赢" =====
            # 常规实体：直接跳过（避免把老数据覆盖到更新的本地记录上）
            if model.__name__ != 'Profile' or rid != 1:
                return 0
            # ===== Profile 特例：字段级"填空式"合并 =====
            # 用户可能只编辑了 B.title（从而 updated_at 整体 bumped），但 bio/nickname 等
            # 其他字段仍是默认空态。若远端这些字段有值（A 机编辑过），应允许远端填入空
            # 值字段，而不是整行跳过。这等价于"字段级 LWW：本字段用户没改过 = 默认态"。
            changed = False
            for k, v in (remote_data or {}).items():
                if not hasattr(model, k) or k in _EXCLUDE_COLUMNS:
                    continue
                local_v = getattr(local, k, None)
                # 远端没值 → 别清空本地
                rv_str = '' if v is None else str(v).strip()
                if not rv_str:
                    continue
                # 本地字段已经不是默认态（用户改过）→ 尊重本地，不做任何覆盖
                if not _profile_field_is_default(k, local_v):
                    continue
                # 本地默认 + 远端非空 → 填入
                if isinstance(v, str) and k.endswith('_at'):
                    dt_v = _iso_to_dt(v)
                    if dt_v is not None:
                        v = dt_v
                setattr(local, k, v)
                changed = True
            # 字段回填成功，算 applied；但不能把本地 updated_at 回拨（否则下一轮会再被覆盖）
            return 1 if changed else 0

    # ---------- 远端更新 → 应用到本地 ----------
    if remote_is_deleted:
        # 墓碑：若本地存在，标记 is_deleted=True；若不存在，也"存一条"墓碑（
        #  防止未来反向再被推过来的旧版本覆盖）。
        if local is None:
            local = model(id=rid)
            # 先插最小字段，其他列用默认
            session.add(local)
            session.flush()
            local = session.query(model).get(rid)
        if hasattr(local, 'is_deleted'):
            local.is_deleted = True
        if hasattr(local, 'updated_at'):
            dt = _iso_to_dt(remote_updated)
            if dt is not None:
                local.updated_at = dt
        return 1

    # 正常内容合并
    if local is None:
        # INSERT：显式指定 id
        local = model(id=rid)
        for k, v in remote_data.items():
            if hasattr(model, k):
                # 字符串日期转回 datetime（适用于 created_at / updated_at 等）
                if isinstance(v, str) and k.endswith('_at'):
                    dt = _iso_to_dt(v)
                    if dt is not None:
                        v = dt
                setattr(local, k, v)
        session.add(local)
    else:
        # UPDATE：只覆盖 remote_data 里有的字段（保留本地其他字段）
        for k, v in remote_data.items():
            if not hasattr(model, k):
                continue
            if k in _EXCLUDE_COLUMNS:
                continue
            if isinstance(v, str) and k.endswith('_at'):
                dt = _iso_to_dt(v)
                if dt is not None:
                    v = dt
            setattr(local, k, v)
        if hasattr(local, 'is_deleted'):
            local.is_deleted = False  # 远端不是墓碑 → 复活（LWW，远端更新所以覆盖）
    if hasattr(local, 'updated_at'):
        dt = _iso_to_dt(remote_updated)
        if dt is not None:
            local.updated_at = dt
    return 1


def _import_post_tags(session, remote_records: Iterable[Dict[str, Any]]) -> int:
    """合并 Post↔Tag 关联；如果 post_id/tag_id 都在本地存在才挂。"""
    import app as _app_module
    applied = 0
    # 先用 app 层挂关系：session.execute(insert(post_tags)...) 更直接
    post_tags = _app_module.post_tags
    for rec in remote_records:
        if bool(rec.get('is_deleted', False)):
            # 关系删除（未来支持）
            continue
        d = rec.get('data') or {}
        pid, tid = d.get('post_id'), d.get('tag_id')
        if not pid or not tid:
            continue
        # 先判断两端都在本地存在
        if session.query(_app_module.Post).get(pid) is None:
            continue
        if session.query(_app_module.Tag).get(tid) is None:
            continue
        # 是否已存在
        exists = session.query(post_tags).filter(
            post_tags.c.post_id == pid,
            post_tags.c.tag_id == tid).first() is not None
        if exists:
            continue
        try:
            session.execute(post_tags.insert().values(post_id=pid, tag_id=tid))
            applied += 1
        except Exception:
            # UNIQUE 冲突兜底
            pass
    return applied


def _import_site_settings(session, remote_records: Iterable[Dict[str, Any]]) -> int:
    """合并 SiteSetting 记录；app 没定义 SiteSetting 模型时直接跳过。"""
    import app as _app_module
    model = getattr(_app_module, 'SiteSetting', None)
    if model is None:
        return 0
    applied = 0
    for rec in remote_records:
        try:
            applied += _apply_one_record(session, model, rec)
        except Exception:
            import logging
            logging.getLogger('sync_engine').exception(
                '合并SiteSetting失败 id=%s', rec.get('id'))
    session.flush()
    return applied


# ============================================================
# 4. sync_state.json 读写
#
# 状态分两类游标：
#   push_cursors[entity]：本地推送到远端时，上一次推出去的最大 updated_at。
#                         下一轮 PUSH 时，since = push_cursors[entity]（只推更新的）。
#   pull_cursors[entity]：本地上次从远端读到的最大 updated_at。
#                         下一轮 PULL 时，只处理 updated_at > pull_cursors 的记录。
#                         这样 LWW 比较"远端没更晚的 → applied=0"就不意味着没新数据，
#                         而是先被增量 since 过滤掉了，节省 DB 比较。
# ============================================================
_STATE_VERSION = 2


def _split_state(raw: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    解析远端或本地 state，返回 (push_cursors, pull_cursors)。
    兼容 v1（单 cursors 字典）：
      v1 只记录了"上次同步到的水位"，无法区分 push / pull，此时
      - push_cursors 用原 cursors：since = 旧水位保证不重推老数据；
      - pull_cursors 置空：拉取 since 为空 → 全量 LWW 过滤（安全，因为 LWW 会 skip）。
    """
    if not raw:
        return {}, {}
    version = raw.get('version', 1)
    push_c = raw.get('push_cursors') or {}
    pull_c = raw.get('pull_cursors') or {}
    if version == 1 or (not push_c and not pull_c):
        legacy = raw.get('cursors') or {}
        push_c = dict(legacy) if not push_c else push_c
        # pull_c 保持空（安全）
    return (
        {k: str(v) for k, v in push_c.items() if v is not None},
        {k: str(v) for k, v in pull_c.items() if v is not None},
    )


def load_state(path: str, reset: Optional[Dict[str, bool]] = None
               ) -> Tuple[Dict[str, str], Dict[str, str]]:
    """读取本地 state。

    Args:
        path: state 文件路径。
        reset: 可选重置参数。形如 {'push': True, 'pull': False}。
               - reset['push'] = True → push_cursors 返回空（等价于“从未 push 过”，
                 下次 PUSH 时 since=None，会全量导出本地记录。）
               - reset['pull'] = True → pull_cursors 返回空（等价于“从未 pull 过”，
                 下次 PULL 时 since=None，会全量 LWW 比较远端 jsonl。）
    """
    reset = reset or {}
    if not path or not os.path.isfile(path):
        return {}, {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            obj = json.load(f)
    except Exception:
        return {}, {}
    push_c, pull_c = _split_state(obj)
    if reset.get('push'):
        push_c = {}
    if reset.get('pull'):
        pull_c = {}
    return push_c, pull_c


def save_state(path: str, push_cursors: Dict[str, str],
               pull_cursors: Dict[str, str]) -> None:
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({
                'version': _STATE_VERSION,
                'push_cursors': push_cursors,
                'pull_cursors': pull_cursors,
            }, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, path)
    except Exception:
        import logging
        logging.getLogger('sync_engine').exception('保存 sync_state 失败')


# ============================================================
# 5. 远端 Adapter 抽象（本地目录 / Gitee REST 都实现同一接口）
# ============================================================
class RemoteAdapter:
    """远端同步存储的抽象接口。"""

    def read_jsonl(self, entity_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def write_jsonl(self, entity_name: str,
                    records: List[Dict[str, Any]]) -> None:
        """用 records 整体覆盖写某个实体文件（一般我们是先 Merge 再整体写）。"""
        raise NotImplementedError

    def read_state(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """返回 (push_cursors, pull_cursors)；任一空表示没记录过，首次用 since='' 全量。"""
        raise NotImplementedError

    def write_state(self, push_cursors: Dict[str, str],
                    pull_cursors: Dict[str, str]) -> None:
        raise NotImplementedError

    def list_attachments(self) -> List[str]:
        """列出远端 sync_attachments/ 下所有相对路径（如 avatars/x.png, bg/y.png）。失败返回 []。"""
        return []

    def download_attachment(self, subpath: str) -> Optional[bytes]:
        """下载单个附件二进制；不存在或失败返回 None。"""
        return None

    def upload_attachment(self, subpath: str, data: bytes,
                          sha256_hex: str = '') -> bool:
        """上传单个附件二进制；相同 sha 或 size 可免传。返回是否真的写入。"""
        raise NotImplementedError

    def attachment_digest(self, subpath: str) -> str:
        """远端附件摘要（sha256/size 混合即可）；未知返回 ''。用于快速比较免下载。"""
        return ''

    def health_check(self) -> Tuple[bool, str]:
        """连通性自检；返回 (ok, 原因)。"""
        return False, '未实现'


# ------------------------------------------------------------
# 5a) 本地目录 Adapter（测试 + 未来单机备份都能用）
# ------------------------------------------------------------
class LocalDirRemoteAdapter(RemoteAdapter):
    def __init__(self, root: str, prefix: str = 'blog-backup'):
        self.root = root
        self.prefix = prefix.strip('/')
        self.data_dir = os.path.join(root, *(x for x in self.prefix.split('/') if x),
                                     'sync_data')
        self.attach_dir = os.path.join(root, *(x for x in self.prefix.split('/') if x),
                                       'sync_attachments')
        self.state_path = os.path.join(root, *(x for x in self.prefix.split('/') if x),
                                       'sync_state.json')
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.attach_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)

    def _entity_path(self, entity_name: str) -> str:
        return os.path.join(self.data_dir, entity_name + '.jsonl')

    def _attach_path(self, subpath: str) -> str:
        sp = subpath.strip('/').replace('\\', '/')
        sp = '/'.join(p for p in sp.split('/') if p and p not in ('.', '..'))
        return os.path.join(self.attach_dir, *sp.split('/'))

    def read_jsonl(self, entity_name):
        p = self._entity_path(entity_name)
        if not os.path.isfile(p):
            return []
        out = []
        with open(p, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
        return out

    def write_jsonl(self, entity_name, records):
        # 先做远端侧合并：LWW 合并旧 records + 新 records → 整体写文件
        old = {r.get('id'): r for r in self.read_jsonl(entity_name)}
        for r in records:
            rid = r.get('id')
            if rid is None:
                continue
            prev = old.get(rid)
            if prev is None:
                old[rid] = r
                continue
            # LWW：新的赢
            if _cmp_iso(r.get('updated_at', '') or '',
                        prev.get('updated_at', '') or '') >= 0:
                old[rid] = r
        # 落盘
        p = self._entity_path(entity_name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            for rid in sorted(old.keys(), key=lambda x: str(x)):
                f.write(json.dumps(old[rid], ensure_ascii=False, sort_keys=True))
                f.write('\n')
        os.replace(tmp, p)

    def read_state(self):
        if not os.path.isfile(self.state_path):
            return {}, {}
        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                obj = json.load(f)
        except Exception:
            return {}, {}
        return _split_state(obj)

    def write_state(self, push_cursors, pull_cursors):
        tmp = self.state_path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({
                'version': _STATE_VERSION,
                'push_cursors': push_cursors,
                'pull_cursors': pull_cursors,
            }, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, self.state_path)

    # ---- 附件 ----
    def list_attachments(self):
        if not os.path.isdir(self.attach_dir):
            return []
        out = []
        for root, _, files in os.walk(self.attach_dir):
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, self.attach_dir).replace('\\', '/')
                out.append(rel)
        return out

    def download_attachment(self, subpath):
        p = self._attach_path(subpath)
        if not os.path.isfile(p):
            return None
        try:
            with open(p, 'rb') as f:
                return f.read()
        except Exception:
            return None

    def upload_attachment(self, subpath, data, sha256_hex=''):
        p = self._attach_path(subpath)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        # 若摘要相同就不写（免 IO）
        if os.path.isfile(p) and sha256_hex:
            try:
                with open(p, 'rb') as f:
                    existing = hashlib.sha256(f.read()).hexdigest()
                if existing == sha256_hex:
                    return False
            except Exception:
                pass
        tmp = p + '.tmp'
        with open(tmp, 'wb') as f:
            f.write(data)
        os.replace(tmp, p)
        return True

    def attachment_digest(self, subpath):
        p = self._attach_path(subpath)
        if not os.path.isfile(p):
            return ''
        try:
            sz = os.path.getsize(p)
            with open(p, 'rb') as f:
                head = f.read(4096)
            return '%d:%s' % (sz, hashlib.sha256(head).hexdigest())
        except Exception:
            return ''

    def health_check(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            touch = os.path.join(self.data_dir, '.health')
            with open(touch, 'w', encoding='utf-8') as f:
                f.write('ok')
            try:
                os.remove(touch)
            except Exception:
                pass
            return True, 'OK'
        except Exception as e:
            return False, str(e)


# ============================================================
# 6. 同步引擎（拉 → 合并 → 推 → 保存状态 + 附件同步）
# ============================================================
_ATTACH_DIR_CANDIDATES = ('avatars', 'bg', 'post_images')  # 相对 DATA_DIR/uploads 的子目录


def _node_provenance_id(state_path: str) -> str:
    """稳定标识本节点（用于 prov 字段，自证来源）。第一次同步时生成保存在 state 同目录。"""
    try:
        base = os.path.dirname(os.path.abspath(state_path)) if state_path else '.'
        f = os.path.join(base, '.sync_node_id')
        if os.path.isfile(f):
            with open(f, 'r', encoding='utf-8') as fh:
                return fh.read().strip() or 'n-a'
        os.makedirs(base, exist_ok=True)
        new_id = 'node-' + hashlib.sha256(
            (str(datetime.datetime.utcnow()) + state_path).encode('utf-8')
        ).hexdigest()[:12]
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(new_id)
        return new_id
    except Exception:
        return 'node-x'


class SyncEngine:
    """
    标准同步流程（run_sync）：
      1. 读取两端游标：本地 load_state()=(push_c, pull_c)，远端 adapter.read_state()=(push_c, pull_c)
      2. PULL：对每个 entity，since = 本地上次 pull 的游标；从远端 read_jsonl(entity)
         再用 only_since_iso=since 做预过滤 → import_records(LWW) → applied=pulled[entity]
         更新本地 pull_cursors = max(已读 records 的 updated_at)
      3. PUSH：对每个 entity，since = 本地上次 push 的游标；
         export_all_records(session, entity, since_iso=since, provenance=节点ID)
         → write_jsonl（远端侧 LWW 合并，避免覆盖）
         更新本地 push_cursors = max(本轮导出 updated_at)
         远端 push_cursors 和它保持一致；远端 pull_cursors 不动（它是对面节点的事情）
      4. Phase D：附件双向同步（push local uploads/ 新文件 → 远端；pull 远端新文件 → 本地）
      5. Phase E：save_state 与 adapter.write_state 分别持久化 (push, pull)
    """

    def __init__(self, session, adapter: RemoteAdapter, state_path: str,
                 data_dir: Optional[str] = None):
        self.session = session
        self.adapter = adapter
        self.state_path = state_path
        # data_dir 没传时，尝试通过 Flask app.config 解析
        if data_dir is None:
            try:
                import app as _a
                data_dir = getattr(getattr(_a, 'Config', None), 'DATA_DIR', None)
            except Exception:
                data_dir = None
        self.data_dir = data_dir or (os.path.dirname(os.path.abspath(state_path))
                                     if state_path else None)
        self._node_id = _node_provenance_id(state_path)

    # ---------------- 工具：找出一组记录的最大 updated_at ----------------
    @staticmethod
    def _max_updated(records, previous=''):
        """返回 records 中最大的 updated_at；records 为空时返回空串。

        注意：previous 参数不再作为起点（旧实现把 previous 当 m 的初值，
        在 records 为空时会返回 previous，导致 cursor 被错误推进到 since
        值，把本地更早的记录永远挡在 PUSH 之外）。空 records → 空串，
        让调用方判断"本轮确实没有变更"，cursor 保持原值。
        """
        m = ''
        for r in records:
            ts = r.get('updated_at', '') or ''
            if ts and (not m or ts > m):
                m = ts
        return m

    # ---------------- 附件镜像：列出本地 uploads/* 子目录 ----------------
    def _list_local_attachments(self) -> List[Tuple[str, str]]:
        """
        返回 [(rel_subpath, abs_local_path)]。
        rel_subpath 形如 avatars/abc.png、bg/xyz.jpg，对应远端 sync_attachments/<rel>。
        """
        if not self.data_dir:
            return []
        upload_root = os.path.join(self.data_dir, 'uploads')
        if not os.path.isdir(upload_root):
            return []
        result: List[Tuple[str, str]] = []
        for sub in _ATTACH_DIR_CANDIDATES:
            base = os.path.join(upload_root, sub)
            if not os.path.isdir(base):
                continue
            for root, _, files in os.walk(base):
                for fn in files:
                    if fn.lower().endswith(('.db', '.tmp', '.swp')):
                        continue
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, upload_root).replace('\\', '/')
                    result.append((rel, full))
        return result

    def _sync_attachments_push(self) -> Tuple[int, int]:
        """把本地新增/变更的附件推到远端。返回 (上传数, 跳过数)。"""
        pushed = skipped = 0
        for rel, full in self._list_local_attachments():
            try:
                with open(full, 'rb') as f:
                    data = f.read()
                digest = hashlib.sha256(data).hexdigest()
                remote_digest = self.adapter.attachment_digest(rel)
                # 快速命中：远端已有同名且 hash 一致 → 跳过
                if remote_digest and remote_digest.endswith(':' + digest):
                    skipped += 1
                    continue
                # 大小粗略比对（省传输）
                if remote_digest and ':' in remote_digest:
                    try:
                        sz_before = int(remote_digest.split(':', 1)[0])
                        if sz_before == len(data):
                            # 下载头字节算 hash 比较
                            rem_head = self.adapter.download_attachment(rel)
                            if rem_head is not None and hashlib.sha256(rem_head).hexdigest() == digest:
                                skipped += 1
                                continue
                    except Exception:
                        pass
                wrote = self.adapter.upload_attachment(rel, data, sha256_hex=digest)
                pushed += 1 if wrote else 0
            except Exception:
                import logging
                logging.getLogger('sync_engine').exception('附件推送失败 rel=%s', rel)
        return pushed, skipped

    def _sync_attachments_pull(self) -> int:
        """把远端新增的附件拉到本地 uploads/<sub>。返回下载数。"""
        if not self.data_dir:
            return 0
        upload_root = os.path.join(self.data_dir, 'uploads')
        os.makedirs(upload_root, exist_ok=True)
        pulled_count = 0
        remote_list = self.adapter.list_attachments() or []
        local_map = dict(self._list_local_attachments())  # {rel:abs}
        for rel in remote_list:
            safe_rel = rel.replace('\\', '/').strip('/')
            safe_rel = '/'.join(p for p in safe_rel.split('/') if p and p not in ('.', '..'))
            if not safe_rel:
                continue
            sub = safe_rel.split('/')[0]
            if sub not in _ATTACH_DIR_CANDIDATES:
                continue
            local_path = os.path.join(upload_root, *safe_rel.split('/'))
            if os.path.isfile(local_path):
                try:
                    with open(local_path, 'rb') as f:
                        local_sha = hashlib.sha256(f.read()).hexdigest()
                    rem_head = self.adapter.download_attachment(rel)
                    if rem_head is not None and hashlib.sha256(rem_head).hexdigest() == local_sha:
                        continue
                except Exception:
                    pass
            data = self.adapter.download_attachment(rel)
            if data is None:
                continue
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            tmp = local_path + '.tmp'
            with open(tmp, 'wb') as f:
                f.write(data)
            os.replace(tmp, local_path)
            pulled_count += 1
        return pulled_count

    def run_sync(self, mode: str = 'both',
                 reset: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
        """执行一次同步。

        Args:
            mode: 运行模式
                - 'both'（默认）：先 PULL 再 PUSH，双向合并。
                - 'pull_only' ：只做 PULL（远端 → 本地，LWW 合并，不覆盖更更新的本地数据）。
                                用于「立即恢复 / 从 Gitee 拉下来」按钮。
                - 'push_only' ：只做 PUSH（本地 → 远端，只推更新内容）。
                                用于「立即备份 / 只更新到 Gitee」按钮。
            reset: 可选重置游标。字典：{'push': True, 'pull': True}。
                   - reset['push']=True：本端 push_cursors 清空（重新全量比对后再推）。
                   - reset['pull']=True：本端 pull_cursors 清空（重新全量 LWW 比对远端）。

        Returns:
            字典摘要（同旧版，含 pushed/pulled/attachments/cursors）。
        """
        mode = str(mode or 'both').strip().lower()
        if mode not in ('both', 'pull_only', 'push_only'):
            raise ValueError(
                'run_sync mode 必须是 both/pull_only/push_only，实际=%r' % mode)

        pushed: Dict[str, int] = {e: 0 for e in SYNCABLE_ENTITY_NAMES}
        pulled: Dict[str, int] = {e: 0 for e in SYNCABLE_ENTITY_NAMES}

        do_pull = mode in ('both', 'pull_only')
        do_push = mode in ('both', 'push_only')

        # 本地 state = (push_cursors, pull_cursors) ；两侧独立
        local_push_c, local_pull_c = load_state(self.state_path, reset=reset)
        # 远端 state = 它自己本地的 push/pull cursors（在分布式里，
        #   远端 push_cursors = 任何节点上次推到远端时的 max；
        #   远端 pull_cursors 远端不使用，只用来兼容 v1 时填 cursors 做兜底）
        remote_push_c, remote_pull_c = self.adapter.read_state()

        new_local_push_c: Dict[str, str] = dict(local_push_c)
        new_local_pull_c: Dict[str, str] = dict(local_pull_c)
        new_remote_push_c: Dict[str, str] = dict(remote_push_c)

        # ============================================================
        # Phase A: PULL（远端 → 本地）
        # since = 我们本地上次 pull 的 max；空=首次/安全模式，全量 LWW 比较。
        # 注意：PULL 阶段只推进本端 pull_cursors，不动远端 push_cursors
        # （远端 push_cursors 是"远端曾经被任何节点推过的 max"，应由 PUSH
        # 阶段在真正推送内容时才推进。否则 A 端 PULL 后 cursor 被错误
        # 推到远端记录 max，A 端本地更早的记录（如冷备份恢复的历史文章）
        # 永远推不上去——这是用户反馈"同步后没加载出来"的根因之一。）
        # ============================================================
        if do_pull:
            for entity in SYNCABLE_ENTITY_NAMES:
                remote_records = self.adapter.read_jsonl(entity)
                pull_since = local_pull_c.get(entity, '') or ''
                applied = import_records(self.session, entity, remote_records,
                                         only_since_iso=pull_since)
                pulled[entity] = applied
                # 本轮远端读到的最大时间戳（只在 records 非空时推进 pull_cursor）
                max_r = self._max_updated(remote_records)
                if max_r and (not new_local_pull_c.get(entity, '')
                              or max_r > new_local_pull_c[entity]):
                    new_local_pull_c[entity] = max_r

            try:
                self.session.commit()
            except Exception:
                self.session.rollback()
                raise

        # ============================================================
        # Phase B: PUSH（本地 → 远端）
        # since = 本地上次 push 的 max（不用远端 push_cursors 兜底）。
        # 远端 LWW 合并保证不会重复覆盖：相同 updated_at 的记录会被跳过。
        # 这样设计：A 端从未 PUSH 过（local push_cursor 空）→ 全量推；
        # A 端 PULL 后获得远端数据但本地从未真正 PUSH → local push_cursor
        # 仍为空 → 下次 PUSH 走全量，把本地所有"远端没有的"记录都推上去。
        # ============================================================
        if do_push:
            for entity in SYNCABLE_ENTITY_NAMES:
                since_iso = local_push_c.get(entity, '') or ''
                local_records = export_all_records(self.session, entity,
                                                   since_iso=since_iso,
                                                   provenance=self._node_id)
                if local_records:
                    self.adapter.write_jsonl(entity, local_records)
                pushed[entity] = len(local_records)
                # 只有本轮真正导出了记录才推进 cursor（避免空轮把 cursor
                # 误设到 since 值，挡掉未来同时间段的记录）
                max_l = self._max_updated(local_records)
                if max_l:
                    if (not new_local_push_c.get(entity, '')
                            or max_l > new_local_push_c[entity]):
                        new_local_push_c[entity] = max_l
                    if (not new_remote_push_c.get(entity, '')
                            or max_l > new_remote_push_c[entity]):
                        new_remote_push_c[entity] = max_l
                # 注：Profile/Posts 等 ORM 的 updated_at 由 DB 自动 bump；
                # 如果本轮有 applied(PULL 端有改动)但自身 PUSH 没导出来，
                # 说明合并 updated_at 与 DB 最终值一致，没问题；若用户反馈
                # 还是拉不到，打开日志看 PROV 字段就能定位谁推送的。

            try:
                self.session.commit()
            except Exception:
                self.session.rollback()
                raise

        # ============================================================
        # Phase C&D: 附件
        #   - push_only：只走附件 push
        #   - pull_only：只走附件 pull
        #   - both：两端都走
        # ============================================================
        att_pull_n = self._sync_attachments_pull() if do_pull else 0
        if do_push:
            att_push_n, att_skip_n = self._sync_attachments_push()
        else:
            att_push_n, att_skip_n = 0, 0

        # ============================================================
        # Phase E: 持久化游标
        # ============================================================
        save_state(self.state_path, new_local_push_c, new_local_pull_c)
        # 远端只写 push_cursors（pull_cursors 是本端私事；远端 pull_cursors 保持原值即可）
        self.adapter.write_state(new_remote_push_c, remote_pull_c)

        return {
            'pushed': pushed,
            'pulled': pulled,
            'attachments': {
                'push': att_push_n, 'skipped': att_skip_n, 'pull': att_pull_n,
            },
            'push_cursors': new_local_push_c,
            'pull_cursors': new_local_pull_c,
            'cursors': new_local_push_c,   # 兼容旧代码
            'node_id': self._node_id,
        }


# ============================================================
# 7. Gitee Remote Adapter（生产用，复用 gitee_backup.py 的 API）
# ============================================================
class GiteeRemoteAdapter(RemoteAdapter):
    """使用 gitee_backup.py 已实现的 upload_bytes_to_gitee / download_bytes_from_gitee。

    注意（签名必须完全匹配 gitee_backup.py 里的函数）：
      - upload_bytes_to_gitee(settings, remote_path, content_bytes, message='...')
        返回：Tuple[bool, dict]
      - download_bytes_from_gitee(settings, remote_path)
        返回：Tuple[bool, bytes]，失败时 bytes 是错误信息。
      - test_connection(settings) → 综合连通性检查
        返回：Tuple[bool, dict{'summary':..., 'steps':[...], ...}]
    build_ssl_context 在上述函数内部调用，调用方不需要再显式传。
    """

    def __init__(self, settings: Dict[str, Any]):
        # settings 来自 gitee_backup.load_settings() 或 /admin/save_settings
        self.settings = dict(settings)
        # 默认 path_prefix 归一化
        prefix = (self.settings.get('path_prefix') or '').strip()
        if not prefix:
            prefix = 'blog-backup'
        prefix = prefix.strip('/')
        # 防止双重嵌套（blog-backup/blog-backup）
        first = prefix.split('/')[0]
        if first and prefix.count('/') > 0 and prefix.startswith(first + '/' + first):
            prefix = '/'.join(prefix.split('/')[1:])
        self.prefix = prefix

    # ---------- 内部：把 <prefix>/<sub_path> 读出/写入 ----------
    def _full_path(self, sub_path: str) -> str:
        sub = sub_path.lstrip('/')
        return self.prefix + '/' + sub if self.prefix else sub

    def _download(self, path: str) -> Optional[bytes]:
        from gitee_backup import download_bytes_from_gitee
        full = self._full_path(path)
        try:
            ok, data = download_bytes_from_gitee(self.settings, full)
            if not ok:
                return None
            return data if isinstance(data, bytes) else bytes(data)
        except Exception:
            return None

    def _upload(self, path: str, data: bytes, message: str = 'sync') -> None:
        from gitee_backup import upload_bytes_to_gitee
        full = self._full_path(path)
        ok, info = upload_bytes_to_gitee(self.settings, full, data, message=message)
        if not ok:
            raise RuntimeError('Gitee 上传失败 %s -> %s' % (full, info))

    # ---------- 接口实现 ----------
    def read_jsonl(self, entity_name):
        raw = self._download('sync_data/%s.jsonl' % entity_name)
        if not raw:
            return []
        out = []
        for line in raw.decode('utf-8', errors='replace').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                pass
        return out

    def write_jsonl(self, entity_name, records):
        # 远端 LWW 合并（同 LocalDirRemoteAdapter）
        old = {r.get('id'): r for r in self.read_jsonl(entity_name)}
        for r in records:
            rid = r.get('id')
            if rid is None:
                continue
            prev = old.get(rid)
            if prev is None:
                old[rid] = r
                continue
            if _cmp_iso(r.get('updated_at', '') or '',
                        prev.get('updated_at', '') or '') >= 0:
                old[rid] = r
        lines = []
        for rid in sorted(old.keys(), key=lambda x: str(x)):
            lines.append(json.dumps(old[rid], ensure_ascii=False, sort_keys=True))
        body = ('\n'.join(lines) + '\n').encode('utf-8') if lines else b''
        self._upload('sync_data/%s.jsonl' % entity_name, body,
                     message='sync: %s (+%d)' % (entity_name, len(records)))

    def read_state(self):
        raw = self._download('sync_state.json')
        if not raw:
            return {}, {}
        try:
            obj = json.loads(raw.decode('utf-8', errors='replace'))
        except Exception:
            return {}, {}
        return _split_state(obj)

    def write_state(self, push_cursors, pull_cursors):
        body = json.dumps({
            'version': _STATE_VERSION,
            'push_cursors': push_cursors,
            'pull_cursors': pull_cursors,
        }, ensure_ascii=False, indent=2, sort_keys=True).encode('utf-8')
        self._upload('sync_state.json', body, message='sync: state v%d' % _STATE_VERSION)

    # ---------- 附件（Gitee 用 contents 接口当文件系统；list 用递归遍历）----------
    def _gitee_list_dir(self, sub_dir: str) -> List[str]:
        """
        列出 <prefix>/<sub_dir>/ 下所有文件（递归，返回相对 <sub_dir>/ 的相对路径）。
        失败返回空列表（不强依赖 list 接口，失败时拉取端退化为 0 附件即可，不影响元数据同步）。
        """
        from gitee_backup import _json_request, normalize_settings
        try:
            s = normalize_settings(self.settings)
        except Exception:
            return []
        token = s.get('token') or ''
        owner = s.get('owner') or ''
        repo = s.get('repo') or ''
        if not (token and owner and repo):
            return []
        base_dir = (self.prefix + '/' + sub_dir.strip('/')).strip('/')

        # 用 GET /repos/{owner}/{repo}/contents/{path} 递归；文件夹返回 array
        results: List[str] = []
        stack: List[str] = [base_dir]
        safety = 0
        while stack and safety < 300:
            safety += 1
            d = stack.pop(0)
            import urllib.parse as _q
            url = ('https://gitee.com/api/v5/repos/%s/%s/contents/%s?access_token=%s'
                   % (_q.quote(owner), _q.quote(repo), _q.quote(d), _q.quote(token)))
            try:
                status, obj, _ = _json_request('GET', url, timeout=15)
            except Exception:
                continue
            if status != 200 or not isinstance(obj, list):
                # 404 = 该目录尚未创建，正常
                continue
            for entry in obj:
                if not isinstance(entry, dict):
                    continue
                etype = entry.get('type') or 'file'
                path = entry.get('path') or ''
                if not path:
                    continue
                if etype == 'dir':
                    stack.append(path)
                elif etype == 'file':
                    # 把 prefix/sub_dir/xxx 变成 xxx
                    prefix_full = base_dir.rstrip('/') + '/'
                    if path.startswith(prefix_full):
                        rel = path[len(prefix_full):]
                    else:
                        rel = os.path.basename(path)
                    rel = rel.replace('\\', '/').strip('/')
                    if rel:
                        results.append(rel)
        return results

    def list_attachments(self):
        return self._gitee_list_dir('sync_attachments')

    def download_attachment(self, subpath):
        sub = subpath.strip('/').replace('\\', '/')
        if not sub:
            return None
        return self._download('sync_attachments/' + sub)

    def upload_attachment(self, subpath, data, sha256_hex=''):
        sub = subpath.strip('/').replace('\\', '/')
        if not sub:
            return False
        # 相同 sha 且远端存在且大小一致 → 直接跳过
        try:
            from gitee_backup import _get_existing_sha, build_ssl_context
            remote_rel = 'sync_attachments/' + sub
            existing, _ = _get_existing_sha(self.settings, self._full_path(remote_rel))
            if existing and sha256_hex:
                old = self._download(remote_rel)
                if old is not None and hashlib.sha256(old).hexdigest() == sha256_hex:
                    return False
        except Exception:
            pass
        try:
            self._upload('sync_attachments/' + sub, data,
                         message='sync: attach %s' % sub.split('/')[-1])
            return True
        except Exception:
            raise

    def attachment_digest(self, subpath):
        data = self.download_attachment(subpath)
        if not data:
            return ''
        return '%d:%s' % (len(data), hashlib.sha256(data).hexdigest())

    def health_check(self):
        from gitee_backup import test_connection
        try:
            ok, info = test_connection(self.settings)
            msg = ''
            if isinstance(info, dict):
                msg = info.get('summary') or info.get('error') or str(info)
            else:
                msg = str(info)
            return bool(ok), (msg or ('连接成功' if ok else '配置未就绪'))[:300]
        except Exception as e:
            return False, str(e)[:300]
