# 第三方库全面教程 · waitress

> 面向初学者：博客"生产模式"下真正接待访客的服务器就是 waitress。学完这份教程，你会理解 WSGI 服务器的原理、阻塞与非阻塞的区别，以及它和 Flask 内置服务器的本质差异。
> 适用版本：waitress 3.x ｜ 博客项目：`app.py` 的 `run_server` + `main.py` 的桌面版后台线程

---

# 第 1 章 这个库是什么

waitress 是一个**纯 Python 写的生产级 WSGI 服务器**。拆开说：

- **WSGI 服务器**：负责"监听端口 → 接收浏览器 HTTP 请求 → 交给 Flask 应用处理 → 把响应发回去"的守门员
- **生产级**：稳定、多线程、可以同时服务很多访客，不会因为一个请求卡住就全站瘫痪
- **纯 Python**：不依赖 C 扩展，Windows/Linux 都能装能跑

一句话：**waitress 是博客的"正式前台"**。Flask 自带的小服务器是"开发练习场"，正式运行（尤其给别人访问）用 waitress。

---

# 第 2 章 核心概念与原理

## 2.1 Flask 自带服务器 vs waitress

| 对比 | Flask 内置（app.run） | waitress |
|---|---|---|
| 用途 | 开发调试 | 生产部署 |
| 并发 | 单进程（threaded=True 才多线程） | 多线程池（默认 4 线程） |
| 稳定性 | 弱，慢请求会拖垮 | 强，一个请求慢不影响别人 |
| 调试器 | 有（debug 模式） | 无（好事——生产不该有） |
| 性能 | 差 | 好 |

**为什么生产不用 app.run？** Flask 官方明说内置服务器不适合生产：它线程处理方式简单，遇到慢请求（比如某个图片加载 30 秒）会占着线程不撒手，来几个慢请求整个服务就堵死了。waitress 有线程池、超时管理、连接控制，是给"真客人"用的。

## 2.2 阻塞 vs 非阻塞：桌面版为什么必须用线程

waitress 有两种启动方式，**区别巨大**：

```python
# 方式一：serve() —— 阻塞
waitress.serve(app, host='127.0.0.1', port=18520)
# 调用后当前线程就"卡"在这里，下面的代码永远不执行
print('这行永远不会打印')   # ❌

# 方式二：create_server() —— 非阻塞
server = waitress.server.create_server(app, host='127.0.0.1', port=18520)
thread = threading.Thread(target=server.run, daemon=True)  # 放后台线程跑
thread.start()
print('这行会打印')        # ✅ 主线程继续干别的（比如开窗口）
```

**博客桌面版为什么用方式二？** main.py 要先启动服务器，然后继续去创建窗口、挂托盘——如果 serve() 阻塞，窗口就永远开不出来。

## 2.3 WSGI 一次握手

```
waitress 监听 18520 端口
  ↓ 浏览器发来 GET /post/3/
waitress 把请求包装成 WSGI 环境（environ 字典）
  ↓ 调用 app(environ, start_response)
Flask 处理完返回响应
  ↓ waitress 把响应发回浏览器
```

---

# 第 3 章 安装与版本

```bash
pip install waitress
pip show waitress   # 版本验证
```

waitress 3.x 要求 Python 3.8+。项目里 waitress 是"软依赖"——装不上就回退 Flask 内置服务器（博客做了 ImportError 兜底）。

---

# 第 4 章 API 全面讲解

## 4.1 waitress.serve：最简启动（✅ 网页版用）

```python
from waitress import serve

serve(app, host='0.0.0.0', port=18520, threads=8)
# host：'0.0.0.0' 允许局域网访问；'127.0.0.1' 仅本机
# threads：工作线程数（默认 4）
```

**阻塞式**：放在脚本最后一行，进程一直跑。

## 4.2 waitress.server.create_server：非阻塞启动（✅ 桌面版用）

```python
from waitress.server import create_server

server = create_server(app, host='127.0.0.1', port=18520, threads=4)
server.run()                # 阻塞跑（放后台线程里）
server.close()              # 优雅关闭：停监听、等现有请求处理完
```

**博客 main.py 的完整模式**：

```python
import threading
import waitress.server

def _start_blog_server(port):
    global _waitress_server
    _waitress_server = waitress.server.create_server(
        app, host='127.0.0.1', port=port,
        threads=8,            # 8 个工作线程
        channel_timeout=60,   # 连接空闲 60 秒断开
        connection_limit=32,  # 最多 32 个并发连接
    )
    threading.Thread(target=_waitress_server.run, daemon=True).start()

def _stop_blog_server():
    if _waitress_server is not None:
        _waitress_server.close()     # 优雅关闭，不留孤儿进程
```

