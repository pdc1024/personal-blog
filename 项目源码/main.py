# -*- coding: utf-8 -*-
"""
个人博客 · 桌面启动器
===================================
- 在后台以子线程启动 Flask/Waitress WSGI 服务，监听 127.0.0.1 的空闲端口
- 用 pywebview 打开原生内嵌本地窗口（Windows 上默认 Edge WebView2）
- 单实例互斥（Win32 Mutex）：若已启动则激活已有窗口并退出
- 窗口关闭时立即停止 WSGI 服务并退出进程，无残留
"""
from __future__ import annotations

import sys
import os
import ctypes
import threading
import time
import socket
import urllib.request
import urllib.error
from typing import Optional

# ---------- 资源路径兼容 PyInstaller ----------
def _get_base_dirs():
    """返回 (RESOURCE_DIR, DATA_DIR)，兼容打包与开发模式"""
    if getattr(sys, 'frozen', False):
        # 打包后：只读资源在 sys._MEIPASS，可写数据与 exe 同级
        RESOURCE_DIR = sys._MEIPASS
        DATA_DIR = os.path.dirname(sys.executable)
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        RESOURCE_DIR = BASE_DIR
        DATA_DIR = BASE_DIR
    # 确保两者在 sys.path 里，import app 能找到
    if RESOURCE_DIR not in sys.path:
        sys.path.insert(0, RESOURCE_DIR)
    if DATA_DIR not in sys.path and DATA_DIR != RESOURCE_DIR:
        sys.path.insert(0, DATA_DIR)
    return RESOURCE_DIR, DATA_DIR

RESOURCE_DIR, DATA_DIR = _get_base_dirs()
os.environ.setdefault('BLOG_RESOURCE_DIR', RESOURCE_DIR)
os.environ.setdefault('BLOG_DATA_DIR', DATA_DIR)


# ---------- Logo.ico：支持用户"在文件夹里自己替换" ----------
def _resolve_external_logo_ico() -> Optional[str]:
    """按优先级解析运行时 logo.ico 路径，允许用户在 exe 同目录直接覆盖 logo.ico。

    打包配置与替换说明：
      · 打包时：
        PyInstaller blog_desktop.spec 会：
         (a) 把 logo.ico 作为内嵌图标写入 EXE（EXE(icon=...)，.rsrc\\ICON 段）；
         (b) 把 logo.ico 和 「logo替换说明.txt」放进 _internal/ 里做兜底；
         (c) 在 COLLECT 钩子中额外复制 logo.ico + 说明 TXT 到 onedir 顶层（与 exe 同级）。
        Inno Setup installer.iss 会：
         (d) 把 dist\\<app>\\ 整棵树装到 {app}；
         (e) 再次从项目根拷贝 logo.ico + 说明 TXT 到 {app} 顶层（和 exe 同级）；
         (f) 把桌面 / 开始菜单快捷方式的 IconLocation 固定指向 {app}\\logo.ico,0，
             这样用户后续换 {app}\\logo.ico 之后，快捷方式图标也会跟新（无需重新建 .lnk）。

      · 用户侧替换：
        只改「exe 旁边的 logo.ico」即可（优先级最高）。换完后：
         - 重启软件 → 标题栏 / 任务栏 / ALT+TAB / 左上角小图标立即刷新
         - 桌面和开始菜单的快捷方式图标 → Windows Explorer 一般在下次刷新时会变，
           想立刻看到：注销重登录，或把 %LOCALAPPDATA%\\IconCache.db 删除后重启 Explorer

    优先级（高→低，命中即返回）：
      1) 可写目录 / exe 同级 (DATA_DIR) 的 logo.ico          ← 用户想自己换就改这里
      2) 环境变量 BLOG_DESKTOP_ICON 指定的路径               ← 便于部署脚本单独覆盖
      3) sys._MEIPASS/_internal/logo.ico（PyInstaller 内嵌兜底）
      4) RESOURCE_DIR/logo.ico（源项目/开发模式兜底）
    """
    candidates = []
    # ① 环境变量强制覆盖（部署工具方便用）
    _env = os.environ.get('BLOG_DESKTOP_ICON')
    if _env and os.path.isfile(_env):
        return _env
    # ② exe 同级（DATA_DIR）
    if getattr(sys, 'frozen', False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), 'logo.ico'))
    else:
        candidates.append(os.path.join(DATA_DIR, 'logo.ico'))
    # ③ _MEIPASS/_internal 兜底（打包内嵌）
    meip = getattr(sys, '_MEIPASS', None)
    if meip:
        candidates.append(os.path.join(meip, 'logo.ico'))
    # ④ 源项目目录
    candidates.append(os.path.join(RESOURCE_DIR, 'logo.ico'))
    # 去重（同路径别重复）
    seen = set()
    for p in candidates:
        if not p or p in seen:
            continue
        seen.add(p)
        if os.path.isfile(p):
            return p
    return None


EXTERNAL_LOGO_ICO = _resolve_external_logo_ico()


