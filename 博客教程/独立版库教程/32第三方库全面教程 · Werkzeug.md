# 第三方库全面教程 · Werkzeug（独立版）

> 面向初学者：本教程**独立成篇**，假设你会基础 Python。术语第一次出现都有白话解释。
> 适用版本：Werkzeug 3.x ｜ 配套知识：与《Flask》配合（Flask 基于 Werkzeug 构建）。
> 学习目标：从"听过名字"到"掌握 Werkzeug 的安全工具与请求响应对象，能脱离 Flask 单独使用"。

---

# 第 1 章 这个库是什么

## 1.1 一句话认识 Werkzeug

**Werkzeug**（德语"工具"）是 Flask 的**底层工具库**——Flask 的路由匹配、请求解析、响应构造、调试器、安全函数，全部由 Werkzeug 提供。它像"发动机"，Flask 是"整车"。

```python
from werkzeug.security import generate_password_hash, check_password_hash

hashed = generate_password_hash("123456")     # 生成密码哈希
print(check_password_hash(hashed, "123456"))  # True
print(check_password_hash(hashed, "wrong"))   # False
```

## 1.2 什么时候直接用它

你**用 Flask 时已经间接在用 Werkzeug**。直接使用的常见场景：
- 密码哈希（`generate_password_hash` / `check_password_hash`）。
- 文件名安全化（`secure_filename`）。
- 独立写 WSGI 应用（不装 Flask 的轻量场景）。
- 请求/响应对象（`Request` / `Response`）。

## 1.3 它是 Flask 的地基

| Flask 功能 | 底层是 Werkzeug 的 |
|---|---|
| `@app.route` 路由 | `routing.Map` / `Rule` |
| `request` 对象 | `Request` |
| `response` | `Response` |
| 调试器 | `DebuggedApplication` |
| 密码哈希 | `security` 模块 |

---

# 第 2 章 核心概念与原理

## 2.1 WSGI：Werkzeug 服务的对象

WSGI（Web Server Gateway Interface）是 Python Web 的标准接口：一个 WSGI 应用就是一个"接收 environ 字典 + start_response 函数，返回可迭代响应体"的调用对象。Werkzeug 帮你把这一切封装成好用的类。

## 2.2 请求（Request）与响应（Response）

- **Request**：把 WSGI 传进来的原始 environ 字典解析成对象——`request.args`（URL 参数）、`request.form`（表单）、`request.files`（上传文件）、`request.headers`（请求头）、`request.json`（JSON）。
- **Response**：构造 HTTP 响应——状态码、响应头、响应体，`response.make_sequence()` 转成 WSGI 需要的格式。

## 2.3 密码为什么要哈希

密码**绝不能明文存数据库**（数据库泄露=密码泄露）。**哈希（hash）** 是单向函数：`明文 → 哈希值` 容易，`哈希值 → 明文` 极难。Werkzeug 默认用 **scrypt/pbkdf2** 加盐哈希（每个密码随机加盐），撞库也难破解。

---

# 第 3 章 安装与版本

```bash
pip install werkzeug
```

- 当前稳定版 3.x。
- **Flask 用户不用单独装**（Flask 依赖自带 Werkzeug）。
- 验证：`python -c "import werkzeug; print(werkzeug.__version__)"`。

---

# 第 4 章 API 全面讲解

> 标注：✅ = 必会；➕ = 推荐；🧪 = 进阶

## 4.1 密码哈希（✅ 最常用）

```python
from werkzeug.security import generate_password_hash, check_password_hash

# 生成哈希（自动加盐，每次结果不同是正常的！）
h1 = generate_password_hash("mypassword")
h2 = generate_password_hash("mypassword")
print(h1 != h2)          # True —— 每次哈希都不同（盐不同）

# 校验（用 check_password_hash，不要自己比较字符串）
print(check_password_hash(h1, "mypassword"))   # True
print(check_password_hash(h1, "wrong"))        # False

# 指定算法（默认 scrypt，可换 pbkdf2:sha256 等）
h3 = generate_password_hash("pw", method="pbkdf2:sha256")
```

**用法**：注册时 `hashed = generate_password_hash(密码)` 存库；登录时 `check_password_hash(库里的哈希, 用户输入的密码)`。

## 4.2 secure_filename：文件名安全化（✅ 上传必备）

```python
from werkzeug.utils import secure_filename

print(secure_filename("我的照片.jpg"))        # 中文会被处理
print(secure_filename("../../etc/passwd"))    # 危险路径被清理
print(secure_filename("a b c.png"))           # 空格变下划线
```

**为什么必须用**：用户上传的文件名可能含 `../`（路径穿越——把文件写到服务器任意目录）或危险字符。`secure_filename` 只保留安全字符。

## 4.3 Request / Response 对象（✅ 独立 WSGI 用）

