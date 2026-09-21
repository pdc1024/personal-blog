# 第三方库全面教程 · Flask

> 面向初学者：不假设你已懂任何 Web 知识，每个概念第一次出现都用大白话解释；同时也不回避原理，凡是博客里用到的机制，都讲到"能自己改"的程度。
> 学完这份教程，你不仅能读懂 `app.py` 的 2545 行，还能自己设计一个类似规模的 Web 项目。
> 适用版本：Flask 3.x（博客 v2.8.3 实际使用）｜ 项目：`D:\blog_pkg\app.py`

---

# 第 1 章 这个库是什么

## 1.1 一句话定位

Flask 是 Python 世界里最流行的 **Web 微框架（micro web framework）**。它做两件事：

1. **接收 HTTP 请求**：把浏览器发来的请求翻译成 Python 能读的对象；
2. **调用你写的函数**：根据网址找到对应的处理函数，把返回值翻译成 HTTP 响应发回浏览器。

数据库、用户登录、表单校验、权限系统——这些它都**不内置**，要用的时候自己装扩展。这种"小内核 + 强生态"的设计哲学叫"微"。

一句话：**Flask 是博客项目的"骨架与指挥中心"**——所有网址（路由）由它登记，所有请求由它接住，所有页面由它调用模板渲染出来。博客项目 `app.py` 约 2545 行，其中 90% 是你写的业务代码，Flask 只负责把这些代码"挂"到网址上。

## 1.2 为什么博客选 Flask，不选别的

Python Web 框架不止 Flask 一个，主流对比：

| 框架 | 定位 | 优点 | 缺点 | 适合谁 |
|---|---|---|---|---|
| **Flask** | 微框架 | 灵活、轻、上手快、生态全 | 大项目要自己组装 | 小型博客、工具、API |
| Django | 全家桶 | 自带 ORM/Admin/表单/鉴权 | 重、约定死、初次配置多 | 大型内容站、后台系统 |
| FastAPI | 现代异步 | 类型提示、自动文档、性能高 | 较新、生态不如 Flask | API 服务、AI 后端 |
| Tornado | 异步服务器 | 长连接/WebSocket 强 | Web 功能弱 | 聊天、推送 |

博客选 Flask 的理由：

- **桌面端单机应用**，不需要 Django 那套重型 Admin；
- **学习成本低**，作者一个人写得动；
- **扩展组合自由**：博客实际用了 Flask-SQLAlchemy（数据库）、Flask 自带模板（Jinja2）、waitress（服务器）——拼积木的过程自己可控；
- **打包体积小**，PyInstaller 打出来 34MB，换成 Django 直接上百 MB。

## 1.3 一个最小 Flask 程序长什么样

```python
# hello.py
from flask import Flask

app = Flask(__name__)          # 1. 创建应用对象

@app.route('/')                 # 2. 把根路径 "/" 绑到下面的函数
def hello():
    return '<h1>你好，博客！</h1>'

if __name__ == '__main__':
    app.run(debug=True)         # 3. 启动开发服务器
```

跑起来：`python hello.py`，浏览器打开 `http://127.0.0.1:5000`。三行核心代码，一个网站就有了——这就是"微框架"的含义。

## 1.4 关键名词预习

后面章节反复出现，先混个脸熟：

- **请求（Request）**：浏览器发给服务器的"我要看 `http://.../post/3/`"。
- **响应（Response）**：服务器还回去的 HTML/JSON/状态码。
- **路由（Route）**：网址 → 函数 的映射表。
- **视图函数（View Function）**：你写的、被路由调用的那个函数。
- **模板（Template）**：HTML 文件里掺了 `{{ 变量 }}` 占位符，Flask 渲染时替换成真实数据。
- **WSGI**：Python Web 服务器和应用之间的统一接口标准（第 2 章详解）。

---

# 第 2 章 核心概念与原理

## 2.1 WSGI：Flask 与世界对话的"接口标准"

### 2.1.1 为什么需要 WSGI

假设没有 WSGI。Flask 想换一个服务器（从开发用的 Werkzeug 换生产用的 waitress），就得为每个服务器重新写一遍"请求怎么传给 Flask"的胶水代码——N 个服务器 × M 个框架 = N×M 份胶水。

WSGI 把这件事变成"两边都遵守同一个协议"：服务器只要会调用 `app(environ, start_response)`，Flask 只要实现这个调用，就能互相接。N + M 份胶水就够了。

### 2.1.2 WSGI 长什么样

一个最小的"符合 WSGI 协议"的应用，甚至不需要 Flask：

