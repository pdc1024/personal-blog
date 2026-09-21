# 第三方库全面教程 · PyInstaller

> 面向初学者到进阶者：博客 exe 怎么来的？就是它打的。
> 学完这份教程，你会掌握 PyInstaller 打包流程、spec 文件、隐藏导入、数据文件、单文件 vs 单目录、纯净版清单。
>
> 适用版本：PyInstaller 6.x ｜ 博客项目：`build.spec` + `D:\blog_pkg\dist\`

---

# 第 1 章 认识 PyInstaller

## 1.1 一句话定位

PyInstaller 把 Python 程序连同解释器、依赖打成一个 exe，用户没装 Python 也能跑：

```bash
pyinstaller --noconfirm --windowed --onefile main.py
```

一句话：**它是博客的打包工**——把代码和运行时塞进一个文件夹。

## 1.2 同类对比

| 工具 | 特点 |
|---|---|
| **PyInstaller** | 最成熟、跨平台 |
| Nuitka | 编译成 C，更快 |
| cx_Freeze | 跨平台 |
| py2exe | 老牌 |

---

# 第 2 章 打包模式

## 2.1 单文件 vs 单目录

| 模式 | 命令 | 启动 | 体积 |
|---|---|---|---|
| 单目录 | `--onedir` | 快 | 一堆文件 |
| 单文件 | `--onefile` | 慢（解压） | 一个 exe |

博客用 `--onedir`：启动快，用户接受一个文件夹。

## 2.2 窗口模式

- `--windowed` / `--noconsole`：不弹黑框；
- 不加：弹命令行。

桌面应用用 `--windowed`。

---

# 第 3 章 spec 文件

## 3.1 为什么需要 spec

命令行参数太多，写在 .spec 里可复现：

```python
# blog.spec
a = Analysis(['main.py'],
             datas=[('templates', 'templates'),
                    ('static', 'static')],
             hiddenimports=['waitress', 'webview'],
             ...)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, name='我的博客', console=False)
coll = COLLECT(exe, a.binaries, a.datas, name='博客')
```

## 3.2 datas：非代码文件

模板、静态、图标、字体必须显式带进去。

## 3.3 hiddenimports：PyInstaller 没扫到的

动态导入的库要手动列：
- `waitress`、`webview.platforms.edgechromium`、`markdown.extensions.toc`。

---

# 第 4 章 纯净版打包清单（v2.8.3）

发朋友的包必须**不含个人数据**：

| 文件 | 打包？ |
|---|---|
| 代码、templates、static | ✅ |
| `blog.db` | ❌ 删，第一次启动自动建空库 |
| `data/`、`uploads/` | ❌ 删 |
| `config.ini` 含 token | ❌ 删，第一次启动让用户填 |
| `__pycache__` | ❌ 删 |
| `.git/` | ❌ 不进包 |

## 4.1 标准流程

```powershell
# 1. 强杀旧进程
Get-Process | Where-Object {$_.Path -like "*blog*"} | Stop-Process -Force

# 2. 清旧产物
Remove-Item dist -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item build -Recurse -Force -ErrorAction SilentlyContinue

# 3. 打包
pyinstaller build.spec

# 4. 清个人数据
Remove-Item dist\博客\blog.db -ErrorAction SilentlyContinue
Remove-Item dist\博客\uploads -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item dist\博客\config.ini -ErrorAction SilentlyContinue
```

## 4.2 自检

发布前自己跑一遍：新机器、新目录、第一次启动能跑、不弹配置、能初始化。

---

# 第 5 章 高频坑

| # | 坑 | 解决 |
|---|---|---|
| 1 | 模板 404 | datas 带 templates |
| 2 | 双击闪退 | 不加 --windowed 看报错 |
| 3 | 杀软误报 | 数字签名 |
| 4 | WebView2 缺失 | 引导装 Runtime |
| 5 | 中文路径 | 绝对路径、UTF-8 |
| 6 | 改代码没重打 | 清 build 再打 |
| 7 | 把 db 打进去了 | 发布前删 |
| 8 | 端口占用 | 启动前 kill |
| 9 | 隐藏导入 | hiddenimports |
| 10 | 图标不显示 | --icon 绝对路径 |

---

# 第 6 章 自测

1. --onefile 和 --onedir 区别？
2. --windowed 做什么？
3. 为什么要用 spec？
4. 发朋友的包要删哪些文件？
5. PyInstaller 找不到动态导入的库怎么办？

**答案**：
1. 单 exe 启动慢；单目录启动快。
2. 不弹命令行。
3. 参数可复现、可版本控制。
4. blog.db、uploads、config.ini。
5. hiddenimports 手动列。

---

## 结语

到这里，05~16 十二份第三方库教程全部重写完成。它们构成了你做个人博客所需的完整技术栈：

| 编号 | 库 | 角色 |
|---|---|---|
| 05 | Flask | Web 框架 |
| 06 | Jinja2 | 模板引擎 |
| 07 | Werkzeug | WSGI 工具箱 |
| 08 | Flask-SQLAlchemy | ORM |
| 09 | SQLite | 数据库 |
| 10 | python-markdown | Markdown 渲染 |
| 11 | Pygments | 代码高亮 |
| 12 | PyYAML | 配置解析 |
| 13 | python-dateutil | 日期处理 |
| 14 | waitress | WSGI 服务器 |
| 15 | pywebview | 桌面窗口 |
| 16 | PyInstaller | 打包 |

**学习建议**：不要一口气全学完。先跑通博客，再按这 12 份逐个对照源码读，每读一份能在博客里找到它的"用武之地"，半年后你就是这个项目的专家。

祝写博客愉快。
