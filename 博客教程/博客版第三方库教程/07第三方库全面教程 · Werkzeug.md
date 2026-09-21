# 第三方库全面教程 · Werkzeug

> 面向初学者：Werkzeug 是 Flask 的"隐形引擎"，你几乎不直接写它，但它一直在背后干活。
> 学完这份教程，你不仅能明白 Flask 的底层原理，还能直接用它解决密码哈希、上传安全、Cookie、代理修正等实际问题。
> 适用版本：Werkzeug 3.x ｜ 博客项目：`app.py` 里 `secure_filename` + Flask 全套底层

---

# 第 1 章 这个库是什么

## 1.1 一句话定位

Werkzeug（德语"工具"）是 Flask 的**底层工具库**。Flask 处理请求时，真正干粗活的其实是它：

- 解析 HTTP 请求（把原始字节流变成好用的 `request` 对象）；
- 匹配路由（判断 `/post/3/` 该交给哪个函数）；
- 构造 HTTP 响应；
- 提供一堆安全工具（文件名消毒、密码哈希、Cookie）；
- 自带一个开发服务器（Flask `app.run()` 跑的就是它）。

一句话：**Flask 是前台接待，Werkzeug 是后台机房**。博客项目直接 `import` 的地方主要是 `secure_filename()`，但它支撑了 Flask 90% 的底层行为。

## 1.2 为什么单独学它

- **Flask 的行为都能在 Werkzeug 找到出处**：理解了 Werkzeug，读 Flask 源码不再是黑盒；
- **它能脱离 Flask 单独用**：写个极简 WSGI 应用、做接口测试、写爬虫都能用；
- **安全工具不挑框架**：密码哈希、文件名消毒这些函数，任何 Python 项目都能用。

## 1.3 一个最小 Werkzeug 应用

不通过 Flask，直接用 Werkzeug 写 WSGI 应用：

```python
from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple

@Request.application
def application(request):
    return Response(f'你访问了 {request.path}', mimetype='text/plain; charset=utf-8')

if __name__ == '__main__':
    run_simple('127.0.0.1', 5000, application)
```

跑起来就是一个完整的 Web 服务。Flask 本质上是对这种写法的一层糖衣。

---

# 第 2 章 核心概念与原理

## 2.1 WSGI：Werkzeug 的老本行

Werkzeug 最初就是为 Python 写 WSGI 工具而生的。完整链路：

```
浏览器发 HTTP 请求
  ↓
Werkzeug 开发服务器 / waitress 收到 TCP 连接
  ↓
把请求解析成 environ 字典（WSGI 标准）
  ↓
Werkzeug 的 Request 类把 environ 包成好用的 request 对象
  ↓
你的视图函数处理
  ↓
返回值被包装成 Response 对象
  ↓
Response 被序列化成 HTTP 响应字节流
  ↓
服务器发回浏览器
```

Flask 的 `request`、`Response`、`abort(404)`，底层全是 Werkzeug 的类。

## 2.2 安全两件套：文件名消毒 + 密码哈希

Werkzeug 最实用的两个工具，**所有 Web 项目必用**：

### 2.2.1 secure_filename()：防路径穿越

用户上传文件时，文件名可能是：

```
../../../../etc/passwd
..\..\..\windows\system32\drivers\etc\hosts
my photo.png
```

如果直接拼路径：

```python
# ❌ 危险
save_path = '/var/www/uploads/' + file.filename
file.save(save_path)
```

攻击者上传名为 `../app.py` 的文件，就可能覆盖你的源码。

`secure_filename()` 把危险字符全部清掉：

```python
secure_filename('../../etc/passwd')     # → 'etc_passwd'
secure_filename('my photo.png')        # → 'my_photo.png'
secure_filename('我的头像.png')         # → 'png'（中文被洗掉！）
```

### 2.2.2 密码哈希：generate_password_hash / check_password_hash

**永远不要明文存密码**。数据库一旦泄露，用户在所有网站上的密码都完了（大家习惯一个密码到处用）。

正确做法：

```python
from werkzeug.security import generate_password_hash, check_password_hash

# 注册时
hash1 = generate_password_hash('mypassword')
hash2 = generate_password_hash('mypassword')
print(hash1 == hash2)   # False！同一密码每次结果不同（因为盐不同）

# 登录时
check_password_hash(hash1, 'mypassword')   # True
check_password_hash(hash1, 'wrong')        # False
```

哈希串长这样：`scrypt:32768:8:1$xQ...$...`，里面包含：

- **算法**（scrypt / pbkdf2:sha256）；
- **迭代次数**（算力参数，越暴力越慢）；
- **盐**（随机串，防彩虹表）；
- **哈希结果**。

**为什么安全？** 攻击者拿到哈希串，只能用暴力破解——每个用户密码不同盐，彩虹表失效。

