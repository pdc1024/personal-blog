# 第三方库全面教程 · Flask

> 面向初学者到进阶者：这是博客项目的 Web 框架骨架。
> 学完这份教程，你将掌握 Flask 从"Hello World"到"理解上下文栈、蓝图、应用工厂、请求钩子、信号机制"的全部核心知识，
> 并能对照博客 v2.8.3 真实源码逐段读懂每个路由在做什么。
>
> 适用版本：Flask 3.x ｜ 博客项目：`app.py`（2545 行）、`main.py`（1241 行）
> 学习路线：基础篇（第 1~3 章）→ 进阶篇（第 4 章）→ 项目实战（第 5 章）→ API 速查与排坑（第 6~7 章）→ 自测（第 8 章）

---

# 第 1 章 认识 Flask

## 1.1 一句话定位

Flask 是一个用 Python 写的**轻量级 Web 框架**。所谓"Web 框架"，就是帮你把"浏览器发来的 HTTP 请求"接住、执行一段 Python 代码、再把结果作为 HTTP 响应发回去的一整套工具。

它的哲学叫 **micro（微内核）**：核心只做一件事——把 URL 映射到 Python 函数；其他功能（数据库、表单、登录、迁移）全部交给扩展。这和 Django 的"全家桶"路线相反。

一句话：**Flask 是博客的骨架**——所有页面（首页、文章详情、后台、点赞接口）都是它在接电话。

## 1.2 Flask 和同类框架对比

| 框架 | 体量 | 特点 | 适合 |
|---|---|---|---|
| **Flask** | 微（约 1MB） | 灵活、扩展生态好 | 个人博客、API、小工具 |
| Django | 重（10MB+） | 自带 ORM/Admin/表单/认证 | 大型内容站 |
| FastAPI | 中 | 异步、类型提示、自动文档 | 现代 API |
| Tornado | 中 | 长连接、异步 | 聊天、推送 |

博客选 Flask 的原因：
- 桌面应用内嵌 Web 服务，启动快、内存小；
- Jinja2 模板和 Werkzeug 路由是它原生带的，上手成本低；
- 扩展够用（Flask-SQLAlchemy、Flask-Login 等）。

## 1.3 一个最小 Flask 应用

把下面代码存为 `hello.py`：

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '<h1>你好，博客！</h1>'

if __name__ == '__main__':
    app.run(debug=True)
```

运行：

```bash
python hello.py
#  * Serving Flask app 'hello'
#  * Running on http://127.0.0.1:5000
```

浏览器打开 `http://127.0.0.1:5000/` 就能看到"你好，博客！"。

**逐行解释**：

1. `from flask import Flask`：从 flask 包导入 Flask 类。
2. `app = Flask(__name__)`：创建一个 Flask 应用对象。`__name__` 是 Python 内置变量，Flask 用它定位项目根目录（找 templates、static）。
3. `@app.route('/')`：装饰器，把下面这个函数和 URL `/` 绑在一起。
4. `def hello():`：视图函数——浏览器访问 `/` 时执行的代码。
5. `return '...'`：返回值作为 HTTP 响应体。
6. `app.run()`：启动开发服务器（仅调试用，生产用 waitress）。

## 1.4 安装

```bash
pip install flask
pip show flask    # 看版本
```

Flask 3.x 要求 Python 3.8+。

## 1.5 博客里的 app 是怎么创建的（app.py 第 122~125 行）

```python
from flask import Flask

app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
app.config.from_object(Config)   # 从 config.py 的 Config 类读配置
```

博客把所有可调参数（数据库路径、密钥、端口）集中到 `config.py` 的 `Config` 类，再用 `from_object` 一次性加载——这是 Flask 推荐的配置管理方式。

---

# 第 2 章 WSGI 与请求-响应循环

## 2.1 WSGI：Python Web 世界的"插座标准"

你可能听过"Flask 是个 WSGI 框架"。WSGI（Web Server Gateway Interface）是 Python 制定的接口标准：**服务器怎么把请求传给框架，框架怎么把结果传回去**。

只要一个东西遵守 WSGI，它就能和任何遵守 WSGI 的另一块配合：

```
浏览器 ──HTTP──> waitress ──WSGI──> Flask ──调用──> 你的视图函数
```