```python
from werkzeug.wrappers import Request, Response

def app(environ, start_response):
    request = Request(environ)                    # 解析请求
    name = request.args.get("name", "世界")
    response = Response(f"你好，{name}！")         # 构造响应
    return response(environ, start_response)      # 返回 WSGI 响应

# 跑起来：werkzeug.serving.run_simple
from werkzeug.serving import run_simple
run_simple("127.0.0.1", 5000, app)
```

## 4.4 run_simple：开发服务器（➕）

```python
from werkzeug.serving import run_simple

run_simple(
    "127.0.0.1",        # 监听地址
    5000,               # 端口
    app,                # WSGI 应用
    use_reloader=True,  # 改代码自动重启（开发用）
    use_debugger=True,  # 调试器（开发用）
)
```

**注意**：`run_simple` 是**开发服务器**，生产要用 waitress/gunicorn（见《waitress》教程）。

## 4.5 路由系统（🧪 独立路由）

```python
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response

url_map = Map([
    Rule("/", endpoint="index"),
    Rule("/post/<int:post_id>/", endpoint="post_detail"),   # 动态段+类型
])

def dispatch(environ, start_response):
    urls = url_map.bind_to_environ(environ)   # 绑定当前请求
    try:
        endpoint, args = urls.match()         # 匹配路由
        if endpoint == "index":
            body = "首页"
        else:
            body = f"文章 {args['post_id']}"
    except Exception:
        body = "404 Not Found"
    return Response(body)(environ, start_response)
```

## 4.6 其他常用工具（➕）

```python
from werkzeug.utils import redirect, escape

# 重定向
resp = redirect("/login", code=302)

# 转义（XSS 防护，Jinja2 已默认做，这里可单独用）
print(escape('<script>alert(1)</script>'))
# → &lt;script&gt;alert(1)&lt;/script&gt;

# URL 编码
from urllib.parse import urlencode
```

## 4.7 调试器与错误处理（🧪）

```python
from werkzeug.debug import DebuggedApplication

app = DebuggedApplication(app, evalex=True)   # 生产禁用！错误页可执行代码
```

---

# 第 5 章 实战项目案例

## 案例 1（入门级）：用户注册登录（密码哈希完整示例）

```python
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

def register(username, password):
    """注册：存哈希，不存明文"""
    conn = sqlite3.connect("users.db")
    hashed = generate_password_hash(password)
    conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                 (username, hashed))
    conn.commit()
    conn.close()
    print(f"用户 {username} 注册成功")

def login(username, password):
    """登录：查库 + 校验哈希"""
    conn = sqlite3.connect("users.db")
    row = conn.execute("SELECT password_hash FROM users WHERE username=?",
                       (username,)).fetchone()
    conn.close()
    if row and check_password_hash(row[0], password):
        print(f"✅ {username} 登录成功")
        return True
    print("❌ 用户名或密码错误")
    return False

register("demo", "mypassword")
login("demo", "mypassword")     # ✅ 成功
login("demo", "wrong")          # ❌ 失败
```

## 案例 2（进阶级）：带安全文件上传的接口

```python
import os
from werkzeug.wrappers import Request, Response
from werkzeug.utils import secure_filename
from werkzeug.serving import run_simple

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED = {".png", ".jpg", ".jpeg", ".gif"}

def app(environ, start_response):
    request = Request(environ)
    if request.method == "POST" and "file" in request.files:
        f = request.files["file"]
        if f.filename:
            safe = secure_filename(f.filename)          # ① 清理文件名
            ext = os.path.splitext(safe)[1].lower()     # ② 校验扩展名
            if ext in ALLOWED:
                f.save(os.path.join(UPLOAD_DIR, safe))  # ③ 安全保存
                return Response(f"上传成功：{safe}")(environ, start_response)
            return Response("不允许的文件类型", status=400)(environ, start_response)
    html = ('<form method="post" enctype="multipart/form-data">'
            '<input type="file" name="file"><button>上传</button></form>')
    return Response(html)(environ, start_response)

run_simple("127.0.0.1", 5000, app)
```

**三层防护**：文件名清理（路径穿越）→ 扩展名白名单（防上传木马）→ 限制大小（见 Werkzeug 请求体限制）。

## 案例 3（综合）：**零 Flask 依赖的迷你 API 服务**