# ---------- pywebview.create_window 参数构造（防版本兼容问题）----------
def _compute_centered_position(width: int, height: int):
    """计算让窗口在屏幕正中央的 (x, y)。

    Windows 上按 DPI 感知返回逻辑像素（DIP）：
      · GetSystemMetrics 返回物理像素；
      · pywebview / WebView2 的 x/y 是 DIP；
      · 若系统缩放（如 125%/150%）非 100%，必须先把物理像素换算成 DIP，
        否则窗口会偏到右下，达不到"每次打开都在屏幕中间"的效果。
    非 Windows / 计算失败时返回 None，调用方保持默认定位。
    """
    try:
        if sys.platform != 'win32':
            return None
        import ctypes
        user32 = ctypes.windll.user32
        SM_CXSCREEN = 0
        SM_CYSCREEN = 1
        sw = user32.GetSystemMetrics(SM_CXSCREEN)
        sh = user32.GetSystemMetrics(SM_CYSCREEN)
        if sw <= 0 or sh <= 0:
            return None
        # DPI 换算
        dpi = 96
        try:
            dpi = int(user32.GetDpiForSystem())
        except Exception:
            dpi = 96
        if dpi <= 0:
            dpi = 96
        scale = dpi / 96.0
        sw = int(sw / scale)
        sh = int(sh / scale)
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
        return x, y
    except Exception:
        return None


def _build_create_window_kwargs(title: str, url: str, _force_icon: bool = False):
    """把 webview.create_window 的参数抽成函数，便于做签名检查。

    返回 (kwargs, icon_path)：kwargs 只包含当前 pywebview 版本**确实支持**的关键字，
    icon_path 是要单独通过 Win32 API 挂上窗口的 ico 路径（可能为 None）。

    关键修复：pywebview 5.2/部分旧版的 create_window 不支持 icon 参数，
    传了会抛：TypeError: create_window() got an unexpected keyword argument 'icon'
    所以这里 **一定不要把 icon 放进 kwargs**。

    窗口定位：默认 1280x820，并计算屏幕居中坐标 (x, y) 一起传入，
    保证每次打开桌面版主窗口都位于屏幕中央（需求 v2.1）。
    """
    import webview as _webview
    try:
        import inspect as _inspect
        allowed = set(_inspect.signature(_webview.create_window).parameters.keys())
    except Exception:
        # 兜底：老版本没有 signature 的时候就保守地写已知参数
        allowed = {'title','url','html','js_api','width','height','x','y','screen',
                   'resizable','fullscreen','min_size','hidden','frameless','easy_drag',
                   'shadow','focus','minimized','maximized','on_top','confirm_close',
                   'background_color','transparent','text_select','zoomable','draggable',
                   'vibrancy','menu','localization','server','http_port','server_args'}

    win_w, win_h = 1280, 820
    kwargs_all = dict(
        title=title,
        url=url,
        width=win_w,
        height=win_h,
        min_size=(960, 640),
        resizable=True,
        confirm_close=False,
        text_select=True,
        zoomable=True,
        background_color='#ffffff',
        frameless=False,
    )
    # 屏幕居中（Windows）：把 x/y 放进参数，版本不支持则自动忽略
    pos = _compute_centered_position(win_w, win_h)
    if pos is not None:
        kwargs_all['x'] = pos[0]
        kwargs_all['y'] = pos[1]
    kwargs = {k: v for k, v in kwargs_all.items() if k in allowed}
    icon = EXTERNAL_LOGO_ICO if (EXTERNAL_LOGO_ICO or _force_icon) else None
    if _force_icon:
        # 单测里就算文件不存在也得有个字符串，真实运行时 EXTERNAL_LOGO_ICO 为 None 我们就不设
        icon = EXTERNAL_LOGO_ICO
    return kwargs, icon


# ---------- Win32：给已创建的 native 窗口挂标题栏/任务栏图标 ----------
def _apply_window_icon_async(icon_path: Optional[str], window_title: str) -> None:
    """后台给当前进程的 top-level 窗口发 WM_SETICON，让标题栏/任务栏/ALT+TAB 显示自定义 logo。

    pywebview.create_window() 不一定支持 icon 参数（依版本），所以改成 Win32 自设，
    同时天然支持"用户替换 exe 旁边的 logo.ico 后下次启动生效"。
    """
    if not icon_path or not os.path.isfile(icon_path) or sys.platform != 'win32':
        return
    import threading as _th
    def _worker():
        # 等 pywebview 真正把窗口拉起来（通常 30~200ms）
        for _ in range(50):
            try:
                _apply_window_icon_win32_impl(icon_path, window_title)
                break
            except Exception:
                time.sleep(0.1)
    threading.Thread(target=_worker, name='SetWindowIcon', daemon=True).start()


