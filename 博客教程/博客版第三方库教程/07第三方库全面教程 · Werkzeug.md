# 第三方库全面教程 · Werkzeug

> 面向初学者到进阶者：Flask 本身是个薄壳，真正干活的路由、请求、响应、密码哈希、安全工具都在 Werkzeug。
> 学完这份教程，你会掌握 Werkzeug 的核心 API：secure_filename、密码哈希、LocalProxy、MultiDict、路由 Map、
> 请求/响应对象、Cookie 处理、代理头修正，并能理解 Flask 为什么长这样。
>
> 适用版本：Werkzeug 3.x ｜ 博客项目：`app.py` 的上传安全、密码哈希、请求指纹
> 学习路线：认识 Werkzeug（第 1 章）→ WSGI 与路由（第 2~3 章）→ 安全工具（第 4 章）→ 请求/响应与 Cookie（第 5 章）→ 项目实战（第 6 章）→ API 与排坑（第 7~8 章）

---

# 第 1 章 认识 Werkzeug

## 1.1 一句话定位

Werkzeug（德语"工具"）是 Flask 背后的 **WSGI 工具库**。Flask 自己只做了路由装饰器、模板集成、session 这些"胶水"，底层所有硬活都是 Werkzeug 干的：

- 把 URL 字符串匹配到视图函数（路由 Map/Rule）；
- 解析 HTTP 请求头、body、文件上传（Request）；
- 构造 HTTP 响应、Set-Cookie、状态码（Response）；
- 密码哈希（generate_password_hash / check_password_hash）；
- 文件名消毒（secure_filename）；
- 线程局部代理（Local / LocalProxy）——Flask 的 request、g 全靠它。

一句话：**Werkzeug 是 Flask 的发动机**。Flask 是方向盘，Werkzeug 是底盘引擎。

## 1.2 为什么单独学 Werkzeug

- 理解 Flask 的 API 为什么长这样（比如 `request.args` 是 ImmutableMultiDict）；
- 知道 Flask 没包装的工具怎么直接用（密码哈希、文件名安全）；
- 脱离 Flask 写纯 WSGI 应用时，Werkzeug 是最好的工具箱。

## 1.3 最小 WSGI 应用（用 Werkzeug）

```python
from werkzeug.wrappers import Request, Response

@Request.application
def application(request):
    return Response(f'你好，{request.remote_addr}')

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('127.0.0.1', 5000, application)
```

没有 Flask，没有路由装饰器，一个 URL 一个函数。这就是 Flask 的内核。

---

# 第 2 章 WSGI 与请求-响应

## 2.1 WSGI 回顾

Werkzeug 是 WSGI 工具集。它提供：
- `Request`：包装 environ，提供 `.args`、`.form`、`.headers` 等友好属性；
- `Response`：提供 `__call__(environ, start_response)`，本身就是 WSGI 应用；
- `run_simple`：开发用的 WSGI 服务器（就是 Flask `app.run()` 用的）。

## 2.2 Request 对象

```python
@Request.application
def app(request):
    request.method          # 'GET'/'POST'
    request.path            # '/hello'
    request.args            # 查询参数（MultiDict）
    request.form            # 表单
    request.files           # 上传文件
    request.headers         # 请求头
    request.cookies         # Cookie 字典
    request.remote_addr     # 客户端 IP
    request.user_agent      # User-Agent
    request.content_type
    return Response('ok')
```

Flask 的 `request` 就是 Werkzeug Request 的代理。

## 2.3 Response 对象

```python
from werkzeug.wrappers import Response

resp = Response('你好', status=200, content_type='text/html; charset=utf-8')
resp.headers['X-App'] = 'blog'
resp.set_cookie('token', 'abc', max_age=3600)
```

Flask 的 `jsonify`、`make_response` 都是 Response 的薄封装。

---

# 第 3 章 路由系统：Map / Rule

## 3.1 为什么需要路由

URL `/post/3/` 要对应到函数 `post_detail(3)`。Werkzeug 用 `Map` 维护所有规则，`Rule` 表示一条规则。

```python
from werkzeug.routing import Map, Rule, RuleFactory

url_map = Map([
    Rule('/', endpoint='index'),
    Rule('/post/<int:post_id>/', endpoint='post_detail'),
    Rule('/about/', endpoint='about'),
])

adapter = url_map.bind('127.0.0.1')
endpoint, values = adapter.match('/post/3/')
# endpoint='post_detail', values={'post_id': 3}
```

Flask 的 `@app.route` 就是往这个 Map 里加 Rule。

## 3.2 URL 转换器

| 转换器 | 匹配 |
|---|---|
| `string`（默认） | 任意非斜杠字符 |
| `int` | 正整数 |
| `float` | 浮点数 |
| `path` | 含斜杠的路径 |
| `uuid` | UUID 字符串 |

