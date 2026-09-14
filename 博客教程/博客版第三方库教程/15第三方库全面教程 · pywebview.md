# 第三方库全面教程 · pywebview

> 面向初学者：博客桌面版的那个"像浏览器的窗口"，就是 pywebview 开的。学完这份教程，你会掌握桌面窗口的完整生命周期、JS 与 Python 双向通信，以及各种窗口参数——不只会 `create_window` + `start`。
> 适用版本：pywebview 5.x ｜ 博客项目：`main.py`（窗口、居中、托盘配合）

---

# 第 1 章 这个库是什么

pywebview 是一个"**用网页做桌面界面**"的库：它创建一个原生操作系统窗口，窗口里塞一个真正的浏览器内核（Windows 上是 Edge WebView2），让你**用 HTML/CSS/JS 写界面，用 Python 写逻辑**。

一句话：**pywebview 是博客的"桌面门面"**——你看到的博客窗口不是浏览器标签页，而是一个原生 Windows 窗口，里面跑着 Flask 提供的网页。

**和 Electron 的关系**：Electron（VS Code 那类应用）也是"网页套壳"，但捆绑一个完整 Chromium（几百 MB）；pywebview 用系统自带的 WebView 内核（几十 MB 都不到）。博客选它就是为了"绿色版体积小"。

---

# 第 2 章 核心概念与原理

## 2.1 生命周期：从创建到退出

```
create_window()          ← 创建窗口对象（此时还没显示）
  ↓
webview.start()          ← 进入事件循环（阻塞！）窗口出现
  ↓
用户操作（点按钮/关窗口）
  ↓
window.events.closing    ← "即将关闭"事件（可拦截：博客用它转托盘）
window.events.closed     ← "已关闭"事件（做清理）
  ↓
start() 返回 → 程序继续/退出
```

**核心认知**：`webview.start()` 是**阻塞**的——它像 Flask 的 `app.run()` 一样接管主线程，直到所有窗口关闭才返回。所以**托盘、后台线程都要在 start() 之前启动**。

## 2.2 GUI 后端：Windows 上默认用谁

pywebview 在不同系统选不同"后端"：

| 平台 | 默认后端 | 说明 |
|---|---|---|
| Windows | `edgechromium`（WebView2） | 微软新内核，支持好（博客指定这个） |
| macOS | Cocoa/WebKit | 系统自带 |
| Linux | GTK/Qt/WebKit | 需要装库 |

**WebView2 Runtime** 是微软的组件，Windows 10/11 一般自带；老系统没有会导致**白屏**（博客踩过这个坑，报错时弹下载链接）。

## 2.3 JS ↔ Python 双向通信（pywebview 的灵魂）

pywebview 不只是"显示网页"，还能让网页里的 JS 直接调用 Python 函数、让 Python 直接执行 JS：

```python
class Api:
    def get_data(self):
        return {'site': '我的博客'}      # JS 可调用的 Python 方法

webview.create_window('博客', url='http://...', js_api=Api())
```

```javascript
// 网页里的 JS：
const data = await window.pywebview.api.get_data();
// data = {site: '我的博客'}
```

**重要**：`js_api` 方法默认**同步阻塞**在主线程，慢操作会卡界面——耗时逻辑要自己开线程。这是做"桌面功能"（比如读取本地文件）的基础。

---

# 第 3 章 安装与版本

```bash
pip install pywebview
pip show pywebview   # 版本验证
```

pywebview 5.x 要求 Python 3.7+，Windows 上需要 WebView2 Runtime。

---

# 第 4 章 API 全面讲解

## 4.1 create_window：全部常用参数（✅ 博客用了大半）

```python
window = webview.create_window(
    title='个人博客',                    # 窗口标题
    url='http://127.0.0.1:18520/',      # 要显示的网址（或本地 HTML 文件）
    width=1280, height=820,             # 窗口尺寸（像素）
    x=100, y=100,                       # 窗口位置（博客用它实现居中）
    min_size=(960, 640),                # 最小尺寸（防拖太小界面崩）
    resizable=True,                     # 可拖拽调整大小
    fullscreen=False,                   # 全屏
    background_color='#ffffff',         # 加载时底色（博客实际用白色）
    confirm_close=False,                # 关闭前弹确认框
    js_api=api_obj,                     # JS↔Python 桥接对象
    on_top=False,                       # 置顶
)
```

| 参数 | 作用 | 博客 |
|---|---|---|
| `width/height/x/y` | 尺寸与位置 | ✅ 居中靠 x/y |
| `min_size` | 最小尺寸 | ✅ |
| `background_color` | 加载底色 | ✅ 深色防闪白 |
| `js_api` | 桥接对象 | ➕ 未用（博客纯展示） |
| `confirm_close` | 关窗确认 | ➕ 未用（托盘逻辑替代） |
| `on_top` | 置顶 | 🧪 |

## 4.2 start：进入事件循环

```python
webview.start(
    gui='edgechromium',     # 指定后端（Windows 推荐）
    debug=False,            # True 会开开发者工具（生产别开）
    http_server=False,      # 关键！不用 pywebview 自带服务器（博客已有 Flask）
    func=[],                # 启动后要执行的函数列表（代替 threading）
)
```

**`http_server=False` 为什么关键？** pywebview 自带一个简易 HTTP 服务器。博客已经有 Flask/waitress 在提供页面，如果开着会端口冲突或双服务。**加载外部网址时务必 False。**

## 4.3 窗口对象方法（✅ 托盘交互的核心）

