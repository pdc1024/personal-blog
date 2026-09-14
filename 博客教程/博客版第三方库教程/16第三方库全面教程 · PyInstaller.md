# 第三方库全面教程 · PyInstaller

> 面向初学者：你手里的"个人博客绿色版.exe"就是 PyInstaller 打包出来的。学完这份教程，你会掌握打包的完整原理、spec 文件的每一个字段，以及"打包后神秘报错"的全部排查套路。
> 适用版本：PyInstaller 6.x ｜ 博客项目：`blog_desktop.spec`

---

# 第 1 章 这个库是什么

PyInstaller 是 Python 的**打包工具**：把 Python 程序（源码 + 依赖库 + 资源文件）打包成一个**可执行文件**（exe），让目标电脑**不需要装 Python** 就能运行。

一句话：**PyInstaller 是博客的"出厂包装线"**——你双击的 `个人博客.exe` 和旁边的 `_internal` 文件夹，都是它的杰作。

**为什么需要它？** 你的朋友不会装 Python，更不会 pip install 一堆库。PyInstaller 把解释器、库、代码、模板全部装进一个包里，双击即用——这就是"绿色版"的含义。

---

# 第 2 章 核心概念与原理

## 2.1 打包原理：静态分析 + 收集依赖

PyInstaller 怎么知道要带哪些文件？两步：

```
① 静态分析：扫描你 import 的模块，递归找到所有依赖
   （app.py → flask → werkzeug → markupsafe → ...）
② 收集资源：按 spec 配置，把模板/静态文件/数据库等一起装进包
```

**致命弱点**：它靠"看得见的 import"找依赖。**动态加载**（`__import__`、字符串形式的模块名、`importlib.import_module`）它看不见——这就是 `HIDDEN_IMPORTS` 存在的意义。

## 2.2 onedir vs onefile：绿色版用哪个

| 模式 | 产物 | 启动速度 | 适合 |
|---|---|---|---|
| `-D` / onedir（默认） | exe + `_internal` 文件夹 | 快 | **博客用的**（绿色版） |
| `-F` / onefile | 单个 exe | 慢（每次启动解压） | 分发方便但启动慢、易被杀软误报 |

**为什么博客用 onedir？** 启动快、不误报、资源文件好管理（`_internal` 里装模板）。用户拷走整个文件夹就是绿色版。

## 2.3 打包后资源路径为什么会变（最大坑）

源码里 `open('templates/base.html')` 这种**相对路径**，打包后会找不到——因为运行时的工作目录不是源码目录，模板被塞进了 `_internal`。

**正解**：代码里用"基于可执行文件位置的绝对路径"：

```python
import sys, os
BASE_DIR = os.path.dirname(sys.executable)          # exe 所在目录
RESOURCE_DIR = os.path.join(BASE_DIR, '_internal')  # 资源目录（onedir 模式）
```

博客的 `config.py` 就是这么用 `Config.RESOURCE_DIR` 定位模板、数据库、日志的——这就是"打包后还能跑"的秘诀。

---

# 第 3 章 安装与版本

```bash
pip install pyinstaller
pyinstaller --version    # 版本验证（6.x）
```

PyInstaller 6.x 要求 Python 3.8+。**注意**：必须在和项目相同的 Python 环境里打包（用什么解释器跑，就用它打包）。

---

# 第 4 章 API 全面讲解

## 4.1 命令行快速入门

```bash
# 最简：生成 onedir（dist/ 目录下出现可执行文件）
pyinstaller myapp.py

# 常用参数组合
pyinstaller -D -w -i logo.ico --name 我的程序 myapp.py
#   -D / -F    onedir / onefile
#   -w         无控制台黑窗（GUI 程序必加）
#   -c         保留控制台（看报错调试用）
#   -i 图标     exe 图标
#   --name     程序名（默认 py 文件名）

# 带资源文件
pyinstaller --add-data "templates;templates" --add-data "static;static" myapp.py
# 注意 Windows 分隔符是分号 ; （Linux/Mac 是冒号 :）

# 补动态依赖
pyinstaller --hidden-import webview.platforms.edgechromium myapp.py

# 排除无关大库（瘦身）
pyinstaller --exclude-module numpy --exclude-module tkinter myapp.py
```

## 4.2 spec 文件：打包的"配方"（✅ 博客的核心）

