# 第三方库全面教程 · pywebview

> 面向初学者：博客双击 exe 后弹出的"原生窗口"就是它。
> 学完这份教程，你会掌握窗口创建、JS-Python 桥接、托盘、菜单、窗口大小记忆——把 Web 应用打包成桌面应用的全部要点。
> 适用版本：pywebview 5.x ｜ 博客项目：`main.py`（1241 行）

---

# 第 1 章 这个库是什么

## 1.1 一句话定位

pywebview 用**操作系统自带的 WebView 内核**（Windows 上是 Edge WebView2，macOS 上是 WKWebView）打开一个原生窗口，里面显示你的网页。

一句话：**pywebview 是博客的"窗口外壳"**——里面是 Flask 网页，外面是原生窗口。

## 1.2 为什么不用 Electron

| 对比 | Electron | pywebview |
|---|---|---|
| 内核 | 自带 Chromium | 用系统 WebView |
| 体积 | 100MB+ | 30MB 左右 |
| 内存 | 高 | 低 |
| 跨平台 | 是 | 是 |

博客选 pywebview：体积小、用系统内核、Windows 上体验和原生一致。

## 1.3 一个最小例子

```python
import webview
webview.create_window('我的博客', 'http://127.0.0.1:5000/')
webview.start()
```

---

# 第 2 章 核心概念与原理

## 2.1 架构

```
main.py
  ├─ 后台线程：waitress 跑 Flask（http://127.0.0.1:5000）
  └─ 主线程：pywebview 打开窗口，加载这个 URL
```

**关键**：Flask 跑在本地端口，pywebview 只是个"壳"。关窗口 = 退出整个程序。

## 2.2 JS-Python 桥接

pywebview 允许 JS 直接调 Python 函数：

```python
# Python 侧
class Api:
    def greet(self, name):
        return f'你好，{name}'

webview.create_window('标题', 'index.html', js_api=Api())
```

```javascript
// JS 侧
window.pywebview.api.greet('小明').then(alert)
```

## 2.3 窗口大小记忆（v2.8.3 新特性）

博客把窗口宽高、是否最大化存进 `config.json`，下次启动恢复。用户拖边调整大小后，窗口关闭时自动记录，下次打开就是最新尺寸。

---

# 第 3 章 安装与版本

```bash
pip install pywebview
pip show pywebview
```

Windows 首次运行会提示装 WebView2 Runtime（Win10/11 一般已自带）。

---

# 第 4 章 API 全面讲解

## 4.1 create_window

```python
webview.create_window(
    title='我的博客',
    url='http://127.0.0.1:5000/',
    width=1200, height=800,
    resizable=True,
    confirm_close=False,
    background_color='#ffffff',
)
```

## 4.2 start

```python
webview.start(debug=False, gui='edgechromium')
```

- `debug=True`：开 F12 开发者工具；
- `gui='edgechromium'`：强制用 WebView2。

## 4.3 窗口对象方法

```python
window = webview.create_window(...)
window.show()
window.hide()
window.load_url('...')
window.evaluate_js('alert(1)')
window.destroy()
```

## 4.4 事件

```python
window.events.closed += on_closed
window.events.closing += on_closing
window.events.shown += on_shown
```

## 4.5 托盘（博客当前未用）

```python
webview.system_tray = {
    'icon': 'icon.png',
    'menu': [('显示', show), ('退出', quit)],
}
```

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客启动（main.py）

```python
import threading, webview
from app import app, init_db

def run_server():
    from waitress import serve
    serve(app, host='127.0.0.1', port=5000, threads=8)

def main():
    init_db()
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    window = webview.create_window(
        '我的博客',
        'http://127.0.0.1:5000/',
        width=1200, height=800, resizable=True)
    webview.start()

if __name__ == '__main__':
    main()
```

## 5.2 项目内示例：窗口大小记忆（v2.8.3）

```python
import json, os

CFG = os.path.join(DATA_DIR, 'window.json')

def load_size():
    if os.path.exists(CFG):
        return json.load(open(CFG, encoding='utf-8'))
    return {'width': 1200, 'height': 800, 'maximized': False}

def save_size(window):
    data = {'width': window.width, 'height': window.height,
            'maximized': window.maximized}
    json.dump(data, open(CFG, 'w', encoding='utf-8'))
```

每次窗口关闭时保存，下次启动恢复。

---

# 第 6 章 高频坑与排查

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | Flask 没起 | 窗口白屏 | 先起 waitress 再 create_window |
| 2 | 端口被占 | 白屏 | 换端口 |
| 3 | 关窗口 Flask 还在跑 | 进程残留 | daemon=True |
| 4 | JS 调 Python 报错 | pywebview 未就绪 | DOMContentLoaded 后再调 |
| 5 | 中文乱码 | 标题乱码 | 系统编码 UTF-8 |
| 6 | WebView2 没装 | 启动失败 | 装 Evergreen Runtime |
| 7 | 打包后图标不显示 | 用默认图标 | PyInstaller --icon |
| 8 | 窗口大小不记忆 | 每次都默认 | 关闭事件里保存 |

---

# 第 7 章 学习路径与自测

## 7.1 学习路径

- 半天：create_window + start；
- 半天：JS-Python 桥接；
- 1 天：窗口事件、托盘、菜单；
- 1 天：窗口大小记忆。

## 7.2 自测题

1. pywebview 和 Flask 是什么关系？
2. 为什么 Flask 要放后台线程？
3. 怎么从 JS 调 Python 函数？
4. 关窗口后 Flask 还在跑怎么修？
5. 博客怎么记住窗口大小？
6. pywebview 用什么内核？

## 7.3 答案

1. pywebview 是外壳，Flask 是内容；pywebview 加载 Flask 的 URL。
2. 主线程必须给 webview.start()，否则窗口起不来。
3. create_window 传 js_api，JS 里 window.pywebview.api.xxx()。
4. 线程设 daemon=True，窗口关了主线程退出。
5. 关闭事件里把 width/height/maximized 存 JSON，启动时读。
6. Windows 上 Edge WebView2（系统自带）。

## 7.4 进一步学习

- 官方文档：https://pywebview.flowrl.com/

---

> 下一篇：PyInstaller —— 打包成 exe 全面教程