```python
window.show()        # 显示/恢复窗口
window.hide()        # 隐藏窗口（托盘"最小化"用它，程序还在跑）
window.destroy()     # 销毁窗口（真正关闭）
window.restore()     # 从最小化恢复
window.minimize()    # 最小化到任务栏
window.maximize()    # 最大化
window.evaluate_js('document.title')   # 在页面里执行 JS 并拿结果
window.load_url('http://...')          # 跳转到别的网址
window.set_title('新标题')             # 改标题
```

**博客托盘逻辑**：点 X → `on_closing` 里 `window.hide()` + 返回 False（阻止关闭）→ 托盘图标还在 → 点图标 `window.show()` 回来 → 托盘"退出"才真正 `destroy()`。

## 4.4 事件（window.events）

```python
window.events.loaded += on_loaded      # 页面加载完成
window.events.closing += on_closing    # 即将关闭（可返回 False 拦截！）
window.events.closed += on_closed      # 已关闭（清理收尾）
window.events.shown += on_shown        # 窗口显示
window.events.hidden += on_hidden      # 窗口隐藏
```

**closing vs closed 区别**：closing 是"还有机会说不"，closed 是"已经没了"。

## 4.5 js_api：JS 调 Python（➕ 强烈推荐掌握）

```python
class Api:
    def __init__(self):
        self._counter = 0
    def ping(self):
        return 'pong'
    def read_local_file(self, path):
        try:
            with open(path, encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f'error: {e}'

api = Api()
window = webview.create_window('Demo', 'http://127.0.0.1:5000/', js_api=api)
webview.start(http_server=False)
```

```javascript
// 页面里：
document.getElementById('btn').onclick = async () => {
  const text = await window.pywebview.api.read_local_file('C:/test.txt');
  console.log(text);
};
```

**安全注意**：暴露给 JS 的方法**不要**直接接收文件路径/系统命令这类高危参数（网页被 XSS 就等于 Python 被控制）；要白名单校验。

## 4.6 多窗口与对话框（🧪 了解）

```python
w2 = webview.create_window('第二个窗口', 'http://...')
# 全关才退出：start() 在所有窗口关闭后返回

from webview import windows   # 管理所有窗口
webview.windows[0].show()
```

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客的窗口创建（浓缩版）

```python
def _build_create_window_kwargs(title, url):
    """构造 create_window 参数：兼容不同 pywebview 版本 + 窗口居中"""
    kwargs = dict(
        title=title, url=url,
        width=1280, height=820,
        min_size=(960, 640),
        background_color='#ffffff',
    )
    pos = _compute_centered_position(1280, 820)   # v2.1 窗口居中
    if pos:
        kwargs['x'], kwargs['y'] = pos
    return kwargs, icon_path

# main() 里：
cw_kwargs, icon = _build_create_window_kwargs('个人博客', base_url + '/')
window = webview.create_window(**cw_kwargs)
window.events.closed += on_closed
window.events.closing += on_closing
_start_tray(window)              # 托盘在 start() 之前！
webview.start(gui='edgechromium', debug=False, http_server=False, func=[])
```

## 5.2 独立示例：10 行做一个"打开本地文件"桌面工具

```python
import webview, os

class FileApi:
    def list_dir(self, path='.'):
        return os.listdir(path)          # 页面按钮点击后调用

api = FileApi()
webview.create_window('文件浏览器', html='''
  <button onclick="show()">列目录</button>
  <ul id="out"></ul>
  <script>
    async function show(){
      const items = await window.pywebview.api.list_dir('.');
      document.getElementById('out').innerHTML =
        items.map(i => '<li>' + i + '</li>').join('');
    }
  </script>
''', js_api=api, width=500, height=400)
webview.start()
```

（`html=` 参数直接传 HTML 字符串，适合无服务器的纯本地工具。）

---

# 第 6 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 白屏 | 窗口开了全白 | WebView2 缺失 / 服务没起 / 端口拼错；报错弹下载链接 |
| start() 后代码不执行 | 托盘等没生效 | 托盘/线程必须在 start() 之前启动 |
| 退出不干净 | 进程残留、端口占用 | 完整链路：hide→destroy→start 返回→server.close()→释放互斥锁 |
| 端口冲突 | 页面加载失败 | `http_server=False`（Flask 已在跑） |
| 位置不对 | 窗口跑到屏幕外 | x/y 用 DIP（逻辑像素），别直接用物理像素（见居中教程） |
| 点 X 程序直接退了 | 没有托盘驻留 | on_closing 里 hide() + return False 拦截 |

---

# 第 7 章 学习路径与自测

**学习路径**：先 create_window + start 跑通（半天）→ 学窗口方法/事件（半天）→ 托盘联动（1 天，博客核心交互）→ js_api 双向通信（1 天，做桌面功能必学）。

**自测题**：

1. `webview.start()` 之后能再开窗口吗？为什么？
2. `closing` 和 `closed` 事件的区别？托盘"点 X 不退出"靠哪个？
3. `http_server=False` 是什么意思？什么时候必须设？
4. 网页里的 JS 怎么调用 Python 函数？
5. Windows 上白屏最常见的原因？

**答案**：
1. 不能，start 阻塞直到所有窗口关闭；窗口要在 start 前创建。
2. closing 可拦截（返回 False 阻止关闭，托盘最小化靠它）；closed 是已关闭后的清理。
3. 不用 pywebview 自带 HTTP 服务器；加载外部网址/已有 Flask 时设 False 防冲突。
4. 创建窗口时传 `js_api=对象`，页面里 `await window.pywebview.api.方法名()`。
5. WebView2 Runtime 缺失（或服务没起/端口错）。

---

> 下一篇：PyInstaller —— 打包全面教程
