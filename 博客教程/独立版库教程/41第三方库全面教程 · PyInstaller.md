# 第三方库全面教程 · PyInstaller（独立版）

> 面向初学者：本教程**独立成篇**，假设你会基础 Python 和命令行。术语第一次出现都有白话解释。
> 适用版本：PyInstaller 6.x ｜ 配套知识：与《pywebview》《waitress》配合（把桌面应用打包成 exe）。
> 学习目标：从"只会 python xxx.py"到"能把任何 Python 程序打包成双击即用的 exe，并处理资源文件、图标、常见打包坑"。

---

# 第 1 章 这个库是什么

## 1.1 一句话认识 PyInstaller

**PyInstaller** 是 Python 的**打包工具**：把你的 `.py` 程序和它依赖的所有第三方库、Python 解释器一起打包成一个独立的**可执行文件**（Windows 的 `.exe`、macOS 的 `.app`），用户不用装 Python 就能运行。

```bash
pip install pyinstaller
pyinstaller -F hello.py        # 一条命令生成独立 exe
# dist/hello.exe —— 双击就能跑
```

## 1.2 打包做了什么

```
hello.py + 依赖库 + Python 解释器
        ↓ PyInstaller 分析依赖
        ↓ 收集代码和二进制
hello.exe（内含解释器和库）
```

**关键认知**：打包产物**内含 Python 解释器**——所以目标机器不需要装 Python；但也因此 exe 体积较大（几十 MB 起）。

## 1.3 两种模式

| 模式 | 命令 | 产物 | 特点 |
|---|---|---|---|
| **单文件（onefile）** | `-F` | 一个 exe | 方便分发，但**启动慢**（每次解压到临时目录） |
| **单目录（onedir）** | 默认 | 一个文件夹（exe + 依赖文件） | 启动快，打包体积小，**推荐** |

**建议**：正式发布用 **onedir**（快、稳）；给人传文件图省事用 onefile。

---

# 第 2 章 核心概念与原理

## 2.1 PyInstaller 怎么找依赖

PyInstaller **静态分析**你的 import：从 `main.py` 出发，追踪所有 `import`，收集对应模块。**局限**：
- **动态导入**（`importlib.import_module("x")`、字符串拼接模块名）追踪不到——需要 `--hidden-import` 手动加。
- 第三方库如果动态加载插件（如 Pygments 的语言列表、pkg_resources 入口点），也要显式声明。

## 2.2 打包后的资源路径变化（最核心的坑）

打包后，你的程序运行在**临时解压目录**（onefile）或 `_internal` 目录（onedir）里——**原来的相对路径全部失效**！标准解法：

```python
import sys, os

def resource_path(relative):
    """打包后也能正确找到资源文件"""
    base = getattr(sys, "_MEIPASS",                    # PyInstaller 注入的路径
                   os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)

# 用法：所有资源文件（html/图片/配置文件）都用它定位
html_path = resource_path("index.html")
```

**`sys._MEIPASS`** 是 PyInstaller 运行时注入的特殊属性：打包后指向资源解压目录；源码运行时不存在（用 `getattr` 兜底回源码目录）。

## 2.3 资源文件必须显式打包

`--add-data` 参数把资源文件/文件夹**塞进打包产物**：

```bash
# Windows 用 ; 分隔（源:目标）
pyinstaller -F --add-data "templates;templates" --add-data "static;static" main.py
# macOS/Linux 用 : 分隔
pyinstaller -F --add-data "templates:templates" main.py
```

---

# 第 3 章 安装与版本

```bash
pip install pyinstaller
pyinstaller --version        # 当前稳定版 6.x
```

---

# 第 4 章 打包命令全面讲解

> 标注：✅ = 必会；➕ = 推荐；🧪 = 进阶

## 4.1 最简打包（✅）

```bash
pyinstaller -F hello.py
# 生成 build/（中间文件）、dist/hello.exe（产物）、hello.spec（配置）
```

## 4.2 常用参数（✅ 生产配置）

```bash
pyinstaller \
    -F \                              # 单文件模式
    -w \                              # 无控制台窗口（GUI 应用用）
    --name MyApp \                    # 产物名（默认 main）
    --icon app.ico \                  # 图标（.ico 格式）
    --add-data "templates;templates" \  # 打包资源（Windows 分号）
    --add-data "static;static" \
    --hidden-import module_name \     # 手动补动态导入的模块
    --exclude-module tkinter \        # 排除不用的模块（瘦身）
    --clean \                         # 清理缓存重新打包
    main.py
```

**关键参数速查**：