Flask 的 `app` 对象本身就是一个 **WSGI 可调用对象**：它能被当成函数调用，接收两个参数 `environ`（请求环境）和 `start_response`（回调函数）。

```python
# 不要真的这么写，只是演示 WSGI 的本质
def simple_wsgi_app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
    return [b'<h1>Hello</h1>']
```

Flask 做的事就是把这个枯燥的协议包装成了 `@app.route`、`request`、`return render_template(...)` 这种好用的 API。

## 2.2 一次请求的完整生命周期

浏览器访问 `http://127.0.0.1:5000/post/3/`，背后发生了：

```
1. waitress 收到 TCP 连接，解析 HTTP 请求
2. waitress 构造 environ 字典（method、path、headers、body...）
3. waitress 调用 flask app(environ, start_response)
4. Flask 做了这些事：
   a. 建立 Request Context（把 request、session 挂到上下文栈）
   b. 建立 Application Context（把 g、current_app 挂上去）
   c. before_request 钩子依次执行
   d. 用 URL Map 匹配到视图函数 post_detail(post_id=3)
   e. 视图函数查数据库、render_template 渲染 HTML
   f. after_request 钩子依次执行
   g. 构造 Response 对象
5. Flask 调用 start_response(status, headers)，返回 body
6. waitress 把 HTTP 响应发回浏览器
7. Flask 销毁两个上下文栈，释放资源
```

理解这个流程，后面所有"为什么 request 能在视图里直接用"的问题都迎刃而解。

## 2.3 同步阻塞模型

Flask 默认是**同步**框架：一个请求占一个线程直到返回。waitress 开 8 个线程，意味着同时最多处理 8 个请求；第 9 个要排队。

博客是个人应用，同时在线个位数访客，完全够用。如果将来要做高并发 API，应该上 FastAPI 或异步框架。

---

# 第 3 章 基础篇：路由、请求、响应、模板、静态文件

## 3.1 路由：URL 和函数的映射

### 3.1.1 基本路由

```python
@app.route('/')
def index():
    return '首页'

@app.route('/about')
def about():
    return '关于我'
```

### 3.1.2 带参数的路由

```python
@app.route('/post/<int:post_id>/')
def post_detail(post_id):
    return f'文章 ID 是 {post_id}'
```

`<int:post_id>` 是 URL 转换器：
- `string`（默认）：接受除 `/` 外的字符；
- `int`：正整数；
- `float`：浮点数；
- `path`：接受含 `/` 的路径；
- `uuid`：UUID 字符串。

博客里真实用法（app.py 第 1058 行）：

```python
@app.route('/post/<int:post_id>/')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post)
```

### 3.1.3 HTTP 方法

```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # 处理表单提交
        ...
    # GET：显示登录页
    return render_template('login.html')
```

快捷装饰器：

```python
@app.get('/')     # 只接 GET
@app.post('/like') # 只接 POST
```

博客点赞接口（app.py 第 1185 行）：

```python
@app.route('/post/<int:post_id>/like/', methods=['POST'])
def post_like(post_id):
    # AJAX 接口，只接 POST
    ...
```

### 3.1.4 反向生成 URL：url_for

不要在模板里硬编码 URL，用 `url_for('视图函数名')` 反向生成：

```python
from flask import url_for

@app.route('/')
def index():
    return redirect(url_for('about'))   # 跳到 /about
```

模板里：

```html
<a href="{{ url_for('post_detail', post_id=3) }}">文章</a>
<!-- 生成 /post/3/ -->
```

**好处**：以后改 URL 规则，只要改 `@app.route` 一处，所有 `url_for` 自动跟着变。

## 3.2 request：读取请求数据

`request` 是一个**全局代理对象**，但它实际上只在请求上下文中有效。它包含浏览器发过来的一切：

```python
from flask import request

@app.route('/search')
def search():
    # 查询参数：/search?q=python
    q = request.args.get('q', '')

    # 表单数据：POST application/x-www-form-urlencoded
    username = request.form.get('username')

    # JSON body：POST application/json
    data = request.get_json()

    # 上传文件
    f = request.files['avatar']

    # 请求头
    ua = request.headers.get('User-Agent')

    # Cookies
    token = request.cookies.get('token')

    # 路径信息
    path = request.path          # '/search'
    method = request.method      # 'GET'
```

