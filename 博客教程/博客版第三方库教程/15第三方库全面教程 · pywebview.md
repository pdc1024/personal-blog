# 第三方库全面教程 · pywebview

> 面向初学者到进阶者：博客双击 exe 弹出的窗口就是它。
> 学完这份教程，你会掌握 pywebview 的原生 WebView 桥、窗口生命周期、JS-Python 互操作、窗口大小记忆、托盘。
>
> 适用版本：pywebview 5.x ｜ 博客项目：`app.py` 第 2516 行附近 + 托盘 + 窗口大小记忆（v2.8.3 特性）

---

# 第 1 章 认识 pywebview

## 1.1 一句话定位

pywebview 用操作系统自带的 **WebView**（Windows Edge WebView2、Mac WKWebView、Linux WebKitGTK）把本地网页包成原生桌面窗口：

```python
import webview
webview.create_window('我的博客', 'http://127.0.0.1:5000/', width=1200, height=800)
webview.start()
```

一句话：**它是博客的窗框**——不内嵌 Chrome，直接用系统浏览器内核。

## 1.2 为什么选它

| 方案 | 体积 | 包 WebView？ |
|---|---|---|
| Electron | 150MB+ | 自带 |
| Tkinter + 浏览器 | 丑 | 无 |
| **pywebview** | 10MB | 系统自带 |
| QtWebEngine | 50MB | 自带 |

博客选 pywebview 是因为小、原生、跨平台。

---

# 第 2 章 工作原理

## 2.1 架构

```
pywebview（Python）
  ↓
系统 WebView（Edge WebView2）
  ↓
加载 http://127.0.0.1:5000（本地 Flask）
```

和"用 Chrome 打开 localhost"没本质区别，但：
- 无地址栏、无标签页；
- 标题是应用名；
- 可加托盘、菜单；
- 看起来像原生应用。

## 2.2 为什么要 Flask

博客逻辑在 Flask；pywebview 只负责"窗户"。启动时先 waitress 起 Flask，再 webview 打开 localhost。

---

# 第 3 章 API

## 3.1 create_window

```python
window = webview.create_window(
    title='我的博客',
    url='http://127.0.0.1:5000/',
    width=1200, height=800,
    resizable=True,
    confirm_close=False,
    on_top=False,
)
```

## 3.2 窗口大小记忆（v2.8.3 特性）

用户拖拉调整后，下次启动恢复上次大小：

```python
import json, os

def load_size():
    try:
        with open('data/window.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'width': 1200, 'height': 800}

def save_size(window):
    @window.events.closing
    def on_close():
        d = {'width': window.width, 'height': window.height}
        with open('data/window.json', 'w', encoding='utf-8') as f:
            json.dump(d, f)

state = load_size()
window = webview.create_window('我的博客', url,
                               width=state['width'],
                               height=state['height'])
save_size(window)
webview.start()
```

**关键**：每次关闭都写最新大小，不是只记第一次。

## 3.3 托盘

pywebview 不直接管托盘，Windows 用 pystray：

```python
import pystray
from PIL import Image

def tray_setup(icon):
    icon.run_detached()

menu = pystray.Menu(
    pystray.MenuItem('显示', lambda: window.show()),
    pystray.MenuItem('退出', lambda: (icon.stop(), app.quit())),
)
icon = pystray.Icon('blog', Image.open('icon.png'), '我的博客', menu)
```

## 3.4 JS ↔ Python 互操作

```python
class Api:
    def do_something(self, text):
        return f'Python 收到：{text}'

window = webview.create_window(..., js_api=Api())
```

JS 里：

```js
window.pywebview.api.do_something('你好').then(...)
```

---

# 第 4 章 项目实战

## 4.1 博客启动序列

```python
from waitress import serve
import threading, webview
from app import app

t = threading.Thread(target=serve,
                     kwargs={'app': app, 'host': '127.0.0.1',
                             'port': 5000, 'threads': 8},
                     daemon=True)
t.start()

window = webview.create_window('我的博客',
                               'http://127.0.0.1:5000/',
                               width=1200, height=800)
webview.start()
```

## 4.2 关闭行为

点 X 时托盘驻留，不退出。托盘"退出"才真正结束。

---

# 第 5 章 高频坑

| # | 坑 | 解决 |
|---|---|---|
| 1 | WebView2 没装 | 引导装 Edge WebView2 Runtime |
| 2 | Flask 没起就开窗 | 等几秒或轮询 |
| 3 | 中文标题乱码 | UTF-8 |
| 4 | 关闭后后台还在 | 托盘处理退出 |
| 5 | 窗口大小不记忆 | 监听 closing 写 JSON |
| 6 | 打包没带图标 | --add-data |

---

# 第 6 章 自测

1. pywebview 和 Electron 区别？
2. 为什么博客用 waitress + pywebview 双层？
3. 窗口大小记忆怎么做？
4. JS 怎么调 Python 方法？
5. Windows 托盘用什么库？

**答案**：
1. pywebview 用系统 WebView，体积小；Electron 自带 Chromium。
2. waitress 起 Flask；pywebview 提供原生窗框。
3. closing 事件写 JSON，下次启动读。
4. create_window 传 js_api，JS 用 window.pywebview.api。
5. pystray + PIL。

---

> 下一篇：PyInstaller —— 打包发布全面教程
