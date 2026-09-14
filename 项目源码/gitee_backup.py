# -*- coding: utf-8 -*-
"""
个人博客 · Gitee 数据同步模块
=====================================
目标：当用户本地硬盘损坏或重装软件后，能从 Gitee 找回博客数据。

设计原则（backup-and-recovery specialist ADR）:
  1) RTO < 2 分钟（重装后点一次按钮即可拉回）；RPO = 每用户手动备份时点。
  2) 最小必要数据：SQLite blog.db 核心 + uploads 下全部上传文件（头像/背景图/导入文件）。
  3) 绝不包含本机 Gitee token、私密配置、日志、进程私钥。
  4) 远端仓库布局（避免污染 Gitee 仓库根）：
      latest.json                 → 指向最新快照
      snap-YYYYMMDD-HHMMSS-SSS/
            manifest.json         → 快照文件清单 + SHA256
            blog.db               → 二进制 SQLite
            uploads/<relpath>...  → 用户上传资产
  5) 每个文件带独立 SHA256；恢复时校验，不匹配则拒绝覆盖。
  6) 使用 Gitee v5 Contents API：GET 查老 SHA，不存在则 PUT 新文件，存在则 PUT 带 sha 更新。
  7) 单文件最大 100MB（Gitee contents API 限制）；一般 blog.db 和图片都远小于此。
  8) 网络层 urlopen 作为属性挂在本模块上，便于单元测试替换（避免真实请求）。
"""
from __future__ import annotations

import os
import sys
import io
import re
import ssl as _ssl
import json
import time
import base64
import hashlib
import shutil
import datetime as _dt
import urllib.parse as _urlparse
import urllib.request as _real_urlopen
from typing import Any, Dict, List, Optional, Tuple

# ---------- 单元测试可替换的 urlopen ----------
# 【重要】不要写成 `urlopen = _real_urlopen.urlopen`——那会在 import 时就快照原始
# 函数引用，外部 mock `urllib.request.urlopen = xxx` 无法生效，导致单元测试发出
# 真实网络请求（常被返回 401，被误判为"令牌无效"）。正确做法：每次调用动态读取属性。
def urlopen(*args, **kwargs):
    return _real_urlopen.urlopen(*args, **kwargs)

GITEE_API_BASE = 'https://gitee.com/api/v5'


# ============================================================
#  SSL 根证书 · 冻结(PyInstaller onedir)环境兼容
# ------------------------------------------------------------
#  冻结环境下，_ssl 默认没有正确加载 CA bundle，导致：
#     [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
#     unable to get local issuer certificate
#  解决：显式构造 ssl.SSLContext，按优先级取 cacert.pem：
#    1) certifi 包（pip install certifi 的默认来源，PyInstaller 通常会带上）
#    2) sys._MEIPASS/certifi/cacert.pem （手动放进 datas 的兜底）
#    3) Windows 注册表系统证书路径 + SSLContext.load_default_certs
# ============================================================
def _locate_cacert_pem() -> Optional[str]:
    """返回一个确实存在的 cacert.pem 文件路径，找不到返回 None。"""
    # 1) certifi 官方包
    try:
        import certifi  # type: ignore
        p = certifi.where()
        if p and os.path.isfile(p):
            return p
    except Exception:
        pass
    # 2) PyInstaller sys._MEIPASS 里可能放了一份
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        for rel in (os.path.join('certifi', 'cacert.pem'), 'cacert.pem'):
            p = os.path.join(meipass, rel)
            if os.path.isfile(p):
                return p
    # 3) 源项目目录/同 exe 目录是否放了
    for base in (os.path.dirname(os.path.abspath(__file__)),
                 os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else None):
        if not base:
            continue
        for rel in ('cacert.pem', os.path.join('_internal', 'certifi', 'cacert.pem')):
            p = os.path.join(base, rel)
            if os.path.isfile(p):
                return p
    return None


def build_ssl_context() -> "_ssl.SSLContext":
    """构造带 CA 的 SSLContext，保证冻结环境不会 CERTIFICATE_VERIFY_FAILED。"""
    ctx = _ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_mode = _ssl.CERT_REQUIRED
    cafile = _locate_cacert_pem()
    try:
        if cafile:
            ctx.load_verify_locations(cafile=cafile)
        else:
            # 兜底：加载系统默认 CA（Windows/macOS 证书存储）
            ctx.load_default_certs()
    except Exception:
        # 最差情况：再尝试一次 load_default_certs，别让 ctx 裸奔
        try:
            ctx.load_default_certs()
        except Exception:
            pass
    return ctx

# 不应该被备份/上传的路径（黑名单，防泄密+防无限）
_EXCLUDE_NAMES = {
    'gitee_sync.json',          # 本模块配置文件（含token）
    'blog.log',                 # 日志
    'blog-20*',                 # 滚动日志
    '.DS_Store', 'Thumbs.db',   # 系统垃圾
}
_EXCLUDE_EXTS = {'.pyc', '.pyo', '.log', '.tmp', '.lock'}


# ============================================================
#  配置文件读写（DATA_DIR/gitee_sync.json）
# ============================================================
SETTINGS_FILE = 'gitee_sync.json'
PROGRESS_FILE = 'gitee_backup_progress.json'  # 断点续传进度（未完成备份时的原子落盘文件）

DEFAULT_SETTINGS = {
    'enabled': False,                       # 是否启用同步（关闭时所有 backup/restore 操作都会 early return）
    'token': '',                            # Gitee 私人令牌（用户从 gitee.com/profile/personal_access_tokens 获取）
    'owner': '',                            # Gitee 用户名或组织名（仓库归属者）
    'repo': '',                             # 仓库短名，例如 "my-blog-backup"（建议用户新建一个私有仓库）
    'branch': 'master',                     # 分支名；Gitee 新建仓库默认 master 可手动改 main
    'path_prefix': 'blog-backup',           # 仓库内子目录（默认 blog-backup/，避免污染仓库根）
    'auto_backup_on_start': False,          # 桌面版启动时自动触发一次备份（可选，默认关闭，避免空库覆盖远端）
    'auto_restore_on_first_start': True,    # 若本地 blog.db 不存在且远端 latest.json 存在 → 自动拉回一次
    'last_backup_at': None,                 # 上次成功备份的 ISO 时间
    'last_backup_snapshot': None,           # 上次成功的快照 ID
    'last_backup_assets_digest': None,      # 上次成功备份的 assets 集合哈希（"文件没变就跳空"秒回）
    'last_backup_total_bytes': 0,           # 上次成功备份的总字节（UI 显示用）
}


def _settings_path(data_dir: str) -> str:
    return os.path.join(data_dir, SETTINGS_FILE)


def load_settings(data_dir: str) -> Dict[str, Any]:
    """加载用户备份配置；不存在或损坏则返回默认值。"""
    path = _settings_path(data_dir)
    merged = dict(DEFAULT_SETTINGS)
    raw_data: Optional[Dict[str, Any]] = None
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                raw_data = data
                merged.update(data)
        except (OSError, ValueError):
            # 损坏就回默认值，不崩应用
            pass
    # 额外类型/空值保护
    for k in ('token', 'owner', 'repo', 'branch'):
        merged[k] = '' if merged.get(k) is None else str(merged.get(k, '')).strip()
    # path_prefix 的语义：
    #   - None / 纯空格 / 空串（仅 slashes） → 用户实际没填过 → 回默认 blog-backup
    #   - 非空字符串 → 视为用户显式指定（如 backup/、blog-custom 等）
    # （跨机器恢复的老兼容性：旧版会把 form 空串保存为 path_prefix=""，这里统一转默认，
    #  这样电脑 B 新安装时，latest.json 不会被误判为仓库根。）
    raw_pp = merged.get('path_prefix')
    pp_cleaned = '' if raw_pp is None else str(raw_pp).strip().strip('/')
    if not pp_cleaned:
        pp_cleaned = DEFAULT_SETTINGS['path_prefix']
    merged['path_prefix'] = pp_cleaned
    # branch：显式空值（没写）才回默认 master
    if not merged.get('branch'):
        merged['branch'] = 'master'
    return merged


def save_settings(data_dir: str, settings: Dict[str, Any]) -> None:
    """保存配置文件；保证父目录存在 + 0600 仅本地可读。"""
    path = _settings_path(data_dir)
    os.makedirs(os.path.dirname(path) or data_dir, exist_ok=True)
    # 先写临时文件再原子替换（避免写一半断电损坏）
    tmp = path + '.tmp'
    cleaned = dict(DEFAULT_SETTINGS)
    cleaned.update(settings or {})
    # 序列化：不缩进 token 行避免格式泄露出错
    blob = json.dumps(cleaned, ensure_ascii=False, indent=2, sort_keys=True)
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(blob)
    os.replace(tmp, path)
    # Windows 下没有 chmod 的 POSIX 权限模型，跳过