### 3.2.1 request.args vs request.form

| 属性 | 来源 | 典型场景 |
|---|---|---|
| `request.args` | URL 查询串 `?a=1&b=2` | GET 表单、搜索、分页 |
| `request.form` | POST 表单 body | 登录、发文章 |
| `request.values` | 两者合一 | 不推荐用 |
| `request.get_json()` | POST JSON body | AJAX 接口 |

博客首页分页：

```python
page = request.args.get('page', 1, type=int)
# /?page=2 → page=2；没传 → 1；传 abc → 1（type=int 自动容错）
```

### 3.2.2 type 参数的魔法

```python
request.args.get('page', 1, type=int)
```

如果 URL 是 `?page=abc`，`int('abc')` 会抛 ValueError，Flask 会自动返回默认值 1——不用自己 try/except。

## 3.3 响应：return 什么都行

视图函数的返回值会被 Flask 包装成 `Response` 对象：

| 返回值 | 结果 |
|---|---|
| `'字符串'` | 200 OK，Content-Type: text/html |
| `'<h1>...</h1>'` | 同上 |
| `render_template('x.html', ...)` | 渲染后的 HTML 字符串 |
| `jsonify({...})` | 200 OK，Content-Type: application/json |
| `redirect('/')` | 302 重定向 |
| `(body, status)` | 自定义状态码 |
| `(body, headers)` | 自定义响应头 |
| `Response(...)` | 完全自定义 |

### 3.3.1 jsonify：AJAX 接口

```python
from flask import jsonify

@app.post('/post/<int:post_id>/like/')
def post_like(post_id):
    count = Like.query.filter_by(post_id=post_id).count()
    return jsonify({'ok': True, 'count': count})
```

浏览器收到：

```json
{"ok": true, "count": 5}
```

自动处理 JSON 序列化、Content-Type、中文转义。

### 3.3.2 redirect 与 url_for 配合

```python
from flask import redirect, url_for

@app.post('/login')
def login():
    # 登录成功后跳回首页
    return redirect(url_for('index'))
```

### 3.3.3 abort：主动抛 HTTP 错误

```python
from flask import abort

@app.route('/admin')
def admin():
    if not logged_in:
        abort(401)    # 直接返回 401 页面
    ...
```

配合 `@app.errorhandler(404)` 自定义错误页：

```python
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404
```

## 3.4 render_template：渲染模板

```python
from flask import render_template

@app.route('/post/<int:post_id>/')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post, now=datetime.now())
```

Flask 会自动在 `templates/` 目录找 `post_detail.html`，把 `post`、`now` 注入模板上下文。

模板语法是 Jinja2（详见 06 教程）：

```html
<h1>{{ post.title }}</h1>
<p>{{ post.content|safe }}</p>
```

## 3.5 静态文件：CSS/JS/图片

放在 `static/` 目录，通过 `/static/xxx` 访问：

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
```

模板里永远用 `url_for('static', filename=...)`，不要硬写路径。

---

# 第 4 章 进阶篇：上下文、蓝图、钩子、session、错误处理

## 4.1 上下文栈：为什么 request 能"全局"用

新手最困惑的问题：`request` 明明是从 flask import 的全局对象，为什么它能拿到"当前请求"的数据？

答案是 **Thread Local（线程局部存储）+ 上下文栈**。

Flask 内部维护两个栈：

```
app_ctx_stack      ← 应用上下文（current_app、g）
request_ctx_stack  ← 请求上下文（request、session）
```

每个请求进来时，Flask 在栈顶 push 一个新的上下文对象；请求结束时 pop 掉。`request` 是一个 **LocalProxy**，它不直接存数据，而是"指向当前栈顶的请求对象"。

```python
# 你以为：
request = ...当前请求数据...

# 实际上：
request = LocalProxy(_find_req)   # 每次访问都去栈顶找
```

### 4.1.1 什么时候会报错

```
RuntimeError: Working outside of request context.
```

出现场景：
- 在普通函数里直接用 `request`，而这个函数不是被视图调用的；
- 在后台线程里用 `request`；
- 在交互式 Python 里直接 `from flask import request; request.path`。

### 4.1.2 手动推上下文（脚本/后台任务用）

```python
with app.app_context():
    # 这里 current_app 可用
    print(app.name)