```python
def my_app(environ, start_response):
    # environ：一个大字典，装着请求方法、路径、headers、query string……
    # start_response：一个回调函数，用来发送状态码和响应头
    path = environ['PATH_INFO']
    start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
    return [f'你访问了 {path}'.encode('utf-8')]

# 用 waitress 跑它：
from waitress import serve
serve(my_app, host='127.0.0.1', port=8080)
```

**Flask 本质上就是对这个协议的一层友好封装**：路由、模板、request 对象，全都是为了让你不用手搓 `environ`。

### 2.1.3 博客里 WSGI 在哪

- 开发模式：`app.run()` 启动 Werkzeug 自带的 WSGI 服务器（只适合开发）；
- 生产模式：`run_server()` 调 `waitress.serve(app, ...)`，waitress 是 WSGI 服务器，`app` 就是 Flask 实例；
- 桌面版：`create_server(app, ...)` 把同一个 `app` 对象放到后台线程跑。

**同一个 `app` 对象，能跑在不同的 WSGI 服务器上，这就是 WSGI 标准的威力。**

## 2.2 请求-响应循环（Request-Response Cycle）

一次访问 `http://blog/post/3/` 的完整生命周期：

```
① 浏览器发出 HTTP 请求
    GET /post/3/ HTTP/1.1
    Host: 127.0.0.1:5000
    User-Agent: ...
        ↓
② WSGI 服务器（waitress/Werkzeug）收到 TCP 连接
    把请求解析成 environ 字典
        ↓
③ Flask 应用被调用：app(environ, start_response)
    a. 创建 RequestContext（请求上下文）和 AppContext（应用上下文），压栈
    b. URL 路由匹配：/post/<int:post_id>/ 对应 post_detail 函数，post_id=3
    c. 跑 before_request 钩子
    d. 调用视图函数 post_detail(3)
       └─ 内部：查数据库 → 渲染 Jinja2 模板 → 得到 HTML 字符串
    e. 视图返回值包装成 Response 对象
    f. 跑 after_request 钩子（博客在这里加 Gzip、安全头）
    g. 上下文出栈销毁
        ↓
④ WSGI 服务器拿到 Response，拼成 HTTP 响应发回浏览器
    HTTP/1.1 200 OK
    Content-Type: text/html; charset=utf-8
    ...
    <html>...</html>
```

**理解这张图，就读懂了 Flask 的全部工作方式。** 后面学的所有 API（request、session、钩子），都是在这条流水线的某个环节介入。

## 2.3 上下文：新手最容易懵，但必须搞懂

### 2.3.1 为什么需要"上下文"这个奇怪的东西

Flask 是**多线程并发**的：同时来 10 个请求，可能用 10 个线程同时跑你的视图函数。

如果 `request` 是一个普通全局变量：

```python
request = None       # 伪代码
def view():
    global request
    request = 当前请求    # 线程 A 刚设置
    ...
    request = 当前请求    # 线程 B 也设置，把 A 的覆盖了！
```

10 个请求互相踩，乱套。

Flask 的解法是**线程局部存储（thread-local）**：每个线程有自己的一份"看不见的全局变量"。你在视图函数里写 `from flask import request`，Flask 会自动返回**当前线程**对应的那个 request 对象——别的线程看不见。

但这套机制有个前提：**必须处于"请求上下文"或"应用上下文"里**。否则 Flask 不知道你在哪个应用、哪个请求里。

### 2.3.2 两个上下文盒子

| 上下文 | 装着什么 | 什么时候有效 |
|---|---|---|
| **应用上下文（app context）** | `current_app`（当前应用实例）、`g`（请求期间的临时存储）、`current_app.config` | 请求处理期间；**脚本/线程里用 db 必须手动包** |
| **请求上下文（request context）** | `request`（当前请求对象）、`session`（用户会话） | 每个请求处理期间 |

### 2.3.3 经典报错：Working outside of application context

博客的云同步是在后台线程跑的。如果直接写：

```python
def sync_worker():
    posts = Post.query.all()   # ❌ 报错：Working outside of application context
```

后台线程**不在请求处理中**，Flask 不知道你用哪个应用。必须手动推入上下文：

```python
def sync_worker(app):
    with app.app_context():    # ✅ 手动把应用上下文压栈
        posts = Post.query.all()
```

**记忆口诀**：视图函数里随便用 `request`/`db`/`current_app`；后台线程、定时任务、导入脚本里用它们之前，先 `with app.app_context():`。

### 2.3.4 `g` 对象：一个请求期间的临时仓库

`g` 是"global"的简写，但它**不是真全局**——每个请求独立一份，请求结束就销毁。

博客用 `g` 存"当前请求期间算出的访客指纹"：