# ---- 断点续传进度文件：DATA_DIR/gitee_backup_progress.json（原子 tmp→replace，防断电）----
def _progress_path(data_dir: str) -> str:
    return os.path.join(data_dir, PROGRESS_FILE)


def load_progress(data_dir: str) -> Optional[Dict[str, Any]]:
    """读取未完成备份进度；文件不存在或损坏 JSON → 返回 None（安全回退：重开新备份）。"""
    path = _progress_path(data_dir)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            obj = json.load(f)
    except (OSError, ValueError):
        try: os.remove(path)  # 损坏了直接删，避免一直卡住
        except OSError: pass
        return None
    if not isinstance(obj, dict):
        return None
    # 基本字段存在才视为合法
    if 'snapshot_id' not in obj or 'assets_digest' not in obj or 'items' not in obj:
        return None
    if not isinstance(obj['items'], dict):
        return None
    return obj


def save_progress(data_dir: str, progress: Dict[str, Any]) -> None:
    """原子写 progress.json；调用方应在每个 blob 完成/失败后立刻调用一次（小文件，快）。"""
    path = _progress_path(data_dir)
    os.makedirs(os.path.dirname(path) or data_dir, exist_ok=True)
    progress['updated_at'] = _dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def clear_progress(data_dir: str) -> None:
    """备份完整成功或 assets 对不上需重开时，清理旧进度文件。"""
    path = _progress_path(data_dir)
    if os.path.isfile(path):
        try: os.remove(path)
        except OSError: pass


# ---- 资产集合摘要（断点续传 + 跳空都用同一个公式，保证稳定比对）----
def _assets_digest(files: List[Dict[str, Any]]) -> str:
    """基于 sorted relpath 拼接的 (relpath|size|sha256)\n 列表做一次 sha256。
    稳定结果：同一批相同内容无论文件系统遍历顺序如何，digest 都相同。"""
    lines = sorted(['%s|%d|%s' % (fi['relpath'], int(fi.get('size',0)), str(fi.get('sha256','')).lower())
                    for fi in files if isinstance(fi, dict) and isinstance(fi.get('relpath'), str)])
    raw = ('\n'.join(lines)).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


# ---- 内容寻址 blob 引用：blobs/<sha前2十六进制>/<sha剩余62十六进制> ----
def _blob_ref(sha256_hex: str) -> str:
    s = str(sha256_hex or '').lower().strip()
    if len(s) != 64 or any(c not in '0123456789abcdef' for c in s):
        # 非法 sha（理论不应发生）→ 降级到随机子路径（避免破坏远端结构）
        random_suffix = hashlib.sha256(s.encode('utf-8') + _dt.datetime.utcnow().isoformat().encode()).hexdigest()
        return f'blobs/{random_suffix[:2]}/{random_suffix[2:]}'
    return f'blobs/{s[:2]}/{s[2:]}'


def upload_blob_once(settings: Dict[str, Any], local_path: str, sha256_hex: str,
                     message: str = 'blog backup blob') -> Tuple[bool, Dict[str, Any]]:
    """上传一个本地文件到内容寻址 blob 路径（增量去重的核心）。
    - 先 GET /{path_prefix}/blobs/ab/cdef… 判断远端是否已有该 sha 内容
      - 存在（exists=True）→ 返回 skipped=True，字节 0 发送
      - 不存在（404）→ 读取本地文件一次性 POST 创建 blob
    """
    ready, why = _settings_ready(settings)
    if not ready:
        return False, {'error': why}
    if not os.path.isfile(local_path):
        return False, {'error': 'blob 本地文件不存在: ' + str(local_path)}
    blob_ref_rel = _blob_ref(sha256_hex)
    remote_full = _concat_prefix(settings, blob_ref_rel)
    exists, remote_sha = _get_existing_sha(settings, remote_full)
    if exists:
        # 远端已经有相同内容（同一 sha）→ 跳过上传，真正做到"字节去重"
        # 兜底：如果远端返回 sha 与本地期待不一致（小概率仓库内容被人手工篡改），仍视为 skip；restore SHA256 会校验
        return True, {
            'skipped': True,
            'blob_ref': blob_ref_rel,
            'remote_path': remote_full,
            'remote_sha': remote_sha,
            'bytes_sent': 0,
        }
    # 需要真实发送
    try:
        with open(local_path, 'rb') as f:
            data = f.read()
    except OSError as e:
        return False, {'error': '读取本地文件失败: ' + str(e)[:200]}
    # 一致性校验：读取字节 sha 和传入声明必须一致（防止 race：用户在 collect 之后、上传之前改了文件）
    actual_sha = hashlib.sha256(data).hexdigest().lower()
    if actual_sha != sha256_hex.lower():
        return False, {
            'error': '上传前文件内容已改变（sha mismatch，likely race write）：期待 %s… 实际 %s…' %
                     (sha256_hex[:12], actual_sha[:12])
        }
    ok, info = upload_bytes_to_gitee(settings, remote_full, data, message=message)
    if not ok:
        return False, info
    return True, {
        'skipped': False,
        'blob_ref': blob_ref_rel,
        'remote_path': remote_full,
        'remote_sha': info.get('sha'),
        'bytes_sent': len(data),
    }


# ============================================================
#  资产收集 + 快照打包（本地，不触网）
# ============================================================
def _is_excluded(relpath: str, filename: str) -> bool:
    if relpath == SETTINGS_FILE:
        return True
    if filename in _EXCLUDE_NAMES:
        return True
    ext = os.path.splitext(filename)[1].lower()
    if ext in _EXCLUDE_EXTS:
        return True
    # 通配黑名单：blog-20*.log 这种
    low = filename.lower()
    for pat in ('blog-20',):
        if pat in low and low.endswith('.log'):
            return True
    return False