with app.test_request_context('/?name=tom'):
    # 这里 request 可用，模拟一个请求
    print(request.path)
```

博客的初始化脚本就在 `app.app_context()` 里跑数据库建表。

## 4.2 g 对象：一次请求内的临时存储

`g` 是一个请求级别的全局对象，同一个请求里的所有视图、钩子、模板都能共享它：

```python
@app.before_request
def before():
    g.fingerprint = hashlib.sha256(...).hexdigest()

@app.post('/like')
def like():
    fp = g.fingerprint    # 同一个请求里，before_request 存的还在
```

博客用 `g.fingerprint` 存访客指纹（app.py 第 691 行附近），所有视图都能取到。

**关键**：`g` 在请求结束后销毁，不要拿它跨请求存数据（那是 session 或数据库的事）。

## 4.3 请求钩子：在请求生命周期插代码

Flask 提供 4 个钩子装饰器：

| 钩子 | 时机 | 典型用途 |
|---|---|---|
| `@app.before_request` | 每个请求进来、视图之前 | 登录检查、记录指纹 |
| `@app.after_request` | 视图执行完、响应发出前 | 加响应头、Gzip 压缩 |
| `@app.teardown_request` | 响应发出后 | 清理资源 |
| `@app.before_first_request` | 第一个请求前（已弃用） | 用 `init_db()` 代替 |

### 4.3.1 before_request 实战（博客 inject_globals 不在这里）

```python
@app.before_request
def attach_fingerprint():
    g.fingerprint = hashlib.sha256(
        (request.remote_addr + request.user_agent.string).encode()
    ).hexdigest()
```

### 4.3.2 context_processor：给所有模板注入变量

和 `before_request` 不同，`context_processor` 返回的字典会自动注入到**每个模板**的上下文中：

```python
@app.context_processor
def inject_globals():
    return {
        'site_name': '我的博客',
        'current_year': datetime.now().year,
        'nav_links': NavLink.query.all(),
    }
```

这样所有模板都能直接用 `{{ site_name }}`、`{{ current_year }}`。

博客的 `inject_globals`（app.py 第 843 行）就是干这个：把站点设置、未读评论数、当前用户注入每个页面。

## 4.4 session：跨请求存数据

`request` 是一次性的，`session` 跨请求：

```python
from flask import session

@app.post('/login')
def login():
    if check_password():
        session['user_id'] = user.id   # 写 session
        return redirect(url_for('admin'))

@app.before_request
def require_login():
    if 'user_id' not in session and request.path.startswith('/admin'):
        return redirect(url_for('login'))
```

**原理**：Flask 默认把 session 数据序列化后加密签名，存在浏览器的 Cookie 里（不是服务器端）。这叫 "client-side session"。

**注意**：
- session cookie 是**签名**不是加密——用户能看到内容但不能篡改；
- 敏感数据（密码）不要放 session；
- 要改服务端 session 存法，用 Flask-Session 扩展。

## 4.5 flash：一次性提示消息

flash 是"闪现消息"：写一次，下次模板渲染后自动清除。

```python
@app.post('/post/<int:id>/delete/')
def delete_post(id):
    ...
    flash('文章已删除', 'success')
    return redirect(url_for('index'))
```

模板里：

```html
{% with messages = get_flashed_messages(with_categories=true) %}
  {% for category, msg in messages %}
    <div class="alert alert-{{ category }}">{{ msg }}</div>
  {% endfor %}
{% endwith %}
```

**为什么用 redirect 而不是直接渲染？** 这叫 POST/Redirect/GET 模式：避免用户刷新浏览器时重复提交表单。

## 4.6 蓝图（Blueprint）：大型项目的模块化

当路由超过 50 个全堆在 `app.py` 里会很难维护。Blueprint 把路由分组：

```python
# blueprints/admin.py
from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard/')
def dashboard():
    return '后台首页'

@admin_bp.route('/posts/')
def posts():
    return '文章管理'