| 参数 | 作用 |
|---|---|
| `-F` / `--onefile` | 单文件模式 |
| `-D` / `--onedir` | 目录模式（默认，推荐） |
| `-w` / `--noconsole` | 不显示控制台黑窗（GUI 用） |
| `-c` / `--console` | 显示控制台（CLI 工具用） |
| `--name` | 产物名 |
| `--icon` | 图标（exe 图标） |
| `--add-data` | 打包资源文件（**多次使用**） |
| `--hidden-import` | 补手动导入的模块（**多次使用**） |
| `--exclude-module` | 排除模块（减小体积） |
| `--clean` | 清理缓存 |
| `--noconfirm` | 覆盖输出不询问 |
| `--version-file` | 版本信息（右键属性里显示） |
| `--uac-admin` | 请求管理员权限 |

## 4.3 spec 文件（➕ 项目级打包配置）

第一次打包会生成 `.spec` 文件（Python 语法）。复杂项目**直接编辑 spec** 再 `pyinstaller app.spec`：

```python
# app.spec
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('static', 'static')],   # 资源
    hiddenimports=['webview.platforms.edgechromium'],            # 动态导入
    hookspath=[],
    excludes=['tkinter', 'unittest'],                            # 排除
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    name='MyApp',
    debug=False, strip=False, upx=True,
    console=False,                 # False = 无控制台
    icon='app.ico',
)
```

---

# 第 5 章 实战项目案例

## 案例 1（入门级）：CLI 工具打包

```python
# hello_cli.py
import sys

def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "世界"
    print(f"你好，{name}！")

if __name__ == "__main__":
    main()
```

```bash
pyinstaller -F -c --name hello hello_cli.py
# 使用：
dist\hello.exe 小明     # 输出：你好，小明！
```

## 案例 2（进阶级）：带资源的 GUI 应用打包

```python
# 项目结构
# ├── main.py
# ├── index.html          ← 界面
# └── icon.ico

import sys, os, webview

def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

def main():
    html = resource_path("index.html")          # 打包后也能找到
    webview.create_window("我的应用", html,
                          width=960, height=640, min_size=(640, 480))
    webview.start()

if __name__ == "__main__":
    main()
```

```bash
pyinstaller \
    -F -w \
    --name MyApp \
    --icon icon.ico \
    --add-data "index.html;." \
    --hidden-import webview.platforms.edgechromium \
    main.py
```

**注意**：`--add-data "index.html;."` 把 html 放到打包根目录，`resource_path("index.html")` 才能找到。

## 案例 3（综合）：**完整桌面博客应用打包**（Flask + waitress + pywebview + SQLite）

```python
# main.py —— 完整桌面应用入口
import sys
import os
import threading
from flask import Flask, render_template_string
from waitress import serve
import webview

def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

# 数据库放用户目录（打包目录可能不可写！）
import sqlite3
DATA_DIR = os.path.join(os.path.expanduser("~"), ".myapp")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "app.db")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"

# ... 路由代码 ...

def run_server():
    serve(app, host="127.0.0.1", port=8765, threads=8)

def main():
    threading.Thread(target=run_server, daemon=True).start()
    webview.create_window("博客", "http://127.0.0.1:8765/",
                          width=960, height=640, min_size=(960, 640),
                          background_color="#ffffff")
    webview.start()

if __name__ == "__main__":
    main()
```

```bash
pyinstaller \
    -F -w \
    --name BlogApp \
    --icon icon.ico \
    --hidden-import webview.platforms.edgechromium \
    --hidden-import sqlalchemy \
    main.py
```

**要点**：
- 数据库/用户数据**不要放打包目录**（只读/每次解压会丢）——放 `~/.应用名/`。
- 资源文件（模板/静态）用 `--add-data` + `resource_path`。
- 依赖库的 `--hidden-import` 按报错逐步补。

---

# 第 6 章 进阶内容（大神之路）

## 6.1 减小体积

```bash
# 排除用不到的库（明显减小体积）
--exclude-module tkinter --exclude-module unittest --exclude-module pydoc

# 用 UPX 压缩（--upx-dir 指定）
# 升级 Python 为精简安装；onedir 比 onefile 小
```

## 6.2 版本信息与图标

```python
# version_info.txt（右键属性 → 详细信息）
VSVersionInfo(
  ffi=FixedFileInfo(filevers=(1, 0, 0, 0), prodvers=(1, 0, 0, 0)),
  kids=[StringFileInfo([StringTable('040904b0', [
    StringStruct('CompanyName', '我的公司'),
    StringStruct('FileDescription', '我的应用'),
    StringStruct('FileVersion', '1.0.0.0'),
    StringStruct('ProductName', 'MyApp'),
  ])])]
)
```