```python
from flask import g

@app.before_request
def load_visitor_fingerprint():
    g.fingerprint = hashlib.md5((request.remote_addr + request.headers.get('User-Agent','')).encode()).hexdigest()

@app.route('/post/<int:post_id>/like/', methods=['POST'])
def post_like(post_id):
    fp = g.fingerprint       # 直接用，不用再算一遍
    ...
```

**为什么用 `g` 而不是全局变量？** 多线程并发时 `g` 自动隔离，全局变量会互相覆盖。

## 2.4 蓝图（Blueprint）：让大项目不变成一坨

### 2.4.1 为什么需要蓝图

博客项目 37 个路由全堆在 `app.py` 里，还能管。但如果做成一个完整 CMS（前台 + 后台 + 用户中心 + API + 管理后台），几百个路由挤一个文件就是灾难。

蓝图是 Flask 官方给的"分模块路由组"：

```python
# admin.py —— 一个独立模块
from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def dashboard():
    return '后台首页'

@admin_bp.route('/posts/')
def posts():
    return '文章管理'
```

```python
# app.py —— 注册蓝图
from admin import admin_bp
app.register_blueprint(admin_bp)
```

现在 `/admin/` 和 `/admin/posts/` 这两个路由归 `admin_bp` 管，但代码写在 `admin.py` 里。

### 2.4.2 蓝图的好处

- **分文件**：`routes/blog.py`、`routes/admin.py`、`routes/api.py` 各管一摊；
- **带前缀**：`url_prefix='/admin'` 让所有蓝图内路由自动加前缀；
- **带静态目录/模板目录**：蓝图可以有自己的 `templates` 文件夹，大型组件化项目常用；
- **可插拔**：不同蓝图可以独立启用/禁用，做插件系统的基础。

### 2.4.3 endpoint 命名：蓝图强制加前缀

蓝图里定义的路由，endpoint 会自动变成 `蓝图名.函数名`：

```python
@admin_bp.route('/posts/')
def posts(): ...
# endpoint 实际是 'admin.posts'

url_for('admin.posts')   # → '/admin/posts/'
url_for('posts')         # ❌ 报错，找不到
```

这是新手用蓝图后最常见的错——`url_for` 里必须带蓝图名。

## 2.5 路由匹配算法（了解即可，调试时有用）

Flask 用 Werkzeug 的路由系统：

1. 启动时把所有 `@app.route` 注册到一个 URL Map；
2. 每个进来的请求，Werkzeug 用 **正则 + 类型转换器** 逐条匹配；
3. 匹配成功就调用对应视图函数，把动态段作为参数传进去；
4. 多个路由都匹配时，按注册顺序取第一个。

**调试技巧**：`app.url_map` 能打印所有路由，排查"405/404 为什么"很好用：

```python
for rule in app.url_map.iter_rules():
    print(rule.rule, '→', rule.endpoint, rule.methods)
```

---

# 第 3 章 安装与版本

## 3.1 标准安装

```bash
# 推荐先建虚拟环境
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装最新稳定版
pip install flask

# 指定版本（博客 requirements.txt 的写法）
pip install flask==3.0.3

# 验证
python -c "import flask; print(flask.__version__)"
```

## 3.2 Flask 自带的"隐形同伴"

`pip install flask` 不会只装 flask，会自动装上一串依赖：

| 包 | 角色 |
|---|---|
| **Werkzeug** | WSGI 工具库（请求/响应对象、调试器、开发服务器） |
| **Jinja2** | 模板引擎 |
| **MarkupSafe** | 转义 HTML 的安全库 |
| **itsdangerous** | 签名（session cookie 加密靠它） |
| **click** | 命令行工具库（flask run 命令靠它） |

所以博客 `requirements.txt` 里写了 Flask、Werkzeug、Jinja2 三个名字，其实装 Flask 时后面两个自动就来了——显式写出是为了锁定版本。

## 3.3 版本选择

- **Flask 2.x**：2021 年发布，引入 async 视图等；
- **Flask 3.x**：2023 年发布，要求 Python 3.8+，推荐新项目用；
- 博客 v2.8.3 用的是 Flask 3.x。

**版本兼容警告**：Flask 2 → 3 之间 `@app.route` 一些细节有变化；博客锁版本是为了打包后行为一致。你在自己电脑装最新版一般没问题，但如果遇到奇怪报错，先 `pip show flask` 看版本。

---

# 第 4 章 API 全面讲解

> 标注：✅ = 博客项目正在用；➕ = 很常用但项目没用到（推荐掌握）；🧪 = 进阶能力（了解即可）。

## 4.1 创建应用：Flask()