```

```python
# app.py
from blueprints.admin import admin_bp
app.register_blueprint(admin_bp)
```

访问路径自动加上前缀：`/admin/dashboard/`、`/admin/posts/`。

**url_for 要带蓝图名**：

```python
url_for('admin.dashboard')   # 而不是 url_for('dashboard')
```

博客目前路由都在 app.py 里，规模还不需要蓝图；如果将来加 API、管理后台分离，蓝图是标准做法。

## 4.7 应用工厂（Application Factory）

```python
def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    db.init_app(app)
    migrate.init_app(app, db)

    from .main import main_bp
    app.register_blueprint(main_bp)
    return app
```

**好处**：
- 同一套代码能创建多个 app 实例（测试用不同配置）；
- 延迟导入，避免循环依赖；
- 配合蓝图天然模块化。

博客是单实例，直接 `app = Flask(__name__)` 就够了；学习 Flask 生态时会频繁看到工厂模式。

## 4.8 自定义错误处理器

```python
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

@app.errorhandler(413)
def too_large(e):
    return '文件太大', 413
```

元组第二个值是状态码，默认 200 不要忘写。

## 4.9 信号（Signals）

信号是"发布订阅"机制：代码 A 发一个信号，代码 B 订阅它做反应，但两者不直接耦合。

```python
from flask import signal

# 订阅
@blinker.signals('post_deleted').connect
def log_post_delete(sender, post_id):
    logger.info(f'文章 {post_id} 被删了')

# 发布
blinker.signals('post_deleted').send(app, post_id=post_id)
```

Flask 内置一些信号（`request_started`、`request_finished`），博客目前没用到；了解概念即可。

---

# 第 5 章 项目实战：博客真实路由逐段讲

## 5.1 应用初始化（app.py 第 122~189 行）

```python
app = Flask(__name__,
            static_folder='static',
            template_folder='templates',
            static_url_path='/static')
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = Config.DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
```

**逐句讲**：

1. `Flask(__name__, ...)`：指定 static 和 templates 目录（默认就是这些，显式写出更清晰）。
2. `from_object(Config)`：把 `Config` 类里的所有大写变量读进 `app.config`。
3. `SQLALCHEMY_TRACK_MODIFICATIONS=False`：关掉 SQLAlchemy 对每个对象修改的追踪——它会发信号、费内存，博客不需要。
4. `db.init_app(app)`：把 Flask-SQLAlchemy 绑定到 app（工厂模式写法）。

## 5.2 首页路由（app.py 第 1014 行）

```python
@app.route('/')
@app.route('/page/<int:page>/')
def index(page=1):
    kw = (request.args.get('kw') or '').strip()
    query = Post.query.filter_by(published=True, deleted=False)

    if kw:
        query = query.filter(or_(
            Post.title.ilike(f'%{kw}%'),
            Post.body.ilike(f'%{kw}%'),
            Post.summary.ilike(f'%{kw}%'),
        ))

    pagination = query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)

    return render_template('index.html',
                           posts=pagination.items,
                           pagination=pagination,
                           kw=kw)
```

**逐段讲**：

- 两个 `@app.route` 装饰器：`/` 和 `/page/2/` 都走这个视图；`page` 默认 1。
- `kw` 从查询串取 `?kw=python`；`or '').strip()` 是防空值。
- `filter_by(published=True, deleted=False)`：只查已发布、未删除的文章。
- 有搜索词时用 `or_` 把标题/正文/摘要三个字段 OR 起来；`ilike` 不区分大小写。
- `order_by(created_at.desc())`：最新在前。
- `paginate(page, per_page=10, error_out=False)`：每页 10 条；页码超界不报错返回空页。
- `pagination.items`：当前页文章列表；模板里用 `pagination.iter_pages()` 画页码。

## 5.3 文章详情（app.py 第 1058 行）

```python
@app.route('/post/<int:post_id>/')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    if not post.published and not session.get('is_admin'):
        abort(404)
    # 浏览量 +1（异步批量写库，见 288~363 行）
    bump_view_count(post_id)
    comments = Comment.query.filter_by(post_id=post_id, approved=True)\
                            .order_by(Comment.created_at.asc()).all()
    return render_template('post_detail.html', post=post, comments=comments)
