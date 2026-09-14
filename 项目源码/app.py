"""
个人博客网站主程序
功能：
  - 文章发布 / 编辑 / 删除（支持Markdown）
  - 标签分类管理、按标签筛选
  - 上传 .md / .yaml 文件导入博客
  - 响应式页面，适配 PC 和手机
  - 简单管理员登录
  - 7 套主题切换、评论点赞、友链、搜索高亮、头像裁剪、背景图片
运行:
  pip install -r requirements.txt
  python app.py           # 启动博客（DEBUG=0 生产模式 waitress，DEBUG=1 开发模式）
  手机局域网访问：python open_firewall.py 放行端口后，同一 WiFi 可访问 http://<本机IP>:5000/
"""
import os
import re
import sys
import json
import traceback
import datetime
import logging
from logging.handlers import RotatingFileHandler
import yaml
from io import StringIO
from typing import Any, Dict, Optional

# Windows GBK 控制台兼容：强制 stdout/stderr 为 UTF-8，避免 emoji/中文触发 UnicodeEncodeError
# （PyCharm / cmd 默认可能是 GBK，print('✅...') 或日志输出 emoji 会崩溃）
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, send_from_directory, abort, jsonify)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

import markdown
from markdown.extensions.toc import TocExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from pygments.formatters import HtmlFormatter

from config import Config

# ------------------------------------------------------------------
# 【PP2 · 性能】HtmlFormatter 只实例化一次（pygments monokai 规则是纯常量），
#              避免每次 inject_globals 都做 20ms 量级的 CSS 规则扫描。
# ------------------------------------------------------------------
try:
    _CODEHILITE_CSS = HtmlFormatter(style='monokai').get_style_defs('.codehilite')
except Exception:
    _CODEHILITE_CSS = ''

# ------------------------------------------------------------------
# 【PP2 · 性能】inject_globals 的 5s TTL 缓存（按"是否登录"分键，避免管理员/游客串页）。
#              失效条件：T>expire，或内容变更（文章 CRUD / 标签 CRUD / profile 修改）显式调 invalidate_globals_cache()。
# ------------------------------------------------------------------
import time as _time
_GLOBALS_CACHE: dict = {}  # { cache_key: (expire_ts, value_dict) }
_GLOBALS_TTL_SEC = 5
_GC_LOCK = None  # lazy init 线程锁（避免多线程同时 stampede）

def invalidate_globals_cache():
    """写路径（保存文章/改资料）后调用，清掉全局变量缓存，保证页面立刻反映新内容。"""
    global _GLOBALS_CACHE
    _GLOBALS_CACHE.clear()


def _setup_logging(app):
    """配置按大小滚动的文件日志 + 简易控制台输出。
    【PP6 · 性能】生产模式 root / file handler 统一 WARNING 级别（减少每个请求 1~2 行磁盘 flush IO）。"""
    # pythonw.exe 无窗口模式下 sys.stdout / sys.stderr 是 None，
    # 任何 print 或 logging.StreamHandler 写入都会触发 AttributeError 导致进程崩溃。
    # 这里把它们重定向到 devnull，保证无窗口模式也能稳定运行。
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')

    log_dir = os.path.join(Config.DATA_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'blog.log')

    fmt = logging.Formatter(
        '%(asctime)s | %(levelname)-5s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

    prod_mode = not bool(app.config.get('DEBUG'))

    # 按大小滚动：单文件 3MB，保留 5 份
    fh = RotatingFileHandler(
        log_file, maxBytes=3 * 1024 * 1024, backupCount=5,
        encoding='utf-8')
    fh.setLevel(logging.WARNING if prod_mode else logging.INFO)  # <-- PP6：生产 WARNING
    fh.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.WARNING if prod_mode else logging.INFO)  # <-- PP6：生产 WARNING
    # 避免重复添加 handler
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(fh)

    # 控制台 handler：仅在有真实 stdout 时添加（pythonw 模式跳过，避免无意义输出）
    try:
        if sys.stdout is not None and sys.stdout.fileno() is not None and sys.stdout.fileno() >= 0:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.WARNING if not app.debug else logging.INFO)
            ch.setFormatter(fmt)
            if not any(isinstance(h, type(ch)) for h in root.handlers):
                root.addHandler(ch)
    except (ValueError, AttributeError, OSError):
        pass

    app.logger.setLevel(logging.INFO)  # 自家日志保持 INFO（不跟 root WARNING 走）
    return log_dir

# ============================================================
# 初始化
# ============================================================
app = Flask(__name__,
            template_folder=os.path.join(Config.RESOURCE_DIR, 'templates'),
            static_folder=os.path.join(Config.RESOURCE_DIR, 'static'))
app.config.from_object(Config)
# 调试：打印实际 template_folder，确认加载的是源码目录还是打包目录
print(f'[DEBUG] template_folder = {app.template_folder}', flush=True)
print(f'[DEBUG] sync.html exists = {os.path.exists(os.path.join(app.template_folder, "admin", "sync.html"))}', flush=True)
print(f'[DEBUG] base.html mtime = {os.path.getmtime(os.path.join(app.template_folder, "base.html"))}', flush=True)

# ============================================================
# SECRET_KEY 双保险：若 config 层（或未来改动）仍使它变成 None/空串，
# 则此处立刻 fallback 生成 + 持久化，避免 Flask session "The session is unavailable
# because no secret key was set" RuntimeError → 登录 POST 统一 500 的灾难级故障。
# ============================================================
def _fallback_ensure_secret_key(flask_app):
    existing = flask_app.config.get('SECRET_KEY')
    if existing and isinstance(existing, str) and len(existing) >= 32:
        return existing
    import secrets as _sec
    try:
        from config import _ensure_persistent_secret_key as _ensure
        data_dir = flask_app.config.get('DATA_DIR') or Config.DATA_DIR or BASE_DIR
        key = _ensure(data_dir)
        if key and len(key) >= 32:
            flask_app.config['SECRET_KEY'] = key
            if hasattr(Config, 'SECRET_KEY'):
                try: Config.SECRET_KEY = key
                except Exception: pass
            return key
    except Exception as e:
        flask_app.logger.warning('fallback _ensure_persistent_secret_key 失败: %s，改用当次随机', e)
    # 最后防线：内存随机密钥（重启后 session 会失效，但比崩强）
    emergency_key = _sec.token_hex(48)
    flask_app.config['SECRET_KEY'] = emergency_key
    return emergency_key

_fallback_ensure_secret_key(app)

# SESSION_PERMANENT 必须在 app 层显式打开（PERMANENT_SESSION_LIFETIME 也会生效），
# 避免"记住我"的 session.permanent=True 被 Flask 默认 SESSION_PERMANENT=False 反向覆盖。
if not app.config.get('SESSION_PERMANENT'):
    app.config['SESSION_PERMANENT'] = True

# 开发模式下开启模板自动重载：修改 templates/*.html 后无需重启进程即可生效。
# 打包后（frozen）禁用，避免每次请求 stat 文件的开销。
if not getattr(sys, 'frozen', False):
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True

# 日志（写入 exe 同级目录的 logs/ 下，保证可写）
LOG_DIR = _setup_logging(app)

# 确保上传目录 & 头像目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
AVATAR_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars')
os.makedirs(AVATAR_FOLDER, exist_ok=True)
# 背景图片上传目录
BG_IMAGE_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], 'bg')
os.makedirs(BG_IMAGE_FOLDER, exist_ok=True)
# 允许的头像扩展名
ALLOWED_AVATAR_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_BG_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['AVATAR_FOLDER'] = AVATAR_FOLDER

db = SQLAlchemy(app)

# ==================================================================
# 【PP3 · 性能】Gzip WSGI 中间件（手写 ≈40 行，避免引入 flask-compress 新依赖）
# 对 text/html / application/json / text/css / application/javascript / image/svg+xml
# 且大小 ≥ 1KB 的响应做 gzip 压缩，返回 Vary: Accept-Encoding + Content-Encoding: gzip
# ==================================================================
import gzip as _gzip
_GZIP_MIN_BYTES = 1024
_GZIP_TYPES = (
    'text/', 'application/json', 'application/javascript',
    'application/x-javascript', 'image/svg+xml', 'application/manifest+json',
)


class _GzipMiddleware:
    def __init__(self, wsgi_app):
        self.app = wsgi_app

    def __call__(self, environ, start_response):
        # 仅当客户端声明 Accept-Encoding: gzip 时才压缩
        accept = environ.get('HTTP_ACCEPT_ENCODING', '')
        if 'gzip' not in accept.lower():
            return self.app(environ, start_response)
        buf: list = []
        status: list = []
        headers: list = []
        exc_info_ref: list = [None]

        def my_start_response(s, h, exc_info=None):
            status.append(s)
            headers.extend(h[:])
            exc_info_ref[0] = exc_info
            return buf.append

        app_iter = self.app(environ, my_start_response)
        try:
            body = b''.join(buf) if buf else b''
            if not body:
                # 流式迭代器（send_file 常返回）：合并所有块再决定是否压缩
                collected = []
                for chunk in app_iter:
                    if chunk:
                        collected.append(bytes(chunk))
                body = b''.join(collected)
        finally:
            if hasattr(app_iter, 'close'):
                try: app_iter.close()
                except Exception: pass

        if not (status and headers):
            start_response('500 Internal Server Error',
                           [('Content-Type', 'text/plain; charset=utf-8')])
            return [b'WSGI middleware error: no status']

        hdrs_dict = {k.lower(): v for k, v in headers}
        ct = (hdrs_dict.get('content-type') or '').lower()
        cl_raw = hdrs_dict.get('content-length')
        clen = int(cl_raw) if cl_raw and cl_raw.isdigit() else len(body)
        already_encoded = hdrs_dict.get('content-encoding') or ''

        want_gzip = (
            not already_encoded
            and clen >= _GZIP_MIN_BYTES
            and any(t in ct for t in _GZIP_TYPES)
        )
        new_headers = [(k, v) for k, v in headers
                       if k.lower() not in ('content-length', 'content-encoding', 'vary')]
        if want_gzip:
            compressed = _gzip.compress(body, 6)
            new_headers.append(('Content-Encoding', 'gzip'))
            new_headers.append(('Content-Length', str(len(compressed))))
            # 保持原有 Vary 再叠加 Accept-Encoding
            vary_old = hdrs_dict.get('vary')
            if vary_old:
                if 'accept-encoding' not in vary_old.lower():
                    vary_old += ', Accept-Encoding'
                new_headers.append(('Vary', vary_old))
            else:
                new_headers.append(('Vary', 'Accept-Encoding'))
            write = start_response(status[0], new_headers, exc_info_ref[0])
            return [compressed]

        # 不压缩：原样回写，但补 Content-Length（WSGI 推荐）
        if 'content-length' not in {k.lower() for k, _ in new_headers}:
            new_headers.append(('Content-Length', str(len(body))))
        if hdrs_dict.get('vary'):
            new_headers.append(('Vary', hdrs_dict['vary']))
        write = start_response(status[0], new_headers, exc_info_ref[0])
        return [body]


app.wsgi_app = _GzipMiddleware(app.wsgi_app)