```python
from flask import Flask

app = Flask(
    __name__,
    template_folder='templates',       # 模板目录（默认就叫 templates）
    static_folder='static',            # 静态资源目录（css/js/图片）
    static_url_path='/static',         # 静态文件的 URL 前缀
    instance_relative_config=False,   # 是否使用 instance 文件夹
)
```

✅ 博客用法（app.py 第 122 行）：

```python
app = Flask(
    __name__,
    template_folder=str(Config.TEMPLATE_DIR),   # 用 RESOURCE_DIR 拼路径
    static_folder=str(Config.STATIC_DIR),
    static_url_path='/static',
)
app.config.from_object(Config)                   # 从 config.py 读配置
```

**为什么模板目录不写死 `'templates'`？** PyInstaller 打包后，模板在 `_internal/templates` 里，工作目录不是源码目录。用 `Config.RESOURCE_DIR` 拼出来的绝对路径，开发模式和打包后都能找到。

**`__name__` 是什么？** 它是 Python 的"当前模块名"。Flask 用它定位"这个包在哪里"，从而找到默认的 templates/static 目录。传 `__name__` 是标准写法，不用纠结。

## 4.2 路由：@app.route

### 4.2.1 基本写法

```python
@app.route('/post/<int:post_id>/', methods=['GET', 'POST'])
def post_detail(post_id):
    ...
```

### 4.2.2 路径变量和类型转换器

尖括号 `<xxx>` 表示动态段，冒号前是类型转换器：

| 转换器 | 匹配什么 | 例子 | 传入视图函数的类型 |
|---|---|---|---|
| `string`（默认） | 不含斜杠的任意字符 | `<name>` | str |
| `int` | 正整数 | `<int:post_id>` | int |
| `float` | 浮点数 | `<float:score>` | float |
| `path` | 含斜杠的路径 | `<path:filepath>` | str |
| `uuid` | UUID 字符串 | `<uuid:uid>` | UUID 对象 |

✅ 博客用法：文章详情 `/post/<int:post_id>/`；归档 `/archive/<int:year>/<int:month>/`。

### 4.2.3 methods 参数

默认只接受 GET。要处理表单 POST 必须显式声明：

```python
@app.route('/admin/posts/new/', methods=['GET', 'POST'])
def new_post():
    if request.method == 'POST':
        # 处理表单提交
        ...
    # GET：显示表单
    return render_template('new_post.html')
```

博客的登录、发文章、编辑资料都是这个模式：一个路由同时接 GET（显示表单）和 POST（处理提交）。

### 4.2.4 endpoint：路由的别名

Flask 默认用函数名当 endpoint。`url_for('post_detail', post_id=3)` 会反推出 `/post/3/`。

显式起别名：

```python
@app.route('/post/<int:post_id>/', endpoint='view_post')
def some_function_name(post_id):
    ...
url_for('view_post', post_id=3)   # /post/3/
```

**为什么需要 endpoint？** 函数名可能重复（尤其蓝图里），endpoint 是"身份证号"，函数名只是"外号"。

### 4.2.5 重定向与 URL 生成：url_for

```python
from flask import url_for, redirect

@app.route('/login/', methods=['POST'])
def login():
    # 验证成功后
    return redirect(url_for('admin_dashboard'))   # 不写死 '/admin/'，写函数名
```

**为什么不写死网址？** 将来路由改了（比如 `/admin/` 改成 `/dashboard/`），只要 `url_for('admin_dashboard')` 自动跟着改，不用全局搜替换。

## 4.3 读取请求数据：request

`request` 是"当前请求"的全局代理，按场景选不同的属性：

| 写法 | 读什么 | 例子 |
|---|---|---|
| `request.args.get('kw')` | **URL 问号参数** | `/search?kw=python` → `kw='python'` |
| `request.form.get('title')` | **表单 POST 字段** | 发文章表单 |
| `request.files.get('file')` | **上传文件对象** | 上传图片 |
| `request.json` / `request.get_json()` | **JSON 请求体** | AJAX 接口 |
| `request.headers.get('User-Agent')` | 请求头 | 点赞指纹 |
| `request.method` | 请求方法字符串 | `'GET'` / `'POST'` |
| `request.remote_addr` | 访客 IP | 点赞指纹 |
| `request.path` | 请求路径（不含 query string） | `/post/3/` |
| `request.full_path` | 路径 + query string | `/post/3/?page=2` |
| `request.url` | 完整 URL | `http://.../post/3/?page=2` |
| `request.referrer` | 来源页（从哪点过来的） | 统计 |
| `request.cookies.get('name')` | Cookie | 记住登录 |

✅ 博客用法：