```

**亮点**：
- `get_or_404`：文章不存在直接 404，不用手写 `if post is None: abort(404)`。
- 未发布的文章只有管理员能看，访客看到 404——假装它不存在。
- 浏览量不直接写库，丢进内存队列 30 秒批量写一次，避免每访问一次就写 SQLite。

## 5.4 点赞接口（app.py 第 1185 行）

```python
@app.post('/post/<int:post_id>/like/')
def post_like(post_id):
    post = Post.query.get_or_404(post_id)
    fp = g.fingerprint

    existing = Like.query.filter_by(post_id=post_id, fingerprint=fp).first()
    if existing:
        db.session.delete(existing)
        action = 'unliked'
    else:
        db.session.add(Like(post_id=post_id, fingerprint=fp))
        action = 'liked'
    db.session.commit()

    count = Like.query.filter_by(post_id=post_id).count()
    return jsonify({'ok': True, 'action': action, 'count': count})
```

**设计思路**：
- "切换式点赞"：点过再点 = 取消；
- 用 IP+UA 哈希当指纹，同浏览器不能重复点；
- 返回 JSON，前端 AJAX 无刷新更新按钮；
- 不维护 `like_count` 列，每次 COUNT——数据准确，博客规模下性能够。

## 5.5 后台首页（app.py 第 1347 行）

```python
@app.route('/admin/')
@login_required
def admin_dashboard():
    stats = {
        'posts': Post.query.filter_by(deleted=False).count(),
        'comments': Comment.query.count(),
        'likes': Like.query.count(),
        'pending_comments': Comment.query.filter_by(approved=False).count(),
    }
    recent = Post.query.order_by(Post.updated_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html', stats=stats, recent=recent)
```

`@login_required` 是自定义装饰器：检查 session，没登录就跳登录页。这种"装饰器包路由"是 Flask 做权限控制的标准手法。

## 5.6 文章删除后停留原位置（v2.8.3 修复点）

```python
@app.post('/admin/post/<int:post_id>/delete/')
@login_required
def post_delete(post_id):
    post = Post.query.get_or_404(post_id)
    # 按顺序删：点赞 → 评论 → 文章（避免外键错）
    Like.query.filter_by(post_id=post_id).delete()
    Comment.query.filter_by(post_id=post_id).delete()
    db.session.delete(post)
    db.session.commit()
    flash('文章已删除', 'success')
    # 不 redirect 到首页，而是回 referer，保持滚动位置
    return redirect(request.referrer or url_for('admin_posts'))
```

**关键**：`request.referrer` 是浏览器带来的"从哪页跳过来的"——回到原列表页，不用滚回顶部。

## 5.7 Gzip 压缩中间件（app.py 第 196 行）

```python
class GzipMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # 简单实现：检查 Accept-Encoding，压缩响应体
        ...

app.wsgi_app = GzipMiddleware(app.wsgi_app)
```

**原理**：WSGI 应用本身就是可调用对象。包一层中间件，等于在 Flask 和 waitress 之间插了一道工序——请求进来先压缩检查，响应出去前压缩 body。文本资源（HTML/CSS/JS）能压缩到 1/3。

## 5.8 inject_globals（app.py 第 843 行）

```python
@app.context_processor
def inject_globals():
    profile = Profile.query.first()
    return {
        'site_name': profile.site_name if profile else '我的博客',
        'profile': profile,
        'unread_count': Comment.query.filter_by(approved=False).count(),
        'current_year': datetime.now().year,
    }
```

每个模板都能直接用 `{{ site_name }}`、`{{ profile.avatar }}`，不用每个视图都传一遍。

## 5.9 时区过滤器（app.py 第 802 行）

```python
@app.template_filter('local_time')
def local_time_filter(dt):
    if dt is None:
        return ''
    # 存的是 UTC，显示转 Asia/Shanghai
    return pytz.utc.localize(dt).astimezone(
        pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M')
```

模板里：

```html
{{ post.created_at|local_time }}
```

---

# 第 6 章 完整 API 速查表

## 6.1 flask 包常用导入

| 导入 | 用途 |
|---|---|
| `Flask` | 创建应用 |
| `request` | 请求对象 |
| `response` / `Response` | 响应对象 |
| `jsonify` | JSON 响应 |
| `redirect` | 重定向 |
| `url_for` | 反向生成 URL |
| `render_template` | 渲染模板 |
| `session` | 跨请求会话 |
| `flash` / `get_flashed_messages` | 闪现消息 |
| `abort` | 抛 HTTP 错误 |
| `g` | 请求级临时存储 |
| `current_app` | 当前应用代理 |
| `send_file` / `send_from_directory` | 下载文件 |
| `make_response` | 构造响应 |

## 6.2 app 对象常用属性/方法

| 属性/方法 | 作用 |
|---|---|
| `app.config` | 配置字典 |
| `app.route(path, methods=[...])` | 注册路由 |
| `app.add_url_rule(...)` | 代码式注册路由 |
| `app.before_request(f)` | 注册钩子 |
| `app.after_request(f)` | 注册钩子 |
| `app.context_processor(f)` | 模板变量注入 |
| `app.template_filter(name)` | 注册模板过滤器 |
| `app.errorhandler(code)` | 错误处理 |
| `app.register_blueprint(bp)` | 注册蓝图 |
| `app.run(...)` | 开发服务器 |
| `app.test_client()` | 测试客户端 |
| `app.app_context()` | 手动推应用上下文 |
| `app.test_request_context(...)` | 模拟请求上下文 |
| `app.url_map` | URL 映射表 |
| `app.view_functions` | 视图函数字典 |

## 6.3 request 对象常用属性

| 属性 | 内容 |
|---|---|
| `request.method` | GET/POST/... |
| `request.path` | 路径部分 |
| `request.url` | 完整 URL |
| `request.args` | 查询参数 |
| `request.form` | 表单数据 |
| `request.files` | 上传文件 |
| `request.get_json()` | JSON body |
| `request.headers` | 请求头字典 |
| `request.cookies` | Cookies |
| `request.remote_addr` | 客户端 IP |
| `request.user_agent` | User-Agent |
| `request.referrer` | 来源页 |
| `request.is_secure` | 是否 HTTPS |

## 6.4 配置项常用

| 配置 | 作用 |
|---|---|
| `SECRET_KEY` | 签名 session/flash 的密钥 |
| `DEBUG` | 调试模式 |
| `TESTING` | 测试模式 |
| `PERMANENT_SESSION_LIFETIME` | session 有效期 |
| `MAX_CONTENT_LENGTH` | 请求体大小上限（防上传爆炸） |
| `SERVER_NAME` | 域名 |
| `APPLICATION_ROOT` | 子路径部署 |
| `PREFERRED_URL_SCHEME` | http/https |

---

# 第 7 章 高频坑与排查（20 条）

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | `app.run()` 当生产 | 官方警告、性能差 | 用 waitress serve |
| 2 | Working outside of context | 后台线程/脚本用 request | `with app.app_context():` |
| 3 | 改了代码不生效 | 旧页面 | debug=True 自动重载；或重启 |
| 4 | 模板变量未定义 | jinja 报错 | context_processor 或视图 render_template 传 |
| 5 | session 不生效 | 登录刷新就掉 | SECRET_KEY 没设或变了 |
| 6 | POST 403 Forbidden | CSRF 保护 | 表单加 `{{ csrf_token() }}` 或用 Flask-WTF |
| 7 | 中文响应乱码 | 浏览器显示问号 | `Content-Type: text/html; charset=utf-8` |
| 8 | 静态文件 404 | CSS 加载不出 | 检查 static 目录和 url_for('static') |
| 9 | url_for 报错 | 端点找不到 | 蓝图要写 `蓝图.函数名` |
| 10 | redirect 后 flash 没了 | 消息不显示 | 用 redirect 不是直接 render；模板调 get_flashed_messages |
| 11 | 大文件上传 413 | 上传失败 | MAX_CONTENT_LENGTH 调大 |
| 12 | g 串请求 | A 请求看到 B 的数据 | 不要跨请求存 g；请求结束自动清 |
| 13 | 蓝图 url_for 命名 | 端点错 | `蓝图名.函数名` |
| 14 | 循环导入 | ImportError | 延迟导入、工厂模式 |
| 15 | 调试模式泄露 | 生产开 debug=True | 生产关 debug |
| 16 | 404 但路由存在 | 末尾斜杠不一致 | `/admin` 和 `/admin/` 是两个路由 |
| 17 | AJAX 返回 HTML | 接口不返回 JSON | 视图用 jsonify 不要 render_template |
| 18 | before_request 死循环 | 一直重定向 | 白名单排除登录页本身 |
| 19 | 多线程 sqlite 报错 | thread 错 | SQLALCHEMY 连接 check_same_thread=False |
| 20 | 响应头不生效 | after_request 没执行 | return 之前确认钩子顺序 |

---

# 第 8 章 学习路径与自测

## 8.1 学习路径

**第 1 周：基础**
- Day 1：Hello World + 路由 + 模板；
- Day 2：request/response/redirect；
- Day 3：静态文件 + 模板继承；
- Day 4：session + flash + 登录页；
- Day 5：错误处理 + 自定义 404；
- Day 6~7：写一个完整的待办应用。

**第 2 周：进阶**
- Day 8：理解 WSGI 和请求生命周期；
- Day 9：上下文栈、g、钩子；
- Day 10：蓝图拆分应用；
- Day 11：应用工厂；
- Day 12：中间件；
- Day 13：信号（了解）；
- Day 14：测试用 test_client。

**第 3 周：对照博客源码**
- 读 app.py 每个路由；
- 画出请求-响应时序图；
- 尝试加一个新功能（如"文章置顶"）。

## 8.2 自测题（20 道）

1. Flask 的"微"体现在哪里？和 Django 有什么取舍？
2. WSGI 是什么？Flask app 为什么能被 waitress 调用？
3. `@app.route('/post/<int:id>/')` 里 `<int:id>` 是什么意思？
4. `request.args` 和 `request.form` 的区别？
5. 视图函数返回 `(html, 404)` 是什么效果？
6. `url_for('post_detail', post_id=3)` 解决什么问题？
7. 为什么会报 `Working outside of request context`？
8. `g` 和 `session` 的区别？
9. `@app.before_request` 和 `@app.context_processor` 区别？
10. flash 消息为什么要配合 redirect？
11. Blueprint 解决什么问题？
12. 应用工厂模式的好处？
13. SECRET_KEY 是干什么的？
14. 为什么生产不能用 app.run()？
15. `abort(404)` 和 `return ('', 404)` 区别？
16. POST/Redirect/GET 模式是什么？
17. 怎么给所有模板注入一个 `site_name` 变量？
18. 蓝图注册后，url_for 的端点名怎么写？
19. after_request 钩子能修改响应吗？
20. 博客点赞接口为什么返回 JSON 而不是 HTML？

## 8.3 答案

1. 核心只做路由+WSGI，其他靠扩展；Django 自带 ORM/Admin/表单。
2. Python Web 服务器和框架的接口标准；app 本身是 WSGI 可调用对象。
3. URL 转换器，把 `/post/3/` 里的 3 转成 int 传给视图。
4. args 是 URL 查询串，form 是 POST 表单 body。
5. 返回 404 状态码 + 该 HTML。
6. 反向生成 URL，改路由规则不用改模板。
7. 在没有请求上下文的地方（后台线程、脚本）用了 request。
8. g 是单次请求内存；session 跨请求存浏览器 cookie。
9. before_request 是预处理代码；context_processor 是往模板注入变量。
10. POST 后 redirect 防止刷新重复提交，flash 存在 session 里跳一次再渲染。
11. 大型项目把路由分组、解耦。
12. 多配置实例、延迟导入、测试友好。
13. 签名 session 和 flash，防止篡改。
14. 单线程、性能差、官方明确不建议生产。
15. abort 直接抛异常走错误处理器；return 是正常返回。
16. 表单 POST → 302 重定向到 GET → 用户刷新不再重复提交。
17. `@app.context_processor` 返回 `{'site_name': ...}`。
18. `蓝图名.函数名`，如 `admin.dashboard`。
19. 能，它接收 response 对象并返回修改后的。
20. AJAX 接口要无刷新更新页面，JSON 让前端 JS 好处理。

## 8.4 进一步学习

- 官方文档：https://flask.palletsprojects.com/
- 多文件应用模式：https://flask.palletsprojects.com/patterns/packages/
- 部署：https://flask.palletsprojects.com/deploying/

---

> 下一篇：Jinja2 —— 模板引擎全面教程