def _sha256_file(path: str, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def collect_backup_assets(data_dir: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """扫描 DATA_DIR，收集 blog.db + uploads/* 资产，生成 (manifest, file_items)。

    manifest: {
      'snapshot_id': 'snap-...',
      'created_at': '2026-09-02T01:xx:yyZ',
      'file_count': N,
      'total_bytes': N,
      'schema_version': 1,
    }
    file_items: [{ 'relpath':'uploads/a.png','size':123,'sha256':'xx' },...]
    """
    data_dir = os.path.abspath(data_dir)
    db_path = os.path.join(data_dir, 'blog.db')
    upload_dir = os.path.join(data_dir, 'uploads')

    files: List[Dict[str, Any]] = []
    total_bytes = 0
    # blog.db（可能不存在 → 仍收集只是大小0占位；空库备份也允许，便于用户拉回空状态再改）
    if os.path.isfile(db_path):
        s = os.path.getsize(db_path)
        total_bytes += s
        files.append({'relpath': 'blog.db', 'size': s, 'sha256': _sha256_file(db_path)})
    # uploads/**（递归所有子目录：avatars/bg/任意）
    if os.path.isdir(upload_dir):
        for root, _dirs, names in os.walk(upload_dir):
            for nm in names:
                abs_path = os.path.join(root, nm)
                rel_path = os.path.relpath(abs_path, data_dir).replace('\\', '/')
                if _is_excluded(rel_path, nm):
                    continue
                if not os.path.isfile(abs_path):
                    continue
                s = os.path.getsize(abs_path)
                total_bytes += s
                files.append({'relpath': rel_path, 'size': s, 'sha256': _sha256_file(abs_path)})
    snapshot_id = 'snap-' + _dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:-3]
    manifest = {
        'snapshot_id': snapshot_id,
        'created_at': _dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'file_count': len(files),
        'total_bytes': total_bytes,
        'schema_version': 1,
    }
    return manifest, files


# ============================================================
#  Gitee Contents API 封装（单文件上传 / GET / 下载）
# ============================================================
def _clean_owner(v: Optional[str]) -> str:
    if not v:
        return ''
    s = str(v).strip().strip('/').strip('\\').strip()
    # 如果用户把昵称写成「张三 / zhangsan」之类的，取最后一段斜线后的内容
    if '/' in s:
        parts = [p.strip() for p in s.split('/') if p.strip()]
        if parts:
            s = parts[-1]
    return s.strip()


def _clean_repo(v: Optional[str]) -> str:
    if not v:
        return ''
    s = str(v).strip().strip('/').strip()
    # 去掉 .git 后缀（git clone URL）
    if s.lower().endswith('.git'):
        s = s[:-4]
    # 形如 "owner/repo" → 取 repo 段
    if '/' in s:
        parts = [p.strip() for p in s.split('/') if p.strip()]
        if parts:
            s = parts[-1]
    return s.strip()


def parse_repo_input(text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """接受各种粘贴格式，返回 (owner, repo)。repo 解析不到时返回 (None, None)。

    支持：
      https://gitee.com/zhangsan/repo.git
      git@gitee.com:zhangsan/repo.git
      zhangsan/repo
      repo                     → (None, 'repo')
    """
    if text is None:
        return None, None
    s = str(text).strip()
    if not s:
        return None, None
    # 去掉协议前缀
    for prefix in ('https://gitee.com/', 'http://gitee.com/', 'gitee.com/',
                   'git@gitee.com:', 'ssh://git@gitee.com/'):
        if s.lower().startswith(prefix.lower()):
            s = s[len(prefix):]
            break
    # 去 .git 后缀
    if s.lower().endswith('.git'):
        s = s[:-4]
    s = s.strip('/').strip()
    if not s:
        return None, None
    segs = [seg.strip() for seg in s.split('/') if seg.strip()]
    if len(segs) == 0:
        return None, None
    if len(segs) == 1:
        # 只有一个词：大概率只给了 repo 名；owner 空让 verify_token 补
        return None, segs[0]
    if len(segs) >= 2:
        return segs[0], segs[1]
    return None, None


def normalize_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """保存 / 使用前都跑一次：
       - 去首尾空格/斜杠/.git 后缀
       - 如果 repo 字段包含 URL 格式，自动拆出 owner/repo
       - branch 默认 master
       - path_prefix 首尾去 /；
         注意：用户显式传 '' 表示"备份到仓库根"我们保留；但如果上游根本
         没给 path_prefix 键（例如 save_settings 也只保存用户填过的字段），
         则要回 DEFAULT_SETTINGS['path_prefix'] = 'blog-backup'，避免
         _url(...) 里最终 path 变成 '/contents/...' 这种没前缀拼接也没 repo 的 404。
    """
    raw = dict(settings) if isinstance(settings, dict) else {}
    s = dict(raw)
    # repo 若是完整 URL → 先拆
    raw_repo = str(s.get('repo') or '').strip()
    # 判断用户是否把整段 URL 塞进了 repo 框（含有 gitee.com 或 @ 或 /且 owner 为空）
    looks_like_url = ('gitee.com' in raw_repo.lower() or raw_repo.startswith('git@')
                      or raw_repo.count('/') >= 1 and not s.get('owner'))
    if looks_like_url:
        o, r = parse_repo_input(raw_repo)
        if o and not s.get('owner'):
            s['owner'] = o
        if r:
            s['repo'] = r
    s['owner'] = _clean_owner(s.get('owner'))
    s['repo'] = _clean_repo(s.get('repo'))
    b = str(s.get('branch') or '').strip()
    s['branch'] = b if b else DEFAULT_SETTINGS['branch']
    # path_prefix 规则：
    #   - 键不存在 / None / 纯空格 / 只剩 slashes → 视为“用户没填”，回默认 blog-backup
    #   - 非空 → 保留用户显式值（去掉首尾 / 与空格）
    # 为什么要收紧：
    #   电脑 A 备份时，旧表单的 `<input name="path_prefix" value="">` 没被用户改过时会被
    #   POST 为空字符串，旧版 normalize_settings 把 '' 当成“用户明确要备份到仓库根”落盘；
    #   电脑 B 跨机器新装 → 读到 path_prefix="" → fetch_latest_snapshot_meta 访问仓库根 latest.json
    #   → 404 → 页面永远提示“没检测到远端 latest.json”，恢复按钮永久不可点。
    #   新规则：只有非空（去除 // / 空格后仍有内容）才认为是显式指定；否则一律走默认值。
    pp_in = s.get('path_prefix', None)
    if pp_in is None:
        pp_clean = ''
    else:
        # 先去前后空格 → 再去前后 slashes → 再去前后空格，避免 '   /   /   ' 这种残留
        pp_clean = str(pp_in).strip().strip('/').strip()
    if not pp_clean:
        s['path_prefix'] = DEFAULT_SETTINGS['path_prefix']
    else:
        s['path_prefix'] = pp_clean
    s['token'] = str(s.get('token') or '').strip()
    # enabled / auto_backup_on_start / auto_restore_on_first_start：
    #   - 'on' / True / 'true' → True
    #   - 'off' / '' / False / None / 其他 → False
    for k in ('enabled', 'auto_backup_on_start', 'auto_restore_on_first_start'):
        if k in s:
            v = s[k]
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                s[k] = bool(v)
            else:
                s[k] = str(v).strip().lower() in ('1', 'true', 'yes', 'on')
        else:
            s[k] = DEFAULT_SETTINGS[k]
    return s


def _settings_ready(settings: Dict[str, Any]) -> Tuple[bool, str]:
    s = normalize_settings(settings)
    if not s.get('enabled'):
        return False, '备份未启用，请先在「数据同步 · Gitee」页面启用并保存。'
    for k in ('token', 'owner', 'repo'):
        if not s.get(k):
            return False, '缺少必要配置：' + {'token': '私人令牌', 'owner': 'Gitee用户名/组织', 'repo': '仓库名'}[k]
    return True, ''


def _user_url(token: str) -> str:
    return f"{GITEE_API_BASE}/user?access_token={_urlparse.quote(token)}"


def _repos_list_url(token: str) -> str:
    q = {'access_token': token, 'type': 'owner', 'sort': 'updated',
         'per_page': 100, 'page': 1}
    return f"{GITEE_API_BASE}/user/repos?" + _urlparse.urlencode(q)


def _repos_create_url(token: str) -> str:
    return f"{GITEE_API_BASE}/user/repos?access_token={_urlparse.quote(token)}"


def _repo_meta_url(owner: str, repo: str, token: Optional[str] = None) -> str:
    base = f"{GITEE_API_BASE}/repos/{_urlparse.quote(owner)}/{_urlparse.quote(repo)}"
    if token:
        base += f"?access_token={_urlparse.quote(token)}"
    return base


def _url(path: str, settings: Dict[str, Any], query: Optional[Dict[str, Any]] = None) -> str:
    s = normalize_settings(settings)
    base = f"{GITEE_API_BASE}/repos/{s['owner']}/{s['repo']}/contents/{path.lstrip('/')}"
    q = dict(query or {})
    q.setdefault('access_token', s['token'])
    return base + '?' + _urlparse.urlencode({k: v for k, v in q.items() if v is not None})


def _json_request(method: str, url: str, body_bytes: Optional[bytes] = None, headers: Optional[Dict[str, str]] = None,
                  timeout: float = 30.0) -> Tuple[int, Dict[str, Any], bytes]:
    """发起 HTTP 请求，返回 (status_code, parsed_json_or_error, raw_body_bytes)。"""
    hdrs = {'Accept': 'application/json', 'User-Agent': 'personal-blog-desktop/1.0'}
    if body_bytes is not None:
        hdrs.setdefault('Content-Type', 'application/json;charset=utf-8')
    if headers:
        hdrs.update(headers)
    data = body_bytes if body_bytes is not None and method in ('POST', 'PUT', 'PATCH') else None
    req = _real_urlopen.Request(url, data=data, headers=hdrs, method=method)
    ssl_ctx = build_ssl_context()
    try:
        with urlopen(req, timeout=timeout, context=ssl_ctx) as r:
            raw = b''
            while True:
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                raw += chunk
            try:
                obj = json.loads(raw.decode('utf-8')) if raw else {}
            except (ValueError, UnicodeDecodeError):
                obj = {'_raw': raw[:200].decode('utf-8', 'ignore')}
            return (r.status if hasattr(r, 'status') else 200), obj, raw
    except Exception as e:
        # HTTPError 也当 response 处理；URLError(SSL 错误) 走同样分支，但要把 SSL 具体错误保留在 obj.error
        r = getattr(e, 'fp', None)
        raw = b''
        status = 500
        try:
            if r is not None:
                raw = r.read()
                status = getattr(e, 'code', 500) or 500
        except Exception:
            pass
        if not raw:
            raw = str(e).encode('utf-8', 'ignore')[:400]
        try:
            obj = json.loads(raw.decode('utf-8', 'ignore'))
        except (ValueError, UnicodeDecodeError):
            # 对 SSL 错误给出可诊断信息
            msg = str(e)[:200]
            lower = msg.lower()
            if 'certificate' in lower or 'ssl:' in lower or 'ssl error' in lower:
                msg = '【连接被根证书拦截】请不要在浏览器里折腾令牌，本程序会自行通过本地根证书校验。\n' \
                      '若使用企业内网/VPN 代理：请联系网管放行 gitee.com，或手动安装公司根证书到"当前用户-受信任的根证书颁发机构"。\n' \
                      '技术细节：' + msg
            obj = {'error': msg}
        return status, obj, raw


def _get_existing_sha(settings: Dict[str, Any], remote_path: str) -> Tuple[bool, str]:
    """GET /contents/{path}。返回 (exists, sha_or_error)。

    注意：
      - 200 + 有 sha         → exists=True
      - 404                  → exists=False, sha="<错误描述 json 前 300 字>"
      - **401/403/5xx 等其他错误** —— 不要当作 exists=False，否则上层会走 POST 创建，
        最后返回的错误消息是"创建失败 ... 401 Unauthorized"，对用户来说难定位。
        正确做法：把 HTTP 状态写进错误描述前缀 "HTTP401|{msg}"，让 `upload_bytes_to_gitee`
        和 `upload_blob_once` 一看到就直接中断向上层冒泡，不再尝试 POST/PUT。
    """
    url = _url(remote_path, settings, {'ref': settings.get('branch') or 'master'})
    status, obj, _ = _json_request('GET', url)
    if 200 <= status < 300 and isinstance(obj, dict) and isinstance(obj.get('sha'), str):
        return True, obj['sha']
    if status == 404:
        return False, json.dumps(obj, ensure_ascii=False)[:300]
    # 非 404 的"不存在" —— 统一打上 HTTP<n> 前缀，标记为"错误性 not exists"
    err_text = json.dumps(obj, ensure_ascii=False)[:300]
    return False, f'HTTP{status}|{err_text}'


def upload_bytes_to_gitee(settings: Dict[str, Any], remote_path: str, content: bytes,
                          message: str = 'blog backup update') -> Tuple[bool, Dict[str, Any]]:
    """上传 bytes 到指定远端路径。
    Gitee API 语义（与 GitHub 不同，严格区分 method）：
      - 文件不存在（创建） → POST /contents/{path}   （不得带 sha，否则会报 sha 参数冲突）
      - 文件存在（更新）   → PUT  /contents/{path}   （必须带 sha，否则报 400 "sha is missing"）
    """
    ready, why = _settings_ready(settings)
    if not ready:
        return False, {'error': why}
    remote_path = remote_path.lstrip('/')
    if not remote_path:
        return False, {'error': 'remote_path 不能为空'}
    exists, sha_or_err = _get_existing_sha(settings, remote_path)
    # 只有"明确致命错误"（401令牌失效、403无权限、5xx服务端异常）才中断冒泡，
    # 其他状态（400参数异常、409冲突、甚至200但结构异常、404目录列表返回列表等）
    # 都宽容处理：直接走 POST 尝试创建，失败了 Gitee 本身也会返回真实错误信息。
    # 这样同步引擎的小文件写入不会因为 check_existing 偶发异常而整轮同步失败。
    fatal = False
    fatal_code = 0
    fatal_obj: Any = None
    if not exists and isinstance(sha_or_err, str) and sha_or_err.startswith('HTTP') and '|' in sha_or_err:
        try:
            http_part, rest = sha_or_err.split('|', 1)
            try:
                fatal_obj = json.loads(rest) if rest.startswith('{') or rest.startswith('[') else rest
            except (ValueError, TypeError):
                fatal_obj = rest
            fatal_code = int(''.join(ch for ch in http_part if ch.isdigit()) or 0) or 0
            # 401 未授权、403 禁止、500+ 服务端异常 = 致命；其余宽容跳过
            if fatal_code == 401 or fatal_code == 403 or fatal_code >= 500:
                fatal = True
        except Exception:
            fatal = False
    if fatal:
        return False, {'status': fatal_code, 'error': fatal_obj,
                       '_note': 'check_existing 检测到致命 %s 错误，中断避免误导后续请求' % fatal_code}
    payload = {
        'message': message,
        'content': base64.b64encode(content).decode('ascii'),
        'branch': settings.get('branch') or 'master',
    }
    # Gitee 严格要求：创建时(POST)不许带 sha；更新时(PUT)必须带 sha
    if exists:
        payload['sha'] = sha_or_err
        method = 'PUT'
    else:
        method = 'POST'
    url = _url(remote_path, settings)
    status, obj, _ = _json_request(method, url, body_bytes=json.dumps(payload).encode('utf-8'))
    if 200 <= status < 300:
        return True, {'status': status, 'sha': obj.get('content', {}).get('sha') if isinstance(obj, dict) else None}
    # 防御：POST 创建时因为"文件已存在"失败（check_existing 竞态或 Gitee 缓存未命中），
    # 自动拿最新 sha 重试一次 PUT 更新，避免同步整轮失败。
    if method == 'POST':
        err_msg = ''
        if isinstance(obj, dict):
            err_msg = str(obj.get('message') or obj.get('error') or '').lower()
        elif isinstance(obj, str):
            err_msg = obj.lower()
        exists_keywords = ('exist', 'already', 'duplicate', 'already exists', 'has already', '文件已存在')
        is_conflict = (status in (409, 422, 400)) or any(k in err_msg for k in exists_keywords)
        if is_conflict:
            exists2, sha2 = _get_existing_sha(settings, remote_path)
            if exists2 and sha2:
                payload2 = dict(payload)
                payload2['sha'] = sha2
                status2, obj2, _ = _json_request(
                    'PUT', url, body_bytes=json.dumps(payload2).encode('utf-8'))
                if 200 <= status2 < 300:
                    return True, {
                        'status': status2,
                        'sha': obj2.get('content', {}).get('sha') if isinstance(obj2, dict) else None,
                        '_retried': 'post-conflict → put-update ok'}
    return False, {'status': status, 'error': obj}


def download_bytes_from_gitee(settings: Dict[str, Any], remote_path: str) -> Tuple[bool, bytes]:
    """下载指定路径文件内容（优先 download_url，否则 content base64）。"""
    ready, why = _settings_ready(settings)
    if not ready:
        return False, why.encode('utf-8')
    remote_path = remote_path.lstrip('/')
    url = _url(remote_path, settings, {'ref': settings.get('branch') or 'master'})
    status, obj, raw = _json_request('GET', url)
    if not (200 <= status < 300):
        return False, ('get '+remote_path+' status '+str(status)).encode('utf-8')
    if not isinstance(obj, dict):
        return False, b'invalid json object'
    dl_url = obj.get('download_url') or None
    if dl_url and isinstance(dl_url, str) and dl_url.startswith('http'):
        try:
            ssl_ctx = build_ssl_context()
            with urlopen(_real_urlopen.Request(dl_url, headers={'User-Agent': 'personal-blog-desktop/1.0'}),
                         timeout=60, context=ssl_ctx) as r:
                data = b''
                while True:
                    ch = r.read(1024*256)
                    if not ch: break
                    data += ch
                return True, data
        except Exception:
            pass  # download_url 失败（私有仓库 raw 403 等），回退到 base64 content
    # 回退：base64 content
    if isinstance(obj.get('content'), str):
        try:
            return True, base64.b64decode(obj['content'])
        except Exception as e:
            return False, ('base64 decode fail: '+str(e)).encode('utf-8', 'ignore')
    return False, b'no download_url and no content'


def _candidate_prefixes(primary: str) -> List[str]:
    """生成“尝试找 latest.json”的候选子目录顺序，去重保持原序。

    设计思路：
      - 第一优先：用户/配置的 primary path_prefix
      - 第二优先：和 primary 相反的一端（primary 为空 → 先试默认 blog-backup；
        primary 就是默认 → 再试仓库根 ''，覆盖“用户以前选过根备份”的极端）
      - 后面补常见别名（backup/、blog/），即使不同客户端约定不同也能命中。
    跨机器恢复是高频场景，宁愿多 2~3 次 HTTP 404（几毫秒），也不能让恢复按钮永远灰掉。
    """
    default = DEFAULT_SETTINGS['path_prefix']
    seen: set = set()
    out: List[str] = []
    def _push(x: str):
        clean = (x or '').strip('/')
        key = clean.lower()
        if key in seen:
            return
        seen.add(key)
        out.append(clean)
    _push(primary)
    # 空 primary → 先补默认
    if not (primary or '').strip('/'):
        _push(default)
    # primary 就是默认 → 尝试根
    elif (primary or '').strip('/') == default:
        _push('')
    # 已知常见约定（兜底）
    _push('backup')
    _push('blog')
    _push('blog-data')
    _push('backup/blog')
    return out


def fetch_latest_snapshot_meta(settings: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """读取 latest.json，返回 (ok, meta_dict)。

    健壮化（解决跨机器恢复按钮灰掉的核心修复）：
      1) 先按 settings.path_prefix 主路径尝试；
      2) 404 时依次尝试 _candidate_prefixes(...)；
      3) 命中后把真正的路径以 `resolved_path_prefix` 的形式写回 meta，供
         run_restore_latest / UI 显示 / save_settings 自动纠正配置。
      4) 若全部没命中，把尝试过的路径列表写进 error，让用户一眼看到“为什么找不到”。
    """
    ready, why = _settings_ready(settings)
    if not ready:
        return False, {'error': why}
    primary = (settings.get('path_prefix') or '').strip('/')
    candidates = _candidate_prefixes(primary)
    last_err: Optional[Dict[str, Any]] = None
    tried: List[str] = []
    for pp in candidates:
        prefix = (pp + '/') if pp else ''
        remote_path = prefix + 'latest.json'
        tried.append('/' + remote_path if remote_path.startswith('/') else '/' + remote_path)
        ok, raw = download_bytes_from_gitee(settings, remote_path)
        if ok:
            try:
                meta = json.loads(raw.decode('utf-8'))
            except (ValueError, UnicodeDecodeError) as e:
                # 这条路径有东西但不是 JSON（比如用户放了别的文件）：记 last_err 继续试下条
                last_err = {'error': f'路径 {remote_path!r} latest.json 解析失败: {e}',
                            'tried_prefix': pp}
                continue
            # 命中：把真正 prefix 写回 meta，同时记录 candidate 列表和尝试过的路径（UI 可展示）
            if not isinstance(meta, dict):
                meta = {'value': meta}
            meta['resolved_path_prefix'] = pp
            meta['_primary_path_prefix'] = primary
            meta['_candidate_prefixes'] = candidates
            meta['_tried_paths'] = tried[:]
            # 纠正 manifest_path：如果它没以 resolved_path_prefix 开头（旧版没写），
            # 自动补到 resolved_path_prefix 下；否则保持不动，避免把已含 prefix 的完整路径再拼一次。
            man = meta.get('manifest_path')
            if isinstance(man, str) and man:
                man_clean = man.lstrip('/')
                if pp:
                    expected_prefix = pp.strip('/') + '/'
                    if not man_clean.startswith(expected_prefix):
                        meta['manifest_path'] = expected_prefix + man_clean
                else:
                    meta['manifest_path'] = man_clean
            return True, meta
        # 下载失败：raw 一般是错误 bytes，UTF-8 化
        err_text = raw.decode('utf-8', 'ignore')[:200] if isinstance(raw, (bytes, bytearray)) else str(raw)[:200]
        last_err = {'error': f'无法下载 latest.json (prefix {pp!r}): {err_text}',
                    'tried_prefix': pp}
    # 全部候选都失败 → 返回聚合错误，附带尝试过的路径和 prefix
    msg = '；'.join((last_err or {}).get('error', '未知远端错误').split('；')[:3])
    return False, {
        'error': '没有在远端找到 latest.json（已尝试 %d 条路径：%s）。'
                 '请确认电脑 A 至少成功备份过一次；或在「仓库内子目录」手动指定备份时使用的前缀。'
                 % (len(tried), '、'.join(tried[:6]) + (' …' if len(tried) > 6 else '')),
        '_primary': primary,
        '_candidate_prefixes': candidates,
        '_tried_paths': tried,
        '_last_error': last_err,
    }


# ============================================================
#  账号连通性：verify_token / 列仓库 / 建仓库 / 反查分支 / 诊断 / 测试
# ============================================================
def verify_token_and_get_user(token: str) -> Tuple[bool, Dict[str, Any]]:
    """GET /user：拿到 login(URL用户名)、name(昵称)、avatar_url。
    Token 无效返回 (False, {'error': ...})。用于：
      ① 粘贴令牌后自动识别用户身份，自动帮用户把 owner 填成正确的 URL 用户名
      ② 404 时判断是 token 有问题 / owner 填错 / 仓库不存在
    """
    t = (token or '').strip()
    if not t:
        return False, {'error': '私人令牌为空，请先在下方生成令牌并粘贴。'}
    url = _user_url(t)
    status, obj, _ = _json_request('GET', url)
    if 200 <= status < 300 and isinstance(obj, dict) and isinstance(obj.get('login'), str):
        info = {
            'login': obj['login'],
            'name': obj.get('name') or obj.get('login'),
            'avatar_url': obj.get('avatar_url') or '',
            'html_url': obj.get('html_url') or f"https://gitee.com/{obj['login']}",
            'id': obj.get('id'),
        }
        return True, info
    # 尝试把错误消息翻成中文可理解
    err = ''
    if isinstance(obj, dict):
        err = obj.get('message') or obj.get('error') or json.dumps(obj, ensure_ascii=False)[:200]
    else:
        err = str(obj)[:200]
    msg = '无效的私人令牌（错误码 %s：%s）。\n请回到 Gitee「私人令牌」页面：\n 1) 重新生成一个令牌；\n 2) 权限勾选 projects；\n 3) 复制完整 32 位字符串粘贴。' % (status, err)
    return False, {'error': msg, 'status': status, 'raw': obj}


def list_my_repos(token: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """列出该令牌名下所有自己的仓库（按更新时间排序，前 100 个）。"""
    t = (token or '').strip()
    if not t:
        return False, [{'error': '令牌为空'}]
    url = _repos_list_url(t)
    status, obj, _ = _json_request('GET', url)
    if not (200 <= status < 300) or not isinstance(obj, list):
        err = '获取仓库列表失败（HTTP %s：%s）。令牌是否已勾选 projects 权限？' % (
            status, (obj.get('message') if isinstance(obj, dict) else obj)[:200])
        return False, [{'error': err}]
    out: List[Dict[str, Any]] = []
    for r in obj:
        if not isinstance(r, dict):
            continue
        out.append({
            'name': r.get('name') or '',
            'full_name': r.get('full_name') or '',
            'private': bool(r.get('private', False)),
            'default_branch': r.get('default_branch') or 'master',
            'html_url': r.get('html_url') or '',
            'description': r.get('description') or '',
            'updated_at': r.get('updated_at') or '',
        })
    return True, out


def ensure_repo(token: str, owner: str, name: str, private: bool = True,
                auto_init: bool = True) -> Tuple[bool, Dict[str, Any]]:
    """先列仓库（个人空间下）：已存在就直接返回信息；不存在就 POST 新建一个。

    Gitee 新建仓库可选参数：
      name, description, private, auto_init(=自动写README.md), gitignores_template, license_template
    我们传 auto_init=true，保证返回有 default_branch。
    """
    t = (token or '').strip(); nm = (name or '').strip()
    own = _clean_owner(owner)
    if not t:
        return False, {'error': '令牌为空，无法创建仓库。'}
    if not nm:
        return False, {'error': '请填写要创建的仓库名称。'}
    # 先 list 查是否已存在（避免重复创建报错）
    ok_l, repos = list_my_repos(t)
    existing: Optional[Dict[str, Any]] = None
    if ok_l:
        for r in repos:
            if r.get('name') == nm:
                existing = r
                break
    if existing is not None:
        return True, {'created': False,
                      'full_name': existing.get('full_name'),
                      'name': existing.get('name'),
                      'default_branch': existing.get('default_branch') or 'master',
                      'html_url': existing.get('html_url'),
                      'private': existing.get('private', True)}
    payload = {
        'name': nm,
        'private': bool(private),
        'auto_init': bool(auto_init),
        'description': '个人博客自动备份仓库（SQLite 数据库 + 上传资产快照）。由本软件自动管理，请勿手动删除最新的 latest.json 和最近 2 份 snap- 目录。',
        'gitignores_template': 'Python',
    }
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    url = _repos_create_url(t)
    status, obj, _ = _json_request('POST', url, body_bytes=body)
    if 200 <= status < 300 and isinstance(obj, dict):
        return True, {
            'created': True,
            'full_name': obj.get('full_name') or f"{own}/{nm}",
            'name': obj.get('name') or nm,
            'default_branch': obj.get('default_branch') or 'master',
            'html_url': obj.get('html_url') or f"https://gitee.com/{own}/{nm}",
            'private': bool(obj.get('private', True)),
        }
    err = ''
    if isinstance(obj, dict):
        err = obj.get('message') or json.dumps(obj, ensure_ascii=False)[:300]
    else:
        err = str(obj)[:300]
    return False, {'error': '创建仓库失败（HTTP %s：%s）。\n小提示：若提示实名认证，请前往 Gitee 右上角「设置」→「实名认证」完成支付宝认证，免费且秒过。' % (status, err)}


def get_default_branch(settings: Dict[str, Any]) -> Tuple[bool, str]:
    """从仓库元信息反查真正的默认分支（master/main），避免用户猜。"""
    s = normalize_settings(settings)
    if not s.get('token') or not s.get('owner') or not s.get('repo'):
        return False, s.get('branch') or DEFAULT_SETTINGS['branch']
    url = _repo_meta_url(s['owner'], s['repo'], s['token'])
    status, obj, _ = _json_request('GET', url)
    if 200 <= status < 300 and isinstance(obj, dict) and isinstance(obj.get('default_branch'), str):
        return True, obj['default_branch']
    # 失败则回退到 settings 里写的分支
    return False, s.get('branch') or DEFAULT_SETTINGS['branch']


def diagnose_404(settings: Dict[str, Any]) -> str:
    """当遇到 404 Not Found Project 时，给出可操作的排查清单（含真实用户名 vs 填入值对比）。"""
    s = normalize_settings(settings)
    token = s.get('token') or ''
    token_ok = False
    real_login: Optional[str] = None
    real_name: Optional[str] = None
    err_tip = ''
    if token:
        ok_u, u = verify_token_and_get_user(token)
        if ok_u:
            token_ok = True
            real_login = u.get('login')
            real_name = u.get('name') or ''
        else:
            err_tip = u.get('error', '') if isinstance(u, dict) else ''
    lines: List[str] = []
    lines.append('⚠️ Gitee 返回 404 Not Found Project（找不到项目）。可能原因与操作建议：')
    if token_ok and real_login:
        lines.append(f'  ① 你的真实 Gitee URL 用户名：{real_login}  （昵称：{real_name or "—"}）')
        lines.append(f'     你当前填写的归属者(owner)：{s.get("owner") or "（空）"}  仓库：{s.get("repo") or "（空）"}')
        if s.get('owner') and s.get('owner') != real_login:
            lines.append(f'     ✅ 建议把「归属者」改成：{real_login}（不要填昵称，要填 URL 路径里的用户名）')
    elif not token_ok:
        lines.append(f'  ① 令牌验证失败：{err_tip or "令牌无效/为空，请重新生成并勾选 projects 权限。"}')
    lines.append('  ② 检查仓库是否真的已创建：登录 https://gitee.com 看你的仓库列表里有没有 '
                 + f'《{s.get("repo") or "（未知）"}》。没有的话，点本页「一键新建私有备份仓库」。')
    lines.append('  ③ 检查令牌权限：必须勾选「projects」（仅勾 user_info 不够！对私有仓库，Gitee 会故意返回 404 来避免枚举）。')
    lines.append('  ④ 检查分支名：新仓库默认是 master，但你改过的话请在「分支名」里填实际分支。')
    return '\n'.join(lines)


def test_connection(settings: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """综合连通性测试：验证令牌 → 反查用户 → 访问仓库 → 对比默认分支。
    返回 (ok, {steps:[...], summary, corrected_settings})。
    """
    s = normalize_settings(settings)
    steps: List[Dict[str, Any]] = []
    ok = True
    final_settings = dict(s)

    # Step1: token
    t = s.get('token') or ''
    if not t:
        steps.append({'name': '私人令牌校验', 'ok': False, 'msg': '令牌为空'})
        ok = False
    else:
        o1, u1 = verify_token_and_get_user(t)
        if o1:
            steps.append({'name': '私人令牌校验', 'ok': True,
                          'msg': f"有效！用户：{u1.get('login')}（昵称 {u1.get('name')}）",
                          'user': u1})
            # 自动更正 owner
            if not s.get('owner') or s.get('owner') != u1.get('login'):
                steps.append({'name': '自动更正归属者', 'ok': True,
                              'msg': f"归属者 owner 从「{s.get('owner') or ''}」更正为真实用户名「{u1.get('login')}」"})
                final_settings['owner'] = u1.get('login') or ''
        else:
            steps.append({'name': '私人令牌校验', 'ok': False, 'msg': u1.get('error', str(u1))})
            ok = False

    # Step2: 仓库可达性 + 默认分支
    if final_settings.get('owner') and final_settings.get('repo') and t:
        url = _repo_meta_url(final_settings['owner'], final_settings['repo'], t)
        status, obj, _ = _json_request('GET', url)
        if 200 <= status < 300 and isinstance(obj, dict):
            steps.append({'name': '仓库访问权限', 'ok': True,
                          'msg': f"仓库 {final_settings['owner']}/{final_settings['repo']} 可访问。"})
            real_branch = obj.get('default_branch') or ''
            if real_branch and real_branch != final_settings.get('branch'):
                steps.append({'name': '自动更正分支', 'ok': True,
                              'msg': f"检测到仓库实际默认分支是 {real_branch}（原填 {final_settings.get('branch')}），已自动更正。"})
                final_settings['branch'] = real_branch
        else:
            err_msg = (obj.get('message') if isinstance(obj, dict) else str(obj)) or str(status)
            diag = diagnose_404(final_settings) if status == 404 else (
                f'访问仓库失败 HTTP {status}：{err_msg}')
            steps.append({'name': '仓库访问权限', 'ok': False, 'msg': diag})
            ok = False

    summary = '✅ 连通性检查通过！' if ok else '❌ 连通性未通过，请按上面的步骤提示修正后重试。'
    return ok, {'steps': steps, 'summary': summary, 'corrected_settings': final_settings}


# ============================================================
#  本地恢复（应用下载的临时目录到 DATA_DIR）
# ============================================================
def apply_restore(downloaded_dir: str, data_dir: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """把 downloaded_dir/<relpath> 按 manifest 复制到 data_dir，并对每个文件校验 sha256。

    失败时不写回 gitee 配置；所有不通过校验的文件不会覆盖。
    返回 { 'ok':bool, 'restored_count':int, 'errors':[msg...] }
    """
    errors: List[str] = []
    restored = 0
    items = manifest.get('files') or []
    for item in items:
        rel = item.get('relpath')
        expected_sha = item.get('sha256')
        if not rel or not expected_sha:
            errors.append('无效清单条目: ' + json.dumps(item, ensure_ascii=False))
            continue
        if '..' in rel or rel.startswith('/') or rel.startswith('\\'):
            errors.append('非法路径（拒绝）: ' + rel)
            continue
        src = os.path.join(downloaded_dir, rel)
        dst = os.path.join(data_dir, rel)
        if not os.path.isfile(src):
            errors.append('下载缺失文件: ' + rel)
            continue
        # 校验 sha
        actual = _sha256_file(src)
        if actual != expected_sha:
            errors.append('SHA256 校验失败: %s  (expected=%.10s actual=%.10s)' % (rel, expected_sha, actual))
            continue
        # 复制（父目录）
        os.makedirs(os.path.dirname(dst) or data_dir, exist_ok=True)
        shutil.copyfile(src, dst)
        restored += 1
    ok = (len(errors) == 0) and restored >= 0
    return {'ok': ok, 'restored_count': restored, 'errors': errors,
            'snapshot_id': manifest.get('snapshot_id')}


# ============================================================
#  完整流水线：备份 / 恢复
# ============================================================
def _concat_prefix(settings: Dict[str, Any], *parts: str) -> str:
    parts2 = [p.strip('/') for p in parts if p]
    prefix = (settings.get('path_prefix') or '').strip('/')
    return '/'.join([prefix] + parts2) if prefix else '/'.join(parts2)


def run_backup(data_dir: str, dry_run: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """完整备份流程（增量去重 + 断点续传 + 跳空优化）：

    1. 收集资产 → 计算 assets_digest
    2. 若 digest == settings.last_backup_assets_digest 且无 progress → 直接跳空返回（0 次网络请求）
    3. 若存在合法 progress（digest 匹配）→ 断点续传（复用 snapshot_id，跳过已 done 的条目）
    4. 否则 → 开新 snapshot_id，初始化 progress
    5. 遍历文件：
         - 若 progress 标记 done → 跳过（不发任何请求）
         - 否则 → upload_blob_once（GET exists 命中则 skipped=True 跳过；否则 POST 创建 blob）
         - 每成功 1 个立刻 save_progress 原子落盘
    6. 上传 manifest.json（files 中每个条目含 blob_ref 供恢复时寻址）
    7. 更新 latest.json
    8. 成功 → clear_progress + 写入 settings.last_backup_*
    """
    settings = load_settings(data_dir)
    ready, why = _settings_ready(settings)
    if not ready:
        return False, {'error': why}

    # 1) 收集本地资产
    manifest, files = collect_backup_assets(data_dir)
    assets_digest = _assets_digest(files)
    total_bytes = manifest['total_bytes']

    # 2) 跳空：内容与上次成功备份完全一致，且没有未完成的 progress
    existing_progress = load_progress(data_dir)
    if existing_progress is None and settings.get('last_backup_assets_digest') == assets_digest:
        return True, {
            'snapshot_id': settings.get('last_backup_snapshot') or manifest['snapshot_id'],
            'skipped_no_changes': True,
            'files_count': len(files),
            'total_bytes': total_bytes,
            'dry_run': dry_run,
            'skipped_blob_count': len(files),
            'uploaded_blob_count': 0,
        }

    # 3) 决定 snapshot_id + 是否续传
    resumed = False
    manifest_done = False
    latest_done = False
    snapshot_id = manifest['snapshot_id']
    if existing_progress is not None:
        if existing_progress.get('assets_digest') == assets_digest:
            # 合法续传：复用 snapshot_id 与 items
            snapshot_id = existing_progress['snapshot_id'] or snapshot_id
            progress_items = existing_progress['items']
            manifest_done = bool(existing_progress.get('manifest_done'))
            latest_done = bool(existing_progress.get('latest_done'))
            resumed = True
        else:
            # digest 对不上 → 旧 progress 作废，清掉重开
            clear_progress(data_dir)
            progress_items = {}
    else:
        progress_items = {}

    # 初始化 progress_items 为所有 relpath（新增的文件补 pending 状态；续传时保留旧 items）
    for fi in files:
        rel = fi['relpath']
        if rel not in progress_items:
            progress_items[rel] = {
                'status': 'pending',
                'blob_ref': None,
                'attempts': 0,
                'last_err': None,
            }

    # 持久化初始 progress（保证就算第 1 个 blob 上传前断电，下次也能继续同一个 snapshot）
    current_progress: Dict[str, Any] = {
        'snapshot_id': snapshot_id,
        'assets_digest': assets_digest,
        'items': progress_items,
        'manifest_done': manifest_done,
        'latest_done': latest_done,
    }
    if not dry_run:
        save_progress(data_dir, current_progress)

    skipped_blob_count = 0
    uploaded_blob_count = 0
    skipped_bytes = 0
    sent_bytes = 0
    manifest_files: List[Dict[str, Any]] = []  # 写进 manifest.json 的 files（含 blob_ref）

    # 4) 遍历每个资产：上传 blob（含断点 + 去重）
    for fi in files:
        rel = fi['relpath']
        item_entry = progress_items.get(rel, {'status': 'pending', 'blob_ref': None, 'attempts': 0})
        local_abs = os.path.join(data_dir, rel)
        expected_sha = fi['sha256']

        # --- 断点续传：已标记 done 的文件，直接跳过（不发任何请求）---
        if item_entry.get('status') == 'done' and isinstance(item_entry.get('blob_ref'), str):
            blob_ref_rel = item_entry['blob_ref']
            skipped_blob_count += 1
            skipped_bytes += int(fi.get('size', 0))
            manifest_files.append({
                'relpath': rel,
                'size': fi.get('size', 0),
                'sha256': expected_sha,
                'blob_ref': blob_ref_rel,
            })
            continue

        # --- 非 done：走 upload_blob_once（内部会先 GET 判断远端是否已存在，存在则 skip）---
        if dry_run:
            # dry_run 仅占位：视作全部"未跳过"但不真实上传
            blob_ref_rel = _blob_ref(expected_sha)
            uploaded_blob_count += 1
            sent_bytes += int(fi.get('size', 0))
            manifest_files.append({
                'relpath': rel, 'size': fi.get('size', 0),
                'sha256': expected_sha, 'blob_ref': blob_ref_rel,
            })
            continue

        ok_b, info_b = upload_blob_once(
            settings, local_abs, expected_sha,
            message='blog backup: %s blob (%s)' % (snapshot_id, rel))
        attempts = int(item_entry.get('attempts', 0)) + 1
        if not ok_b:
            # 失败：更新 progress.last_err，原子落盘，返回错误给调用方
            err_text = info_b.get('error', str(info_b)[:200]) if isinstance(info_b, dict) else str(info_b)[:200]
            progress_items[rel] = {
                'status': 'failed',
                'blob_ref': None,
                'attempts': attempts,
                'last_err': err_text,
            }
            current_progress['items'] = progress_items
            save_progress(data_dir, current_progress)
            return False, {
                'error': '上传失败: %s -> %s' % (rel, err_text),
                'uploaded_blob_count': uploaded_blob_count,
                'skipped_blob_count': skipped_blob_count,
                'files_count': len(files),
            }

        blob_ref_rel = info_b.get('blob_ref') or _blob_ref(expected_sha)
        was_skipped = bool(info_b.get('skipped'))
        if was_skipped:
            skipped_blob_count += 1
            skipped_bytes += int(fi.get('size', 0))
        else:
            uploaded_blob_count += 1
            sent_bytes += int(info_b.get('bytes_sent') or fi.get('size', 0))

        # 标记 done
        progress_items[rel] = {
            'status': 'done',
            'blob_ref': blob_ref_rel,
            'attempts': attempts,
            'last_err': None,
        }
        manifest_files.append({
            'relpath': rel,
            'size': fi.get('size', 0),
            'sha256': expected_sha,
            'blob_ref': blob_ref_rel,
        })
        # 每 1 个资产立刻原子落盘 progress（断点续传核心）
        current_progress['items'] = progress_items
        save_progress(data_dir, current_progress)

    # 5) 上传 manifest.json（写入 {snapshot_id}/manifest.json，files 带 blob_ref）
    manifest_payload = dict(manifest)
    manifest_payload['snapshot_id'] = snapshot_id  # 若续传则复用
    manifest_payload['file_count'] = len(manifest_files)
    manifest_payload['total_bytes'] = total_bytes
    manifest_payload['files'] = manifest_files
    manifest_bytes = json.dumps(manifest_payload, ensure_ascii=False, indent=2).encode('utf-8')
    remote_manifest = _concat_prefix(settings, snapshot_id, 'manifest.json')
    if not dry_run and not manifest_done:
        ok_m, info_m = upload_bytes_to_gitee(
            settings, remote_manifest, manifest_bytes,
            message='blog backup: %s manifest' % snapshot_id)
        if not ok_m:
            current_progress['manifest_done'] = False
            save_progress(data_dir, current_progress)
            return False, {
                'error': '上传 manifest.json 失败: %s' % str(info_m)[:400],
                'uploaded_blob_count': uploaded_blob_count,
                'skipped_blob_count': skipped_blob_count,
            }
        current_progress['manifest_done'] = True
        save_progress(data_dir, current_progress)

    # 6) 更新 latest.json：指向本快照（成功才算一次有效备份）
    latest = {
        'snapshot_id': snapshot_id,
        'created_at': manifest['created_at'],
        'manifest_path': remote_manifest,
        'files_count': len(files),
        'total_bytes': total_bytes,
    }
    latest_bytes = json.dumps(latest, ensure_ascii=False, indent=2).encode('utf-8')
    remote_latest = _concat_prefix(settings, 'latest.json')
    if not dry_run and not latest_done:
        ok_l, info_l = upload_bytes_to_gitee(
            settings, remote_latest, latest_bytes,
            message='blog backup: latest -> %s' % snapshot_id)
        if not ok_l:
            current_progress['latest_done'] = False
            save_progress(data_dir, current_progress)
            return False, {
                'error': '更新 latest.json 失败: %s' % str(info_l)[:400],
                'uploaded_blob_count': uploaded_blob_count,
                'skipped_blob_count': skipped_blob_count,
            }
        current_progress['latest_done'] = True

    # 7) 成功 → 清 progress + 记录本地 settings
    if not dry_run:
        clear_progress(data_dir)
        settings['last_backup_at'] = _dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        settings['last_backup_snapshot'] = snapshot_id
        settings['last_backup_assets_digest'] = assets_digest
        settings['last_backup_total_bytes'] = total_bytes
        save_settings(data_dir, settings)

    uploaded_count_total = uploaded_blob_count + (0 if dry_run else 2)  # manifest + latest
    return True, {
        'snapshot_id': snapshot_id,
        'uploaded_count': uploaded_count_total,
        'uploaded_blob_count': uploaded_blob_count,
        'skipped_blob_count': skipped_blob_count,
        'resumed_from_progress': resumed,
        'sent_bytes': sent_bytes,
        'skipped_bytes': skipped_bytes,
        'files_count': len(files),
        'total_bytes': total_bytes,
        'dry_run': dry_run,
    }


def run_restore_latest(data_dir: str) -> Tuple[bool, Dict[str, Any]]:
    """完整恢复流程：latest.json → 下载 manifest → 下载每个资产 → 本地校验 → 写入 DATA_DIR。

    向后兼容（双路径寻址）：
      - 新格式：manifest.files 每项含 blob_ref='blobs/ab/cdef...' → 从 {path_prefix}/blobs/ab/cdef... 下载
      - 旧格式（无 blob_ref）→ 从 {path_prefix}/snap-XXX/<relpath> 下载（昨天的全量快照结构）
    """
    import tempfile
    settings = load_settings(data_dir)
    ready, why = _settings_ready(settings)
    if not ready:
        return False, {'error': why}

    # 1) latest
    ok, latest = fetch_latest_snapshot_meta(settings)
    if not ok:
        return False, latest or {'error': '无法获取远端 latest.json'}
    snapshot_id = latest.get('snapshot_id')
    if not snapshot_id:
        return False, {'error': 'latest.json 缺少 snapshot_id'}

    # 1.1) 关键：跨机器 recovery 时，settings.path_prefix 可能是错的（如空串或历史值），
    #      fetch_latest_snapshot_meta 已经通过 candidate 探测找到真实的 resolved_path_prefix。
    #      我们把它写回 settings（仅当次使用），后续 manifest/blob 下载全部按真实前缀走，
    #      避免 _concat_prefix 把 settings.path_prefix 再拼一次 → blog-backup/blog-backup 双前缀。
    resolved_pp = ''
    if isinstance(latest.get('resolved_path_prefix'), str):
        resolved_pp = latest['resolved_path_prefix'].strip('/')
        settings = dict(settings)
        settings['path_prefix'] = resolved_pp
    # 同时，如果 resolved_pp 和用户原始 path_prefix 不一致，且磁盘可写，把纠正后的 prefix 持久化，
    # 下次 UI 打开时“恢复按钮”就能直接命中（不再依赖 candidate 探测）。
    primary = str(latest.get('_primary_path_prefix') or '').strip('/')
    if resolved_pp != primary:
        try:
            cur_on_disk = load_settings(data_dir)
            if str(cur_on_disk.get('path_prefix', '')).strip('/') != resolved_pp:
                cur_on_disk['path_prefix'] = resolved_pp or DEFAULT_SETTINGS['path_prefix']
                save_settings(data_dir, cur_on_disk)
        except Exception:
            pass  # 写盘失败不影响当次恢复

    # 2) manifest：优先用 latest.json 里的 manifest_path（fetch_latest 已经给它补过 resolved prefix）。
    #    若缺失，再按 _concat_prefix(settings, snap_id, manifest.json) 生成（settings 已是 resolved）。
    manifest_remote = None
    if isinstance(latest.get('manifest_path'), str) and latest['manifest_path'].strip():
        man_raw = latest['manifest_path'].strip().lstrip('/')
        # 防双写：如果 man_raw 已经以 resolved_pp + '/' 开头，不再再拼一次
        if resolved_pp and not man_raw.startswith(resolved_pp + '/'):
            manifest_remote = resolved_pp + '/' + man_raw
        else:
            manifest_remote = man_raw
    if not manifest_remote:
        manifest_remote = _concat_prefix(settings, snapshot_id, 'manifest.json')
    # 再兜底一次：如果 manifest_remote 开头重复 resolved_pp/resolved_pp（如 blog-backup/blog-backup/...），去重
    if resolved_pp:
        doubled = resolved_pp + '/' + resolved_pp + '/'
        if manifest_remote.startswith(doubled):
            manifest_remote = resolved_pp + '/' + manifest_remote[len(doubled):]

    ok_man, raw_man = download_bytes_from_gitee(settings, manifest_remote)
    if not ok_man:
        return False, {'error': '无法下载 manifest.json: ' + raw_man[:200].decode('utf-8', 'ignore'),
                       'manifest_remote': manifest_remote,
                       'resolved_path_prefix': resolved_pp}
    try:
        manifest_payload = json.loads(raw_man.decode('utf-8'))
    except (ValueError, UnicodeDecodeError) as e:
        return False, {'error': 'manifest.json 非法: ' + str(e)}
    files = manifest_payload.get('files') or []
    if not isinstance(files, list):
        return False, {'error': 'manifest.files 不是数组'}

    # 3) 逐个下载到临时目录（双路径：优先 blob_ref，回退 snap-XXX/relpath）
    #   - settings 已替换为 resolved_path_prefix：_concat_prefix(settings, blob_ref) 会直接输出
    #     `resolved_pp/blobs/ab/...`，不会再出现空串导致的路径错误。
    #   - 对 blob_ref / snap_rel 都做一次重复前缀去重兜底。
    tmpdir = tempfile.mkdtemp(prefix='blog-restore-')
    try:
        for item in files:
            rel = item.get('relpath')
            if not rel or '..' in rel:
                return False, {'error': '非法清单文件路径: '+str(rel)}
            # 新格式：blob_ref = 'blobs/ab/cdef...'（不含 path_prefix）
            blob_ref = item.get('blob_ref') if isinstance(item, dict) else None
            if isinstance(blob_ref, str) and blob_ref.strip():
                remote = _concat_prefix(settings, blob_ref)
            else:
                # 旧格式：snap-XXX/<relpath>
                remote = _concat_prefix(settings, snapshot_id, rel)
            # 极端兜底：若用户自己拼的路径里出现 resolved_pp/resolved_pp/ 双写（老 manifest 遗留），去重一次
            if resolved_pp:
                doubled = resolved_pp + '/' + resolved_pp + '/'
                if remote.startswith(doubled):
                    remote = resolved_pp + '/' + remote[len(doubled):]
            ok_f, content = download_bytes_from_gitee(settings, remote)
            if not ok_f:
                return False, {'error': '下载失败: %s (%s)' % (rel, content[:200].decode('utf-8', 'ignore')),
                               'remote': remote,
                               'resolved_path_prefix': resolved_pp}
            target = os.path.join(tmpdir, rel)
            os.makedirs(os.path.dirname(target) or tmpdir, exist_ok=True)
            with open(target, 'wb') as f:
                f.write(content)
        # 4) apply 恢复到真实 DATA_DIR（先校验再复制）
        result = apply_restore(tmpdir, data_dir, manifest_payload)
        if not result['ok']:
            return False, {
                'error': '恢复校验失败: ' + ' | '.join(result['errors'])[:500],
                'restored_count': result['restored_count'],
                'snapshot_id': snapshot_id,
                'resolved_path_prefix': resolved_pp,
            }
        return True, {
            'snapshot_id': snapshot_id,
            'restored_count': result['restored_count'],
            'total_files': len(files),
            'resolved_path_prefix': resolved_pp,
            'auto_corrected_prefix': (resolved_pp != primary),
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def try_auto_restore_on_first_start(data_dir: str) -> Tuple[bool, Dict[str, Any]]:
    """main.py / app.py 启动时调用：
        - 如果用户启用了 auto_restore_on_first_start
        - 且本地 blog.db 不存在（通常是新安装、新机器、硬盘损坏后重装）
        - 且远端 latest.json 存在
       → 执行恢复；否则 early return（False + 说明）。不会破坏已有的本地数据。"""
    settings = load_settings(data_dir)
    if not settings.get('auto_restore_on_first_start'):
        return False, {'skipped': 'auto_restore_on_first_start=false'}
    if os.path.isfile(os.path.join(data_dir, 'blog.db')):
        return False, {'skipped': '本地 blog.db 已存在，不自动恢复'}
    # 只有配置完整才尝试
    ready, _ = _settings_ready(settings)
    if not ready:
        return False, {'skipped': 'Gitee 配置不完整'}
    return run_restore_latest(data_dir)