def _apply_window_icon_win32_impl(icon_path: str, window_title: str) -> None:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x00000010
    LR_DEFAULTSIZE = 0x00000040
    SM_CXICON = 11
    SM_CYICON = 12
    SM_CXSMICON = 49
    SM_CYSMICON = 50
    WM_SETICON = 0x0080
    ICON_BIG = 1
    ICON_SMALL = 0
    GCLP_HICONSM = -34
    GCLP_HICON = -14

    LoadImageW = user32.LoadImageW
    LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                           ctypes.c_int, ctypes.c_int, wintypes.UINT]
    LoadImageW.restype = wintypes.HANDLE

    SendMessageW = user32.SendMessageW
    SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                             wintypes.WPARAM, wintypes.LPARAM]
    SendMessageW.restype = ctypes.c_ssize_t

    SetClassLongPtrW = getattr(user32,
        'SetClassLongPtrW' if ctypes.sizeof(ctypes.c_void_p) == 8 else 'SetClassLongW')
    SetClassLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    SetClassLongPtrW.restype = ctypes.c_ssize_t

    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    GetWindowTextLengthW = user32.GetWindowTextLengthW
    GetWindowTextW = user32.GetWindowTextW
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    IsWindowVisible = user32.IsWindowVisible

    # 加载两种尺寸（大：任务栏 / 小：标题栏）
    cx_big = user32.GetSystemMetrics(SM_CXICON)
    cy_big = user32.GetSystemMetrics(SM_CYICON)
    cx_small = user32.GetSystemMetrics(SM_CXSMICON)
    cy_small = user32.GetSystemMetrics(SM_CYSMICON)
    flags = LR_LOADFROMFILE | LR_DEFAULTSIZE
    hicon_big = LoadImageW(None, icon_path, IMAGE_ICON, cx_big, cy_big, flags)
    hicon_small = LoadImageW(None, icon_path, IMAGE_ICON, cx_small, cy_small, flags)
    if not hicon_big and not hicon_small:
        return  # 图标加载失败，静默，不影响主程序

    current_pid = kernel32.GetCurrentProcessId()
    found = []

    def _cb(hwnd, _lparam):
        if not IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value != current_pid:
            return True
        length = GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        # 标题里带我们的窗口前缀即可（窗口标题是 "个人博客"）
        if window_title in buf.value or buf.value.startswith(window_title.split('·')[0].strip()):
            found.append(hwnd)
            return False  # 找到一个也够；继续枚举也行
        return True

    EnumWindows(EnumWindowsProc(_cb), 0)
    for hwnd in found:
        if hicon_big:
            SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
            SetClassLongPtrW(hwnd, GCLP_HICON, hicon_big)
        if hicon_small:
            SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
            SetClassLongPtrW(hwnd, GCLP_HICONSM, hicon_small)


# ---------- 单实例互斥 ----------
_WIN32_MUTEX_HANDLE = None
_MUTEX_NAME = r"Global\PersonalBlog.Desktop.Instance.Mutex"

def _acquire_single_instance() -> bool:
    global _WIN32_MUTEX_HANDLE
    if sys.platform != 'win32':
        return True
    try:
        import ctypes
        from ctypes import wintypes
        CreateMutexW = ctypes.windll.kernel32.CreateMutexW
        CreateMutexW.argtypes = [wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCWSTR]
        CreateMutexW.restype = wintypes.HANDLE
        GetLastError = ctypes.windll.kernel32.GetLastError
        ERROR_ALREADY_EXISTS = 183
        handle = CreateMutexW(None, True, _MUTEX_NAME)
        if not handle:
            return True  # 兜底允许
        if GetLastError() == ERROR_ALREADY_EXISTS:
            ctypes.windll.kernel32.CloseHandle(handle)
            return False
        _WIN32_MUTEX_HANDLE = handle
        return True
    except Exception:
        return True

def _release_single_instance():
    global _WIN32_MUTEX_HANDLE
    try:
        if _WIN32_MUTEX_HANDLE:
            import ctypes
            ctypes.windll.kernel32.ReleaseMutex(_WIN32_MUTEX_HANDLE)
            ctypes.windll.kernel32.CloseHandle(_WIN32_MUTEX_HANDLE)
            _WIN32_MUTEX_HANDLE = None
    except Exception:
        pass

