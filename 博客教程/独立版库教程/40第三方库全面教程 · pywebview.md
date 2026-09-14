# 第三方库全面教程 · pywebview（独立版）

> 面向初学者：本教程**独立成篇**，假设你会基础 Python 和 HTML/CSS/JS 一点概念。术语第一次出现都有白话解释。
> 适用版本：pywebview 5.x ｜ 配套知识：与《Flask》《waitress》配合（Web 界面 + 本地服务器 = 桌面应用）。
> 学习目标：从"不知道桌面应用怎么写"到"能用 pywebview 把网页变成 Windows/macOS 桌面应用，并掌握 JS↔Python 双向通信"。

---

# 第 1 章 这个库是什么

## 1.1 一句话认识 pywebview

**pywebview** 是 Python 的**轻量桌面界面库**：它用一个原生窗口加载网页（HTML/JS/CSS），让"网页即界面"——前端用 HTML/CSS/JS 写界面，后端用 Python 干活，两边通过 API 通信。

```python
import webview

def hello():
    return "你好，我是 Python！"

window = webview.create_window("我的应用", "https://example.com",
                                js_api=hello, width=900, height=600)
webview.start()
```

## 1.2 为什么用 pywebview 而不是 Electron/Tkinter

| 方案 | 体积 | 界面能力 | 学习成本 |
|---|---|---|---|
| Electron | 100MB+ | 最强 | 高（要 Node.js） |
| Tkinter | 小 | 简陋 | 中 |
| **pywebview** | 小 | 强（走系统浏览器内核） | 低（会 HTML 就会） |

**核心优势**：复用系统自带浏览器内核（Windows 用 EdgeChromium、macOS 用 WebKit）——**不打包浏览器，体积小**；界面用 Web 技术，好看且熟悉。

## 1.3 两种使用模式

- **加载远程/本地网页**：`webview.create_window("标题", "http://127.0.0.1:8000")`——配合本地 Flask+waitress 服务器，桌面应用的常见姿势。
- **加载本地 HTML 文件**：直接给文件路径或 HTML 字符串。

---

# 第 2 章 核心概念与原理

## 2.1 架构：前端（网页） + 后端（Python）

```
┌─────────────── pywebview 窗口 ───────────────┐
│  ┌──────────── 网页（HTML/JS/CSS）───────────┐ │
│  │  界面、交互、显示                         │ │
│  │  window.pywebview.api.xxx() ← JS 调 Python│ │
│  └───────────────────────────────────────────┘ │
│          ↑ js_api 对象（Python 方法暴露给 JS）  │
│  ┌──────────── Python（后端逻辑）──────────────┐ │
│  │  数据库、文件、网络……                     │ │
│  └───────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

## 2.2 三种通信方式

| 方式 | 方向 | 用法 |
|---|---|---|
| **js_api** | JS → Python | `window.pywebview.api.方法名(参数)` |
| **window.evaluate_js** | Python → JS | `window.evaluate_js("document.title")` |
| **事件（events）** | 双向 | 窗口关闭、加载完成等事件回调 |

## 2.3 GUI 线程与主线程

**重要**：pywebview 窗口操作（如 `evaluate_js`）必须在**主线程**（webview.start() 所在线程）执行；**Python 函数回调（js_api）运行在单独的线程**——在里面不能直接操作窗口，需要用到第 6 章的线程安全模式。

---

# 第 3 章 安装与版本

```bash
pip install pywebview
```

- 当前稳定版 5.x。
- Windows 需要已装 Edge Chromium（Win10/11 自带）；macOS 用系统 WebKit。
- 验证：

```python
import webview
print(webview.__version__)
```

---

# 第 4 章 API 全面讲解

> 标注：✅ = 必会；➕ = 推荐；🧪 = 进阶

## 4.1 create_window 参数（✅）

```python
window = webview.create_window(
    "应用标题",                 # 窗口标题
    "https://example.com",     # 加载的 URL（或本地 HTML 文件路径/字符串）
    width=960,                 # 窗口宽度（px）
    height=640,                # 窗口高度
    min_size=(640, 480),       # 最小尺寸（防止拖太小布局崩）
    resizable=True,            # 可调整大小
    fullscreen=False,          # 全屏
    frameless=False,           # 无边框（自定义标题栏用）
    easy_drag=False,           # frameless 时拖动窗口
    background_color="#ffffff",# 背景色（加载中显示）
    transparent=False,         # 透明窗口
    js_api=api_object,         # 暴露给 JS 的 Python 对象
    confirm_close=False,       # 关闭前弹确认框
)
```

## 4.2 webview.start()（✅ 必须最后调用）

```python
webview.start()                    # 进入事件循环（阻塞，直到窗口关闭）
webview.start(func, args)          # 窗口创建后立即执行 func（在主线程）
webview.start(gui="edgechromium")  # 指定 GUI 后端（Windows 默认 edgechromium）
webview.start(http_server=False)   # 不用内置服务器（自己配 waitress 时）
```

## 4.3 js_api：JS 调用 Python（✅ 核心通信）

```python
import webview