- 点赞接口（app.py 第 1185 行）：`g.fingerprint`（IP+UA）做去重；
- 新手向导 API：`request.get_json()` 收 JSON；
- 上传头像：`request.files.get('avatar')`。

### 4.3.1 `.get()` vs `[]`

```python
request.args.get('page')      # 没有 page 参数 → None，不报错
request.args['page']          # 没有 page 参数 → 抛 KeyError
```

**推荐永远用 `.get()`**，然后给默认值：

```python
page = request.args.get('page', 1, type=int)   # 自动转 int，缺省 1
```

`type=int` 会尝试把字符串转 int，失败自动返回默认值——这是 Flask 给的便利。

### 4.3.2 文件上传：request.files

```python
@app.route('/upload/', methods=['POST'])
def upload():
    f = request.files['avatar']
    if f.filename == '':
        return '没选文件', 400
    # 安全做法：用 werkzeug.utils.secure_filename 清洗文件名
    f.save(os.path.join(Config.UPLOAD_DIR, secure_filename(f.filename)))
```

博客的头像上传就是这套，还额外做了 MIME 类型白名单校验（`allowed_avatar`，app.py 第 722 行）。

## 4.4 返回响应

视图函数可以返回多种东西，Flask 自动包装成 Response：

| 返回值 | Flask 的处理 |
|---|---|
| `'hello'` | 200 + text/html |
| `render_template('index.html', **数据)` | 渲染模板后返回 HTML |
| `redirect(url_for('index'))` | 302 跳转 |
| `jsonify({'ok': True})` | 200 + application/json |
| `abort(404)` | 立即抛出 404（交给错误处理器） |
| `(body, status)` | 自定义状态码，如 `('未登录', 401)` |
| `(body, headers)` | 自定义响应头 |
| `Response` 对象本身 | 直接返回 |

### 4.4.1 jsonify：AJAX 接口专用

```python
from flask import jsonify

@app.route('/post/<int:post_id>/like/', methods=['POST'])
def post_like(post_id):
    return jsonify({'ok': True, 'count': 42})
# → HTTP/1.1 200 OK
#   Content-Type: application/json
#   {"ok": true, "count": 42}
```

直接 `return {'ok': True}` 在 Flask 1.x 不行，2.0+ 才支持自动转 JSON。**养成用 `jsonify` 的习惯**，明确意图。

### 4.4.2 自定义状态码

```python
return jsonify({'error': '文章不存在'}), 404
return '未登录', 401
```

AJAX 前端根据状态码判断成功/失败。

### 4.4.3 abort 与错误处理器

```python
from flask import abort

@app.route('/post/<int:post_id>/')
def post_detail(post_id):
    post = Post.query.get(post_id)
    if post is None:
        abort(404)              # 立即中断，跳到错误处理器
    ...

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404   # 返回自定义 404 页
```

✅ 博客有自己的 404/500 模板，用户看到的不是 Flask 默认的英文错误页。

## 4.5 请求钩子：before/after/teardown

### 4.5.1 四种钩子

```python
@app.before_request          # 每个请求进来、进视图前执行
def before():
    pass

@app.after_request           # 视图返回后、响应发给浏览器前执行
def after(response):
    return response           # 必须 return response

@app.teardown_request         # 请求结束后执行（即使没返回也执行）
def teardown(exc):
    pass

@app.teardown_appcontext      # 应用上下文销毁时执行
def teardown_ctx(exc):
    pass
```

### 4.5.2 博客怎么用钩子

- `@app.before_request`（app.py 第 373 行附近）：给静态文件加长缓存头；
- `@app.after_request`：加安全头（X-Frame-Options）、Gzip 压缩；
- `@app.teardown_appcontext`：每次请求结束自动 `db.session.remove()`（防止连接泄漏）。

### 4.5.3 钩子的执行顺序

```
请求进来
  → before_request（按注册顺序）
  → 视图函数
  → after_request（按注册**逆序**，类似栈）
  → 响应发出
  → teardown_request
  → teardown_appcontext
```

记住 after_request 是"后注册先执行"——想加多个中间件时有用。

## 4.6 会话与一次性提示：session / flash

### 4.6.1 SECRET_KEY：必须设置

```python
app.secret_key = '一串随机字符串'   # 或者 app.config['SECRET_KEY'] = '...'
```

session 和 flash 都靠 SECRET_KEY 加密 Cookie。**不设 SECRET_KEY，第一次用 session 就崩**：

```
RuntimeError: The session is unavailable because no secret key was set.
```

✅ 博客做法：config.py 自动生成一个随机 SECRET_KEY，存到 `.session_key` 文件里，下次启动读出来——重启后用户还保持登录状态。