```bash
pyinstaller --version-file version_info.txt main.py
```

## 6.3 多进程/多线程注意

- 子进程在 onefile 模式下会重复解压——用 `multiprocessing.freeze_support()`。
- 打包带 `multiprocessing` 的程序：`main` 里第一行加 `multiprocessing.freeze_support()`。

## 6.4 日志排查

打包后程序闪退又看不到报错时：

```bash
# 开发期先用控制台模式跑（不加 -w），看报错
pyinstaller -F main.py
dist\main.exe            # 命令行运行看输出
# 或运行时在 main 里写日志文件
logging.basicConfig(filename=os.path.join(DATA_DIR, "app.log"))
```

---

# 第 7 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 打包后找不到文件 | `FileNotFoundError` | `--add-data` 打包资源 + `sys._MEIPASS` 定位 |
| 程序闪退没提示 | 双击没反应 | 用控制台模式跑；main 里写日志文件 |
| 动态导入模块缺失 | `ModuleNotFoundError` | `--hidden-import` 补上 |
| 资源路径失效 | 图片/模板白屏 | 一律用 `resource_path()`，不要相对路径 |
| 数据丢失 | 数据库每次重来 | 数据放 `~/.应用名/`，不放打包目录 |
| 杀毒误报 | exe 被报毒 | 加白名单；用 onedir；避免可疑 UPX 混淆 |
| 体积太大 | 100MB+ | `--exclude-module` 排除；onedir；精简依赖 |
| 图标不生效 | exe 图标默认 | `--icon` 必须 .ico 格式 |
| 控制台黑窗 | GUI 应用带黑框 | `-w`（--noconsole） |
| 打包报错缺模块 | PyInstaller 分析失败 | 看报错补 hidden-import；升级 PyInstaller |
| 中文路径打包失败 | 路径含中文报错 | 项目放英文路径打包（老坑） |
| multiprocessing 卡死 | 子进程反复启动 | `multiprocessing.freeze_support()` |

---

# 第 8 章 学习路径与自测

**学习路径**：
1. 最简打包 -F（半天）
2. 参数全家桶（-w/--name/--icon）（半天）
3. 资源文件 --add-data + resource_path（1 天，重点）
4. spec 文件编辑（1 天）
5. hidden-import 排查（1 天）
6. GUI 应用打包（pywebview/Flask）（2 天，案例 3）
7. 数据目录规划（半天）
8. 体积优化 + 版本信息（1 天）
9. 日志与闪退排查（1 天）

**自测题**：
1. PyInstaller 打包产物里有什么？目标机器要装 Python 吗？
2. `-F` 和默认 onedir 的区别？正式发布推荐哪个？
3. `-w` 和 `-c` 分别什么时候用？
4. `--add-data` 干什么？Windows 和 Linux 的分隔符区别？
5. `sys._MEIPASS` 是什么？为什么要 getattr 兜底？
6. 为什么打包后相对路径失效？
7. 动态导入的模块怎么处理？
8. 数据库文件为什么不能放打包目录？放哪？
9. 程序闪退怎么看报错？（两个方法）
10. 综合：描述"桌面应用（Flask+waitress+pywebview）完整打包"的步骤。

**答案提示**：
1. 程序 + 依赖库 + Python 解释器；目标机器不用装 Python。
2. -F 单文件（方便、启动慢）；onedir 文件夹（快、小），正式发布推荐 onedir。
3. GUI 应用用 -w（无黑窗）；CLI 工具用 -c（要看到输出）。
4. 把资源文件打包进产物；Windows `;`，Linux/macOS `:`。
5. PyInstaller 注入的临时资源目录；getattr 兜底让源码运行时也正常。
6. 打包后程序在临时/内部目录运行，原相对路径指向变了。
7. `--hidden-import 模块名` 手动声明。
8. 打包目录只读/临时（onefile 每次解压会丢）；放 `~/.应用名/`。
9. ① 不加 -w 控制台运行看报错；② main 里 logging 写文件日志。
10. 参考案例 3：resource_path + 数据目录 + 三件套 + `-F -w --add-data --hidden-import` 打包。

---

> 到这里，12 个博客技术栈库（Flask/Jinja2/Werkzeug/Flask-SQLAlchemy/SQLite/python-markdown/Pygments/PyYAML/python-dateutil/waitress/pywebview/PyInstaller）+ Django 的**独立版**全部完成。加上 Playwright/Requests/BeautifulSoup4/Pandas/NumPy/Matplotlib/Selenium/Pytest/Pillow/Openpyxl/PyAutoGUI 共 24 份独立库教程，构成纯教程网站的完整内容库。