class Api:
    def greet(self, name):
        return f"你好，{name}！来自 Python 的问候"

    def add(self, a, b):
        return a + b

api = Api()
window = webview.create_window("JS↔Python 通信",
                               "https://example.com", js_api=api)
webview.start()
```

前端 JS：

```javascript
// 调用 Python 方法（异步，返回 Promise）
window.pywebview.api.greet("小明").then(function (result) {
    console.log(result);            // "你好，小明！来自 Python 的问候"
});

// 传多个参数
window.pywebview.api.add(3, 5).then(function (r) {
    console.log(r);                 // 8
});
```

**要点**：
- Python 方法必须返回**可 JSON 序列化**的值（dict/list/str/int/bool）。
- JS 侧调用是**异步**的（Promise）。
- 参数可以传字符串/数字/布尔，也能传 JSON 对象（Python 侧收 dict）。

## 4.4 evaluate_js：Python 调 JS（✅）

```python
import webview

window = webview.create_window("测试", "https://example.com")

def main_thread_work():
    """窗口加载完成后执行（主线程）"""
    result = window.evaluate_js("document.title")
    print("页面标题：", result)
    window.evaluate_js("document.body.style.backgroundColor = 'lightblue'")

webview.start(main_thread_work)
```

**⚠️**：`evaluate_js` 必须在**主线程**（`webview.start(func)` 的回调里）。

## 4.5 窗口事件（➕）

```python
import webview

def on_closing():
    print("窗口正在关闭，可以保存数据")
    return True        # 返回 False 可阻止关闭

def on_loaded():
    print("页面加载完成")

window = webview.create_window("事件", "https://example.com")
window.events.closing += on_closing
window.events.loaded += on_loaded
webview.start()
```

**常用事件**：`loaded`（加载完成）、`closing`（关闭前）、`closed`（已关闭）、`shown`（显示）、`minimized`/`restored`。

## 4.6 本地 HTML 与资源（✅ 打包应用关键）

```python
import webview
from pathlib import Path

# 方式一：HTML 文件路径
html_path = Path("index.html").resolve()
window = webview.create_window("本地应用", str(html_path))

# 方式二：HTML 字符串（简单演示）
window = webview.create_window("内嵌", """<h1>你好</h1><script>...js...</script>""")

# 方式三：内置 http 服务器托管整个目录
webview.create_window("目录", "index.html")   # 配合 http_server=True
webview.start(http_server=True)               # pywebview 内置服务器托管相对资源
```

**打包注意**：资源路径用 `sys._MEIPASS` 定位（PyInstaller 场景，见《PyInstaller》教程）。

---

# 第 5 章 实战项目案例

## 案例 1（入门级）：带 API 的计算器

```python
import webview

class CalcApi:
    def add(self, a, b):
        return a + b
    def sub(self, a, b):
        return a - b
    def mul(self, a, b):
        return a * b
    def div(self, a, b):
        return "不能除以 0" if b == 0 else a / b

HTML = """
<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>body{font-family:sans-serif;padding:40px}
input{padding:8px;margin:4px}button{padding:8px 20px}</style></head>
<body>
<h2>Python 计算器</h2>
<input id="a" type="number" value="6">
<input id="b" type="number" value="3">
<button onclick="calc('add')">+</button>
<button onclick="calc('sub')">-</button>
<button onclick="calc('mul')">×</button>
<button onclick="calc('div')">÷</button>
<p>结果：<b id="r">?</b></p>
<script>
function calc(op) {
    var a = parseFloat(document.getElementById('a').value);
    var b = parseFloat(document.getElementById('b').value);
    window.pywebview.api[op](a, b).then(function (r) {
        document.getElementById('r').textContent = r;
    });
}
</script></body></html>
"""

api = CalcApi()
webview.create_window("计算器", HTML, js_api=api,
                      width=420, height=260, min_size=(360, 220))