def _try_find_port(start: int = 18520, end: int = 18620) -> int:
    """找一个 127.0.0.1 上肯定空闲的本地端口

    桌面内嵌登录持久化关键：**首选端口固定为 18520**。
    原因：Edge Chromium WebView2 / pywebview 的 cookie 存储虽然是 user-data-dir 级的，
    但部分实现仍会把不同端口(origin=host:port)的 session cookie 独立存储；
    如果每次启动都随机跳到 18521 / 18522 / …，用户会以为"重启一次就要重登一次"。
    只有当 18520 真的被其他进程占用（比如用户同时跑了 Web 源服务、
    或开了第二个博客实例被 Mutex 放行之前的冲突窗口），才会向后 +1 扫描。
    用户看到"偶尔重登"也是可以解释的（端口漂移时，那极少数一次重新登录一次即可）。
    """
    # 允许环境变量强制指定端口（部署/调试覆盖用，最高优先级）
    env_port = (os.environ.get('BLOG_PORT') or '').strip()
    if env_port.isdigit():
        p = int(env_port)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('127.0.0.1', p))
            return p
        except OSError:
            # 指定端口被占，兜底扫一遍 18520-18620，不直接崩
            pass
        finally:
            s.close()
    # 首选固定 18520，空闲就占它，绝大多数情况下端口稳定不变
    preferred = 18520
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', preferred))
        return preferred
    except OSError:
        pass
    finally:
        s.close()
    # 18520 被占 → 退而求其次向后扫
    for p in range(max(preferred + 1, start), end):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('127.0.0.1', p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    # 全部被占，让系统兜底分配一个（这种极端情况下重启后端口肯定变化，用户需重新登录一次）
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    _, port = s.getsockname()
    s.close()
    return port

def _wait_for_server(url: str, timeout: float = 30.0) -> None:
    """等博客服务就绪（HTTP 2xx/3xx 返回都算好）"""
    t0 = time.time()
    last_err = None
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as r:
                if 200 <= r.status < 500:
                    return
        except Exception as e:
            last_err = e
            time.sleep(0.2)
    raise RuntimeError(f"博客服务启动超时: {last_err!r}")

# ---------- Flask WSGI 后台线程 ----------
_server_shutdown = threading.Event()
_server_thread: Optional[threading.Thread] = None
_waitress_server: Optional[object] = None

def _start_blog_server(port: int):
    """在 daemon 线程启动 waitress-serve，直到 shutdown 事件触发后关闭"""
    global _waitress_server
    import waitress.server

    # 导入 app 时就会执行 config/init_db（app.py 顶层），但 init_db 内部幂等，我们再跑一次确保旧库补齐
    import app as _app_mod
    from config import Config as _Cfg

    # 确保目录存在
    os.makedirs(_Cfg.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(_Cfg.UPLOAD_FOLDER, 'avatars'), exist_ok=True)
    os.makedirs(os.path.join(_Cfg.UPLOAD_FOLDER, 'bg'), exist_ok=True)
    # 数据库初始化（幂等）
    _app_mod.init_db()

    server = waitress.server.create_server(
        _app_mod.app,
        host='127.0.0.1',
        port=port,
        threads=8,
        channel_timeout=60,
        connection_limit=32,
    )

    def _run():
        try:
            server.run()
        except Exception as e:
            print(f"[博客服务] exited: {e}", file=sys.stderr)

    _waitress_server = server
    t = threading.Thread(target=_run, name='blog-wsgi', daemon=True)
    t.start()
    return t


def _stop_blog_server():
    global _server_thread, _waitress_server
    try:
        # waitress 官方关闭 API：server.close() + 等待主循环自然退出
        if _waitress_server is not None:
            close = getattr(_waitress_server, 'close', None)
            if callable(close):
                try: close()
                except Exception: pass
    except Exception:
        pass
    _server_shutdown.set()
    if _server_thread and _server_thread.is_alive():
        _server_thread.join(timeout=5)


# ---------- 系统托盘（v1.3 新增：纯 Win32 ctypes，零新依赖）----------
# 行为合同：
#   · 点窗口 X：不退出，最小化到系统托盘（首次弹气球提示"仍在运行"）
#   · 托盘图标：左键双击 = 显示/隐藏切换；右键菜单 = 显示/隐藏窗口、打开管理后台、退出博客
#   · 托盘"退出博客"：真正结束进程（关服务 + 释放互斥量）
#   · 非 Windows / 托盘注册失败：自动降级为原行为（X = 关闭即退出）
_TRAY_ACTIVE = False          # 托盘消息窗口注册成功与否
_tray_class_seq = 0           # 托盘消息窗口类名递增序号（重试时避免同名类冲突）
_last_menu_time = 0.0         # 右键菜单去重时间戳（WM_RBUTTONUP 与 WM_CONTEXTMENU 双触发）
_TRAY_QUITTING = False        # 用户已点托盘"退出"：禁止再最小化到托盘
_tray_hwnd = None             # 托盘消息窗口句柄
_MAIN_WINDOW = None           # pywebview 主窗口引用（供托盘退出/切换用）
_TRAY_BASE_URL = ''           # 托盘"打开管理后台"用的 base_url

WM_TRAYICON = 0x8000          # WM_APP，托盘回调消息
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_CONTEXTMENU = 0x007B      # v4 通知协议下右键单击发 WM_CONTEXTMENU
WM_COMMAND = 0x0111
NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIM_SETVERSION = 0x00000004
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NOTIFYICON_VERSION_4 = 4
ID_TRAY_ICON = 1001
IDM_TRAY_SHOW = 40001       # 显示/隐藏窗口
IDM_TRAY_ADMIN = 40002      # 打开管理后台
IDM_TRAY_QUIT = 40003       # 退出博客
SW_HIDE = 0
SW_RESTORE = 9
MF_STRING = 0x00000000
TPM_RETURNCMD = 0x00000100


if sys.platform == 'win32':
    import ctypes as _ct
    from ctypes import wintypes as _wt

    # WNDPROC 回调类型：必须先于 _WndClassExW 定义（lpfnWndProc 字段的类型）
    _WNDPROC_T = getattr(_ct, 'WINFUNCTYPE', _ct.CFUNCTYPE)(
        _ct.c_ssize_t, _wt.HWND, _ct.c_uint, _wt.WPARAM, _wt.LPARAM)

    class _NotifyIconDataW(_ct.Structure):
        """Shell_NotifyIconW 用的 NOTIFYICONDATAW（兼容结构，字段顺序对齐 SDK）"""
        _fields_ = [
            ('cbSize', _ct.c_ulong),
            ('hWnd', _wt.HWND),
            ('uID', _ct.c_uint),
            ('uFlags', _ct.c_uint),
            ('uCallbackMessage', _ct.c_uint),
            ('hIcon', _wt.HANDLE),
            ('szTip', _ct.c_wchar * 128),
            ('dwState', _ct.c_ulong),
            ('dwStateMask', _ct.c_ulong),
            ('szInfo', _ct.c_wchar * 256),
            ('uTimeoutOrVersion', _ct.c_uint),
            ('szInfoTitle', _ct.c_wchar * 64),
            ('dwInfoFlags', _ct.c_ulong),
            ('guidItem', _ct.c_byte * 16),
            ('hBalloonIcon', _wt.HANDLE),
        ]

    class _WndClassExW(_ct.Structure):
        _fields_ = [
            ('cbSize', _ct.c_uint),
            ('style', _ct.c_uint),
            ('lpfnWndProc', _WNDPROC_T),
            ('cbClsExtra', _ct.c_int),
            ('cbWndExtra', _ct.c_int),
            ('hInstance', _wt.HINSTANCE),
            ('hIcon', _wt.HANDLE),
            ('hCursor', _wt.HANDLE),
            ('hbrBackground', _wt.HANDLE),
            ('lpszMenuName', _wt.LPCWSTR),
            ('lpszClassName', _wt.LPCWSTR),
            ('hIconSm', _wt.HANDLE),
        ]
else:
    _NotifyIconDataW = None
    _WndClassExW = None


def _init_tray_win32_prototypes():
    """集中声明托盘相关 Win32 API 的调用原型。

    关键：CreateWindowExW / Shell_NotifyIconW / RegisterClassExW 等若不声明
    argtypes，ctypes 默认把句柄按 c_int 传，64 位句柄会 OverflowError。
    """
    import ctypes as _ct
    from ctypes import wintypes as _wt
    u = _ct.windll.user32
    s = _ct.windll.shell32
    k = _ct.windll.kernel32

    s.Shell_NotifyIconW.argtypes = [_wt.HWND, _ct.c_void_p]
    s.Shell_NotifyIconW.restype = _wt.BOOL
    u.RegisterClassExW.argtypes = [_ct.POINTER(_WndClassExW)]
    u.RegisterClassExW.restype = _ct.c_ushort  # ATOM
    u.CreateWindowExW.argtypes = [
        _wt.DWORD, _wt.LPCWSTR, _wt.LPCWSTR, _wt.DWORD,
        _ct.c_int, _ct.c_int, _ct.c_int, _ct.c_int,
        _wt.HWND, _wt.HMENU, _wt.HINSTANCE, _ct.c_void_p,
    ]
    u.CreateWindowExW.restype = _wt.HWND
    u.DefWindowProcW.argtypes = [_wt.HWND, _wt.UINT, _wt.WPARAM, _wt.LPARAM]
    u.DefWindowProcW.restype = _ct.c_ssize_t
    u.GetMessageW.argtypes = [_ct.POINTER(_wt.MSG), _wt.HWND, _wt.UINT, _wt.UINT]
    u.GetMessageW.restype = _wt.BOOL
    u.TranslateMessage.argtypes = [_ct.POINTER(_wt.MSG)]
    u.DispatchMessageW.argtypes = [_ct.POINTER(_wt.MSG)]
    u.AppendMenuW.argtypes = [_wt.HMENU, _wt.UINT, _ct.c_size_t, _wt.LPCWSTR]
    u.AppendMenuW.restype = _wt.BOOL
    u.TrackPopupMenu.argtypes = [_wt.HMENU, _wt.UINT, _ct.c_int, _ct.c_int,
                                 _ct.c_int, _wt.HWND, _ct.c_void_p]
    u.TrackPopupMenu.restype = _wt.BOOL
    u.GetCursorPos.argtypes = [_ct.POINTER(_wt.POINT)]
    u.GetCursorPos.restype = _wt.BOOL
    u.DestroyMenu.argtypes = [_wt.HMENU]
    u.CreatePopupMenu.restype = _wt.HMENU
    u.ShowWindow.argtypes = [_wt.HWND, _ct.c_int]
    u.SetForegroundWindow.argtypes = [_wt.HWND]
    u.IsWindowVisible.argtypes = [_wt.HWND]
    u.IsWindowVisible.restype = _wt.BOOL
    u.FindWindowW.argtypes = [_wt.LPCWSTR, _wt.LPCWSTR]
    u.FindWindowW.restype = _wt.HWND
    u.LoadImageW.argtypes = [_wt.HINSTANCE, _wt.LPCWSTR, _wt.UINT,
                             _ct.c_int, _ct.c_int, _wt.UINT]
    u.LoadImageW.restype = _wt.HANDLE
    k.GetModuleHandleW.argtypes = [_wt.LPCWSTR]
    k.GetModuleHandleW.restype = _wt.HINSTANCE


# 模块加载时即预热/设置全部托盘相关 Win32 原型（一次成功，避免运行期偶发未初始化）
if sys.platform == 'win32':
    try:
        _init_tray_win32_prototypes()
    except Exception:
        pass


def _tray_build_nid(hwnd, tip=None):
    """构造 NOTIFYICONDATAW（不含通知消息；图标+悬停提示+回调消息）"""
    import ctypes
    icon_path = EXTERNAL_LOGO_ICO
    hicon = None
    if icon_path and os.path.isfile(icon_path):
        try:
            hicon = ctypes.windll.user32.LoadImageW(
                None, icon_path, 1, 0, 0, 0x00000010 | 0x00000040)  # IMAGE_ICON | LR_LOADFROMFILE | LR_DEFAULTSIZE
        except Exception:
            hicon = None
    nid = _NotifyIconDataW()
    nid.cbSize = ctypes.sizeof(_NotifyIconDataW)
    nid.hWnd = hwnd
    nid.uID = ID_TRAY_ICON
    nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
    nid.uCallbackMessage = WM_TRAYICON
    nid.hIcon = hicon or 0
    nid.szTip = (tip or '个人博客')[:127]
    return nid


def _find_main_hwnd():
    """按窗口标题找 pywebview 主窗口句柄（标题固定为 '个人博客'）"""
    import ctypes
    try:
        return ctypes.windll.user32.FindWindowW(None, '个人博客')
    except Exception:
        return None


def _tray_hide_window():
    """最小化到托盘：仅隐藏主窗口（不弹任何通知消息）"""
    import ctypes
    hwnd = _find_main_hwnd()
    if hwnd:
        try:
            ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)
        except Exception:
            pass