### 4.6.2 session：跨请求保持用户数据

```python
from flask import session

@app.route('/login/', methods=['POST'])
def login():
    if verify(request.form['username'], request.form['password']):
        session['user_id'] = user.id        # 写进 session
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/')
def admin_dashboard():
    if 'user_id' not in session:            # 读 session
        return redirect(url_for('login'))
    ...
```

**原理**：session 数据被序列化 + 加密签名后，存到浏览器的一个 Cookie 里。下次浏览器自动带上这个 Cookie，Flask 解密还原。服务器端不存 session 数据，所以叫"无状态"。

### 4.6.3 flash：一次性提示

```python
from flask import flash

@app.route('/login/', methods=['POST'])
def login():
    if 密码错:
        flash('用户名或密码错误', 'error')
        return redirect(url_for('login'))
    flash('登录成功，欢迎回来', 'success')
    return redirect(url_for('admin_dashboard'))
```

模板里：

```jinja
{% with messages = get_flashed_messages(with_categories=true) %}
  {% for category, msg in messages %}
    <div class="alert alert-{{ category }}">{{ msg }}</div>
  {% endfor %}
{% endwith %}
```

**特点**：flash 的消息**只显示一次**——模板渲染完就从 session 里删掉，刷新页面不再出现。这就是"提交表单后跳转到列表页，顶部弹一行'保存成功'"的经典模式。

## 4.7 context_processor：全局模板变量

每个页面都要用的数据（站点名、导航、当前用户），不必每个路由都 `render_template(..., site_name=...)`：

```python
@app.context_processor
def inject_globals():
    return dict(
        site_name=Config.SITE_NAME,
        current_year=datetime.now().year,
    )
```

之后**任何模板**都能直接用 `{{ site_name }}`，不用传。

✅ 博客用法（app.py 第 843 行 `inject_globals`）：把站点名、导航、分类、未读评论数等注入模板。v2.8.3 还给它加了 5 秒 TTL 缓存，避免每个请求都查数据库。

## 4.8 其他常用 API

### 4.8.1 配置系统

```python
# 从对象加载
app.config.from_object('config.ProductionConfig')

# 从 py 文件加载
app.config.from_pyfile('config.py')

# 从环境变量加载
app.config.from_envvar('BLOG_SETTINGS')

# 手动设置
app.config['SECRET_KEY'] = 'xxx'
```

✅ 博客：`app.config.from_object(Config)`（app.py 第 125 行），Config 是 config.py 里的类。

### 4.8.2 日志

```python
app.logger.info('博客启动在 %s', url)
app.logger.error('同步失败: %s', e)
```

Flask 自带一个标准 logging.Logger，比 `print` 好用——能带级别、时间、写到文件。

### 4.8.3 测试客户端（➕ 写单元测试用）

```python
with app.test_client() as c:
    resp = c.get('/')
    assert resp.status_code == 200
    assert '博客' in resp.get_data(as_text=True)
```

不启动真实服务器就能测路由，CI 跑测试必备。

### 4.8.4 信号（🧪 进阶，了解即可）

```python
from flask import request_started, request_finished

def log_request(sender, **extra):
    app.logger.info('请求: %s', request.path)

request_started.connect(log_request)
```

类似钩子但更松耦合，插件系统常用。博客没用，知道有这回事就行。

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客首页路由（app.py 第 1014 行）

```python
@app.route('/')
@app.route('/page/<int:page>/')
def index(page=1):
    """首页：分页列出已发布文章"""
    per_page = 10
    query = Post.query.filter_by(published=True, deleted=False) \
                      .order_by(Post.created_at.desc())

    # 搜索关键词
    kw = request.args.get('kw', '').strip()
    if kw:
        query = query.filter(
            db.or_(Post.title.contains(kw), Post.body.contains(kw))
        )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('index.html', posts=pagination.items, pagination=pagination)
```

**要点拆解**：

1. **一个函数绑两个路由**：`/` 和 `/page/N/`，分别是第 1 页和第 N 页；
2. **published=True + deleted=False**：软删机制——删除不真删，标记 `deleted=True`；
3. **paginate**：Flask-SQLAlchemy 自带分页，返回一个分页对象，模板里直接生页码；
4. **`db.or_`**：标题或正文含关键词都算命中。

## 5.2 项目内示例：点赞接口（app.py 第 1185 行）

