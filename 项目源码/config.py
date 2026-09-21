"""
博客网站配置文件

加载顺序（后者覆盖前者）：
    .env 文件 > 系统环境变量 > 默认值
这样迁移到新电脑时，只需在新机器复制一份 .env 即可保留个性化配置，
不需要改 config.py 源代码。
"""
import os
import sys
import re
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# PyInstaller 打包后：资源目录(只读 templates/static)与数据目录(可写 db/uploads/logs)分离
if getattr(sys, 'frozen', False):
    RESOURCE_DIR = sys._MEIPASS                        # 打包资源解压目录（只读）
    DATA_DIR = os.path.dirname(sys.executable)         # exe 所在目录（可写）
else:
    RESOURCE_DIR = BASE_DIR                            # 开发模式：源码目录
    DATA_DIR = BASE_DIR

# 允许 BLOG_DATA_DIR 环境变量覆盖（main.py / 单元测试 / 冒烟测试注入临时数据目录）
DATA_DIR = os.environ.get('BLOG_DATA_DIR') or DATA_DIR
# 允许 BLOG_RESOURCE_DIR 覆盖（PyInstaller 冻结环境独立配置 templates/static 路径）
if os.environ.get('BLOG_RESOURCE_DIR'):
    RESOURCE_DIR = os.environ['BLOG_RESOURCE_DIR']


def _ensure_persistent_secret_key(data_dir: str) -> str:
    """登录持久化（跨重启不用重登）的关键：把 SECRET_KEY 写入并固定读 DATA_DIR/.session_key。

    为什么需要这个：
      Flask session 是用 SECRET_KEY 签名的 cookie，cookie 里没有绑定端口的字段，但一旦：
       (a) 密钥被改（例如环境没把 SECRET_KEY 落盘，每次跑默认值分支里有拼接随机量时）
       (b) 端口频繁跳变（浏览器某些实现会把 cookie 按 host:port 分别隔离）
      用户就会"每次启动都要重新登录"。

    这里做两件事：
      1) 若 data_dir/.session_key 有内容 → 直接返回，保证二次启动同密钥
      2) 若不存在 → 用强随机 secrets.token_hex(48)（96 hex chars）生成，原子写回磁盘
    环境变量 SECRET_KEY 仍然优先（保留原 config 行为：运维注入覆盖一切）。
    """
    key_env = os.environ.get('SECRET_KEY')
    if key_env:
        return key_env
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, '.session_key')
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if len(content) >= 32:
                return content
        except OSError:
            pass  # 文件损坏 → 走下面重建
    # 生成 + 原子写
    import secrets as _secrets, tempfile as _tf
    new_key = _secrets.token_hex(48)  # 48 bytes → 96 hex chars, 强度极高
    try:
        fd, tmp = _tf.mkstemp(prefix='.session_key.', dir=data_dir, text=True)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(new_key + '\n')
            try:
                os.replace(tmp, path)
                # ⚠️ replace 成功必须 return。之前漏写导致函数隐式返回 None，
                # 引发 Flask session 签名缺失 → 登录 POST 统一 500 错误。
                return new_key
            except OSError:
                # 并发首次启动冲突：另一进程已经写过就直接读回
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return f.read().strip() or new_key
                except OSError:
                    return new_key
        except Exception:
            try: os.unlink(tmp)
            except OSError: pass
            raise
    except OSError:
        return new_key  # 写盘失败也得给一个当次能用的 key，总比崩强

    # 兜底：上面所有正常路径都应 return，真走到这里就直接 return new_key，绝不能返回 None
    return new_key


def _load_dotenv(path=None):
    """轻量 .env 加载（不依赖 python-dotenv）。

    语法：KEY=VALUE，# 开头注释，忽略空行；值两侧可选单/双引号。
    不覆盖已存在的环境变量（符合 .env 文件语义）。
    若已安装 python-dotenv，优先调用它（支持更多特性）。
    """
    env_path = path or os.path.join(BASE_DIR, '.env')
    if not os.path.isfile(env_path):
        return
    try:
        from dotenv import load_dotenv as _ext_load  # type: ignore
        _ext_load(dotenv_path=env_path, override=False, encoding='utf-8')
        return
    except Exception:
        pass
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                # export KEY=VALUE 也兼容
                line = re.sub(r'^export\s+', '', line, flags=re.IGNORECASE)
                m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line)
                if not m:
                    continue
                key, value = m.group(1), m.group(2)
                # 去两侧空格 & 引号
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                if key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


# 先于 Config 类加载 .env，保证后续 os.environ.get 能读到
_load_dotenv()


class Config:
    # 应用版本号（三位数语义版本，显示于后台页脚/托盘提示；打包 zip 命名同步）
    APP_VERSION = '2.8.3'

    # PyInstaller 打包：资源目录（只读：templates/static）与数据目录（可写：db/uploads/logs）
    # 放在类属性上，保证 app.py / launcher.py 通过 Config.RESOURCE_DIR / Config.DATA_DIR 可读
    RESOURCE_DIR = RESOURCE_DIR
    DATA_DIR = DATA_DIR

    # 安全密钥（生产环境请修改；切勿泄露，它用于签名 session cookie，
    # 改动后所有已登录会话立即失效，需重新登录）
    #  1) SECRET_KEY 环境变量最高优先级；
    #  2) 否则把密钥持久化到 DATA_DIR/.session_key，跨启动保持一致 → 登录态不会失效
    SECRET_KEY = _ensure_persistent_secret_key(DATA_DIR)

    # 会话持久化：登录状态保留 30 天，重启服务后仍保持登录
    # （Flask 默认 session 存在客户端 cookie，只要 SECRET_KEY 不变 + cookie 未过期，登录即保持）
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_PERMANENT = True
    # 桌面版我们用"固定默认端口 + 同密钥"来规避浏览器把 session cookie 按 port 分别隔离的现象；
    # 同时确保 SESSION_COOKIE_NAME 固定、SAMESITE 宽松，避免 EdgeChromium/WebView2 存不下 cookie：
    SESSION_COOKIE_NAME = 'personal_blog_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # 桌面版都是 http://127.0.0.1:<port> 本地回环，不能 Secure

    # SQLite 数据库 + 连接池配置
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL') or 'sqlite:///' + os.path.join(DATA_DIR, 'blog.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLite 需要 check_same_thread=False 才能跨线程使用连接池
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 1800,      # 连接 30 分钟自动回收
        'connect_args': {'check_same_thread': False, 'timeout': 30}
    }

    # 上传目录
    UPLOAD_FOLDER = os.path.join(DATA_DIR, 'uploads')
    ALLOWED_EXTENSIONS = {'md', 'markdown', 'yaml', 'yml'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB 最大上传

    # 分页
    POSTS_PER_PAGE = 8

    # 管理员账号（v1.3 起登录功能已移除，以下两项仅保留兼容，不再参与任何校验）
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'

    # 监听地址 / 端口
    HOST = os.environ.get('BLOG_HOST') or '0.0.0.0'
    PORT = int(os.environ.get('BLOG_PORT') or 5000)
    # 生产模式：关闭自动重载和调试器（FLASK_DEBUG=1 可临时开启调试）
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