def _tray_show_window():
    """从托盘恢复主窗口"""
    import ctypes
    hwnd = _find_main_hwnd()
    if hwnd:
        try:
            ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass


def _tray_toggle_window():
    import ctypes
    hwnd = _find_main_hwnd()
    if hwnd and ctypes.windll.user32.IsWindowVisible(hwnd):
        _tray_hide_window()
    else:
        _tray_show_window()


def _tray_open_admin():
    import webbrowser
    url = (_TRAY_BASE_URL or 'http://127.0.0.1:18520') + '/admin/'
    webbrowser.open(url)


def _tray_request_quit():
    """托盘"退出博客"：置退出标记后走正常关闭闭环（closing 放行 → closed 清理）"""
    global _TRAY_QUITTING
    _TRAY_QUITTING = True
    try:
        if _MAIN_WINDOW is not None and getattr(_MAIN_WINDOW, 'destroy', None):
            _MAIN_WINDOW.destroy()
            return
    except Exception:
        pass
    # 兜底：destroy 不可用则直接退出
    os._exit(0)


def _tray_handle_command(cmd):
    if cmd == IDM_TRAY_SHOW:
        _tray_show_activate()   # 打开博客（显示并置前，不隐藏）
    elif cmd == IDM_TRAY_ADMIN:
        _tray_open_admin()
    elif cmd == IDM_TRAY_QUIT:
        _tray_request_quit()


