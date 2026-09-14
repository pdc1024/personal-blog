# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置 —— 个人博客
- 入口：main.py
- 模式：--onedir + --windowed（无控制台黑框）
- 内嵌浏览器：pywebview（Windows 使用 WebView2 = Edge Chromium）
"""

import os
import sys
import glob

PROJECT_DIR = os.path.abspath(SPECPATH)

block_cipher = None

# 与传统服务版共享的只读资源
SHARED_DATAS = [
    (os.path.join(PROJECT_DIR, 'templates'), 'templates'),
    (os.path.join(PROJECT_DIR, 'static'), 'static'),
    # uploads/ 目录：头像/背景图上传落点 + sample 示例文件
    # 若用户 install 到新机器没运行过一次博客，uploads/ 为空没关系，至少目录建好 + sample 到位
    (os.path.join(PROJECT_DIR, 'uploads'), 'uploads'),
    (os.path.join(PROJECT_DIR, '.env.example'), '.'),
    (os.path.join(PROJECT_DIR, 'logo.png'), '.'),
    (os.path.join(PROJECT_DIR, 'logo.ico'), '.'),
]

# ========== 用户外置资源（运行时可替换的主路径）==========
# 除了上面 SHARED_DATAS 会把 logo.ico / logo替换说明.txt 装进 _internal/ 做兜底，
# 我们还会在 COLLECT 钩子（文件末尾）里再额外复制一份到 onedir 顶层（和 exe 同级），
# 这样 main.py 的 _resolve_external_logo_ico() 会优先命中 exe 同级那一份，
# 用户改它 → 下次启动窗口标题栏 / 任务栏 / ALT+TAB 就立即生效。
USER_REPLACEABLE_TOP = [
    ('logo.ico', 'logo.ico'),            # 用户可自行替换的运行时窗口/任务栏图标
    ('logo替换说明.txt', 'logo替换说明.txt'),
]

EXCLUDES = [
    'tkinter',
    'unittest',
    'pydoc',
    'doctest',
    'pdb',
    'test',
    'numpy',
    'scipy',
    'pandas',
    'matplotlib',
    'PyQt5',
    'PyQt6',
    'PySide6',
    'tornado',
    'IPython',
]

HIDDEN_IMPORTS = [
    # --- 博客自身需要的 ---
    'waitress',
    'waitress.server',
    'yaml',
    'markdown',
    'markdown.extensions.fenced_code',
    'markdown.extensions.toc',
    'pygments',
    'pygments.formatters',
    'pygments.formatters.HtmlFormatter',
    'pygments.lexers',
    'dateutil',
    'gitee_backup',        # Gitee 备份/恢复模块（新加）
    'sync_engine',         # 双向同步引擎（Chrome 式 LWW 合并）
    'urllib.request',
    'certifi',              # SSL CA bundle（frozen 环境 gitee_backup.build_ssl_context() 会用到）
    '_ssl',                 # 保证 ssl 标准库模块被打包（有时 hiddenimport 才会被带进来）

    # --- pywebview 6.x (Edge Chromium / WebView2) 需要的 ---
    'webview',
    'webview.platforms.winforms',     # Windows 下的后端
    'webview.platforms.cef',          # 备用
    'webview.platforms.edgechromium', # 主要使用的 WebView2 后端
    'webview.http',
    'webview.js.css',
    'webview.js.css.bootstrap',
    # pythonnet / clr_loader（pythonnet 3.x）
    'pythonnet',
    'clr_loader',
    'clr_loader._functional',
    'clr_loader.netfx',
    'clr_loader.netcore',
    # 经典 .NET 命名空间（pythonnet 3.x 把它做成延迟 import）
    'System',
    'System.Collections',
    'System.Drawing',
    'System.Windows.Forms',
]

# ========== pywebview 的 WebView2 / pythonnet 二进制 + 运行时 / 数据 ==========
def _collect_pkg(subpkg):
    """返回 site-packages/<subpkg> 的绝对路径（定位隐藏资源用）"""
    import importlib.util
    spec = importlib.util.find_spec(subpkg)
    if spec is None:
        return None
    origin = spec.origin or ''
    if origin.endswith('__init__.py'):
        return os.path.dirname(origin)
    return os.path.dirname(origin)

BINS = []
DATAS = list(SHARED_DATAS)

# clr_loader/runtimes/ 含 .NET 托管 dll，整个目录采集
clr_dir = _collect_pkg('clr_loader')
if clr_dir and os.path.isdir(clr_dir):
    DATAS.append((clr_dir, 'clr_loader'))

# pythonnet: Python.Runtime.dll 等 runtime 文件（一般在 pythonnet/runtimes 下）
pynt_dir = _collect_pkg('pythonnet')
if pynt_dir and os.path.isdir(pynt_dir):
    DATAS.append((pynt_dir, 'pythonnet'))

# webview 自带的 JS/CSS 资源
wv_dir = _collect_pkg('webview')
if wv_dir and os.path.isdir(wv_dir):
    # webview/lib/ etc.
    for item in os.listdir(wv_dir):
        fp = os.path.join(wv_dir, item)
        if os.path.isdir(fp) and item in ('lib', 'js'):
            DATAS.append((fp, os.path.join('webview', item)))

# 桌面化打包：无控制台窗口 = windowed=True
a = Analysis(
    [
        os.path.join(PROJECT_DIR, 'main.py'),
        os.path.join(PROJECT_DIR, 'app.py'),
        os.path.join(PROJECT_DIR, 'gitee_backup.py'),
        os.path.join(PROJECT_DIR, 'sync_engine.py'),
    ],
    pathex=[PROJECT_DIR],
    binaries=BINS,
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='个人博客',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # 无控制台黑窗口（GUI app）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_DIR, 'logo.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='个人博客',
)

# ===== 外置资源：支持用户"在 exe 同目录里自己替换 logo.ico / 查看说明" =====
# PyInstaller 的 SHARED_DATAS 会把文件落到 _internal/ 里，用户找不到。
# 这里在 COLLECT 完成后，把项目根目录的 USER_REPLACEABLE_TOP 列表里的文件
# 额外复制一份到 dist/个人博客/ 顶层（和 exe 同级）：
#   · logo.ico → main.py 的 EXTERNAL_LOGO_ICO 会优先命中它 → 改掉它，下次启动窗口/任务栏图标就变
#   · logo替换说明.txt → 给用户看"哪条图标链路改哪个文件"的说明
import shutil as _shutil
_OUTDIR = os.path.join(os.path.dirname(os.path.abspath(SPECPATH)), 'dist', '个人博客')
if os.path.isdir(_OUTDIR):
    for _name, _name_out in USER_REPLACEABLE_TOP:
        _src = os.path.join(PROJECT_DIR, _name)
        if not os.path.isfile(_src):
            print(f'[spec 钩子] 跳过不存在文件: {_src}')
            continue
        _dst = os.path.join(_OUTDIR, _name_out)
        try:
            _shutil.copy2(_src, _dst)
            print(f'[spec 钩子] 外置可替换资源已复制: {_name_out} -> {_dst}')
        except Exception as _e:
            print(f'[spec 钩子] 外置资源复制失败 {_name_out}: {_e}')
