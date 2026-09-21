# 第三方库全面教程 · waitress

> 面向初学者：博客打包后双击 exe 启动的 HTTP 服务器就是它。
> 学完这份教程，你会理解 Flask 为什么"自己跑不适合生产"，为什么 waitress 是 Windows 桌面应用的最佳选择。
> 适用版本：waitress 3.x ｜ 博客项目：`main.py` 第 42 行 / `app.py` 第 2516 行

---

# 第 1 章 这个库是什么

## 1.1 一句话定位

waitress 是一个**纯 Python 写的生产级 WSGI 服务器**——你的 Flask 应用是个"按请求调用的 Python 函数"，waitress 负责监听端口、接收 HTTP、调用你的函数、返回响应。

一句话：**waitress 是博客的"门卫"**——外网/本地浏览器来的请求先到它，再转给 Flask。

## 1.2 为什么不直接用 Flask 的 run

```python
app.run()   # Flask 自带服务器
```

Flask 官方反复说：**自带服务器只供开发，不要在生产用**。原因：

- 性能差（单线程、慢）；
- 官方明确说不要在生产用；
- 有安全问题。

**waitress 就是替代品**：跨平台、纯 Python、稳定、无 C 扩展（PyInstaller 打包友好）。

## 1.3 一个最小例子

```python
from waitress import serve
serve(app, host='127.0.0.1', port=5000)
```

---

# 第 2 章 核心概念与原理

## 2.1 WSGI：Python 的 HTTP 标准

```
浏览器请求
  ↓
操作系统：TCP 端口
  ↓
waitress：解析 HTTP → 调 WSGI 函数
  ↓
Flask app：路由分发 → 视图函数 → 返回 HTML
  ↓
waitress：包装成 HTTP 响应 → 返回浏览器
```

**WSGI** 是 Python 服务器和 Web 框架的"插座标准"：任何符合 WSGI 的服务器都能跑任何符合 WSGI 的框架。

## 2.2 多线程工作模型

waitress 默认开 `threads=8` 线程处理并发请求。博客同时几个访客完全够用。

## 2.3 host 绑定

- `127.0.0.1`：只本机访问（博客桌面应用选它）；
- `0.0.0.0`：局域网可访问（分享给同学用）。

---

# 第 3 章 安装与版本

```bash
pip install waitress
pip show waitress
```

---

# 第 4 章 API 全面讲解

## 4.1 serve 函数

```python
from waitress import serve

serve(
    app,
    host='127.0.0.1',
    port=5000,
    threads=8,               # 并发线程数
    url_prefix='',           # 前缀
    clear_untrusted_proxy_headers=False,
)
```

## 4.2 日志与生产调优

```python
serve(app,
      host='127.0.0.1',
      port=5000,
      threads=16,
      channel_timeout=120)
```

## 4.3 命令行模式

```bash
waitress-serve --host=127.0.0.1 --port=5000 app:app
```

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客启动入口（app.py 第 2516 行）

```python
if __name__ == '__main__':
    init_db()
    print('博客已启动：http://127.0.0.1:5000/')
    serve(app, host='127.0.0.1', port=5000, threads=8)
```

桌面应用在 `main.py` 里开线程起 waitress，主线程给 pywebview 用。

## 5.2 独立示例：带优雅退出

```python
import signal
from waitress import serve

serve(app, host='127.0.0.1', port=5000)
# 按 Ctrl+C 后 waitress 自动结束
```

---

# 第 6 章 高频坑与排查

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | app.run 当生产 | 官方警告 | 改 waitress serve |
| 2 | 端口被占 | 启动失败 | 改 port 或杀占用进程 |
| 3 | 外网访问不了 | 只本机通 | host 改 0.0.0.0 |
| 4 | 多线程 SQLite 报错 | thread 错 | check_same_thread=False |
| 5 | 打包后 waitress 找不到 | exe 报错 | hidden-import 声明 |

---

# 第 7 章 学习路径与自测

## 7.1 学习路径

- 半天：从 app.run 切到 serve；
- 半天：理解 WSGI；
- 1 天：调并发、日志、生产部署。

## 7.2 自测题

1. 为什么生产不用 `app.run()`？
2. waitress 和 Flask 是什么关系？
3. host='127.0.0.1' 和 '0.0.0.0' 区别？
4. threads=8 是什么意思？
5. 博客为什么把 waitress 放后台线程？

## 7.3 答案

1. 自带服务器单线程、官方明确不建议生产用。
2. waitress 是 WSGI 服务器，Flask 是 WSGI 应用；waitress 调 Flask。
3. 前者只本机；后者局域网可访问。
4. 同时处理 8 个请求的线程数。
5. 主线程要留给 pywebview 显示窗口。

## 7.4 进一步学习

- 官方文档：https://docs.pylonsproject.org/projects/waitress/

---

> 下一篇：pywebview —— 桌面窗口容器全面教程