## 2.3 线程局部存储：Local / LocalProxy

Flask 的 `request` 之所以"每个请求各看各的"，靠的是 Werkzeug 的：

- **Local**：线程局部存储，每个线程一份独立数据；
- **LocalProxy**：延迟代理，访问属性时再去 Local 里拿真实对象。

```python
from werkzeug.local import Local, LocalProxy

local = Local()
local.user = 'alice'      # 当前线程设 user
# 别的线程看不到 local.user

request = LocalProxy(lambda: local.user)
print(request)            # 'alice'，但你不知道背后是 Local
```

**你不需要会用它们**，但要理解：Flask 的 `request`、`current_app`、`g` 都是 LocalProxy 包出来的——这就是为什么后台线程里"看不到当前请求"，必须 `with app.app_context()` 手动推入。

## 2.4 路由系统：Map / Rule

Flask 的 `@app.route` 底层是 Werkzeug 的 `Map` 和 `Rule`：

```python
from werkzeug.routing import Map, Rule

url_map = Map([
    Rule('/', endpoint='index'),
    Rule('/post/<int:post_id>/', endpoint='post_detail'),
    Rule('/post/<int:post_id>/edit/', endpoint='post_edit'),
])
adapter = url_map.bind('127.0.0.1:5000')

endpoint, args = adapter.match('/post/42/')
print(endpoint, args)   # 'post_detail', {'post_id': 42}
```

**类型转换器**（`<int:post_id>` 的 `int`）也是 Werkzeug 提供的：`IntegerConverter`、`StringConverter`、`PathConverter`、`FloatConverter`、`UUIDConverter`。

**自定义转换器**（进阶）：

```python
from werkzeug.routing import BaseConverter

class RegexConverter(BaseConverter):
    def __init__(self, url_map, regex):
        super().__init__(url_map)
        self.regex = regex

url_map.converters['re'] = RegexConverter
# 现在可以写: Rule('/<re(r"[a-z]{3}"):code>/', endpoint='...')
```

---

# 第 3 章 安装与版本

```bash
pip install werkzeug
pip show werkzeug
```

安装 Flask 自动带上。Werkzeug 3.x 要求 Python 3.8+。博客 `requirements.txt` 显式写出是为了锁定版本。

---

# 第 4 章 API 全面讲解

## 4.1 上传安全：secure_filename（✅ 项目用到）

```python
from werkzeug.utils import secure_filename

# 基础用法
safe = secure_filename('我的 头像.png')   # 中文被洗掉

# 博客的写法：时间戳 + 消毒名，防重名
import time
save_name = f"{int(time.time())}_{secure_filename(file.filename)}"
file.save(os.path.join(Config.UPLOAD_DIR, save_name))
```

**完整上传安全三连**：

```python
file = request.files.get('avatar')
if not file or not file.filename:
    return '没选文件', 400

# ① 扩展名白名单（在 secure_filename 之前判断原扩展名）
ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
if ext not in {'png', 'jpg', 'jpeg', 'webp'}:
    return '不支持的图片格式', 400

# ② 消毒文件名
safe_name = secure_filename(file.filename)
if not safe_name:
    return '非法文件名', 400

# ③ 拼绝对路径保存
file.save(os.path.join(Config.UPLOAD_DIR, safe_name))
```

## 4.2 密码哈希：生成与校验（➕ 强烈推荐）

```python
from werkzeug.security import generate_password_hash, check_password_hash

# 注册：存哈希到数据库
hashed = generate_password_hash(
    'mypassword',
    method='scrypt:32768:8:1',   # 算法和参数（默认就行）
)

# 登录
if check_password_hash(user.password_hash, input_password):
    login_success()
else:
    login_failed()
```

**参数调整**（需要更安全时）：

```python
# pbkdf2 算法，迭代 600000 次
generate_password_hash('pw', method='pbkdf2:sha256:600000')
```

## 4.3 Request 对象完整属性

Flask 的 `request` 是 Werkzeug `Request` 的子类。常用属性：

| 属性 | 内容 |
|---|---|
| `request.method` | 'GET'/'POST'/... |
| `request.args` | URL query 参数（MultiDict） |
| `request.form` | 表单 POST 字段（MultiDict） |
| `request.files` | 上传文件（MultiDict） |
| `request.json` / `get_json()` | JSON 请求体 |
| `request.headers` | 请求头（ EnvironHeaders） |
| `request.cookies` | Cookie 字典 |
| `request.remote_addr` | 客户端 IP |
| `request.path` / `request.full_path` / `request.url` | 路径信息 |
| `request.user_agent` | User-Agent 解析后的对象 |
| `request.content_type` | Content-Type 头 |
| `request.content_length` | 请求体长度 |
| `request.referrer` / `request.origin` | 来源页 |