def _tray_show_activate():
    """左键单击：显示/聚焦主窗口（不隐藏）"""
    import ctypes
    hwnd = _find_main_hwnd()
    if hwnd:
        try:
            ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass


def _tray_show_menu():
    """托盘右键菜单：打开博客 · 打开管理后台 · 退出博客"""
    import ctypes
    global _last_menu_time
    now = time.time()
    if now - _last_menu_time < 0.3:
        return   # 右键会同时触发 WM_RBUTTONUP 与 WM_CONTEXTMENU，300ms 内去重
    _last_menu_time = now
    user32 = ctypes.windll.user32
    hmenu = user32.CreatePopupMenu()
    user32.AppendMenuW(hmenu, MF_STRING, IDM_TRAY_SHOW, '打开博客')
    user32.AppendMenuW(hmenu, MF_STRING, IDM_TRAY_ADMIN, '打开管理后台')
    user32.AppendMenuW(hmenu, MF_STRING, IDM_TRAY_QUIT, '退出博客')
    from ctypes import wintypes
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    # 菜单需要前台窗口才能弹出：先把托盘消息窗口置前（标准做法）
    try:
        if _tray_hwnd:
            user32.SetForegroundWindow(_tray_hwnd)
    except Exception:
        pass
    # TPM_RETURNCMD：阻塞返回用户点击的菜单项 ID，随后自行分发
    cmd = user32.TrackPopupMenu(hmenu, TPM_RETURNCMD, pt.x, pt.y, 0, _tray_hwnd or 0, None)
    if cmd:
        _tray_handle_command(cmd)
    user32.DestroyMenu(hmenu)


def _tray_wndproc(hwnd, msg, wparam, lparam):
    """托盘消息窗口过程：处理图标回调与菜单命令

    注意：实际 Shell 发送的 WM_TRAYICON 消息 lParam 为
    (uID << 16) | 鼠标事件（高 16 位是图标 ID），因此必须用
    lParam 低 16 位匹配鼠标事件码。
    """
    if msg == WM_TRAYICON:
        ev = lparam & 0xFFFF   # 低 16 位 = 鼠标事件码
        # v4 通知协议：右键=WM_CONTEXTMENU；v3 兼容：右键=WM_RBUTTONUP
        if ev in (WM_RBUTTONUP, WM_CONTEXTMENU):
            _tray_show_menu()
        elif ev in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
            # 左键单击/双击：打开应用（显示并置前）
            _tray_show_activate()
    elif msg == WM_COMMAND:
        _tray_handle_command(wparam & 0xFFFF)
    import ctypes
    return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)