webview.start()
```

## 案例 2（进阶级）：Flask + waitress + pywebview 桌面应用

```python
"""Web 技术栈桌面应用：Flask 渲染页面 + waitress 服务 + pywebview 壳"""
import threading
import webview
from flask import Flask, render_template_string, jsonify
from waitress import serve

app = Flask(__name__)

PAGE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
body{font-family:sans-serif;padding:40px;background:#f5f6fa}
.card{background:white;padding:20px;border-radius:10px;max-width:400px}
button{padding:10px 24px;background:#3498db;color:white;border:none;border-radius:6px}
</style></head><body>
<div class="card"><h2>桌面数据面板</h2>
<p id="info">点击按钮从 Python 取数据</p>
<button onclick="loadData()">获取数据</button></div>
<script>
function loadData() {
    fetch('/api/data').then(r => r.json()).then(d => {
        document.getElementById('info').textContent =
            '标题：' + d.title + '，数量：' + d.count;
    });
}
</script></body></html>
"""

@app.route("/")
def index():
    return render_template_string(PAGE)

@app.route("/api/data")
def data():
    return jsonify({"title": "来自 Flask 的数据", "count": 42})

def run_server():
    serve(app, host="127.0.0.1", port=8765, threads=4)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    webview.create_window("桌面应用", "http://127.0.0.1:8765/",
                          width=960, height=640, min_size=(800, 600),
                          background_color="#f5f6fa")
    webview.start()
```

**模式**：waitress 起本地服务（后台线程）→ pywebview 窗口指向它——**前端完全走 HTTP，JS 和 Python 通过 fetch 通信**，和开发网页一样简单。

## 案例 3（综合）：**文件管理桌面应用**（js_api + 原生文件对话框 + 列表）

```python
"""桌面文件浏览器：Python 负责文件系统，JS 负责界面"""
import os
import webview

class FileApi:
    def __init__(self):
        self.current = os.path.expanduser("~")

    def list_dir(self, path=None):
        """列出目录内容"""
        if path:
            self.current = path
        try:
            items = []
            for name in sorted(os.listdir(self.current)):
                full = os.path.join(self.current, name)
                items.append({
                    "name": name,
                    "is_dir": os.path.isdir(full),
                    "size": os.path.getsize(full) if os.path.isfile(full) else 0,
                })
            return {"path": self.current, "items": items}
        except PermissionError:
            return {"path": self.current, "items": [], "error": "无权限"}

    def get_parent(self):
        """上一级目录"""
        parent = os.path.dirname(self.current)
        if parent != self.current:
            self.current = parent
        return self.list_dir()

HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
body{font-family:sans-serif;margin:0;background:#ecf0f1}
.header{background:#2c3e50;color:white;padding:12px;display:flex;gap:10px}
#list{padding:15px}
.item{padding:10px;background:white;margin:6px 0;border-radius:6px;cursor:pointer;
      display:flex;justify-content:space-between}
.item:hover{background:#dfe6e9}
.folder{color:#2980b9;font-weight:bold}
</style></head><body>
<div class="header">
  <button onclick="goUp()">⬆ 上一级</button>
  <b id="path">路径</b>
</div>
<div id="list"></div>
<script>
function load() {
    window.pywebview.api.list_dir().then(function (d) {
        document.getElementById('path').textContent = d.path;
        var html = '';
        d.items.forEach(function (it) {
            var cls = it.is_dir ? 'folder' : '';
            var size = it.is_dir ? '' : (it.size / 1024).toFixed(1) + ' KB';
            html += '<div class="item ' + cls + '" onclick="openItem(\\'' +
                    it.name.replace(/'/g, "\\\\'") + '\\')">' +
                    '<span>' + (it.is_dir ? '📁 ' : '📄 ') + it.name + '</span>' +
                    '<span>' + size + '</span></div>';
        });
        document.getElementById('list').innerHTML = html;
    });
}
function openItem(name) {
    window.pywebview.api.list_dir(
        document.getElementById('path').textContent + '/' + name
    ).then(load);
}
function goUp() {
    window.pywebview.api.get_parent().then(load);
}
load();
</script></body></html>
"""

api = FileApi()
webview.create_window("文件浏览器", HTML, js_api=api,
                      width=800, height=600, min_size=(640, 480))
webview.start()
```

**本案例展示了 js_api 的完整应用**：Python 管文件系统、JS 管界面、异步调用刷新——**桌面应用的经典双向通信模式**。

---

# 第 6 章 进阶内容（大神之路）

## 6.1 线程安全：js_api 回调里操作窗口

js_api 的方法运行在**非主线程**，不能直接 `window.evaluate_js`：

```python
import webview

class Api:
    def __init__(self, window):
        self._window = window

    def long_task(self):
        import time
        time.sleep(2)                       # 模拟耗时
        # ❌ 直接 self._window.evaluate_js 会崩（非主线程）
        # ✅ 用 pywebview 提供的线程安全执行
        def do_in_main():
            self._window.evaluate_js("document.title='完成'")
        self._window.events.loaded += on_loaded  # 或用库级工具
```

pywebview 5.x 提供 `webview.windows` 和事件机制解决；**最稳妥模式**：js_api 只返回结果，界面刷新由 JS 侧 Promise 回调完成（案例 3 就是这种）。

## 6.2 与 PyInstaller 打包（✅ 桌面应用交付关键）

```bash
pyinstaller -F -w --name MyApp \
    --add-data "index.html;." \
    --hidden-import webview.platforms.edgechromium \
    main.py
```

```python
# main.py 里定位资源（打包后资源在 _internal）
import sys, os
def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

html = resource_path("index.html")
webview.create_window("应用", html)
```

## 6.3 无边框窗口 + 自定义标题栏

```python
webview.create_window("应用", html,
    frameless=True, easy_drag=True)   # 无边框 + 拖动
# JS 里自己做最小化/关闭按钮：window.pywebview.api.close()
```

---

# 第 7 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| evaluate_js 没反应 | 无报错但没变化 | 必须在主线程（webview.start(func) 回调里） |
| js_api 调用失败 | JS 报 undefined | 确认 create_window 传了 `js_api=`；方法名大小写 |
| 返回中文乱码 | Python 返回中文显示乱 | 确保 HTML `<meta charset="UTF-8">`；返回值正常编码 |
| 窗口加载白屏 | 本地 HTML 打不开 | 用绝对路径；检查资源路径（打包用 _MEIPASS） |
| 关闭窗口进程不退出 | 后台线程还活着 | waitress 线程设 `daemon=True`；主程序正常结束 |
| 打包后找不到页面 | FileNotFoundError | `--add-data` 加资源；用 resource_path 定位 |
| 点击无反应（frameless） | 窗口拖不动 | `easy_drag=True` |
| JS 里 this 丢失 | 事件回调拿不到 pywebview | 回调用箭头函数或绑定 this |
| 多窗口操作串 | 操作错窗口 | 保存窗口引用；用 window 对象操作 |
| 中文路径打不开 | HTML 路径含中文失败 | 用 `Path.resolve()`；文件用 UTF-8 |

---

# 第 8 章 学习路径与自测

**学习路径**：
1. 第一个窗口 + 本地 HTML（半天）
2. create_window 参数（半天）
3. js_api：JS → Python（1 天，重点）
4. evaluate_js：Python → JS（1 天）
5. 窗口事件（半天）
6. Flask + waitress + pywebview 组合（2 天，重点）
7. 文件对话框/系统能力（1 天）
8. 线程安全模式（1 天）
9. PyInstaller 打包（1 天）

**自测题**：
1. pywebview 相比 Electron 的优势是什么？
2. js_api 和 evaluate_js 分别是什么方向？
3. JS 调用 Python 是同步还是异步？怎么接结果？
4. evaluate_js 为什么必须在主线程？
5. 桌面应用里 Flask 起什么作用？（两种模式）
6. 打包后资源路径怎么定位？
7. min_size 参数干什么？
8. waitress 线程为什么要 daemon=True？
9. js_api 方法返回什么类型才能给 JS？
10. 综合：描述"pywebview + Flask + waitress"三件套的协作流程。

**答案提示**：
1. 复用系统浏览器内核，体积小、跨平台、会 Web 技术就能做桌面应用。
2. js_api 是 JS→Python；evaluate_js 是 Python→JS。
3. 异步（Promise）；`.then(function(result){...})` 接结果。
4. pywebview 窗口操作受 GUI 线程限制；非主线程调用会失败/崩溃。
5. 模式一：waitress 起本地服务，窗口指向 URL；模式二：页面用 js_api 直连 Python。
6. `getattr(sys, "_MEIPASS", 源码目录)` 拼资源路径。
7. 限制窗口最小尺寸，防止拖太小布局崩溃。
8. 应用退出时后台服务器线程跟着结束，进程不残留。
9. JSON 可序列化类型（dict/list/str/int/bool/None）。
10. 参考案例 2：waitress 后台线程起服务 → create_window 指向 URL → JS fetch/js_api 与 Python 通信 → webview.start() 事件循环。

---

> 下一篇：《PyInstaller（独立版）》——打包发布从零到精通。