用 `pyinstaller myapp.py` 后同目录会生成 `myapp.spec`，**以后改 spec 再打包**（`pyinstaller myapp.spec`）。博客的 `blog_desktop.spec` 就是手改过的配方，结构如下：

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# ① Analysis：分析依赖。a.binaries 是编译后的库，a.datas 是资源
a = Analysis(
    ['main.py'],                      # 入口文件（桌面版）
    pathex=[],                        # 额外搜索路径
    binaries=[],                      # 额外二进制（dll 等）
    datas=[                           # ★ 资源文件（模板/静态/上传目录）
        ('templates', 'templates'),
        ('static', 'static'),
        ('uploads', 'uploads'),
    ],
    hiddenimports=[                   # ★ 动态加载的模块，漏了必崩
        'waitress', 'waitress.server',
        'yaml', 'markdown', 'pygments', 'dateutil',
        'gitee_backup', 'sync_engine',       # 项目自己的模块（被局部 import）
        'certifi', '_ssl',                    # SSL 证书链（Gitee 同步用）
        'webview.platforms.edgechromium',     # pywebview 按平台动态导入
        'webview.platforms.winforms',
        'pythonnet', 'clr_loader',            # pywebview 的 .NET 桥接
        'System', 'System.Windows.Forms',
    ],
    excludes=['tkinter', 'unittest', 'numpy', 'scipy', 'pandas',
              'matplotlib', 'PyQt5', 'PyQt6', 'PySide6', 'tornado', 'IPython'],
    noarchive=False,
)

# ② PYZ：把 Python 字节码压成一个归档
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ③ EXE：生成启动器 exe
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,            # onedir 模式：主体库不塞进 exe
    name='个人博客',                   # exe 文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                        # 不用 UPX 压缩（可能被杀软误报）
    console=False,                    # ★ 无控制台黑窗
    icon='logo.ico',                  # exe 图标
)

# ④ COLLECT：把 exe + 库 + 资源收拢成一个文件夹
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False,
    name='个人博客',                   # 输出文件夹名（绿色版文件夹）
)
```

**四个环节各管什么**：Analysis（找依赖）→ PYZ（压缩代码）→ EXE（生成启动器）→ COLLECT（收拢成文件夹）。

## 4.3 spec 里的博客经验（务必看）

```python
SHARED_DATAS = [('templates', 'templates'), ('static', 'static'), ('uploads', 'uploads')]
# 博客把它定义成变量复用——资源目录一次改全改

EXCLUDES = ['tkinter', 'unittest', 'pydoc', 'doctest', 'pdb', 'numpy',
            'scipy', 'pandas', 'matplotlib', 'PyQt5', 'PyQt6', 'PySide6',
            'tornado', 'IPython']
# 排除项目没用的重型库/调试模块，包体积从几百 MB 降到 34MB 左右

HIDDEN_IMPORTS = [
    'waitress', 'waitress.server', 'yaml', 'markdown', 'pygments', 'dateutil',
    'gitee_backup', 'sync_engine', 'certifi', '_ssl',
    'webview.platforms.edgechromium', 'webview.platforms.winforms',
    'pythonnet', 'clr_loader', 'System', 'System.Windows.Forms',
]
# waitress/markdown/pygments 等被局部 import；pywebview 用字符串动态导入平台模块、
# pythonnet/clr_loader/System 系列是它底层 .NET 桥接；gitee_backup/sync_engine
# 被 app.py 局部导入——全是静态分析看不见的，必须手写
```

## 4.4 运行时调试套路（✅ 踩坑必看）

```python
# 双击 exe 没反应时：
# ① 命令行直接跑 exe，看报错
cd dist\个人博客
.\个人博客.exe          # 如果有 console=False 没输出，先改 True 再打包

# ② 快速定位：临时把 console=False 改成 True，重新打包，看黑窗报什么
# ③ 定位"缺模块"后，加入 hiddenimports，重新打包
# ④ 每次改代码/改 spec 都要【先删 build/ 和 dist/】再打包，
#    否则可能打的是旧缓存！
```

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客 config.py 的资源路径（打包后还能跑的秘诀）

```python
import sys, os

# PyInstaller 打包后：资源目录(只读 templates/static) 与数据目录(可写 db/uploads/logs) 分离
if getattr(sys, 'frozen', False):
    RESOURCE_DIR = sys._MEIPASS                 # 打包资源解压目录（只读）
    # onedir 模式下 _MEIPASS 就指向 exe 旁边的 _internal 文件夹
    DATA_DIR = os.path.dirname(sys.executable)  # exe 所在目录（可写：db/uploads/logs 放这）