```python
@app.route('/post/<int:post_id>/like/', methods=['POST'])
def post_like(post_id):
    post = Post.query.get_or_404(post_id)
    if not post.published:
        return jsonify({'ok': False, 'error': '文章不可点赞'}), 404

    fp = getattr(g, 'fingerprint', None) or 'unknown'
    existing = Like.query.filter_by(post_id=post_id, fingerprint=fp).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        action = False
    else:
        db.session.add(Like(post_id=post_id, fingerprint=fp))
        db.session.commit()
        action = True

    count = Like.query.filter_by(post_id=post_id).count()
    return jsonify({'ok': True, 'liked': action, 'count': count})
```

**设计决策**：计数用"重新查数据库数一遍"，而不是在 Post 表维护一个 `like_count` 列。数据永远准确，代价是多一次查询（博客数据量小，值得）。

## 5.3 独立示例：一个完整的登录 + 受保护页面

```python
from flask import Flask, request, redirect, url_for, render_template_string, session, flash

app = Flask(__name__)
app.secret_key = 'dev-secret-key-change-me'

LOGIN_FORM = '''
<form method="post">
  <input name="username" placeholder="用户名">
  <input name="password" type="password" placeholder="密码">
  <button>登录</button>
</form>
{% with m = get_flashed_messages() %}{% for x in m %}<p>{{ x }}</p>{% endfor %}{% endwith %}
'''

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == '123456':
            session['user'] = request.form['username']
            flash('登录成功')
            return redirect(url_for('dashboard'))
        flash('用户名或密码错误')
    return render_template_string(LOGIN_FORM)

@app.route('/dashboard/')
def dashboard():
    if 'user' not in session:
        flash('请先登录')
        return redirect(url_for('login'))
    return f'欢迎 {session["user"]}，这是后台'

@app.route('/logout/')
def logout():
    session.pop('user', None)
    flash('已退出')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
```

跑起来访问 `http://127.0.0.1:5000/dashboard/`——会被踢到登录页；用 admin/123456 登录后再访问就能进。这就是所有"登录保护"页面的最小模型。

## 5.4 独立示例：RESTful JSON API

```python
@app.route('/api/posts/')
def api_posts():
    posts = Post.query.filter_by(published=True).order_by(Post.created_at.desc()).all()
    return jsonify([{'id': p.id, 'title': p.title} for p in posts])

@app.route('/api/posts/<int:post_id>/')
def api_post_detail(post_id):
    p = Post.query.get_or_404(post_id)
    return jsonify({'id': p.id, 'title': p.title, 'body': p.body})
```

手机 App、小程序、第三方前端想接博客数据，就走这种 JSON 接口。

---

# 第 6 章 高频坑与排查

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | 视图函数重名 | `AssertionError: View function mapping is overwriting` | 换函数名或加 endpoint |
| 2 | 忘了 methods | 直接打开页面 405 Method Not Allowed | `methods=['GET', 'POST']` |
| 3 | form 取不到值 | 提交后字段全 None | HTML 的 `name` 属性必须和代码字段名一致 |
| 4 | 没设 SECRET_KEY | session/flash 一用就 RuntimeError | `app.secret_key = '随机字符串'` |
| 5 | 生产开 debug | 出错页泄露源码、可被远程执行代码 | 生产用 waitress，永远 `debug=False` |
| 6 | 脚本里用 db | `Working outside of application context` | `with app.app_context():` 包起来 |
| 7 | 两个装饰器叠一个函数 | 路由只最后一个生效 | 每个装饰器单独一行 |
| 8 | `request.form['key']` 字段缺失 | KeyError 500 | 永远用 `.get('key')` 给默认值 |
| 9 | 重定向后刷新重复提交 | 表单重复提交 | POST 处理完 `redirect(url_for(...))`（PRG 模式） |
| 10 | 返回中文乱码 | 页面问号/乱码 | `Content-Type` 加 `charset=utf-8`，模板存成 UTF-8 |
| 11 | 静态文件 404 | CSS/JS 加载不出来 | 检查 `static_folder` 路径、HTML 里 `url_for('static', filename=...)` |
| 12 | 改代码不生效 | Flask 没自动重载 | debug=True 才自动重载；生产模式要手动重启 |
| 13 | 蓝图 url_for 报错 | `Endpoint 'xxx' not found` | url_for 里写 `蓝图名.函数名` |
| 14 | 上传文件名带中文 | 保存失败/乱码 | `secure_filename()` 清洗，或存哈希名 |
| 15 | AJAX 跨域被拦 | 浏览器控制台 CORS 错误 | 装 flask-cors 或同源部署 |
| 16 | session 重启失效 | 用户每次重启要重新登录 | SECRET_KEY 持久化到文件（博客做法） |
| 17 | 后台线程里查数据库报错 | 同坑 6 | 把 app 作为参数传进线程，包 app_context |
| 18 | 循环 import | `ImportError: cannot import name` | 把公共对象抽到 `extensions.py`，用 `init_app` 绑定 |