## 4.3 常用配置参数

| 参数 | 默认 | 作用 |
|---|---|---|
| `threads` | 4 | 工作线程数（博客 8） |
| `host` | `0.0.0.0` | 监听地址 |
| `port` | 8080 | 端口 |
| `url_scheme` | `http` | 反向代理走 https 时设 `https` |
| `trusted_proxy` | 无 | 信任的代理 IP（配合获取真实客户端 IP） |
| `channel_timeout` | 120 | 连接空闲超时（秒） |
| `connection_limit` | 100 | 最大并发连接数 |
| `log_socket_errors` | True | 是否记录连接错误日志 |
| `ident` | `waitress` | 响应头 Server 值 |

**博客的端口策略**：默认 18520，被占用时自动往后找空闲端口（`_try_find_port`）。

## 4.4 反向代理（nginx 后面）时的关键配置（🧪 进阶）

如果将来把博客部署到服务器并用 nginx 反代，需要两件事：

```python
serve(app, host='127.0.0.1', port=18520, url_scheme='https',
      trusted_proxy='127.0.0.1', trusted_proxy_headers={'x-forwarded-for': 0})
```

否则 Flask 里 `request.remote_addr` 拿到的是 nginx 的 IP，且 `url_for` 生成 http 链接（页面上 https 资源会报错）。

---

# 第 5 章 实战示例

## 5.1 项目内示例：网页版 run_server（app.py 末尾）

```python
def run_server(port=18520, host='127.0.0.1'):
    """启动 waitress 生产服务器；未安装则回退 Flask 内置"""
    try:
        from waitress import serve
    except ImportError:
        print('未安装 waitress，回退 Flask 内置服务器（仅适合开发）')
        app.run(host=host, port=port, threaded=True, debug=False)
        return
    print(f'博客已启动：http://{host}:{port}')
    serve(app, host=host, port=port, threads=8)
```

## 5.2 独立示例：一个"秒回"的并发压测对比

```python
# server_demo.py —— 演示阻塞与线程池的区别
from flask import Flask, time
import threading, time as t
from waitress.server import create_server

app = Flask(__name__)

@app.route('/slow')
def slow():
    t.sleep(3)          # 模拟慢请求
    return 'done'

# 开 3 个请求打 /slow，看 waitress 线程池能同时处理几个
server = create_server(app, host='127.0.0.1', port=5001, threads=3)
threading.Thread(target=server.run, daemon=True).start()

def hit(i):
    import urllib.request
    s = t.time()
    urllib.request.urlopen('http://127.0.0.1:5001/slow', timeout=10)
    print(f'请求 {i} 耗时 {t.time()-s:.1f}s')

threads = [threading.Thread(target=hit, args=(i,)) for i in range(3)]
for th in threads: th.start()
for th in threads: th.join()
# threads=3 时三个并发请求都能 3 秒左右完成（不排队）
```

---

# 第 6 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| serve() 后面的代码不执行 | 打印永远不出现 | serve 是阻塞的；要并行用 create_server + 线程 |
| 端口被占用 | `address already in use` | `netstat -ano \| findstr 18520` 查 PID 杀掉，或换端口 |
| 局域网访问不了 | 别人打不开 | host 用 `0.0.0.0` 并放行防火墙 |
| 想热重载 | 改了代码不生效 | waitress 没有调试器；开发用 `FLASK_DEBUG=1` |
| 反代后 IP 全一样 | 拿不到真实客户端 IP | trusted_proxy + x-forwarded-for 配置 |
| 退出后端口还占着 | 再启动报端口占用 | 确认进程真的退出（server.close() + 线程结束） |

---

# 第 7 章 学习路径与自测

**学习路径**：先会用 serve() 跑起来（半天）→ 理解阻塞/非阻塞（半天，桌面版必懂）→ 学配置参数（半天）→ 反向代理场景（1 天，部署时再看）。

**自测题**：

1. 为什么生产环境不用 Flask 内置服务器？
2. `serve(app)` 和 `create_server(app)` + 线程的区别？
3. 局域网让别人访问，host 该填什么？
4. 端口被占用怎么排查？
5. 桌面版为什么要用 create_server 而不是 serve？

**答案**：
1. 内置服务器线程处理简单、易被慢请求拖垮、有调试器泄漏风险。
2. serve 阻塞当前线程直到退出；create_server 返回 server 对象可放后台线程跑，主线程继续干活。
3. `0.0.0.0`（监听所有网卡）。
4. `netstat -ano | findstr 18520`，找到 PID 结束进程或换端口。
5. main.py 还要继续开窗口/挂托盘，serve 会卡住主线程。

---

> 下一篇：pywebview —— 桌面窗口全面教程