else:
    RESOURCE_DIR = BASE_DIR                     # 开发模式：源码目录
    DATA_DIR = BASE_DIR

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(DATA_DIR, 'blog.db')
TEMPLATE_DIR = os.path.join(RESOURCE_DIR, 'templates')
```

**`sys.frozen` / `sys._MEIPASS` 是关键**：
- `sys.frozen`：打包后运行才有（源码运行没有这个属性）——判断"现在在 exe 里还是源码里"
- `sys._MEIPASS`：PyInstaller 在运行时自动设置的资源解压目录；onedir 模式就是 `_internal`，onefile 模式是临时解压目录
- 把"只读资源"（模板/静态）和"可写数据"（数据库/上传）**分开目录**，用户升级版本时直接覆盖 exe+_internal 也不会丢数据

## 5.2 独立示例：给任意脚本打包的完整流程

```bash
# 1. 第一次打包（生成 spec）
pyinstaller -D -w --name MyTool tool.py

# 2. 编辑 MyTool.spec：加资源、hiddenimports
#     datas=[('assets', 'assets')]
#     hiddenimports=['secret_module']

# 3. 清缓存重打（重要！）
rmdir /s /q build dist
pyinstaller MyTool.spec

# 4. 验证
cd dist\MyTool
MyTool.exe        # 双击或命令行跑
```

---

# 第 6 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 打包后找不到模板 | `TemplateNotFound` | datas 加 templates/static；代码用 RESOURCE_DIR 绝对路径 |
| 打包后 ModuleNotFoundError | 运行到某处才崩 | 动态导入的模块加进 hiddenimports |
| 双击没反应 | 无窗口无报错 | 命令行跑 exe；临时 console=True 看报错 |
| 中文路径 | 打包失败或运行异常 | 项目放英文路径（D:\\blog） |
| 改了代码还是旧行为 | 打出来是旧的 | 先删 build/ 和 dist/ 再打包 |
| 被杀软误报 | exe 被删/拦截 | onedir 模式 + upx=False；加白名单 |
| 包太大 | 几百 MB | excludes 排除无关库（numpy 等） |
| 图标没生效 | exe 还是默认图标 | -i logo.ico；exe 图标缓存（重启资源管理器） |

---

# 第 7 章 学习路径与自测

**学习路径**：先命令行打一个"Hello 窗口"（半天）→ 加资源文件（半天）→ 手改 spec 四个环节（1 天）→ 排查 hiddenimports（1 天，博客实战）→ 资源路径 sys.frozen 改造（半天）。

**自测题**：

1. onedir 和 onefile 的区别？博客为什么选 onedir？
2. 打包后为什么模板/数据库会找不到？
3. `HIDDEN_IMPORTS` 是给谁用的？举个博客里的例子。
4. `sys.frozen` 是什么意思？
5. 改了代码重新打包，为什么先删 build/ 和 dist/？

**答案**：
1. onedir 是 exe+文件夹（启动快、好调试）；onefile 是单 exe（慢、易误报）。博客要绿色版文件夹所以 onedir。
2. 相对路径在工作目录找不到资源——要用基于 sys.executable 的绝对路径（RESOURCE_DIR）。
3. 动态加载（字符串 import）的模块，静态分析看不见。如 pywebview 的 webview.platforms.edgechromium、gitee_backup。
4. 打包后运行才有的标志，用它判断"现在是在 exe 里还是源码里"，决定资源路径。
5. build/dist 有旧缓存，不删可能打的是旧代码，改了等于白改。

---

# 全部 12 份教程完结

到这里，博客项目用到的 **12 个库**（11 个第三方库 + SQLite 标准库）都各有了一份"从零到精通"全面教程。学习建议：

1. **主线四件套必学**：Flask → Flask-SQLAlchemy → Jinja2 → python-markdown（改博客功能的主战场）
2. **桌面两件套**：waitress + pywebview（桌面版的一切）
3. **按需查**：Werkzeug（上传/密码）、PyYAML（配置）、dateutil（日期）、Pygments（高亮）、PyInstaller（打包）
4. **每份教程的自测题**能独立答出来，才算真正掌控该库