# WINFUNCTYPE 仅 Windows 有；用 CFUNCTYPE 兜底以便非 Windows 环境能 import 本文件
_TRAY_WNDPROC_PTR = getattr(ctypes, 'WINFUNCTYPE', ctypes.CFUNCTYPE)(
    ctypes.c_ssize_t,
    ctypes.wintypes.HWND,
    ctypes.c_uint,
    ctypes.wintypes.WPARAM,
    ctypes.wintypes.LPARAM,
)(_tray_wndproc)


def _tray_thread_main():
    """托盘线程：注册消息窗口 → 添加托盘图标 → GetMessageW 消息循环（必须同线程）"""
    global _TRAY_ACTIVE, _tray_hwnd
    if sys.platform != 'win32':
        return
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    wc = _WndClassExW()
    wc.cbSize = ctypes.sizeof(_WndClassExW)
    wc.lpfnWndProc = _TRAY_WNDPROC_PTR
    wc.hInstance = kernel32.GetModuleHandleW(None)
    # 用递增类名：重试时避免与已注册的同名窗口类冲突（RegisterClassExW 同类名重复注册会失败）
    global _tray_class_seq
    _tray_class_seq += 1
    class_name = 'PersonalBlogTrayWindow%d' % _tray_class_seq
    wc.lpszClassName = class_name

    try:
        if not user32.RegisterClassExW(ctypes.byref(wc)):
            return
    except Exception:
        return

    try:
        hwnd = user32.CreateWindowExW(
            0, class_name, 'PersonalBlogTray', 0,
            0, 0, 0, 0, None, None, wc.hInstance, None)
    except Exception:
        return
    if not hwnd:
        return
    _tray_hwnd = hwnd

    try:
        nid = _tray_build_nid(hwnd, tip='个人博客')
        if not ctypes.windll.shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
            return
        # 请求 v4 版通知协议（右键/双击回调更可靠）
        nid_v4 = _tray_build_nid(hwnd)
        nid_v4.uTimeoutOrVersion = NOTIFYICON_VERSION_4
        ctypes.windll.shell32.Shell_NotifyIconW(NIM_SETVERSION, ctypes.byref(nid_v4))
        _TRAY_ACTIVE = True
    except Exception:
        _TRAY_ACTIVE = False
        return

    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

    # 消息循环结束：删除托盘图标并销毁消息窗口
    try:
        ctypes.windll.shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(_tray_build_nid(hwnd)))
    except Exception:
        pass
    user32.DestroyWindow(hwnd)
    _tray_hwnd = None
    _TRAY_ACTIVE = False


def _start_tray(webview_window=None):
    """启动托盘线程并等待注册结果；非 Windows / 失败返回 False（降级为 X=关闭即退出）"""
    global _MAIN_WINDOW, _TRAY_ACTIVE
    import sys
    if sys.platform != 'win32':
        return False
    try:
        _init_tray_win32_prototypes()
    except Exception:
        pass
    _MAIN_WINDOW = webview_window
    # 托盘注册失败时自动重试（偶发的 Shell/窗口初始化竞态可自愈）
    for attempt in range(5):
        try:
            t = threading.Thread(target=_tray_thread_main, name='TrayThread', daemon=True)
            t.start()
            # 最多等 3 秒确认托盘注册成功
            for _ in range(30):
                if _TRAY_ACTIVE or not t.is_alive():
                    break
                time.sleep(0.1)
            if _TRAY_ACTIVE:
                return True
        except Exception:
            pass
        # 线程失败（未激活且已退出）时短暂等待后重试
        if attempt < 4:
            time.sleep(0.3)
    return _TRAY_ACTIVE