自定义转换器：

```python
from werkzeug.routing import BaseConverter

class RegexConverter(BaseConverter):
    def __init__(self, url_map, regex):
        super().__init__(url_map)
        self.regex = regex

url_map.converters['regex'] = RegexConverter
```

## 3.3 build：反向生成 URL

```python
adapter.build('post_detail', {'post_id': 3})
# '/post/3/'
```

Flask 的 `url_for` 就是它。

---

# 第 4 章 安全工具（博客重点）

## 4.1 secure_filename：文件名消毒

用户上传文件时，文件名可能是 `../../etc/passwd` 或 `run.py;rm -rf`。`secure_filename` 把它变成安全的：

```python
from werkzeug.utils import secure_filename

secure_filename('../../etc/passwd')     # 'etc_passwd'
secure_filename('我的照片.png')           # 'png'（非 ASCII 会被剥掉！）
secure_filename('photo (1).jpg')         # 'photo_1.jpg'
```

**博客用法**（app.py 第 722 行附近）：

```python
def allowed_avatar(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

f = request.files['avatar']
if f and allowed_avatar(f.filename):
    filename = secure_filename(f.filename)
    # 中文文件名会被剥光！要自己处理
    if not filename or '.' not in filename:
        filename = f'avatar_{int(time.time())}.png'
    f.save(os.path.join(app.config['UPLOAD_DIR'], filename))
```

**中文文件名坑**：`secure_filename` 会剥掉非 ASCII 字符，`我的头像.png` 变成 `png`。博客的处理是：消毒后如果没扩展名，自己拼一个时间戳文件名。

## 4.2 密码哈希

**永远不要明文存密码**。Werkzeug 提供：

```python
from werkzeug.security import generate_password_hash, check_password_hash

# 注册时
hash = generate_password_hash('用户输入的密码', method='pbkdf2:sha256')
# 存数据库

# 登录时
if check_password_hash(stored_hash, '用户输入的密码'):
    # 登录成功
```

**为什么不能自己写哈希？**
- 自己 `hashlib.md5(password)`：彩虹表一秒破解；
- Werkzeug 用 pbkdf2:sha256 + 随机 salt + 慢哈希（故意算得慢，防暴力破解）；
- `check_password_hash` 自动处理时间安全比较（防时序攻击）。

**不要自定义 method**，用默认即可。新 Werkzeug 默认 `scrypt` 或 `pbkdf2:sha256`。

## 4.3 其他安全工具

```python
from werkzeug.security import safe_str_cmp

# 时间安全字符串比较（防时序攻击）
safe_str_cmp(a, b)
```

---

# 第 5 章 MultiDict 与 LocalProxy

## 5.1 MultiDict：一键多值

普通字典一键一值。MultiDict 一键多值：

```python
from werkzeug.datastructures import MultiDict

md = MultiDict([('tag', 'python'), ('tag', 'flask'), ('sort', 'new')])

md.get('tag')          # 'python'（第一个）
md.getlist('tag')      # ['python', 'flask']
md['sort']             # 'new'
```

**为什么需要它？** HTML 表单复选框同名多值：

```html
<input type="checkbox" name="tag" value="python">
<input type="checkbox" name="tag" value="flask">
```

提交后 `request.form.getlist('tag')` 拿到 `['python', 'flask']`。如果用普通字典，第二个会覆盖第一个。

## 5.2 ImmutableMultiDict

Flask 的 `request.args`、`request.form` 是不可变的——防止视图里意外修改请求数据。需要可改版本用 `MultiDict(request.form)` 复制一份。

## 5.3 Local / LocalProxy：线程局部

这是 Flask `request`、`g`、`current_app` 的底层。

```python
from werkzeug.local import Local, LocalProxy

_requests = Local()          # 线程/协程隔离的存储
_requests.request = '...'

request = LocalProxy(lambda: _requests.request)
# 你访问 request.method 时，Proxy 转发到当前线程的 request
```

**关键**：不同线程看到不同的"当前请求"，互不干扰。这就是为什么多线程 WSGI 服务器下 Flask 不会串请求。

---

# 第 6 章 项目实战

## 6.1 访客指纹：IP + UA 哈希

博客用 IP + User-Agent 生成访客指纹（app.py 第 691 行）：

```python
import hashlib
from flask import request, g

@app.before_request
def attach_fingerprint():
    raw = (request.remote_addr or '') + '|' + (request.user_agent.string or '')
    g.fingerprint = hashlib.sha256(raw.encode('utf-8')).hexdigest()
```

点赞时按指纹去重：同浏览器不能重复点。

**隐私说明**：这不是真匿名（IP 能定位到运营商级），但对个人博客防重复点赞足够。