# ==================================================================
# 【PP4 · 性能】浏览量 view_count 的内存计数 + 后台线程 30s 批量 flush。
# 避免每次访问文章详情页都立刻 commit（SQLite 写者锁串行所有读，是大并发卡顿元凶）
# ==================================================================
import threading as _threading
_VC_COUNTER: dict = {}  # post_id -> int
_VC_LOCK = _threading.Lock()
_VC_STOP = _threading.Event()
_VC_FLUSH_INTERVAL = 30  # 秒
_vc_flusher_thread = None


def _vc_flush_now():
    """把内存中累计的 view_count 增量一次性写回 DB（批量 CASE WHEN，1 条 SQL）。
    在 sync 周期内若 DB 异常，绝不抛错影响请求线程，只是丢失本次 flush（下次继续）。"""
    snapshot = {}
    with _VC_LOCK:
        if _VC_COUNTER:
            snapshot = dict(_VC_COUNTER)
            _VC_COUNTER.clear()
    if not snapshot:
        return
    try:
        with app.app_context():
            cases = []
            ids = []
            for pid, inc in snapshot.items():
                if inc and isinstance(pid, int) and pid > 0:
                    cases.append(f'WHEN {int(pid)} THEN view_count + {int(inc)}')
                    ids.append(int(pid))
            if not ids:
                return
            ids_csv = ','.join(str(i) for i in ids)
            sql = (f'UPDATE post SET view_count = CASE id {" ".join(cases)} '
                   f'ELSE view_count END WHERE id IN ({ids_csv})')
            db.session.execute(db.text(sql))
            db.session.commit()
    except Exception as exc:
        app.logger.warning('view_count 批量 flush 失败（下次重试）: %s', exc)
        # 失败：把 snapshot 合并回内存计数器，避免丢计数
        with _VC_LOCK:
            for pid, inc in snapshot.items():
                _VC_COUNTER[pid] = _VC_COUNTER.get(pid, 0) + inc


def _vc_flusher_loop():
    """后台线程：每 30s 批量 flush；被 Event.set() 立刻唤醒也可（关机时）。"""
    while not _VC_STOP.is_set():
        _vc_flush_now()
        _VC_STOP.wait(_VC_FLUSH_INTERVAL)


def _vc_count_view(post_id: int):
    """详情页调用：只是内存 +1，不做任何 DB commit。"""
    if not isinstance(post_id, int) or post_id <= 0:
        return
    with _VC_LOCK:
        _VC_COUNTER[post_id] = _VC_COUNTER.get(post_id, 0) + 1


def _start_vc_flusher():
    """进程内只启动一次（waitress 多线程环境下也只起一个 flush 线程）。"""
    global _vc_flusher_thread, _GC_LOCK
    if _GC_LOCK is None:
        _GC_LOCK = _threading.Lock()
    if _vc_flusher_thread is None or not _vc_flusher_thread.is_alive():
        _vc_flusher_thread = _threading.Thread(
            target=_vc_flusher_loop, name='blog-vc-flusher', daemon=True)
        _vc_flusher_thread.start()


def _stop_vc_flusher():
    """退出前：Event.set() 立刻唤醒 flush 一次，确保最后 30s 的计数不丢。"""
    _VC_STOP.set()
    # Event.set() 打断 wait，循环会再执行一次 flush
    try:
        if _vc_flusher_thread and _vc_flusher_thread.is_alive():
            _vc_flusher_thread.join(timeout=5)
    except Exception:
        pass

# 启动时机：在 run_server() 内 init_db 之后立即调用 _start_vc_flusher()。


# ==================================================================
# 【PP3 · 性能】静态文件响应头：/static/、/avatars/、/bg/ → 7 天强缓存 + immutable
# 动态页不加（避免 flash 消息被浏览器缓存）。
# ==================================================================
@app.after_request
def _static_cache_control(response):
    path = request.environ.get('PATH_INFO') or request.path or ''
    is_static = (path.startswith('/static/')
                 or path.startswith('/avatars/')
                 or path.startswith('/bg/'))
    if is_static:
        response.headers['Cache-Control'] = 'public, max-age=604800, immutable'
        # 若已有 Last-Modified / ETag 就保留（Flask send_file 会自动带），不覆盖
    return response


# 数据库会话异常回滚钩子（防止单次数据库错误导致连接耗尽）
@app.teardown_appcontext
def shutdown_session(exception=None):
    if exception is not None:
        app.logger.warning('请求出现异常，回滚会话: %s', exception)
        db.session.rollback()
    db.session.remove()


# 全局异常处理：记录完整堆栈 + 返回友好页面
@app.errorhandler(Exception)
def handle_all_exception(e):
    code = getattr(e, 'code', 500)
    if isinstance(code, int) and code >= 500:
        app.logger.error(
            'HTTP %s 未捕获异常 | URL=%s | Method=%s | IP=%s\n%s',
            code, request.path, request.method,
            request.headers.get('X-Forwarded-For', request.remote_addr),
            traceback.format_exc())
    elif code == 404:
        # 404 不打印详细堆栈
        app.logger.info('404 Not Found: %s %s', request.method, request.path)
    try:
        tmpl = f'errors/{code}.html'
        return render_template(tmpl, error=str(e)[:200], code=code), code
    except Exception:
        try:
            return render_template('error.html', code=code, error=str(e)[:200]), code
        except Exception:
            return f'<h1>Error {code}</h1><p>{e}</p>', code


@app.route('/health')
def health_check():
    """健康检查接口：给守护脚本和运维监控用。"""
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify(status='ok', time=datetime.datetime.now().isoformat())
    except Exception as exc:
        app.logger.error('health check failed: %s', exc)
        return jsonify(status='error', error=str(exc)), 500


# ============================================================
# 数据模型（多对多：文章 <-> 标签）
# ============================================================
post_tags = db.Table(
    'post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)


class Post(db.Model):
    """博客文章"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.String(500))  # 摘要（可选，自动生成）
    content = db.Column(db.Text, nullable=False)  # Markdown 原文
    # 【PP4 · 性能】Markdown -> HTML 渲染结果缓存列，避免每次详情页 render_markdown 几十 ms
    # 写文章时自动写入；编辑后清空；详情页读时懒回填（一次性）。
    rendered_html = db.Column(db.Text)
    # 【同步】墓碑标记（软删），配合双向同步用；查询时默认 is_deleted=False
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                           onupdate=datetime.datetime.utcnow)
    published = db.Column(db.Boolean, default=True)
    view_count = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50))  # 分类（如：编程/生活/笔记）

    # 关联标签
    tags = db.relationship('Tag', secondary=post_tags,
                           backref=db.backref('posts', lazy='dynamic'))

    def __repr__(self):
        return f'<Post {self.title}>'


class Tag(db.Model):
    """标签"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    # 【同步】软删墓碑
    is_deleted = db.Column(db.Boolean, default=False)

    @staticmethod
    def slugify(name):
        """把标签名转成URL友好的slug"""
        s = re.sub(r'[^\w\s-]', '', name.strip().lower())
        s = re.sub(r'[-\s]+', '-', s)
        return s or 'tag'

    def __repr__(self):
        return f'<Tag {self.name}>'


class Profile(db.Model):
    """个人中心-博主资料（单例）"""
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(50), default='博主')
    title = db.Column(db.String(100))  # 职业/头衔，如「全栈开发工程师」
    bio = db.Column(db.String(500))   # 一句话简介
    about = db.Column(db.Text)        # 关于我（Markdown正文，替代旧about）
    avatar = db.Column(db.String(255))  # 头像文件路径
    location = db.Column(db.String(50))  # 所在地
    email = db.Column(db.String(120))
    github = db.Column(db.String(200))
    weibo = db.Column(db.String(200))
    zhihu = db.Column(db.String(200))
    juejin = db.Column(db.String(200))
    bilibili = db.Column(db.String(200))
    website = db.Column(db.String(200))
    tech_stack = db.Column(db.Text)   # 技术栈，逗号分隔
    career_years = db.Column(db.Integer, default=0)  # 工作年限
    bg_image = db.Column(db.String(500))     # 背景图片 URL（可选）
    bg_opacity = db.Column(db.Float, default=0.25)  # 背景图片透明度 0~1
    # 【同步】软删墓碑
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                           onupdate=datetime.datetime.utcnow)

    @property
    def avatar_url(self):
        if self.avatar:
            return url_for('serve_avatar', filename=self.avatar)
        # 默认头像：使用 DiceBear API 科技风头像
        seed = self.nickname or 'coder'
        return f'https://api.dicebear.com/7.x/bottts-neutral/svg?seed={seed}&backgroundColor=0ea5e9,06b6d4,38bdf8,6366f1,8b5cf6'

    @property
    def tech_list(self):
        if not self.tech_stack:
            return []
        return [s.strip() for s in re.split(r'[,，]', self.tech_stack) if s.strip()]

    def __repr__(self):
        return f'<Profile {self.nickname}>'


class Comment(db.Model):
    """文章评论（支持一级嵌套回复）"""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), index=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)  # 回复的父评论
    nickname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120))      # 可选，用于 Gravatar 头像
    website = db.Column(db.String(200))    # 可选个人站点
    content = db.Column(db.Text, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)   # 博主回复标记
    is_visible = db.Column(db.Boolean, default=True)  # 是否显示（可隐藏垃圾评论）
    # 【同步】软删墓碑
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # 关联
    # cascade='all, delete-orphan'：删除文章时级联删除其全部评论，
    # 避免 SQLAlchemy 默认把评论 post_id 置 NULL 而违反 NOT NULL 约束
    post = db.relationship('Post', backref=db.backref('comments', lazy='dynamic',
                                                      cascade='all, delete-orphan'))
    replies = db.relationship('Comment',
                              backref=db.backref('parent', remote_side=[id]),
                              lazy='dynamic', foreign_keys=[parent_id])

    @property
    def avatar_url(self):
        """Gravatar 头像（基于 email md5），失败回退到 DiceBear"""
        import hashlib
        if self.email:
            h = hashlib.md5(self.email.strip().lower().encode('utf-8')).hexdigest()
            return f'https://cravatar.cn/avatar/{h}?d=identicon&s=80'
        seed = (self.nickname or 'guest') + str(self.id)
        return f'https://api.dicebear.com/7.x/identicon/svg?seed={seed}'

    def __repr__(self):
        return f'<Comment #{self.id} on Post {self.post_id}>'


class Like(db.Model):
    """文章点赞（基于 IP+UA 指纹去重）"""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), index=True, nullable=False)
    fingerprint = db.Column(db.String(64), nullable=False)  # sha256(ip + ua)
    # 【同步】软删墓碑
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('post_id', 'fingerprint', name='uq_post_fingerprint'),)

    post = db.relationship('Post', backref=db.backref('likes', lazy='dynamic'))

    def __repr__(self):
        return f'<Like on Post {self.post_id}>'


