# 第三方库全面教程 · PyInstaller

> 面向初学者：博客从 Python 源码变成"双击就能跑的 exe"，就是它干的。
> 学完这份教程，你能掌握打包原理、spec 文件、单文件/单目录模式、隐藏导入、数据文件、常见坑——把 Python 应用发给不懂 Python 的朋友。
> 适用版本：PyInstaller 6.x ｜ 博客项目：`build.spec` / `build.bat`

---

# 第 1 章 这个库是什么

## 1.1 一句话定位

PyInstaller 把你的 Python 应用 + Python 解释器 + 依赖库 + 静态资源**打包成一个文件夹或单个 exe**，目标机器不需要装 Python。

一句话：**PyInstaller 是博客的"封装车间"**——把代码、解释器、模板、图标全封进一个可分发的包。

## 1.2 打包后是什么

```
dist/博客/
  ├─ 博客.exe            ← 双击这个
  ├─ _internal/          ← Python 解释器 + 依赖 + 模板
  └─ blog.db             ← 用户数据（首次启动自动建）
```

## 1.3 一个最小例子

```bash
pyinstaller --noconfirm --windowed --name 博客 main.py
```

---

# 第 2 章 核心概念与原理

## 2.1 打包流程

```
分析你的 import
  ↓
收集 Python 解释器 + 依赖 .pyd/.dll
  ↓
把 .py 编译成 .pyc
  ↓
按 spec 组装目录
  ↓
可选：压缩成单文件 exe
```

## 2.2 单文件 vs 单目录

| 模式 | 命令 | 特点 |
|---|---|---|
| 单目录 | `--onedir`（默认） | 启动快、好调试 |
| 单文件 | `--onefile` | 分发方便、启动慢（要解压临时目录） |

博客用**单目录**——启动快，朋友解压即用。

## 2.3 --windowed / --noconsole

- `--windowed`：不弹黑色控制台窗口（桌面应用选它）；
- 不加：会有一个黑窗口显示 print。

## 2.4 DATA_DIR：源码目录 vs 打包目录

```python
if getattr(sys, 'frozen', False):
    DATA_DIR = os.path.dirname(sys.executable)   # 打包后：exe 所在目录
else:
    DATA_DIR = os.path.dirname(__file__)          # 源码：项目目录
```

**关键**：模板/静态是"只读资源"放 `_internal`；blog.db 是"用户数据"放 exe 旁边——升级覆盖 exe 不会丢数据。

---

# 第 3 章 安装与版本

```bash
pip install pyinstaller
pyinstaller --version
```

---

# 第 4 章 API 全面讲解

## 4.1 常用命令

```bash
pyinstaller \
  --noconfirm \
  --windowed \
  --name 博客 \
  --icon=app.ico \
  --add-data "templates;templates" \
  --add-data "static;static" \
  --hidden-import=waitress \
  main.py
```

| 参数 | 作用 |
|---|---|
| `--noconfirm` | 覆盖旧 dist |
| `--windowed` | 无控制台 |
| `--name` | 输出名 |
| `--icon` | exe 图标 |
| `--add-data "src;dst"` | 带数据文件（Windows 用分号） |
| `--hidden-import` | 显式声明动态导入 |
| `--clean` | 清缓存 |

## 4.2 spec 文件

复杂项目用 spec 文件代替命令行：

```python
a = Analysis(['main.py'],
             datas=[('templates', 'templates'),
                    ('static', 'static')],
             hiddenimports=['waitress', 'pywebview'])
pyz = PYZ(a.pure)
exe = EXE(pyz, ...)
```

`pyinstaller build.spec` 直接读 spec。

## 4.3 排除不需要的包

```bash
--exclude-module=tkinter --exclude-module=matplotlib
```

减小体积。

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客的 build.bat

```bat
pyinstaller --noconfirm --clean ^
  --windowed ^
  --name 博客 ^
  --icon=app.ico ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "config.py;." ^
  --hidden-import=waitress ^
  --hidden-import=webview ^
  main.py
```

## 5.2 纯净版打包清单（v2.8.3）

打包后发朋友前，删干净个人数据：

- `blog.db` / `blog.db-wal` / `blog.db-shm`
- `instance/` 目录（如有）
- `config.json`（同步配置）
- `uploads/`（用户上传）

保留：模板、静态、依赖。首次启动让朋友自己初始化。

## 5.3 独立示例：看启动日志排查

```bash
博客.exe --debug 2>&1 | tee start.log
```

PyInstaller 启动失败时，先看它打印哪一步找不到模块。

---

# 第 6 章 高频坑与排查

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | 模板/静态没带上 | TemplateNotFound | --add-data 声明 |
| 2 | 隐藏导入漏 | ModuleNotFoundError | --hidden-import |
| 3 | db 路径错 | 数据存临时目录 | sys.frozen 判断 |
| 4 | 图标不显示 | 默认图标 | --icon 路径对 |
| 5 | 朋友电脑缺 WebView2 | 白屏 | 装 Evergreen Runtime |
| 6 | 杀毒软件误报 | exe 被删 | 签名或换工具 |
| 7 | 单文件启动慢 | 5 秒才开 | 改 onedir |
| 8 | 数据写 exe 旁边 | 升级丢数据 | DATA_DIR 分离 |
| 9 | 路径用反斜杠 | Linux 炸 | os.path.join |
| 10 | 打包后 print 看不到 | 黑窗口没了 | 临时去 --windowed 调试 |

---

# 第 7 章 学习路径与自测

## 7.1 学习路径

- 第 1 天：第一次打包成功跑起来；
- 第 2 天：加模板/静态/图标；
- 第 3 天：理解 DATA_DIR；
- 第 4 天：spec 文件、隐藏导入；
- 第 5 天：纯净版打包清单、发给朋友验证。

## 7.2 自测题

1. `--onefile` 和 `--onedir` 区别？
2. `--windowed` 做什么？
3. 为什么要 `sys.frozen` 判断路径？
4. PyInstaller 找不到模板怎么办？
5. 发朋友前为什么要删 blog.db？
6. 怎么调试打包后的程序？
7. 为什么博客选 onedir？

## 7.3 答案

1. onefile 单 exe 启动慢；onedir 文件夹启动快。
2. 不弹黑色控制台窗口。
3. 打包后源码目录不可写（只读资源），用户数据要放 exe 旁边。
4. --add-data 声明 templates 目录。
5. blog.db 是作者的个人数据，朋友应该用自己的空库。
6. 临时去掉 --windowed，看控制台报错。
7. 启动快、调试方便、朋友解压即用。

## 7.4 进一步学习

- 官方文档：https://pyinstaller.org/
- 常见问题：https://pyinstaller.org/en/stable/where-things-are-broken.html

---

> 全系列完：这 12 份教程合起来覆盖了个人博客从前端到后端、从开发到分发的全部技术栈。
> 建议配合 `02` 技术栈总览一起看，建立全局地图后再深挖单个库。
