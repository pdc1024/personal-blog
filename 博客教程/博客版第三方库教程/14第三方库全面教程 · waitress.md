# 第三方库全面教程 · waitress

> 面向初学者到进阶者：博客双击 main.py 后，真正在 5000 端口服务的是它。
> 学完这份教程，你会掌握 WSGI 服务器对比、waitress 配置、生产部署、与 Flask 开发服务器的区别。
>
> 适用版本：waitress 3.x ｜ 博客项目：`main.py` 第 1241 行 `waitress.serve`

---

# 第 1 章 认识 waitress

## 1.1 一句话定位

waitress 是 **Python 写的生产级 WSGI 服务器**，跨平台、多线程、稳定：

```python
from waitress import serve
serve(app, host='127.0.0.1', port=5000, threads=8)
```

一句话：**它是博客的接待员**——接住浏览器请求，分发给 Flask。

## 1.2 为什么不用 Flask run

Flask 自带 `app.run()` 是开发服务器：
- 单线程、慢；
- 官方文档明确写"不要用于生产"；
- 单文件小项目没事，多人同时访问就崩。

## 1.3 WSGI 服务器对比

| 服务器 | 平台 | 性能 |
|---|---|---|
| **waitress** | Win/Mac/Linux | 稳，多线程 |
| Gunicorn | Linux/Mac | 主流 |
| uWSGI | Linux | 老牌 |
| mod_wsgi | Apache | 老 |

Windows 桌面应用选 waitress。

---

# 第 2 章 工作原理

## 2.1 启动流程

```
waitress.serve(app, ...)
  ↓ 监听 host:port
  ↓ 浏览器连来 → 建线程池
  ↓ 每个请求一个线程跑 app(environ, start_response)
  ↓ 返回响应
```

## 2.2 为什么多线程

一个请求阻塞（读文件、写库）不影响其他请求。

## 2.3 桌面打包为什么选它

main.py 内嵌 waitress，不用外部装服务，双击 exe 即用。

---

# 第 3 章 API

## 3.1 serve

```python
serve(
    app,
    host='127.0.0.1',
    port=5000,
    threads=8,
    channel_timeout=120,
)
```

## 3.2 关键参数

| 参数 | 作用 |
|---|---|
| `host` | 监听地址 |
| `port` | 端口 |
| `threads` | 线程数 |
| `channel_timeout` | 空闲超时 |
| `url_scheme='https'` | 反代 HTTPS |
| `clear_untrusted_proxy_headers` | 代理头清理 |

## 3.3 host 选择

- `127.0.0.1`：只本机访问（桌面应用默认）；
- `0.0.0.0`：所有网卡，局域网可访问。

---

# 第 4 章 项目实战

## 4.1 博客 main.py（app.py 第 2516 行）

```python
from waitress import serve
from app import app

if __name__ == '__main__':
    serve(app, host='127.0.0.1', port=5000, threads=8)
```

## 4.2 端口被占用怎么办

换端口，或找占端口的进程：

```powershell
netstat -ano | findstr :5000
taskkill /PID <pid> /F
```

---

# 第 5 章 高频坑

| # | 坑 | 解决 |
|---|---|---|
| 1 | 开发完用 app.run 上线 | 用 waitress |
| 2 | 端口被占 | 换端口 |
| 3 | 浏览器连不上 | 检查 host 是否 0.0.0.0 |
| 4 | 改代码没重启 | waitress 不会自动重载 |
| 5 | 线程数太小 | 根据并发调 |

---

# 第 6 章 自测

1. 为什么不用 Flask 自带服务器？
2. threads=8 是什么意思？
3. 想让局域网访问，host 写什么？
4. 改代码后 waitress 会自动重启吗？

**答案**：
1. 单线程、慢、官方不推荐生产。
2. 同时最多处理 8 个请求。
3. 0.0.0.0。
4. 不会，手动重启。

---

> 下一篇：pywebview —— 把网页包成桌面应用全面教程