class FriendLink(db.Model):
    """友情链接"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    avatar = db.Column(db.String(255))   # 头像/站点图标 URL（可选）
    sort_order = db.Column(db.Integer, default=0)  # 排序权重（小在前）
    is_visible = db.Column(db.Boolean, default=True)
    # 【同步】软删墓碑
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<FriendLink {self.name}>'


# ============================================================
# 工具函数
# ============================================================
def render_markdown(text):
    """Markdown -> HTML，带目录、代码高亮、表格等"""
    extensions = [
        FencedCodeExtension(),
        'tables',
        'sane_lists',
        TocExtension(permalink=True, toc_depth='2-4'),
        'codehilite',
        'nl2br',
    ]
    extension_configs = {
        'codehilite': {
            'css_class': 'codehilite',
            'linenums': False,
            'guess_lang': False,
        }
    }
    md = markdown.Markdown(
        extensions=extensions,
        extension_configs=extension_configs,
        output_format='html5'
    )
    return md.convert(text)


def generate_summary(content, length=180):
    """从Markdown内容生成摘要：去掉特殊符号，截取前N字"""
    # 去掉代码块
    text = re.sub(r'```.*?```', '', content, flags=re.S)
    # 去掉Markdown标记
    text = re.sub(r'[#*_`>\-\[\]!()]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > length:
        text = text[:length] + '...'
    return text


def generate_search_snippet(content, query, length=160):
    """从正文中提取包含搜索词的片段（用于搜索结果高亮预览）"""
    if not query or not content:
        return ''
    # 清理 Markdown 标记
    text = re.sub(r'```.*?```', '', content, flags=re.S)
    text = re.sub(r'[#*_`>\[\]!()]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # 不区分大小写定位匹配位置
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[:length] + '...' if len(text) > length else text
    # 以匹配词为中心截取片段
    half = max(0, length // 2 - len(query) // 2)
    start = max(0, idx - half)
    end = min(len(text), idx + len(query) + (length - half))
    snippet = text[start:end]
    if start > 0:
        snippet = '...' + snippet
    if end < len(text):
        snippet = snippet + '...'
    return snippet


def parse_front_matter(text):
    """
    解析 Markdown / YAML 文件中的 front-matter（--- 包裹的 YAML 头部）。
    返回 (metadata_dict, body_content)
    """
    if text.startswith('---'):
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', text, flags=re.S)
        if match:
            try:
                meta = yaml.safe_load(match.group(1)) or {}
                body = match.group(2)
                return meta, body
            except yaml.YAMLError:
                pass
    return {}, text


def allowed_file(filename):
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS'])


def highlight_text(text, query):
    """搜索高亮：把 text 中匹配 query 的子串包成 <mark class="search-hl">…</mark>"""
    if not text or not query:
        return text
    # 转义 HTML 特殊字符，避免 XSS / 模板破坏
    safe = (str(text).replace('&', '&amp;')
                       .replace('<', '&lt;')
                       .replace('>', '&gt;'))
    # 转义 query 中正则元字符，做不区分大小写全局替换
    pattern = re.escape(query)
    repl = lambda m: f'<mark class="search-hl">{m.group(0)}</mark>'
    return re.sub(pattern, repl, safe, flags=re.IGNORECASE)


def like_fingerprint():
    """生成访客指纹：sha256(IP + User-Agent)"""
    import hashlib
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'anon')
    ua = request.headers.get('User-Agent', '')
    return hashlib.sha256(f'{ip}|{ua}'.encode('utf-8')).hexdigest()


# 注册 Jinja 过滤器：搜索高亮
app.jinja_env.filters['highlight'] = highlight_text


def allowed_avatar(filename):
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXT)


def get_profile():
    """获取博主资料单例，不存在则创建默认"""
    p = Profile.query.first()
    if not p:
        p = Profile(
            nickname='Cyber Coder',
            title='全栈开发工程师 / AI 爱好者',
            bio='热爱编程，热爱生活。用代码点亮世界 ✨',
            tech_stack='Python, Flask, Vue, React, Docker, PostgreSQL, AI, FastAPI',
            location='中国 · 深圳',
            email='hello@example.com',
            github='https://github.com/your-username',
            juejin='https://juejin.cn/',
            career_years=5,
            about='''# 👋 你好，我是 Cyber Coder

我是一名热爱技术的全栈开发工程师，拥有 **5 年+** 的开发经验。

## 🚀 擅长领域

- **后端**：Python / Flask / FastAPI / Django
- **前端**：Vue / React / TypeScript
- **AI**：LangChain / RAG / 大模型应用
- **DevOps**：Docker / K8s / CI-CD

## 💡 我的信念

> 代码改变世界，分享让成长加速。

在这里我会记录我的技术探索、项目实战、生活思考。欢迎交流～ 🤝
''')
        db.session.add(p)
        db.session.commit()
    return p


def get_or_create_tag(tag_name):
    tag_name = tag_name.strip()
    if not tag_name:
        return None
    slug = Tag.slugify(tag_name)
    # 用 slug 查询（slug 是真正的唯一约束，且 slugify 后大小写统一）
    # 避免大小写不同但 slug 相同时触发 UNIQUE constraint failed
    tag = Tag.query.filter_by(slug=slug).first()
    if not tag:
        tag = Tag(name=tag_name, slug=slug)
        db.session.add(tag)
        try:
            db.session.flush()
        except Exception:
            # 并发或重复时回退查询
            db.session.rollback()
            tag = Tag.query.filter_by(slug=slug).first()
    return tag


def login_required(view):
    """登录装饰器（登录功能已移除，直接放行）。

    v1.3 起博客不再需要登录：管理后台对所有访问者开放（个人自用场景），
    因此本装饰器保留函数名以兼容既有 @login_required 标注，但不再做任何
    会话校验与跳转。
    """
    return view


# ============================================================
# 上下文 & 错误处理
# ============================================================
@app.context_processor
def inject_globals():
    """全局模板变量（PP2 性能版）。

    策略（性能从强到弱）：
      1) 若请求是静态路径（/static/* /avatars/* /bg/* /health）→ **完全短路**，
         只返回常量字段，不做任何数据库查询。这避免了 Vditor 10+ 静态子请求
         触发 12×10=120 条 SQL 的"SQL 风暴"问题。
      2) 否则查 TTL 缓存：登录已移除，统一按 cache_key='anon' 分键，
         5 秒内请求复用同一 value；写路径（保存/删除）显式 invalidate_globals_cache()。
      3) TTL miss 时才执行真实 SQL 查询集合（profile / tags / categories /
         archives / stats / friend_links），极端容错 + 日志兜底。
    """
    # ---- 变量默认值 ----
    site_year = datetime.date.today().year
    codehilite_css = _CODEHILITE_CSS  # <-- 模块级常量，不再每次 HtmlFormatter

    # ---- 1) 静态路径：极快短路 ----
    try:
        _p = request.path
    except Exception:
        _p = ''
    if any(_p.startswith(x) for x in ('/static/', '/avatars/', '/bg/', '/health')):
        # 注意：所有 heavy_keys 对应的值必须是 falsy（None/[]/{}），避免测试/缓存误判
        return {
            'site_year': site_year,
            'site_name': '个人博客',
            'codehilite_css': codehilite_css,
            # 显式写 falsy 值，保证模板里 {% if profile %} 仍安全工作，
            # 同时也满足 TDD 测试"静态路径不返回任何实际 DB 数据"的语义。
            'profile': None,
            'all_tags': [],
            'all_categories': [],
            'archives': [],
            'stats': {},       # <-- 空 dict（falsy），不是非空 dict
            'friend_links': [],
        }

    # ---- 2) 动态路径：TTL 缓存 ----
    # 登录功能已移除，不再区分 admin / anon 视图，统一按同一份缓存计算
    cache_key = 'anon'
    now = _time.time()
    if _GC_LOCK is None:
        pass  # 极早期初始化时锁还没建（不会发生实际并发，跳过锁即可）
    # 读缓存（简单 dict thread-safe 读；过期或不存在都重算）
    cached = _GLOBALS_CACHE.get(cache_key)
    if cached and cached[0] > now:
        # HIT：直接返回缓存副本（为安全不返回引用；但 dict 内都是不可变/只读值，直接共享 OK）
        return cached[1]

    # ---- 3) MISS：真实计算 ----
    profile = None
    tag_counts = []
    categories = []
    archives = []
    stats = {
        'total_posts': 0, 'total_tags': 0, 'total_views': 0,
        'total_categories': 0, 'total_comments': 0, 'total_likes': 0,
    }
    friend_links = []
    try:
        try:
            profile = get_profile()
        except Exception:
            profile = None

        try:
            tag_counts = db.session.query(
                Tag, db.func.count(post_tags.c.post_id).label('count')
            ).outerjoin(post_tags).group_by(Tag.id).order_by(db.desc('count')).all()
        except Exception:
            tag_counts = []

        try:
            categories = [c[0] for c in db.session.query(
                Post.category.distinct()).filter(Post.category.isnot(None)).all()
                          if c[0]]
        except Exception:
            categories = []

        try:
            archives = db.session.query(
                db.func.strftime('%Y-%m', Post.created_at).label('ym'),
                db.func.count(Post.id).label('count')
            ).filter(Post.published == True).group_by('ym').order_by(db.desc('ym')).all()
        except Exception:
            archives = []

        try:
            stats = {
                'total_posts': Post.query.filter_by(published=True).count(),
                'total_tags': Tag.query.count(),
                'total_views': db.session.query(db.func.sum(Post.view_count)).scalar() or 0,
                'total_categories': len(categories),
                'total_comments': Comment.query.filter_by(is_visible=True).count(),
                'total_likes': Like.query.count(),
            }
        except Exception:
            pass

        try:
            friend_links = FriendLink.query.filter_by(is_visible=True).order_by(
                FriendLink.sort_order.asc(), FriendLink.id.asc()).all()
        except Exception:
            friend_links = []
    except Exception:
        app.logger.exception('inject_globals 出现未预期异常，已兜底继续渲染')

    if profile is not None and getattr(profile, 'nickname', None):
        site_name = profile.nickname + ' · 个人博客'
    else:
        site_name = '个人博客'

    value = {
        'all_tags': tag_counts,
        'all_categories': categories,
        'archives': archives,
        'profile': profile,
        'stats': stats,
        'friend_links': friend_links,
        'site_name': site_name,
        'site_year': site_year,
        'codehilite_css': codehilite_css,
    }
    expire_at = now + _GLOBALS_TTL_SEC
    try:
        # TTL 写缓存（不互斥：多线程同时重算 OK，只是覆盖为相同值）
        _GLOBALS_CACHE[cache_key] = (expire_at, value)
    except Exception:
        pass
    return value


# 头像静态文件路由
@app.route('/avatars/<path:filename>')
def serve_avatar(filename):
    return send_from_directory(AVATAR_FOLDER, filename, as_attachment=False)


# 背景图片静态文件路由
@app.route('/bg/<path:filename>')
def serve_bg_image(filename):
    return send_from_directory(BG_IMAGE_FOLDER, filename, as_attachment=False)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    return render_template('errors/500.html'), 500


# ============================================================
# 公共页面路由
# ============================================================
@app.route('/')
def index():
    """首页：文章列表"""
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()

    q = Post.query.filter_by(published=True)
    if query:
        q = q.filter(db.or_(
            Post.title.ilike(f'%{query}%'),
            Post.content.ilike(f'%{query}%'),
            Post.summary.ilike(f'%{query}%')
        ))
    if category:
        q = q.filter(Post.category == category)

    pagination = q.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False
    )

    # 生成摘要（若数据库未存）
    for post in pagination.items:
        if not post.summary:
            post.summary = generate_summary(post.content)

    # 搜索时：为标题/摘要未命中但正文命中的文章生成正文片段，用于高亮预览
    if query:
        ql = query.lower()
        for post in pagination.items:
            in_title = ql in (post.title or '').lower()
            in_summary = ql in (post.summary or '').lower()
            if not in_title and not in_summary:
                post.search_snippet = generate_search_snippet(post.content, query)
            else:
                post.search_snippet = ''

    return render_template('index.html',
                           posts=pagination.items,
                           pagination=pagination,
                           query=query,
                           active_category=category)


@app.route('/post/<int:post_id>/')
def post_detail(post_id):
    """文章详情（PP4 · 性能三件套：VC 内存计数 + Markdown 缓存 + 评论批量查询 1 次）"""
    post = Post.query.get_or_404(post_id)
    # 登录功能已移除：未发布（草稿）文章一律不对外展示
    if not post.published:
        abort(404)

    # ---- 【PP4-3】浏览量计数：不 commit DB，只是内存 dict +1，30 秒后台线程批量 flush ----
    _vc_count_view(post.id)

    # ---- 【PP4-1】Markdown 渲染缓存：优先读 rendered_html 列，缺失时懒回填（首次访问写入）----
    #    写文章时自动填，老文章升级无该值时这里一次性回填。
    html = None
    if isinstance(post.rendered_html, str) and post.rendered_html.strip():
        html = post.rendered_html
    if not html:
        html = render_markdown(post.content or '')
        # 懒回填（异常不影响响应）：下一次访问就命中缓存列
        try:
            Post.query.filter_by(id=post.id).update(
                {'rendered_html': html}, synchronize_session=False)
            db.session.commit()
        except Exception:
            db.session.rollback()

    # 上下篇
    prev_post = Post.query.filter(
        Post.id < post.id, Post.published == True
    ).order_by(Post.id.desc()).first()
    next_post = Post.query.filter(
        Post.id > post.id, Post.published == True
    ).order_by(Post.id.asc()).first()

    # ---- 【PP4-2】评论批量查询（1 条 SQL 拿所有评论，Python 分组）----
    # 旧实现：
    #   1) top_comments = WHERE post_id=? AND parent_id IS NULL (1 次)
    #   2) for each top: replies.filter_by().all() (N 次 — N+1)
    #   3) Comment.query.filter_by().all() 再 count 一次
    # 新实现：
    #   1 条 SELECT * FROM comment WHERE post_id=? AND is_visible=1 ORDER BY created_at
    #   → Python dict 分组成 tree → comment_count = len(all_comments)（内存 O(1)）
    all_visible = (Comment.query
                   .filter_by(post_id=post.id, is_visible=True)
                   .order_by(Comment.created_at.asc())
                   .all())
    by_parent: dict = {}
    for c in all_visible:
        pid = c.parent_id or None
        by_parent.setdefault(pid, []).append(c)
    top_comments = by_parent.get(None, [])
    comments_tree = [
        {'comment': c, 'replies': by_parent.get(c.id, [])}
        for c in top_comments
    ]
    comment_count = len(all_visible)

    # 点赞（仍 2 条查询，因为 one query count + one query me，数据量小）
    like_count = Like.query.filter_by(post_id=post.id).count()
    liked = Like.query.filter_by(
        post_id=post.id, fingerprint=like_fingerprint()
    ).first() is not None

    return render_template('post_detail.html',
                           post=post,
                           html_content=html,
                           prev_post=prev_post,
                           next_post=next_post,
                           comments_tree=comments_tree,
                           comment_count=comment_count,
                           like_count=like_count,
                           liked=liked)


# ------------------------------------------------------------
# 文章评论
# ------------------------------------------------------------
@app.route('/post/<int:post_id>/comment/', methods=['POST'])
def post_comment(post_id):
    """提交评论"""
    post = Post.query.get_or_404(post_id)
    if not post.published:
        abort(404)

    nickname = request.form.get('nickname', '').strip()
    email = request.form.get('email', '').strip()
    website = request.form.get('website', '').strip()
    content = request.form.get('content', '').strip()
    parent_id = request.form.get('parent_id', type=int)

    if not nickname or not content:
        flash('昵称和评论内容不能为空', 'danger')
        return redirect(url_for('post_detail', post_id=post_id) + '#comments')

    # 简单长度限制
    if len(nickname) > 50 or len(content) > 2000:
        flash('昵称或评论内容过长', 'danger')
        return redirect(url_for('post_detail', post_id=post_id) + '#comments')

    # 父评论必须存在且属于同一篇文章
    if parent_id:
        parent = Comment.query.filter_by(id=parent_id, post_id=post_id).first()
        if not parent:
            flash('回复的评论不存在', 'danger')
            return redirect(url_for('post_detail', post_id=post_id) + '#comments')

    # 登录功能已移除：评论一律按访客身份记录，不再有"博主身份"标记
    is_admin = False

    comment = Comment(
        post_id=post_id,
        parent_id=parent_id,
        nickname=nickname,
        email=email or None,
        website=website or None,
        content=content,
        is_admin=is_admin,
        is_visible=True,
    )
    db.session.add(comment)
    db.session.commit()
    flash('评论发布成功！', 'success')
    return redirect(url_for('post_detail', post_id=post_id) + '#comment-' + str(comment.id))


# ------------------------------------------------------------
# 文章点赞（JSON 接口，支持切换）
# ------------------------------------------------------------
@app.route('/post/<int:post_id>/like/', methods=['POST'])
def post_like(post_id):
    """点赞 / 取消点赞（基于访客指纹去重）"""
    post = Post.query.get_or_404(post_id)
    if not post.published:
        return jsonify({'ok': False, 'error': '文章不可点赞'}), 404

    fp = like_fingerprint()
    existing = Like.query.filter_by(post_id=post_id, fingerprint=fp).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        count = Like.query.filter_by(post_id=post_id).count()
        return jsonify({'ok': True, 'liked': False, 'count': count})
    else:
        like = Like(post_id=post_id, fingerprint=fp)
        db.session.add(like)
        db.session.commit()
        count = Like.query.filter_by(post_id=post_id).count()
        return jsonify({'ok': True, 'liked': True, 'count': count})


# ------------------------------------------------------------
# 友情链接
# ------------------------------------------------------------
@app.route('/links/')
@app.route('/friend_links/')
def friend_links():
    """友情链接公开页"""
    links = FriendLink.query.filter_by(is_visible=True).order_by(
        FriendLink.sort_order.asc(), FriendLink.id.asc()).all()
    return render_template('friend_links.html', links=links)


@app.route('/tag/<slug>/')
def tag_posts(slug):
    """按标签查看（支持在标签下进一步搜索）"""
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '').strip()

    q = tag.posts.filter_by(published=True)
    if query:
        q = q.filter(db.or_(
            Post.title.ilike(f'%{query}%'),
            Post.content.ilike(f'%{query}%'),
            Post.summary.ilike(f'%{query}%')
        ))
    pagination = q.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False
    )
    for post in pagination.items:
        if not post.summary:
            post.summary = generate_summary(post.content)
    # 搜索时：为标题/摘要未命中但正文命中的文章生成正文片段
    if query:
        ql = query.lower()
        for post in pagination.items:
            in_title = ql in (post.title or '').lower()
            in_summary = ql in (post.summary or '').lower()
            post.search_snippet = '' if (in_title or in_summary) else generate_search_snippet(post.content, query)
    return render_template('tag_posts.html',
                           tag=tag,
                           posts=pagination.items,
                           pagination=pagination,
                           query=query)


@app.route('/tags/')
def all_tags():
    """所有标签页"""
    tag_counts = db.session.query(
        Tag, db.func.count(post_tags.c.post_id).label('count')
    ).outerjoin(post_tags).group_by(Tag.id).order_by(db.desc('count')).all()
    return render_template('tags.html', tag_counts=tag_counts)


@app.route('/archive/')
def archive_index():
    """总归档页：按月份分组的完整时间线"""
    rows = db.session.query(
        Post.id, Post.title, Post.summary, Post.category, Post.created_at,
        Post.published, Post.view_count
    ).filter(Post.published == True).order_by(Post.created_at.desc()).all()
    # 按 ym 分组
    from collections import OrderedDict
    groups = OrderedDict()
    counts = {}
    for r in rows:
        ym = r.created_at.strftime('%Y-%m')
        groups.setdefault(ym, []).append(r)
        counts[ym] = counts.get(ym, 0) + 1
    return render_template('archive_index.html',
                           groups=groups,
                           counts=counts,
                           total_posts=len(rows))


@app.route('/archive/<ym>/')
def archive(ym):
    """按月归档"""
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.filter(
        Post.published == True,
        db.func.strftime('%Y-%m', Post.created_at) == ym
    ).order_by(Post.created_at.desc()).paginate(
        page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False
    )
    for post in pagination.items:
        if not post.summary:
            post.summary = generate_summary(post.content)
    return render_template('archive.html',
                           ym=ym,
                           posts=pagination.items,
                           pagination=pagination)


@app.route('/about/')
def about():
    """关于页面（复用 Profile.about 渲染）"""
    profile = get_profile()
    about_html = ''
    if profile.about:
        about_html = render_markdown(profile.about)
    return render_template('about.html',
                           profile=profile,
                           about_html=about_html)


@app.route('/profile/')
def profile_home():
    """个人中心主页"""
    profile = get_profile()
    # 博主最新文章
    latest_posts = Post.query.filter_by(published=True).order_by(
        Post.created_at.desc()).limit(6).all()
    for p in latest_posts:
        if not p.summary:
            p.summary = generate_summary(p.content)
    # 热门文章（根据阅读量）
    hot_posts = Post.query.filter_by(published=True).order_by(
        Post.view_count.desc()).limit(5).all()
    # about 正文渲染
    about_html = render_markdown(profile.about) if profile.about else ''
    return render_template('profile.html',
                           profile=profile,
                           latest_posts=latest_posts,
                           hot_posts=hot_posts,
                           about_html=about_html)


# ============================================================
# 管理后台
# ============================================================
@app.route('/admin/')
@login_required
def admin_dashboard():
    """后台首页：统计 & 文章列表"""
    total_posts = Post.query.count()
    published = Post.query.filter_by(published=True).count()
    total_tags = Tag.query.count()
    total_views = db.session.query(db.func.sum(Post.view_count)).scalar() or 0
    total_comments = Comment.query.count()
    total_likes = Like.query.count()

    posts = Post.query.order_by(Post.created_at.desc()).limit(20).all()
    return render_template('admin/dashboard.html',
                           total_posts=total_posts,
                           published=published,
                           total_tags=total_tags,
                           total_views=total_views,
                           total_comments=total_comments,
                           total_likes=total_likes,
                           posts=posts)


@app.route('/admin/profile/', methods=['GET', 'POST'])
@login_required
def admin_profile():
    """后台编辑博主资料 + 上传头像"""
    profile = get_profile()

    if request.method == 'POST':
        profile.nickname = request.form.get('nickname', '').strip() or '博主'
        profile.title = request.form.get('title', '').strip()
        profile.bio = request.form.get('bio', '').strip()
        profile.about = request.form.get('about', '').strip()
        profile.location = request.form.get('location', '').strip()
        profile.email = request.form.get('email', '').strip()
        profile.github = request.form.get('github', '').strip()
        profile.weibo = request.form.get('weibo', '').strip()
        profile.zhihu = request.form.get('zhihu', '').strip()
        profile.juejin = request.form.get('juejin', '').strip()
        profile.bilibili = request.form.get('bilibili', '').strip()
        profile.website = request.form.get('website', '').strip()
        profile.tech_stack = request.form.get('tech_stack', '').strip()
        try:
            profile.career_years = int(request.form.get('career_years') or 0)
        except (TypeError, ValueError):
            profile.career_years = 0

        # 处理头像上传
        avatar_file = request.files.get('avatar')
        if avatar_file and avatar_file.filename:
            if not allowed_avatar(avatar_file.filename):
                flash('头像仅支持 png/jpg/jpeg/gif/webp', 'danger')
                return redirect(request.url)
            ext = avatar_file.filename.rsplit('.', 1)[1].lower()
            save_name = f"avatar_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{ext}"
            # 移除旧头像
            if profile.avatar:
                old_path = os.path.join(AVATAR_FOLDER, profile.avatar)
                try:
                    if os.path.isfile(old_path):
                        os.remove(old_path)
                except OSError:
                    pass
            avatar_file.save(os.path.join(AVATAR_FOLDER, save_name))
            profile.avatar = save_name

        # 移除头像
        if request.form.get('remove_avatar'):
            if profile.avatar:
                old_path = os.path.join(AVATAR_FOLDER, profile.avatar)
                try:
                    if os.path.isfile(old_path):
                        os.remove(old_path)
                except OSError:
                    pass
                profile.avatar = None

        # 背景图片设置（清除 > 本地上传 > URL 输入框）
        if request.form.get('clear_bg'):
            # 清除背景图：删除旧文件并置空
            if profile.bg_image and profile.bg_image.startswith('/bg/'):
                old = os.path.join(BG_IMAGE_FOLDER, os.path.basename(profile.bg_image))
                try:
                    if os.path.isfile(old):
                        os.remove(old)
                except OSError:
                    pass
            profile.bg_image = None
        else:
            bg_file = request.files.get('bg_image_file')
            if bg_file and bg_file.filename:
                ext = secure_filename(bg_file.filename).rsplit('.', 1)[-1].lower()
                if ext in ALLOWED_BG_EXT:
                    # 删除旧背景图文件
                    if profile.bg_image and profile.bg_image.startswith('/bg/'):
                        old = os.path.join(BG_IMAGE_FOLDER, os.path.basename(profile.bg_image))
                        try:
                            if os.path.isfile(old):
                                os.remove(old)
                        except OSError:
                            pass
                    save_name = f"bg_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(bg_file.filename)}"
                    bg_file.save(os.path.join(BG_IMAGE_FOLDER, save_name))
                    profile.bg_image = f"/bg/{save_name}"
                else:
                    flash('背景图片格式不支持，仅支持 png/jpg/jpeg/gif/webp', 'error')
            else:
                # 没有上传文件时，使用 URL 输入框的值
                profile.bg_image = request.form.get('bg_image', '').strip() or None
        try:
            profile.bg_opacity = max(0.0, min(1.0, float(request.form.get('bg_opacity') or 0.25)))
        except (TypeError, ValueError):
            profile.bg_opacity = 0.25

        db.session.commit()
        flash('个人资料已更新！', 'success')
        return redirect(url_for('admin_profile'))

    return render_template('admin/profile_edit.html', profile=profile)


# ------------------------------------------------------------
# 后台：友情链接管理
# ------------------------------------------------------------
@app.route('/admin/links/')
@login_required
def admin_links():
    """友链列表管理"""
    links = FriendLink.query.order_by(
        FriendLink.sort_order.asc(), FriendLink.id.asc()).all()
    return render_template('admin/links.html', links=links)


@app.route('/admin/links/create/', methods=['POST'])
@login_required
def admin_link_create():
    name = request.form.get('name', '').strip()
    url = request.form.get('url', '').strip()
    if not name or not url:
        flash('名称和 URL 必填', 'danger')
        return redirect(url_for('admin_links'))
    # 简单校验 URL
    if not re.match(r'^https?://', url):
        flash('URL 必须以 http:// 或 https:// 开头', 'danger')
        return redirect(url_for('admin_links'))
    link = FriendLink(
        name=name,
        url=url,
        description=request.form.get('description', '').strip() or None,
        avatar=request.form.get('avatar', '').strip() or None,
        sort_order=request.form.get('sort_order', type=int) or 0,
        is_visible=bool(request.form.get('is_visible')),
    )
    db.session.add(link)
    db.session.commit()
    flash(f'友链「{name}」已添加', 'success')
    return redirect(url_for('admin_links'))


@app.route('/admin/links/<int:link_id>/update/', methods=['POST'])
@login_required
def admin_link_update(link_id):
    link = FriendLink.query.get_or_404(link_id)
    name = request.form.get('name', '').strip()
    url = request.form.get('url', '').strip()
    if not name or not url:
        flash('名称和 URL 必填', 'danger')
        return redirect(url_for('admin_links'))
    if not re.match(r'^https?://', url):
        flash('URL 必须以 http:// 或 https:// 开头', 'danger')
        return redirect(url_for('admin_links'))
    link.name = name
    link.url = url
    link.description = request.form.get('description', '').strip() or None
    link.avatar = request.form.get('avatar', '').strip() or None
    link.sort_order = request.form.get('sort_order', type=int) or 0
    link.is_visible = bool(request.form.get('is_visible'))
    db.session.commit()
    flash(f'友链「{name}」已更新', 'success')
    return redirect(url_for('admin_links'))


@app.route('/admin/links/<int:link_id>/delete/', methods=['POST'])
@login_required
def admin_link_delete(link_id):
    link = FriendLink.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    flash(f'友链「{link.name}」已删除', 'info')
    return redirect(url_for('admin_links'))


@app.route('/admin/post/new/', methods=['GET', 'POST'])
@login_required
def post_new():
    """新建文章（在线编辑器）"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '')
        summary = request.form.get('summary', '').strip()
        category = request.form.get('category', '').strip()
        published = bool(request.form.get('published'))
        tag_names = [t.strip() for t in
                     request.form.get('tags', '').split(',') if t.strip()]

        if not title or not content:
            flash('标题和内容必填', 'danger')
            return redirect(url_for('post_new'))

        post = Post(
            title=title,
            content=content,
            summary=summary or generate_summary(content),
            category=category or None,
            published=published,
        )
        for name in tag_names:
            tag = get_or_create_tag(name)
            if tag:
                post.tags.append(tag)

        db.session.add(post)
        db.session.commit()
        flash('文章发布成功！', 'success')
        return redirect(url_for('post_detail', post_id=post.id))

    return render_template('admin/post_form.html', post=None)


@app.route('/admin/post/<int:post_id>/edit/', methods=['GET', 'POST'])
@login_required
def post_edit(post_id):
    """编辑文章"""
    post = Post.query.get_or_404(post_id)
    if request.method == 'POST':
        post.title = request.form.get('title', '').strip()
        post.content = request.form.get('content', '')
        post.summary = request.form.get('summary', '').strip() or generate_summary(post.content)
        post.category = request.form.get('category', '').strip() or None
        post.published = bool(request.form.get('published'))
        post.updated_at = datetime.datetime.utcnow()

        # 重新设置标签
        tag_names = [t.strip() for t in
                     request.form.get('tags', '').split(',') if t.strip()]
        post.tags.clear()
        for name in tag_names:
            tag = get_or_create_tag(name)
            if tag:
                post.tags.append(tag)

        db.session.commit()
        flash('文章已更新！', 'success')
        return redirect(url_for('post_detail', post_id=post.id))

    tag_str = ','.join([t.name for t in post.tags])
    return render_template('admin/post_form.html', post=post, tag_str=tag_str)


@app.route('/admin/post/<int:post_id>/delete/', methods=['POST'])
@login_required
def post_delete(post_id):
    post = Post.query.get_or_404(post_id)
    # 先清理该文章的点赞记录（Like 无 relationship 级联，不显式删除会残留孤儿行）
    Like.query.filter_by(post_id=post.id).delete(synchronize_session=False)
    # 评论由 Comment.post relationship 的 cascade='all, delete-orphan' 级联删除
    db.session.delete(post)
    db.session.commit()
    flash('文章已删除', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/post/<int:post_id>/toggle/', methods=['POST'])
@login_required
def post_toggle_publish(post_id):
    post = Post.query.get_or_404(post_id)
    post.published = not post.published
    db.session.commit()
    status = '已发布' if post.published else '已下架'
    flash(f'{status}', 'info')
    return redirect(url_for('admin_dashboard'))


# ============================================================
# 文件上传导入
# ============================================================
@app.route('/admin/upload/', methods=['GET', 'POST'])
@login_required
def upload_file():
    """上传 .md / .yaml 文件导入成文章"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('请选择文件', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('未选择文件', 'danger')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash(f'仅支持格式: {", ".join(app.config["ALLOWED_EXTENSIONS"])}', 'danger')
            return redirect(request.url)

        try:
            raw = file.read().decode('utf-8-sig')  # 兼容带BOM的UTF-8
            ext = file.filename.rsplit('.', 1)[1].lower()

            # ======== .yaml / .yml：纯YAML格式 ========
            if ext in ('yaml', 'yml'):
                data = yaml.safe_load(raw)
                if isinstance(data, dict):
                    # 单篇文章
                    posts_to_create = [data]
                elif isinstance(data, list):
                    # 多篇文章列表
                    posts_to_create = data
                else:
                    flash('YAML 格式错误：需要对象或数组', 'danger')
                    return redirect(request.url)

                for item in posts_to_create:
                    if not isinstance(item, dict):
                        continue
                    title = str(item.get('title') or item.get('name') or '').strip()
                    content = str(item.get('content') or item.get('body') or
                                  item.get('text') or '').strip()
                    if not title or not content:
                        continue
                    summary = str(item.get('summary') or item.get('excerpt') or
                                  '').strip()
                    category = str(item.get('category') or item.get('type') or
                                   '').strip()
                    published = bool(item.get('published', True))
                    tag_input = item.get('tags') or item.get('tag') or []
                    if isinstance(tag_input, str):
                        tag_names = [t.strip() for t in re.split(r'[,，]', tag_input) if t.strip()]
                    else:
                        tag_names = [str(t).strip() for t in tag_input if str(t).strip()]

                    post = Post(
                        title=title,
                        content=content,
                        summary=summary or generate_summary(content),
                        category=category or None,
                        published=published,
                    )
                    for name in tag_names:
                        tag = get_or_create_tag(name)
                        if tag:
                            post.tags.append(tag)
                    db.session.add(post)
                db.session.commit()
                flash('YAML 文件导入成功！', 'success')
                return redirect(url_for('admin_dashboard'))

            # ======== .md / .markdown：Markdown，支持 front-matter ========
            else:
                meta, body = parse_front_matter(raw)

                # 从front-matter取字段，没取到的给默认
                title = ''
                if isinstance(meta, dict):
                    title = str(meta.get('title') or '').strip()
                    summary = str(meta.get('summary') or meta.get('excerpt') or '').strip()
                    category = str(meta.get('category') or meta.get('type') or '').strip()
                    published = bool(meta.get('published', True))
                    date_str = meta.get('date') or meta.get('created') or meta.get('datetime')
                    tag_input = meta.get('tags') or meta.get('tag') or []
                    if isinstance(tag_input, str):
                        tag_names = [t.strip() for t in re.split(r'[,，]', tag_input) if t.strip()]
                    else:
                        tag_names = [str(t).strip() for t in tag_input if str(t).strip()]
                else:
                    summary = category = ''
                    published = True
                    date_str = None
                    tag_names = []

                # 标题未指定：用第一个 # 标题，或文件名
                if not title:
                    m = re.match(r'\s*#\s*(.+?)\s*\n', body)
                    if m:
                        title = m.group(1).strip()
                        body = body[m.end():]  # 去掉首行标题
                if not title:
                    # 文件名（去掉扩展名）
                    title = os.path.splitext(secure_filename(file.filename))[0]

                post = Post(
                    title=title,
                    content=body.strip(),
                    summary=summary or generate_summary(body),
                    category=category or None,
                    published=published,
                )
                # 处理指定日期
                if date_str:
                    try:
                        from dateutil import parser as date_parser
                        post.created_at = date_parser.parse(str(date_str))
                    except Exception:
                        pass

                for name in tag_names:
                    tag = get_or_create_tag(name)
                    if tag:
                        post.tags.append(tag)

                db.session.add(post)
                db.session.commit()

                # 把文件也保存到 uploads
                fname = secure_filename(file.filename)
                save_name = f"{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{fname}"
                with open(os.path.join(app.config['UPLOAD_FOLDER'], save_name), 'wb') as f:
                    file.seek(0)
                    f.write(file.read())

                flash('Markdown 文件导入成功！', 'success')
                return redirect(url_for('post_detail', post_id=post.id))

        except UnicodeDecodeError:
            flash('文件编码错误，请使用 UTF-8 编码', 'danger')
        except yaml.YAMLError as e:
            flash(f'YAML 解析错误：{e}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'导入失败：{e}', 'danger')

        return redirect(request.url)

    return render_template('admin/upload.html')


# ============================================================
# ============================================================
# Gitee 云同步：零门槛 · 新手向导（个人 Gitee）+ 账号配置
# 说明：备份/恢复模块已并入同步模块（push = 备份 / pull = 恢复），
#       本区只保留新手向导所需的 4 个 JSON API 与常量。
# ============================================================
import gitee_backup as _gb

# Gitee 私人令牌生成页（个人账号专用，无需创建第三方 OAuth App）
GITEE_NEW_TOKEN_URL = (
    'https://gitee.com/profile/personal_access_tokens/new'
    '?description=%E4%B8%AA%E4%BA%BA%E5%8D%9A%E5%AE%A2%E6%A1%8C%E9%9D%A2%E7%89%88'
    '&scope=projects'
)
GITEE_NEW_REPO_URL = 'https://gitee.com/projects/new'


# ==================== 零门槛 · 新手向导 JSON APIs ====================

@app.route('/admin/sync/bootstrap_user', methods=['POST'])
@login_required
def admin_sync_bootstrap_user():
    """AJAX：新手向导步骤② 粘贴令牌 → 验证并返回用户信息（login/name/头像）。

    前端若成功会自动把「所有者」字段填成 Gitee URL 用户名，
    避免新手把昵称当用户名填错（昵称与 URL 用户名经常不一致）。
    """
    token = (request.form.get('token') or request.json.get('token')
             if request.is_json else request.form.get('token')) or ''
    token = (token or '').strip()
    if not token:
        return jsonify({'ok': False, 'error': '令牌为空，请先把 Gitee 页面生成的 32 位令牌字符串粘贴到这里。'}), 400
    ok, info = _gb.verify_token_and_get_user(token)
    if not ok:
        return jsonify({'ok': False, 'error': info.get('error', '令牌验证失败')}), 400
    return jsonify({'ok': True, 'user': info})


@app.route('/admin/sync/list_repos', methods=['POST'])
@login_required
def admin_sync_list_repos():
    """AJAX：新手向导步骤③ 列出用户名下所有仓库（用于下拉选择）。"""
    token = (request.form.get('token') or '').strip()
    if request.is_json:
        data = request.get_json(silent=True) or {}
        token = (data.get('token') or token or '').strip()
    if not token:
        return jsonify({'ok': False, 'error': '缺少令牌，请先完成步骤②验证令牌。'}), 400
    ok, repos = _gb.list_my_repos(token)
    if not ok:
        return jsonify({'ok': False, 'error': (repos[0].get('error')
                                               if isinstance(repos, list) and repos else '列表失败')}), 502
    return jsonify({'ok': True, 'repos': repos})


@app.route('/admin/sync/create_repo', methods=['POST'])
@login_required
def admin_sync_create_repo():
    """AJAX：新手向导步骤③ 一键新建一个私有同步仓库，并把配置写到本地。

    创建成功即自动写入 token/owner/repo/branch/path_prefix/enabled，
    相当于「走完向导即开启云同步」。
    """
    data = request.get_json(silent=True) if request.is_json else None
    if data is None:
        data = request.form.to_dict()
    token = (data.get('token') or '').strip()
    owner = (data.get('owner') or '').strip()
    repo_name = (data.get('repo_name') or '').strip() or '个人博客备份'
    if not token or not owner:
        return jsonify({'ok': False, 'error': '参数不完整：需要令牌 + 归属者用户名（上一步已自动填入）。'}), 400
    ok, info = _gb.ensure_repo(token, owner, repo_name, private=True, auto_init=True)
    if not ok:
        return jsonify({'ok': False, 'error': info.get('error', '创建失败')}), 502
    # 创建成功：顺手把配置写到本地（启用同步、默认分支、path_prefix=blog-backup）
    data_dir = Config.DATA_DIR
    current = _gb.load_settings(data_dir)
    new_s = _gb.normalize_settings({
        'token': token,
        'owner': owner,
        'repo': info.get('name') or repo_name,
        'branch': info.get('default_branch') or 'master',
        'path_prefix': 'blog-backup',
        'enabled': True,
    })
    current.update(new_s)
    _gb.save_settings(data_dir, current)
    return jsonify({'ok': True, 'info': info, 'saved_settings': current})


@app.route('/admin/sync/test_connection', methods=['POST'])
@login_required
def admin_sync_test_connection():
    """AJAX：新手向导步骤④ 连通性测试（令牌→用户名→仓库→分支），
    并把自动更正的设置写回磁盘。"""
    data = request.get_json(silent=True) if request.is_json else None
    if data is None:
        data = request.form.to_dict()
    raw: dict = {}
    for k in ('token', 'owner', 'repo', 'branch', 'path_prefix'):
        raw[k] = (data.get(k) or '').strip()
    raw = _gb.normalize_settings(raw)
    if not raw.get('token'):
        return jsonify({'ok': False, 'error': '请先填写或粘贴 Gitee 私人令牌。'}), 400
    ok, info = _gb.test_connection(raw)
    # 如果返回了自动更正的 settings → 写回磁盘（保留用户旧 last_backup_* 等）
    if 'corrected_settings' in info:
        data_dir = Config.DATA_DIR
        current = _gb.load_settings(data_dir)
        corrected = info['corrected_settings']
        for k in ('token', 'owner', 'repo', 'branch', 'path_prefix'):
            if corrected.get(k) is not None:
                current[k] = corrected[k]
        _gb.save_settings(data_dir, current)
        info['saved_settings'] = _gb.normalize_settings(current)
    return jsonify({'ok': ok, 'result': info})

# 双向同步（类 Chrome/Edge 云同步体验）
# ============================================================
def _sync_last_run_path() -> str:
    return os.path.join(Config.DATA_DIR, 'sync_last_run.json')


def _sync_read_last_run() -> dict:
    p = _sync_last_run_path()
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _sync_write_last_run(data: dict) -> None:
    try:
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        tmp = _sync_last_run_path() + '.tmp'
        payload = dict(data)
        # 防御：把 datetime 等非 JSON 原生类型统一转 str
        def _default(x):
            return str(x)
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=_default)
        os.replace(tmp, _sync_last_run_path())
    except Exception as e:
        # 失败时至少写一行到 app logger，方便用户排查"为什么摘要没更新"
        try:
            app.logger.warning('写入 sync_last_run.json 失败: %s', e)
        except Exception:
            pass


def _sync_is_enabled() -> bool:
    try:
        s = _gb.load_settings(Config.DATA_DIR)
        return bool(s.get('sync_enabled'))
    except Exception:
        return False


def _sync_build_status_dict() -> dict:
    settings = _gb.load_settings(Config.DATA_DIR)
    last = _sync_read_last_run()
    # 连通性：有 token 且可连通时才健康
    health_ok = False
    health_msg = '未登录 Gitee'
    if settings.get('token') and settings.get('repo') and settings.get('owner'):
        # 轻量判断（不发网络请求，避免页面卡）
        health_ok = True
        health_msg = '已登录'
    return {
        'sync_enabled': bool(settings.get('sync_enabled')),
        'token_configured': bool(settings.get('token')),
        'owner': settings.get('owner') or '',
        'repo': settings.get('repo') or '',
        'path_prefix': settings.get('path_prefix') or 'blog-backup',
        'last_run': last,
        'health_msg': health_msg,
        'health_ok': health_ok,
    }


def _sync_do_run(direction: str = 'both',
                 reset: Optional[dict] = None) -> dict:
    """执行一次同步（支持三种模式 + 游标重置）。

    Args:
        direction: 'both'   立即同步（双向合并，默认 Chrome 风格一键同步）
                   'push'   只备份到 Gitee（本地 → 远端，增量 PUSH）
                   'pull'   只从 Gitee 恢复（远端 → 本地，LWW 合并不覆盖更新本地数据）
        reset:     可选 {'push':True,'pull':True} 清空本端游标，重新全量比对远端。
    """
    direction = (direction or 'both').strip().lower()
    if direction == 'push':
        mode = 'push_only'
    elif direction == 'pull':
        mode = 'pull_only'
    else:
        mode = 'both'
    settings = _gb.load_settings(Config.DATA_DIR)
    if not settings.get('token') or not settings.get('repo') or not settings.get('owner'):
        return {'ok': False,
                'error': '请先完成 Gitee 登录：令牌、仓库所有者、仓库名都是必填。到下方「Gitee 账号配置」展开填写。',
                'mode': mode}
    try:
        from sync_engine import SyncEngine, GiteeRemoteAdapter
        adapter = GiteeRemoteAdapter(settings)
        engine = SyncEngine(
            db.session,
            adapter,
            state_path=os.path.join(Config.DATA_DIR, 'sync_state.json'),
        )
        result = engine.run_sync(mode=mode, reset=reset)
    except Exception as e:
        app.logger.exception('同步执行异常 mode=%s', mode)
        err = {'ok': False, 'error': str(e)[:500],
               'finished_at': datetime.datetime.utcnow().isoformat(),
               'mode': mode}
        _sync_write_last_run(err)
        return err
    out = {
        'ok': True,
        'mode': mode,
        'finished_at': datetime.datetime.utcnow().isoformat(),
        'pushed': result.get('pushed', {}),
        'pulled': result.get('pulled', {}),
        'cursors_keys': sorted(list(result.get('cursors', {}).keys())),
        'attachments': result.get('attachments', {}),
    }
    _sync_write_last_run(out)
    return out


# ---------- Gitee 配置直接保存（简化版：非 4 步向导，直接填 token/owner/repo/path_prefix）----------
def _read_sync_simple_settings() -> dict:
    out: dict = {}
    for k in ('token', 'owner', 'repo', 'branch', 'path_prefix'):
        v = ''
        if request.is_json:
            v = (request.json.get(k, '') or '').strip()
        else:
            v = (request.form.get(k, '') or '').strip()
        out[k] = v
    if not out.get('path_prefix'):
        out['path_prefix'] = 'blog-backup'
    # 如果 repo 里直接贴了完整 Gitee URL → 自动解析 owner/repo
    url = out.get('repo') or ''
    if '://' in url or url.startswith('git@'):
        try:
            cleaned = url.replace('git@', '').replace(':', '/').replace('.git', '')
            parts = [p for p in cleaned.split('/') if p]
            if len(parts) >= 2 and 'gitee' in parts[-3] if len(parts)>=3 else True:
                if 'gitee' in parts[0] if True else False:
                    # 形如 gitee.com/owner/repo  → parts = ['https','gitee.com','owner','repo']
                    candidates = [p for p in parts if p and 'gitee' not in p]
                    if len(candidates) >= 2:
                        out['owner'] = out['owner'] or candidates[-2]
                        out['repo'] = candidates[-1]
        except Exception:
            pass
    return out


@app.route('/admin/sync/save_settings', methods=['POST'])
@login_required
def admin_sync_save_settings():
    """云同步页「Gitee 账号配置」直接保存（含自动补全）。

    保存时做两个智能补全（失败不影响保存）：
      1) owner 为空但 token 非空 → 调 Gitee /user 自动回填 URL 用户名；
      2) owner+repo+token 齐全 → 自动探测真实默认分支并更正。
    """
    raw = _read_sync_simple_settings()
    data_dir = Config.DATA_DIR
    cur = _gb.load_settings(data_dir)
    for k, v in raw.items():
        if v is not None:
            cur[k] = v

    auto_notes: list = []
    # 1) 自动补 owner
    if cur.get('token') and not cur.get('owner'):
        try:
            ok_u, u = _gb.verify_token_and_get_user(cur['token'])
            if ok_u:
                cur['owner'] = u.get('login') or ''
                auto_notes.append("已根据令牌自动识别你的 Gitee 用户名：{}（昵称：{}）。".format(
                    u.get('login'), u.get('name') or '—'))
        except Exception as e:
            flash("自动识别 Gitee 用户名失败：{}".format(e), 'warning')
    # 2) 自动探测分支
    if cur.get('token') and cur.get('owner') and cur.get('repo'):
        try:
            ok_br, br = _gb.get_default_branch(cur)
            if ok_br and br and br != cur.get('branch'):
                auto_notes.append("检测到仓库实际默认分支为 {}（你填的是 {}），已自动更正。".format(
                    br, cur.get('branch') or 'master'))
                cur['branch'] = br
        except Exception:
            pass

    # 只要有 token+owner+repo 就算"已登录"（按钮解除 disabled），不强制立即走网络。
    if all(cur.get(k) for k in ('token', 'owner', 'repo')):
        cur['enabled'] = True  # 等同于"完成向导即开启云端"语义，但 sync_enabled 由用户另点开关。
    _gb.save_settings(data_dir, cur)
    msg = '✅ Gitee 配置已保存。现在可点击下方三个按钮 同步/备份/恢复。'
    if auto_notes:
        msg += '  ' + '  '.join('🔧 ' + n for n in auto_notes)
    flash(msg, 'success')
    return redirect(url_for('admin_sync'))


@app.route('/admin/sync/reset_cursors', methods=['POST'])
@login_required
def admin_sync_reset_cursors():
    """重置同步游标（下次运行视为首次，全量 LWW 比对）。"""
    p = os.path.join(Config.DATA_DIR, 'sync_state.json')
    try:
        if os.path.isfile(p):
            os.remove(p)
    except Exception as e:
        flash('重置失败：' + str(e), 'danger')
    else:
        flash('✅ 同步游标已清空。下一次 立即同步/恢复/备份 会重新做全量比对。', 'info')
    return redirect(url_for('admin_sync'))


@app.route('/admin/sync/', methods=['GET'])
@login_required
def admin_sync():
    """同步页：三按钮 + 账号配置折叠区 + 同步摘要。"""
    status = _sync_build_status_dict()
    gitee_settings = _gb.load_settings(Config.DATA_DIR)
    return render_template('admin/sync.html',
                           sync_status=status,
                           gitee_settings=gitee_settings,
                           gitee_new_token_url=GITEE_NEW_TOKEN_URL,
                           gitee_new_repo_url=GITEE_NEW_REPO_URL)


@app.route('/admin/sync/toggle', methods=['POST'])
@login_required
def admin_sync_toggle():
    """开启/关闭 自动同步开关。支持 JSON 响应。"""
    want_json = (request.is_json
                 or (request.headers.get('Accept') or '').lower() == 'application/json'
                 or request.headers.get('X-Requested-With') == 'XMLHttpRequest')
    enabled = (request.form.get('enabled') or request.json.get('enabled')
               if request.is_json else request.form.get('enabled'))
    enabled = str(enabled or '').strip().lower() in {'1', 'on', 'true', 'yes'}
    s = _gb.load_settings(Config.DATA_DIR)
    if enabled and (not s.get('token') or not s.get('repo') or not s.get('owner')):
        msg = '开启同步前，请先完成 Gitee 账号与仓库配置（到本页上方「零门槛 · 新手向导」走完 4 步即可）。'
        if want_json:
            return jsonify({'ok': False, 'error': msg, 'enabled': False})
        flash(msg, 'warning')
        return redirect(url_for('admin_sync'))
    s['sync_enabled'] = enabled
    _gb.save_settings(Config.DATA_DIR, s)
    msg = '自动同步已 ' + ('开启 ✅' if enabled else '关闭') + '。'
    if want_json:
        return jsonify({'ok': True, 'message': msg, 'enabled': enabled})
    flash(msg, 'success' if enabled else 'info')
    return redirect(url_for('admin_sync'))


@app.route('/admin/sync/run', methods=['POST'])
@login_required
def admin_sync_run():
    """立即同步 / 只备份到 Gitee / 只从 Gitee 恢复。

    表单/JSON 里 direction=both | push | pull；reset_push=on/true 时清空 push 游标，
    reset_pull=on/true 时清空 pull 游标（用于"强制全量比对"）。
    """
    if request.is_json:
        direction = (request.json.get('direction') or 'both').strip().lower()
        reset = {'push': bool(request.json.get('reset_push')),
                 'pull': bool(request.json.get('reset_pull'))}
    else:
        direction = (request.form.get('direction') or 'both').strip().lower()
        reset = {'push': bool(request.form.get('reset_push')),
                 'pull': bool(request.form.get('reset_pull'))}
    if direction not in ('both', 'push', 'pull'):
        direction = 'both'
    result = _sync_do_run(direction=direction,
                          reset=reset if any(reset.values()) else None)
    if request.is_json or (request.headers.get('Accept') or '').lower() == 'application/json':
        return jsonify(result)

    if result.get('ok'):
        p = result.get('pushed', {})
        pl = result.get('pulled', {})
        att = result.get('attachments') or {}
        pushed_sum = sum(p.values()) if isinstance(p, dict) else 0
        pulled_sum = sum(pl.values()) if isinstance(pl, dict) else 0
        att_up = att.get('uploaded') if isinstance(att, dict) else 0
        att_down = att.get('downloaded') if isinstance(att, dict) else 0

        mode_label = {
            'both': '✅ 立即同步完成（双向 LWW 合并）',
            'push_only': '💾 只备份到 Gitee 完成',
            'pull_only': '📥 只从 Gitee 恢复完成（LWW 合并不覆盖本地更新）',
        }.get(result.get('mode') or '', '✅ 操作完成')
        msg = (f'{mode_label}。 推送 {pushed_sum} 条 / 拉取 {pulled_sum} 条。'
               f'附件：↑{att_up or 0} / ↓{att_down or 0} 个。')
        flash(msg, 'success')
    else:
        flash('操作失败：' + str(result.get('error', result))[:400], 'danger')
    return redirect(url_for('admin_sync'))


@app.route('/admin/sync/status', methods=['GET'])
@login_required
def admin_sync_status():
    """JSON 状态接口（轮询 / 小程序 / 桌面端线程都可用）。"""
    status = _sync_build_status_dict()
    return jsonify(status)


@app.route('/api/preview', methods=['POST'])
def api_preview():
    """编辑器实时预览：Markdown -> HTML"""
    content = request.json.get('content', '') if request.is_json else request.form.get('content', '')
    return jsonify({'html': render_markdown(content)})


# ============================================================
# 数据库初始化 & 启动
# ============================================================
def init_db():
    """创建数据库，并插入一篇示例文章。

    【PP5 · 性能 + 同步】额外做 2 件事（幂等）：
      1) 轻量 schema 迁移：ALTER TABLE ... ADD COLUMN 补 is_deleted / rendered_html
         等新增列（给已经存在的旧数据库用）。
      2) 建立 7 张关键索引：Post / Comment / FriendLink / Like / post_tags。
      3) 给 Profile 旧表补 bg_image / bg_opacity（已有实现，保留）。
    """
    with app.app_context():
        db.create_all()
        # 自动为旧数据库补充新增列（无迁移框架时的轻量方案）
        from sqlalchemy import inspect, text
        insp = inspect(db.engine)

        # --- 1. Profile 旧列（bg_image/bg_opacity）：历史实现保留 ---
        if 'profile' in insp.get_table_names():
            cols = {c['name'] for c in insp.get_columns('profile')}
            if 'bg_image' not in cols:
                db.session.execute(text("ALTER TABLE profile ADD COLUMN bg_image VARCHAR(500)"))
            if 'bg_opacity' not in cols:
                db.session.execute(text("ALTER TABLE profile ADD COLUMN bg_opacity FLOAT DEFAULT 0.25"))
            # --- 同步新增：is_deleted（墓碑）---
            if 'is_deleted' not in cols:
                db.session.execute(text("ALTER TABLE profile ADD COLUMN is_deleted BOOLEAN DEFAULT 0"))
            db.session.commit()

        # --- 2. 补 is_deleted / rendered_html（各表）---
        _upgrade = {
            'post': [
                "ALTER TABLE post ADD COLUMN rendered_html TEXT",
                "ALTER TABLE post ADD COLUMN is_deleted BOOLEAN DEFAULT 0",
            ],
            'tag': [
                "ALTER TABLE tag ADD COLUMN is_deleted BOOLEAN DEFAULT 0",
            ],
            'comment': [
                "ALTER TABLE comment ADD COLUMN is_deleted BOOLEAN DEFAULT 0",
            ],
            'like': [
                "ALTER TABLE like ADD COLUMN is_deleted BOOLEAN DEFAULT 0",
            ],
            'friend_link': [
                "ALTER TABLE friend_link ADD COLUMN is_deleted BOOLEAN DEFAULT 0",
            ],
        }
        for t, alters in _upgrade.items():
            if t in insp.get_table_names():
                colnames = {c['name'] for c in insp.get_columns(t)}
                for stmt in alters:
                    # ALTER TABLE {t} ADD COLUMN {colname} ... → 解析 colname
                    # 简单从 "ADD COLUMN xxx" 里取列名
                    m = re.search(r'ADD COLUMN\s+([A-Za-z_][A-Za-z0-9_]*)', stmt, re.I)
                    colname = m.group(1).lower() if m else None
                    if colname and colname in colnames:
                        continue  # 已有，幂等跳过
                    try:
                        db.session.execute(text(stmt))
                        db.session.commit()
                    except Exception as exc:
                        app.logger.info('schema 升级跳过（可能列已存在）%s → %s', stmt, exc)
                        db.session.rollback()

        # --- 3. 建索引（IF NOT EXISTS，幂等）---
        indexes_sql = [
            # Post 列表页高频：published+created_at（首页 / 分类 / 搜索排序）
            "CREATE INDEX IF NOT EXISTS ix_post_published_created ON post(published, created_at DESC)",
            # Post 分类页：published+category+created_at
            "CREATE INDEX IF NOT EXISTS ix_post_cat_pub_cr ON post(published, category, created_at DESC)",
            # Post 详情页上下文（prev/next）：id + published
            "CREATE INDEX IF NOT EXISTS ix_post_published_id ON post(published, id)",
            # Comment 详情页批量查：post_id+is_visible+parent_id+created_at
            "CREATE INDEX IF NOT EXISTS ix_comment_post_vis ON comment(post_id, is_visible, parent_id, created_at)",
            # Comment 回复索引：parent_id 是最常见 WHERE 条件
            "CREATE INDEX IF NOT EXISTS ix_comment_parent ON comment(parent_id)",
            # FriendLink 列表：is_visible+sort_order+id
            "CREATE INDEX IF NOT EXISTS ix_friendlink_vis_sort ON friend_link(is_visible, sort_order, id)",
            # Like 详情页 count / 查重：post_id（created_at 作为排序字段可选）
            "CREATE INDEX IF NOT EXISTS ix_like_post ON like(post_id)",
        ]
        for sql in indexes_sql:
            try:
                db.session.execute(text(sql))
                db.session.commit()
            except Exception as exc:
                app.logger.info('建索引跳过（已存在或失败）%s → %s', sql, exc)
                db.session.rollback()
        # 无文章时，插入示例（updated_at 设为极早时间，确保云同步恢复时远端数据 LWW 优先）
        _SAMPLE_TS = datetime.datetime(2000, 1, 1)
        if Post.query.count() == 0:
            tag1 = get_or_create_tag('Python')
            tag2 = get_or_create_tag('编程笔记')
            tag3 = get_or_create_tag('生活')

            sample = Post(
                title='欢迎来到我的博客！',
                summary='这是使用 Flask + SQLite 搭建的个人博客，支持 Markdown 写作、标签分类、文件导入。',
                category='公告',
                content="""# 欢迎来到我的博客 👋

这是一个使用 **Python + Flask** 搭建的个人博客网站，同时适配电脑和手机浏览。

## ✨ 功能特性

1. **Markdown 写作**：支持在线编辑器和实时预览
2. **标签系统**：通过标签快速筛选文章
3. **分类与归档**：按分类或月份浏览
4. **文件导入**：上传 `.md` 或 `.yaml` 文件批量创建
5. **代码高亮**：使用 Pygments 渲染代码块
6. **响应式布局**：PC / Pad / 手机 都好看

## 💻 代码示例

```python
def hello(name):
    print(f"Hello, {name}!")

hello("Blog")
```

## 📌 使用说明

- 管理后台：点击右上角「管理」，或访问 `/admin/`
- 默认账号：**admin** / **admin123**（请在 config.py 中修改）
- 上传文件支持：`.md` `.markdown` `.yaml` `.yml`

祝写作愉快！✍️
""",
                published=True,
                updated_at=_SAMPLE_TS,
            )
            sample.tags.extend([tag1, tag2])
            db.session.add(sample)

            sample2 = Post(
                title='我的第一篇生活随笔',
                summary='记录一下搭建这个博客的心路历程，以及今天的天气……',
                category='生活',
                content="""# 第一篇生活随笔 🌿

今天天气不错，阳光明媚。

花了一整天的时间把博客搭起来了，从设计数据库到写前端样式，虽然有点累，但还是挺有成就感的 🙂

## 今天的 TODO

- [x] 完成博客后端
- [x] 实现响应式样式
- [ ] 再写几篇文章填充内容
- [ ] 部署到服务器

> 分享一个小技巧：如果你想快速导入文章，可以直接上传带有 YAML front-matter 的 Markdown 文件，非常方便！

```yaml
---
title: 我的文章标题
category: 编程
tags:
  - Python
  - Flask
date: 2026-08-30
---

这里是 Markdown 正文内容……
```

接下来准备把以前的笔记陆续搬运过来～
""",
                published=True,
                updated_at=_SAMPLE_TS,
            )
            sample2.tags.append(tag3)
            db.session.add(sample2)

            db.session.commit()
            print('✅ 数据库初始化完成，已插入示例文章')
        else:
            print('✅ 数据库已就绪')

        # 无友链时，插入示例
        if FriendLink.query.count() == 0:
            demo_links = [
                FriendLink(name='阮一峰的博客', url='https://www.ruanyifeng.com/blog/',
                            description='科技爱好者周刊 · ES6 教程作者',
                            avatar='https://www.ruanyifeng.com/favicon.ico', sort_order=0),
                FriendLink(name='廖雪峰的官方网站', url='https://www.liaoxuefeng.com/',
                            description='Python / Git / JavaScript 教程',
                            avatar='https://www.liaoxuefeng.com/favicon.ico', sort_order=1),
                FriendLink(name='V2EX', url='https://www.v2ex.com/',
                            description='创意工作者们的社区',
                            avatar='https://www.v2ex.com/static/favicon.ico', sort_order=2),
                FriendLink(name='少数派', url='https://sspai.com/',
                            description='高质量数字消费指南',
                            avatar='https://cdn.sspai.com/favicon.ico', sort_order=3),
                FriendLink(name='掘金', url='https://juejin.cn/',
                            description='一个帮助开发者成长的社区',
                            avatar='https://juejin.cn/favicon.ico', sort_order=4),
                FriendLink(name='GitHub', url='https://github.com/',
                            description='全球最大代码托管平台 · 开发者之家',
                            avatar='https://github.githubassets.com/favicons/favicon.svg', sort_order=5),
            ]
            db.session.add_all(demo_links)
            db.session.commit()
            print('✅ 已插入示例友情链接')


def _write_pid():
    """写 PID 文件，便于 run.bat / 运维脚本 kill 进程。"""
    pid_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blog.pid')
    try:
        with open(pid_file, 'w', encoding='utf-8') as f:
            f.write(str(os.getpid()))
    except OSError:
        pass


def run_server():
    init_db()
    _write_pid()
    host = app.config['HOST']
    port = app.config['PORT']
    debug = app.config['DEBUG']

    # ---------- 启动横幅（用 print 绕过日志级别限制，PyCharm 控制台直接可见）----------
    lan_ip = None
    try:
        import socket as _sock
        _s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
        _s.connect(('8.8.8.8', 80))
        lan_ip = _s.getsockname()[0]
        _s.close()
    except Exception:
        pass
    mode = '开发模式 (Flask debug, 热重载)' if debug else '生产模式 (waitress WSGI)'
    bar = '=' * 60
    print(bar)
    print('  个人博客 已启动')
    print(bar)
    print(f'  运行模式 : {mode}')
    print(f'  本机访问 : http://127.0.0.1:{port}/')
    if lan_ip:
        print(f'  局域网   : http://{lan_ip}:{port}/  (手机连同一WiFi可访问)')
    print(f'  管理后台 : http://127.0.0.1:{port}/admin/  (已移除登录，直接进入)')
    print(f'  进程 PID : {os.getpid()}')
    print(f'  日志文件 : {os.path.join(LOG_DIR, "blog.log")}')
    print('  停止服务 : 按 Ctrl+C')
    print(bar)
    sys.stdout.flush()

    if debug:
        # 开发模式：Flask 内置开发服务器（含调试器 + 热重载）
        app.logger.info('启动个人博客（开发模式）: host=%s port=%d pid=%d logs=%s',
                        host, port, os.getpid(), LOG_DIR)
        try:
            app.run(host=host, port=port, debug=True, threaded=False,
                    use_reloader=True, extra_files=None)
        except KeyboardInterrupt:
            app.logger.info('收到 Ctrl+C，正常退出')
        except Exception as exc:
            app.logger.error('服务意外退出: %s\n%s', exc, traceback.format_exc())
            raise
    else:
        # 生产模式：优先使用 waitress（纯 Python 多线程 WSGI，稳定性优于 Flask 内置）
        try:
            from waitress import serve as waitress_serve
            app.logger.info('启动个人博客（生产模式 waitress WSGI）: host=%s port=%d pid=%d logs=%s',
                            host, port, os.getpid(), LOG_DIR)
            waitress_serve(app, host=host, port=port,
                           threads=8,            # 并发线程数（个人博客足够）
                           connection_limit=512,
                           channel_timeout=120,  # 超时回收
                           ident='PersonalBlog',
                           backlog=2048)
        except ImportError:
            app.logger.warning('未安装 waitress，退回 Flask 内置多线程服务器。运行：pip install -r requirements.txt')
            app.logger.info('启动个人博客（生产模式 Flask 内置）: host=%s port=%d pid=%d logs=%s',
                            host, port, os.getpid(), LOG_DIR)
            try:
                app.run(host=host, port=port, debug=False, threaded=True,
                        use_reloader=False)
            except KeyboardInterrupt:
                app.logger.info('收到 Ctrl+C，正常退出')
            except Exception as exc:
                app.logger.error('服务意外退出: %s\n%s', exc, traceback.format_exc())
                raise
        except KeyboardInterrupt:
            app.logger.info('收到 Ctrl+C，正常退出')
        except Exception as exc:
            app.logger.error('waitress 异常退出: %s\n%s', exc, traceback.format_exc())
            raise


if __name__ == '__main__':
    run_server()