# ---------- pywebview 主流程 ----------
def main() -> int:
    if not _acquire_single_instance():
        # 已存在实例：弹个简单系统提示框然后退出
        try:
            import ctypes
            MB_ICONINFORMATION = 0x40
            MB_OK = 0x0
            ctypes.windll.user32.MessageBoxW(
                None,
                "个人博客已经在运行了，我帮你把它调到前面来～",
                "个人博客",
                MB_OK | MB_ICONINFORMATION,
            )
            # 尝试激活已存在的主窗口
            import ctypes as ct
            hwnd = ct.windll.user32.FindWindowW(None, "个人博客")
            if hwnd:
                SW_RESTORE = 9
                ct.windll.user32.ShowWindow(hwnd, SW_RESTORE)
                ct.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        return 0

    port = _try_find_port()
    base_url = f'http://127.0.0.1:{port}'
    global _TRAY_BASE_URL
    _TRAY_BASE_URL = base_url

    global _server_thread
    _server_thread = _start_blog_server(port)

    try:
        _wait_for_server(base_url + '/', timeout=30.0)
    except Exception as e:
        _stop_blog_server()
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None,
                f"博客服务启动失败：\n{e}",
                "个人博客 · 启动失败",
                0x10,
            )
        except Exception:
            print(f"启动失败: {e}", file=sys.stderr)
        return 2

    # ---------- 双向同步：每 5 分钟后台自动执行一次（Chrome 式同步）----------
    _SYNC_INTERVAL_SEC = 5 * 60  # 5 分钟

    def _periodic_sync_worker(port_for_ref: int):
        """
        后台定时同步线程：
          • 每 5 分钟检测一次 settings.sync_enabled
          • 已开启 & 配置齐全 → 调用 sync_engine 实际同步（push+pull LWW 合并）
          • 未开启 → 不做任何事，循环等待
        """
        # 启动后先等 30 秒，避免和自动备份/开窗口竞争 CPU
        time.sleep(30.0)
        while not _server_shutdown.is_set():
            try:
                import app as _app_m
                import gitee_backup as _gb
                from sync_engine import SyncEngine, GiteeRemoteAdapter

                _set = _gb.load_settings(DATA_DIR)
                if (not _set.get('sync_enabled')
                        or not _set.get('token')
                        or not _set.get('repo')
                        or not _set.get('owner')):
                    # 没开同步或配置未齐 → 继续等下一轮
                    time.sleep(_SYNC_INTERVAL_SEC)
                    continue

                with _app_m.app.app_context():
                    try:
                        adapter = GiteeRemoteAdapter(_set)
                        state_path = os.path.join(DATA_DIR, 'sync_state.json')
                        engine = SyncEngine(_app_m.db.session, adapter, state_path)
                        result = engine.run_sync()
                        # 写同步摘要
                        try:
                            last_path = os.path.join(DATA_DIR, 'sync_last_run.json')
                            os.makedirs(DATA_DIR, exist_ok=True)
                            tmp = last_path + '.tmp'
                            import json as _json
                            with open(tmp, 'w', encoding='utf-8') as f:
                                _json.dump({
                                    'ok': True,
                                    'finished_at': __import__('datetime').datetime.utcnow().isoformat(),
                                    'pushed': result.get('pushed', {}),
                                    'pulled': result.get('pulled', {}),
                                    'cursors_keys': sorted(list(result.get('cursors', {}).keys())),
                                }, f, ensure_ascii=False, indent=2)
                            os.replace(tmp, last_path)
                        except Exception:
                            pass
                    except Exception:
                        # 失败静默记录，不影响主循环
                        try:
                            _app_m.app.logger.exception('周期同步异常')
                            last_path = os.path.join(DATA_DIR, 'sync_last_run.json')
                            os.makedirs(DATA_DIR, exist_ok=True)
                            tmp = last_path + '.tmp'
                            import json as _json
                            with open(tmp, 'w', encoding='utf-8') as f:
                                _json.dump({'ok': False,
                                            'error': '周期同步异常，详见日志',
                                            'finished_at': __import__('datetime').datetime.utcnow().isoformat()},
                                           f, ensure_ascii=False, indent=2)
                            os.replace(tmp, last_path)
                        except Exception:
                            pass
            except Exception:
                pass
            # 每轮 sleep 分片，及时响应 shutdown
            for _ in range(_SYNC_INTERVAL_SEC // 2):
                if _server_shutdown.is_set():
                    break
                time.sleep(2.0)

    threading.Thread(target=_periodic_sync_worker, name='PeriodicAutoSync',
               args=(port,), daemon=True).start()

    import webview

    def on_closing():
        """点窗口 X：托盘可用时最小化到托盘而不是退出；托盘"退出"命令则放行关闭"""
        if _TRAY_ACTIVE and not _TRAY_QUITTING:
            _tray_hide_window()
            return False
        return True

    def on_closed():
        """窗口关闭后立即退出：关服务 + 释放互斥量"""
        _stop_blog_server()
        _release_single_instance()
        # webview 6.x 下 closed 事件之后主线程的 start() 会返回
        # 这里强制退出避免 webview 子线程 linger
        os._exit(0)

    win_title = '个人博客'
    # 关键：不传 icon= 给 create_window（pywebview 5.x 不支持，会 TypeError）
    cw_kwargs, win_icon = _build_create_window_kwargs(title=win_title, url=base_url + '/')
    # 提前启动后台 Win32 图标挂载线程（它会等窗口出现再操作）
    _apply_window_icon_async(win_icon, win_title)

    window = webview.create_window(**cw_kwargs)
    window.events.closed += on_closed
    window.events.closing += on_closing

    # 启动系统托盘（v1.3）：注册成功 → X=最小化到托盘；失败（非 Windows 等）→ 保持"关闭即退出"
    _start_tray(window)

    try:
        webview.start(
            gui='edgechromium',  # Windows 优先 WebView2（Edge Chromium）
            debug=False,
            http_server=False,   # 不用 webview 自带的 http 协议服务，我们已经有 Flask
            func=[],
        )
    except Exception as e:
        # 兜底：WebView2 Runtime 未安装时给出明确提示
        msg = (
            "无法启动桌面内嵌浏览器窗口：\n"
            f"{e}\n\n"
            "可能是缺少 Windows WebView2 Runtime（个人博客使用它来渲染界面）。\n"
            "请到下面地址免费下载并安装 Evergreen Bootstrapper（几十 KB，几秒钟装好）：\n"
            "https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
            "安装完成后重新启动博客即可。"
        )
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg, "个人博客 · 缺少组件", 0x10)
        except Exception:
            print(msg, file=sys.stderr)
        return 3
    finally:
        _stop_blog_server()
        _release_single_instance()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _stop_blog_server()
        _release_single_instance()
        sys.exit(130)