```python
"""Werkzeug 独立写一个 JSON API：GET 列表 / POST 新增 / GET 详情"""
import json
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.serving import run_simple

# 内存数据（演示）
DATA = [{"id": 1, "title": "第一条"}, {"id": 2, "title": "第二条"}]

url_map = Map([
    Rule("/api/posts", endpoint="posts", methods=["GET", "POST"]),
    Rule("/api/posts/<int:pid>", endpoint="post_detail"),
])

def json_resp(data, status=200):
    resp = Response(json.dumps(data, ensure_ascii=False),
                    mimetype="application/json", status=status)
    resp.headers["Access-Control-Allow-Origin"] = "*"   # 跨域
    return resp

def app(environ, start_response):
    request = Request(environ)
    urls = url_map.bind_to_environ(environ)
    try:
        endpoint, args = urls.match()
        if endpoint == "posts" and request.method == "GET":
            return json_resp(DATA)(environ, start_response)
        if endpoint == "posts" and request.method == "POST":
            data = request.get_json() or {}
            new_id = max(p["id"] for p in DATA) + 1
            DATA.append({"id": new_id, "title": data.get("title", "未命名")})
            return json_resp(DATA[-1], 201)(environ, start_response)
        if endpoint == "post_detail":
            post = next((p for p in DATA if p["id"] == args["pid"]), None)
            if post:
                return json_resp(post)(environ, start_response)
            return json_resp({"error": "not found"}, 404)(environ, start_response)
    except Exception:
        return json_resp({"error": "not found"}, 404)(environ, start_response)

run_simple("127.0.0.1", 5000, app, use_reloader=True)
```

**这个案例展示了 Werkzeug 的完整能力**：路由 Map/Rule、Request 解析 JSON、Response 构造 JSON、动态段 int 转换——**不装 Flask 也能写正经 API**。

---

# 第 6 章 进阶内容（大神之路）

## 6.1 请求体大小限制

```python
from werkzeug.wrappers import Request

Request.max_content_length = 5 * 1024 * 1024   # 全局限制 5MB
# 或单次：request.max_content_length = ...
```

## 6.2 会话与 Cookie 签名

```python
from werkzeug.wrappers import Request, Response

def app(environ, start_response):
    req = Request(environ)
    resp = Response("ok")
    resp.set_cookie("user", "demo", httponly=True, samesite="Lax")  # 安全 Cookie
    return resp(environ, start_response)
```

## 6.3 与 Flask 的关系再理解

Flask 把 Werkzeug 的 Request/Response/路由**封装成更友好的 API**（`request` 全局对象、`@app.route` 装饰器、`jsonify`）。**你写 Flask 时，底层全是 Werkzeug 在工作**。

---

# 第 7 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 密码哈希每次不一样 | 以为存错了 | 正常！盐机制；用 check_password_hash 校验 |
| 直接比较哈希字符串 | 登录永远失败 | 必须 `check_password_hash(存库哈希, 输入)` |
| 上传文件名含中文/路径 | 保存失败/乱写 | 必须 `secure_filename()` |
| run_simple 在生产用 | 性能差/有风险 | 生产用 waitress/gunicorn |
| use_debugger=True 上生产 | 可远程执行代码 | 生产永远关调试器 |
| 路由匹配失败 | 500 而不是 404 | match() 抛异常要捕获，返回 404 |
| 中文响应乱码 | JSON 中文变 \uXXXX | `json.dumps(data, ensure_ascii=False)` |
| 上传扩展名只看后缀 | 绕过限制 | 白名单 + 校验文件头（如 PNG 魔数） |

---

# 第 8 章 学习路径与自测

**学习路径**：
1. 密码哈希两个函数（半天）
2. secure_filename 与上传安全（半天）
3. Request/Response 对象（1 天）
4. run_simple 开发服务器（半天）
5. Map/Rule 路由（1 天）
6. 独立 API 服务（2 天，案例 3）
7. 安全加固（大小限制/Cookie/调试器）（1 天）

**自测题**：
1. 为什么密码不能存明文？哈希有什么特点？
2. `generate_password_hash` 每次结果不同，怎么校验？
3. `secure_filename` 解决什么问题？
4. run_simple 能不能用于生产？
5. Request 对象从哪来？它能解析哪些数据？
6. Map/Rule 是什么？和 Flask 的 @app.route 什么关系？
7. 上传文件的三层防护是什么？
8. 调试器为什么不能上生产？
9. Werkzeug 和 Flask 是什么关系？
10. 综合：用 Werkzeug 写一个带密码哈希的注册接口。

**答案提示**：
1. 明文泄露=密码泄露；哈希单向不可逆，加盐防撞库。
2. 用 `check_password_hash(存库哈希, 输入)` 校验，不要直接比较。
3. 清理文件名中的路径穿越字符（`../`）和危险字符。
4. 不能，开发服务器；生产用 waitress/gunicorn。
5. `Request(environ)` 从 WSGI environ 构造；可解析 args/form/files/headers/json。
6. Map 是路由表、Rule 是单条规则；Flask 的 @app.route 是它的封装。
7. secure_filename + 扩展名白名单 + 大小限制。
8. 错误页可执行任意代码，生产是灾难。
9. Werkzeug 是底层工具库（发动机），Flask 是基于它的框架（整车）。
10. 参考案例 1+3：POST JSON → generate_password_hash → 存库 → 返回。

---

> 下一篇：《Flask-SQLAlchemy（独立版）》——数据库 ORM 从零到精通。