**User-Agent 解析**：

```python
ua = request.user_agent
print(ua.browser)    # 'Chrome'
print(ua.platform)    # 'Windows'
print(ua.string)      # 完整字符串
```

博客的点赞指纹就用 `remote_addr + user_agent.string` 的哈希。

## 4.4 MultiDict：一键多值字典

`request.args`、`request.form`、`request.files` 不是普通 dict，是 **MultiDict**：

```python
# 多选标签 / 多选文件
request.form.get('tag')         # 取第一个
request.form.getlist('tag')     # 全部 → ['python', 'flask']
request.form.get('age', 18, type=int)   # 自动类型转换
```

**坑**：普通字典 `form['key']` 取不到抛 KeyError；`.get()` 返回 None。多选字段务必用 `getlist()`。

## 4.5 Response 对象

Flask 视图返回的字符串/字典，最终都变成 Werkzeug `Response` 对象：

```python
from werkzeug.wrappers import Response

resp = Response('hello', status=200, mimetype='text/html; charset=utf-8')
resp.headers['X-Custom'] = 'value'
resp.set_cookie('theme', 'dark', max_age=3600, httponly=True)
resp.delete_cookie('theme')
```

**设置 Cookie 的关键参数**：

| 参数 | 作用 |
|---|---|
| `max_age` | 存活秒数 |
| `httponly=True` | JS 读不到（防 XSS 偷 Cookie） |
| `secure=True` | 只在 HTTPS 下传输 |
| `samesite='Lax'` | 防 CSRF |
| `domain` | 生效域名 |

## 4.6 Cookie 签名：ItsDangerous

Werkzeug 还提供 `URLSafeTimedSerializer`，用来做"带过期时间的签名 Cookie"（Flask session 底层就是它）：

```python
from itsdangerous import URLSafeTimedSerializer

s = URLSafeTimedSerializer('secret-key')
token = s.dumps({'user_id': 1})            # 生成签名串
data = s.loads(token, max_age=3600)         # 1 小时内有效，过期抛异常
```

做"密码重置链接"、"邮箱验证链接"常用。

## 4.7 反向代理修正：ProxyFix

部署在 nginx 后面时，`request.remote_addr` 拿到的是 nginx 的 IP（127.0.0.1），不是真实访客 IP。用 ProxyFix 中间件修正：

```python
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
```

之后 `request.remote_addr` 自动读 `X-Forwarded-For` 头。

## 4.8 其他常用工具

| 工具 | 作用 |
|---|---|
| `werkzeug.utils.cached_property` | 属性只算一次并缓存 |
| `werkzeug.utils.redirect` | 生成 302 响应 |
| `werkzeug.utils.append_slash_redirect` | 路径斜杠重定向 |
| `werkzeug.exceptions.HTTPException` | 所有 HTTP 异常基类 |
| `werkzeug.debug.DebuggedApplication` | 交互式调试器 |
| `werkzeug.test.Client` | 测试客户端（不启服务器测路由） |
| `werkzeug.security.generate_password_hash` | 密码哈希 |
| `werkzeug.utils.secure_filename` | 文件名消毒 |

---

# 第 5 章 实战示例

## 5.1 项目内示例：友链头像上传（app.py 第 722 行附近）

```python
ALLOWED_AVATAR_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_avatar(filename):
    """校验扩展名白名单"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXT

@app.route('/admin/links/save/', methods=['POST'])
def admin_link_save():
    file = request.files.get('avatar_file')
    if file and file.filename and allowed_avatar(file.filename):
        ext = secure_filename(file.filename).rsplit('.', 1)[-1].lower()
        save_name = f"link_{int(time.time())}.{ext}"
        file.save(os.path.join(Config.LINK_AVATAR_DIR, save_name))
        link.avatar_url = f"/uploads/links/{save_name}"
    db.session.commit()
```

**逐行要点**：

- 先判断 `file and file.filename`——空文件名不上传；
- `allowed_avatar()` 白名单——防"伪装图片的脚本"；
- 时间戳命名——防同名覆盖、防 CDN 缓存；
- 数据库只存相对 URL——迁移机器不改数据。

## 5.2 项目内示例：点赞指纹（before_request）

```python
import hashlib

@app.before_request
def load_fingerprint():
    ua = request.headers.get('User-Agent', '')
    fp_source = f"{request.remote_addr}|{ua}".encode('utf-8')
    g.fingerprint = hashlib.md5(fp_source).hexdigest()
```

视图函数里直接用 `g.fingerprint`，不用每个路由都算一遍。

## 5.3 独立示例：完整登录系统（密码哈希版）