## 6.2 文件上传安全三连

博客头像上传的完整安全检查：

```python
import os
from flask import request, current_app
from werkzeug.utils import secure_filename

def save_avatar(file):
    # 1. 文件类型白名单
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
        return None, '不支持的格式'

    # 2. 文件名消毒
    safe_name = secure_filename(file.filename)
    if not safe_name or '.' not in safe_name:
        safe_name = f'avatar_{int(time.time())}.{ext}'

    # 3. 保存到指定目录，不用用户给的路径
    path = os.path.join(current_app.config['UPLOAD_DIR'], safe_name)
    file.save(path)
    return safe_name, None
```

**安全三连**：
- 白名单扩展（不是黑名单）；
- secure_filename 消毒；
- 拼到自己控制的目录，不用 `os.path.join(UPLOAD_DIR, file.filename)`。

## 6.3 ProxyFix：反向代理后拿到真 IP

如果博客挂在 nginx/caddy 后面，`request.remote_addr` 永远是 nginx 的 IP（127.0.0.1）。装 ProxyFix：

```python
from werkzeug.middleware.proxyfix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
```

之后 `request.remote_addr` 取 `X-Forwarded-For` 头。

**安全警告**：只有在你确认前面有可信代理时才开——否则用户自己伪造 `X-Forwarded-For` 就能骗过 IP 记录。

## 6.4 完整登录示例

```python
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'change-me-in-production'

@app.post('/login')
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        return redirect(url_for('admin'))
    return '用户名或密码错', 401
```

---

# 第 7 章 API 速查与排坑

## 7.1 werkzeug.utils

| 函数 | 作用 |
|---|---|
| `secure_filename(s)` | 文件名消毒 |
| `redirect(location, code=302)` | 重定向 |
| `append_slash_redirect` | 加斜杠重定向 |

## 7.2 werkzeug.security

| 函数 | 作用 |
|---|---|
| `generate_password_hash(pw)` | 生成哈希 |
| `check_password_hash(hash, pw)` | 校验 |
| `safe_str_cmp(a, b)` | 时间安全比较 |

## 7.3 werkzeug.datastructures

| 类 | 用途 |
|---|---|
| `MultiDict` | 一键多值字典 |
| `ImmutableMultiDict` | 不可变（request.args） |
| `Headers` | 请求/响应头 |
| `FileStorage` | 上传文件 |
| `CallbackDict` | 带回调的字典 |

## 7.4 高频坑

| # | 坑 | 解决 |
|---|---|---|
| 1 | 明文存密码 | generate_password_hash |
| 2 | 中文文件名被剥光 | 消毒后判空，自己拼 |
| 3 | 用用户给的路径 save | 拼到自己控制的目录 |
| 4 | request.remote_addr 是 nginx IP | ProxyFix |
| 5 | 上传 .html/.svg 被当脚本 | 白名单扩展 |
| 6 | getlist 忘写 | 复选框只拿到一个 |
| 7 | 自己写 md5 密码 | 用 Werkzeug |
| 8 | 安全比较用 == | safe_str_cmp |

---

# 第 8 章 学习路径与自测

## 8.1 学习路径

- 第 1 天：Request/Response；
- 第 2 天：secure_filename + 密码哈希；
- 第 3 天：MultiDict；
- 第 4 天：LocalProxy（理解 Flask 上下文）；
- 第 5 天：对照博客上传、登录代码。

## 8.2 自测题

1. Werkzeug 和 Flask 什么关系？
2. 为什么不能 `hashlib.md5(password)` 存密码？
3. `secure_filename('../../etc/passwd')` 返回什么？
4. 中文文件名消毒后变空怎么办？
5. MultiDict 解决什么问题？
6. `request.args` 是可变还是不可变？
7. LocalProxy 是什么？Flask 的哪些对象是它？
8. ProxyFix 解决什么问题？有什么风险？
9. `request.form.getlist('tag')` 什么时候用？
10. 上传文件安全检查有哪三步？

## 8.3 答案

1. Flask 是薄壳，Werkzeug 提供 WSGI 工具、路由、请求/响应、安全函数。
2. md5 快、彩虹表能爆；Werkzeug 用 pbkdf2 慢哈希 + salt。
3. `'etc_passwd'`。
4. 自己拼时间戳文件名。
5. 一键多值（复选框、多选）。
6. ImmutableMultiDict，不可变。
7. 线程局部代理；request/g/current_app/session。
8. 反向代理后取真 IP；只有前面有可信代理才开。
9. 复选框同名多值。
10. 白名单扩展、secure_filename、保存到自己目录。

---

> 下一篇：Flask-SQLAlchemy —— 数据库 ORM 全面教程