**排查万能法**：

1. 报错信息里找 `File "xxx.py", line N`，先看是哪个路由、哪一行；
2. 打开 `http://127.0.0.1:5000/console`（debug 模式下），Flask 提供一个交互式 Python 控制台，可以现场查 `app.url_map`、`Post.query.all()`；
3. 实在搞不定，在视图函数第一行写 `import pdb; pdb.set_trace()`，浏览器请求一次就在终端停下，现场 inspect。

---

# 第 7 章 学习路径与自测

## 7.1 推荐学习路径

**第 1 周：跑起来**
- 跟着 5.3 写一个登录小站；
- 读博客 `app.py` 前 200 行（创建 app、配置、路由注册）；
- 目标：能改首页文案、能加一个 `/about/` 页面。

**第 2 周：理解原理**
- 搞懂 WSGI（2.1）和请求-响应循环（2.2）；
- 在博客里找一个 `@app.before_request`、一个 `@app.context_processor`，看懂它做了什么；
- 目标：能给博客加一个"请求耗时统计"中间件。

**第 3 周：上手业务**
- 通读博客所有前台路由（index、post_detail、archive、friend_links）；
- 通读博客所有后台路由（admin_*）；
- 目标：能自己加一个"关于我"页面。

**第 4 周：进阶**
- 学蓝图，把博客的 `/admin/*` 拆到 `admin_routes.py`；
- 学应用工厂 `create_app()`，把 app.py 改造成可测试结构；
- 写几个 `pytest` 测试用 `test_client()`。

## 7.2 自测题（答案在末尾）

1. WSGI 是什么？为什么 Flask 能换服务器？
2. `request.args.get('kw')` 和 `request.form.get('kw')` 分别读哪里的数据？
3. 为什么两个视图函数不能重名？怎么解决？
4. 在后台线程里想查数据库，第一行要写什么？
5. `redirect(url_for('index'))` 做了什么？为什么不直接写网址？
6. debug=True 为什么不能上生产环境？
7. `session` 和 `flash` 的数据存在哪里？为什么需要 SECRET_KEY？
8. `@app.context_processor` 解决什么问题？
9. 蓝图是什么？用蓝图后 `url_for` 有什么变化？
10. POST 处理完为什么要 redirect，而不是直接 return 页面？
11. `g` 对象和普通全局变量有什么区别？
12. `abort(404)` 和 `return '404'` 有什么区别？

## 7.3 答案

1. WSGI 是 Python Web 服务器和应用之间的统一调用约定；双方都遵守它，Flask 就能换 waitress/Werkzeug/gunicorn 等任意 WSGI 服务器。
2. `args` 读 URL 问号后参数（GET）；`form` 读表单 POST 字段。
3. Flask 用函数名当 endpoint 默认值，重名会互相覆盖；换函数名或显式 `endpoint='别名'`。
4. `with app.app_context():`。
5. 返回 302 让浏览器跳到 index 路由对应的 URL；路由改了 URL 自动跟着改，不用全局替换。
6. debug 模式的出错页会泄露完整堆栈和源码，且 Werkzeug 调试器允许在浏览器里执行 Python 代码——生产环境开了等于把服务器送人。
7. 都加密签名后存浏览器 Cookie；SECRET_KEY 用来签名，没有它 Flask 无法验证 Cookie 是不是被篡改过。
8. 把每个模板都要用的公共变量注入上下文，避免每个路由 `render_template` 都重复传。
9. 蓝图是分模块的路由组；蓝图里的 endpoint 自动变成 `蓝图名.函数名`，`url_for` 必须带蓝图前缀。
10. PRG（Post/Redirect/Get）模式：防止用户刷新浏览器时重复提交表单；也让"保存成功"提示只出现一次。
11. `g` 是线程局部的，每个请求/线程独立一份；普通全局变量多线程并发会互相覆盖。
12. `abort(404)` 抛出 HTTPException，立即中断视图并走 `@app.errorhandler(404)`；`return '404'` 只是返回一个 200 状态码的字符串，浏览器不知道这是错误页。

## 7.4 进一步学习

- 官方文档：https://flask.palletsprojects.com/（3.x 版）
- Flask 大型项目结构推荐：https://flask.palletsprojects.com/patterns/packages/
- Flask 生态圈：https://flask.palletsprojects.com/extensions/
- 博客项目本身就是最好的教材——读完本教程后，对照 `app.py` 逐行读一遍，你就入门了。

---

> 下一篇：Jinja2 —— 模板引擎全面教程