```python
from flask import Flask, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'change-me-in-production'

USERS = {'admin': generate_password_hash('admin123')}

@app.route('/login/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username in USERS and check_password_hash(USERS[username], password):
            session['user'] = username
            return redirect(url_for('dashboard'))
        error = '用户名或密码错误'
    return f'''
    <form method=post>
      {error}
      <input name=username><input name=password type=password>
      <button>登录</button>
    </form>'''

@app.route('/dashboard/')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return f'欢迎 {session["user"]}'

@app.route('/logout/')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))
```

跑起来访问 `/login/`，用 admin/admin123 登录。这就是所有"密码登录"功能的最小模型。

---

# 第 6 章 高频坑与排查

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | 中文文件名被洗掉 | 上传后文件名变下划线 | secure_filename 的设计；要保原名用哈希+原扩展名 |
| 2 | 不消毒直接拼路径 | 路径穿越攻击 | secure_filename + os.path.join |
| 3 | 文件保存 0 字节 | 先 read 再 save | 保存前 `file.seek(0)` |
| 4 | 多选字段只取到一个 | form.get 只返回第一个 | 用 `getlist()` |
| 5 | 明文存密码 | 数据库泄露 = 密码泄露 | generate_password_hash |
| 6 | 空文件名 | secure_filename('') 返回空 | 空结果兜底 |
| 7 | 上传文件超大 | 服务器卡 | Flask 设置 `MAX_CONTENT_LENGTH` |
| 8 | nginx 后 IP 全是 127.0.0.1 | 统计错 | ProxyFix 中间件 |
| 9 | Cookie 不生效 | 登录后还是跳登录 | 检查 httponly/secure/samesite 配置 |
| 10 | 密码哈希校验失败 | 明明对了却说错 | 数据库里存的不是 generate_password_hash 的结果 |
| 11 | 大文件上传占满磁盘 | DoS | 限制 MAX_CONTENT_LENGTH + 流式保存 |
| 12 | 不同用户看到同一份 request | 代码写错 | request 是 LocalProxy，别存成全局变量 |

**排查上传问题**：临时把 `MAX_CONTENT_LENGTH` 调大、`console=True` 打包看错误、用 Postman 模拟上传抓请求。

---

# 第 7 章 学习路径与自测

## 7.1 学习路径

**第 1 天：安全两件套**
- 学会 `secure_filename` 上传三连；
- 学会 `generate_password_hash` 登录；
- 目标：给自己的项目加文件上传和登录。

**第 2 天：Request / Response**
- 熟悉 request 全部常用属性；
- 理解 MultiDict；
- 目标：能从请求里拿到任何数据。

**第 3~4 天：进阶**
- 学 ProxyFix、Cookie 签名；
- 读一次 Flask 源码里怎么把 environ 变成 request；
- 学自定义路由转换器。

## 7.2 自测题

1. `secure_filename('../../etc/passwd')` 会发生什么？
2. 密码为什么要存哈希不存明文？"加盐"是什么？
3. 多选表单字段在 Flask 里怎么取？
4. 文件保存前读了内容导致 0 字节，怎么修？
5. 上传文件的全套安全步骤是哪几步？
6. `request.args` 和 `request.form` 有什么区别？
7. 为什么 `check_password_hash` 不会因为盐不同而失败？
8. nginx 反向代理后 `request.remote_addr` 为什么不准？怎么修？
9. LocalProxy 解决什么问题？
10. Cookie 设 `httponly=True` 有什么用？

## 7.3 答案

1. 返回 `'etc_passwd'`，`..` 和 `/` 被清掉，路径穿越失效。
2. 数据库泄露时明文可被撞库；加盐=每个密码混入随机串再哈希，同一密码结果不同，防彩虹表。
3. `request.form.getlist('字段名')`。
4. 保存前 `file.seek(0)` 把文件指针倒回开头。
5. ① 检查空文件名；② 扩展名白名单；③ secure_filename 消毒；④ os.path.join 拼路径；⑤ file.save。
6. args 读 URL 问号参数（GET），form 读表单 POST 字段。
7. 盐和算法参数存在哈希串里，`check_password_hash` 会自己解析出来再用同样的盐计算。
8. 因为 nginx 把真实 IP 放在 `X-Forwarded-For` 头，Werkzeug 默认读不到；用 `ProxyFix` 中间件修正。
9. 多线程并发时让每个线程看到自己的 request/app，互不干扰；同时对外暴露成"像全局变量"一样方便使用。
10. 浏览器里的 JS 读不到这个 Cookie，能阻止 XSS 脚本偷登录态。

## 7.4 进一步学习

- 官方文档：https://werkzeug.palletsprojects.com/
- Werkzeug 路由系统：https://werkzeug.palletsprojects.com/routing/
- 安全考量：https://werkzeug.palletsprojects.com/security/

---

> 下一篇：Flask-SQLAlchemy —— 数据库 ORM 全面教程
