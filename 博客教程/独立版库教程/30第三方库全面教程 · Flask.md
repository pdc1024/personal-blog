# 第三方库全面教程 · Flask（独立版）

> 面向初学者：本教程**独立成篇**，不假设你已懂任何 Web 知识，每个概念第一次出现都用大白话解释。术语第一次出现都有白话解释。
> 适用版本：Flask 3.x ｜ 学习目标：从"完全不懂 Web"到"能独立用 Flask 搭建完整的网站并部署上线"。

---

# 第 1 章 这个库是什么

## 1.1 一句话认识 Flask

Flask 是 Python 世界里最流行的 **Web 微框架**。拆开说：

- **Web 框架**：别人写好的、专门用来"接收浏览器请求 → 处理 → 返回页面/数据"的一套工具。没有它，你要自己用 socket 解析 HTTP 协议（那个过程极其痛苦）。
- **微框架**：核心只做"请求路由 + 响应返回"两件事，数据库、登录、表单校验这些都不内置，要用的时候自己装扩展。好处是轻、灵活、学起来快。

一句话：**Flask 是网站应用的"骨架与指挥中心"**——所有网址（路由）由它登记，所有请求由它接住，所有页面由它调用模板渲染出来。

你不需要懂 HTTP 协议细节，但需要知道两个概念：
- **请求（request）**：浏览器发给服务器的"我要看什么"。
- **响应（response）**：服务器还回去的"这就是你要的内容"。

## 1.2 什么时候用 Flask

- 中小型网站、API 服务、个人项目、教学项目——轻快小巧，几分钟跑起来。
- 想要"自己掌控一切"、按需挑选数据库/登录/表单方案的场景。
- 作为学习 Web 开发的入门框架——概念最少、心智负担最低。

## 1.3 Flask 的生态位

Python Web 三大主流：**Flask**（轻量灵活）、**Django**（全家桶）、**FastAPI**（高性能 API）。三者互补，Flask 是理解其他框架的最佳起点。

---

# 第 2 章 核心概念与原理

## 2.1 WSGI：Flask 与世界对话的"接口标准"

WSGI（读作"威斯忌"，Web Server Gateway Interface）是一个约定：**服务器（如 waitress）把请求交给 Flask 应用，Flask 把响应还给服务器**。因为大家都遵守这个约定，Flask 才能无缝换服务器（开发用内置的，生产用 waitress 或 gunicorn）。

## 2.2 请求-响应循环

一次访问的完整生命周期：

```
浏览器 → HTTP 请求 → Flask 应用
   ① 路由匹配：这个网址对应哪个函数？
   ② 调用视图函数（你的代码，比如查数据库、渲染模板）
   ③ 返回 Response 对象
Flask → HTTP 响应 → 浏览器
```

## 2.3 应用上下文与请求上下文（新手最容易懵的概念）

Flask 内部有两个"看不见的全局变量盒"：

| 上下文 | 装着什么 | 什么时候有效 |
|---|---|---|
| **应用上下文**（app context） | `current_app`（当前应用）、`g`（请求期间的临时存储） | 请求处理期间；**脚本里用 db 必须手动包** `with app.app_context():` |
| **请求上下文**（request context） | `request`（当前请求）、`session`（用户会话） | 每个请求处理期间 |

**为什么需要这个机制？** Flask 是线程并发的——多个请求同时在跑。如果 `request` 是真全局变量，两个请求会互相覆盖。Flask 用"线程局部存储（thread-local）"让每个线程看到自己的 `request`。你只要记住结论：**在视图函数里随便用 `request`；在后台脚本/线程里想用 `db`、`current_app`，先包一层 `with app.app_context():`**。

## 2.4 蓝图（Blueprint）——让大项目不变成一坨

Flask 微框架的"微"是相对的。项目变大了，把所有路由堆在一个文件里很难维护。**蓝图**就是"分文件夹的路由组"：

```python
# admin.py
from flask import Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def dashboard():
    return '后台首页'
```

```python
# app.py 里注册
from admin import admin_bp
app.register_blueprint(admin_bp)   # 所有 /admin/* 路由都归 admin_bp 管
```

蓝图是 Flask 官方推荐的大型项目组织方式——**项目路由超过 20 个就值得拆**。

---

# 第 3 章 安装与版本

```bash
pip install flask        # 装最新稳定版
pip install flask==3.0.3 # 指定版本
python -c "import flask; print(flask.__version__)"  # 验证装没装上
```

Flask 3.x 要求 Python 3.8+。Flask 自带两个"隐形同伴"：**Jinja2**（模板引擎）和 **Werkzeug**（WSGI 工具库）——安装 Flask 会自动带上，这就是为什么 `requirements.txt` 里经常看到三个名字。

---

# 第 4 章 API 全面讲解

> 标注说明：✅ = 最常用必会；➕ = 很常用推荐掌握；🧪 = 进阶能力（了解即可）。

## 4.1 创建应用：Flask()（✅）

```python
from flask import Flask
app = Flask(__name__, 
            template_folder='templates',   # 模板目录（默认就叫 templates）
            static_folder='static')        # 静态资源目录（css/js/图片）
```

**`__name__` 是什么？** 传当前模块名，Flask 靠它定位资源。传 `__name__` 是标准写法，不用纠结。

## 4.2 路由：@app.route（✅）

```python
@app.route('/post/<int:post_id>/', methods=['GET', 'POST'])
def post_detail(post_id):
    ...
```

| 参数 | 作用 |
|---|---|
| 路径字符串 | 支持动态段 `<post_id>`，尖括号里是变量名 |
| `<int:post_id>` | 类型转换器：`int`（整型）、`string`（默认，不含斜杠）、`float`、`path`（含斜杠）、`uuid` |
| `methods` | 允许的请求方法：GET（默认只此一个）、POST、PUT、DELETE、PATCH |
| `endpoint` | 给路由起别名（默认就是函数名），`url_for` 靠它反推网址 |

➕ **注意**：函数名不能重名！两个函数都用 `index` 会报 `AssertionError: View function mapping is overwriting`。

## 4.3 读取请求数据：request（✅）

`request` 是"当前请求"的入口，最常用的读取方式：

| 写法 | 读什么 | 例子 |
|---|---|---|
| `request.args.get('kw')` | **网址问号后面**的参数 | `/search?kw=python` |
| `request.form.get('title')` | **表单 POST** 的字段 | 提交表单 |
| `request.files.get('file')` | 上传的文件对象 | 上传图片 |
| `request.headers.get('User-Agent')` | 请求头 | 统计浏览器 |
| `request.method` | 请求方法（GET/POST） | 判断当前是哪种请求 |
| `request.json` 或 `request.get_json()` | **JSON 请求体** | AJAX 接口 |
| `request.remote_addr` | 访客 IP | 访问日志 |

➕ **坑**：`.get()` 取不到返回 `None` 不会崩；用 `request.form['key']` 取不到会抛 `KeyError`。**表单字段名必须和 HTML 的 `name` 属性一致**——这是新手最常见的"怎么取不到值"。

## 4.4 返回响应（✅）

视图函数可以返回多种东西，Flask 自动帮你包装成 Response：

| 返回 | Flask 的处理 |
|---|---|
| 字符串 `'hello'` | 200 + text/html |
| `render_template('index.html', **数据)` | 渲染模板后返回 |
| `redirect(url_for('index'))` | 302 跳转（配合 `url_for` 反推网址） |
| `abort(404)` | 抛 404 错误（配合 `@app.errorhandler(404)` 显示友好页） |
| `jsonify({...})` | 200 + application/json（AJAX 接口专用） |
| 元组 `(内容, 状态码)` | 自定义状态码 |

## 4.5 请求钩子（before/after_request）（➕）

```python
@app.before_request
def do_before():
    # 每个请求进来先执行这里（权限校验、计数器等）
    pass

@app.after_request
def do_after(resp):
    resp.headers['X-Frame-Options'] = 'SAMEORIGIN'  # 安全头
    return resp
```

**典型用途**：统一加安全头、统计访问量、Gzip 压缩、登录检查。

## 4.6 会话与一次性提示（➕）

```python
from flask import session, flash
app.secret_key = '必须设置！'   # 会话加密密钥，不设 flash/session 全崩

session['user'] = 'admin'       # 写入会话（浏览器存加密 cookie）
flash('保存成功', 'success')    # 存一条一次性提示
```

**SECRET_KEY 是必设项**：它给 session 签名加密。建议用 `secrets.token_hex(32)` 生成并持久化保存（重启不丢，否则用户登录态全部失效）。

## 4.7 全局模板变量：context_processor（➕）

```python
@app.context_processor
def inject_globals():
    return dict(site_name='我的网站', nav_links=[...])
```

把站点名、导航、分类、计数等"每个页面都要用"的数据注入模板——模板里不用每次传。

## 4.8 蓝图、应用工厂（进阶但重要）（🧪）

- **蓝图**：见 2.4，大型项目分模块的标准姿势。
- **应用工厂**：写一个 `create_app()` 函数返回应用实例，测试和多实例部署都用得上：

```python
def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('config.py')
    db.init_app(app)   # 扩展用 init_app 方式绑定
    return app
```

---

# 第 5 章 实战项目案例

## 案例 1（入门级）：30 行写一个"待办事项"小网站

```python
from flask import Flask, request, redirect, url_for, render_template_string

app = Flask(__name__)
app.secret_key = 'dev-key'
todos = []                      # 内存列表当数据库（演示用）

HTML = '''<form method="post"><input name="item"><button>添加</button></form>
<ul>{% for t in todos %}<li>{{ t }} <a href="/del/{{ loop.index0 }}">删</a></li>{% endfor %}</ul>'''

@app.route('/')
def index():
    return render_template_string(HTML, todos=todos)

@app.route('/', methods=['POST'])
def add():
    if request.form.get('item'):
        todos.append(request.form['item'])
    return redirect(url_for('index'))     # 提交后跳回，防止刷新重复提交

@app.route('/del/<int:i>/')
def delete(i):
    if 0 <= i < len(todos):
        todos.pop(i)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)         # debug=True 改代码自动重启（仅开发用！）
```

跑起来：`python 文件名.py`，浏览器开 `http://127.0.0.1:5000`。

## 案例 2（进阶级）：带数据库的留言板（Flask + Flask-SQLAlchemy）

```python
from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///guestbook.db'
app.config['SECRET_KEY'] = 'secret-key'
db = SQLAlchemy(app)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def index():
    messages = Message.query.order_by(Message.created_at.desc()).all()
    return render_template('index.html', messages=messages)

@app.route('/add', methods=['POST'])
def add():
    name = (request.form.get('name') or '').strip()
    content = (request.form.get('content') or '').strip()
    if name and content:                       # 校验：都不能为空
        db.session.add(Message(name=name, content=content))
        db.session.commit()
    return redirect(url_for('index'))

with app.app_context():
    db.create_all()                            # 建表（首次运行）

if __name__ == '__main__':
    app.run(debug=True)
```

配套模板 `templates/index.html`：

```html
<h1>留言板</h1>
<form method="post" action="/add">
  <input name="name" placeholder="昵称" required>
  <textarea name="content" placeholder="留言内容" required></textarea>
  <button>提交</button>
</form>
{% for m in messages %}
  <div><b>{{ m.name }}</b>（{{ m.created_at.strftime('%Y-%m-%d') }}）：{{ m.content }}</div>
{% endfor %}
```

## 案例 3（综合）：**带文件上传和分页的文章系统**

```python
import os
from flask import Flask, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI='sqlite:///posts.db',
    SECRET_KEY='secret-key',
    UPLOAD_FOLDER='static/uploads',      # 上传目录
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # 限制 5MB，防恶意大文件
)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    cover = db.Column(db.String(200), default='')

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)      # 当前页（自动转 int）
    pagination = Post.query.paginate(page=page, per_page=5)   # 每页 5 条
    return render_template('index.html', pagination=pagination)

@app.route('/new', methods=['GET', 'POST'])
def new_post():
    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        body = (request.form.get('body') or '').strip()
        if not title or not body:
            flash('标题和正文不能为空', 'error')
            return redirect(url_for('new_post'))
        cover = ''
        f = request.files.get('cover')
        if f and f.filename:
            filename = secure_filename(f.filename)    # 清理危险文件名
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cover = url_for('static', filename='uploads/' + filename)
        db.session.add(Post(title=title, body=body, cover=cover))
        db.session.commit()
        flash('发布成功', 'success')
        return redirect(url_for('index'))
    return render_template('new.html')

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
```

**要点**：
- `secure_filename` 防止路径穿越攻击（文件名含 `../` 会乱写文件）。
- `MAX_CONTENT_LENGTH` 限制上传体积。
- `pagination` 是 Flask-SQLAlchemy 自带分页对象：`pagination.items` 当前页数据、`pagination.has_prev/has_next` 翻页。

---

# 第 6 章 进阶内容（大神之路）

## 6.1 应用工厂 + 蓝图组织大型项目

```
project/
├── app.py                  ← create_app() 工厂 + 注册蓝图
├── config.py               ← 配置类（开发/生产分开）
├── models.py               ← 所有数据模型
├── blueprints/
│   ├── main.py             ← 首页/关于
│   ├── posts.py            ← 文章增删改查
│   └── admin.py            ← 后台管理
└── templates/ static/
```

## 6.2 REST API：jsonify + 请求方法

```python
@app.route('/api/posts/<int:pid>', methods=['GET', 'PUT', 'DELETE'])
def api_post(pid):
    post = Post.query.get_or_404(pid)
    if request.method == 'GET':
        return jsonify({'id': post.id, 'title': post.title})
    if request.method == 'PUT':
        data = request.get_json()          # 前端发 JSON
        post.title = data.get('title', post.title)
        db.session.commit()
        return jsonify({'ok': True})
    db.session.delete(post)
    db.session.commit()
    return jsonify({'ok': True}), 204
```

## 6.3 自定义错误页

```python
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    db.session.rollback()      # 出错时回滚数据库，防脏数据
    return render_template('500.html'), 500
```

## 6.4 生产部署

```bash
pip install waitress
waitress-serve --host=0.0.0.0 --port=8000 app:app
# 或用 gunicorn（Linux）：
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

**生产三原则**：`debug=False`、用生产级 WSGI 服务器、反向代理加 HTTPS（nginx）。

---

# 第 7 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 函数重名 | `AssertionError: View function mapping is overwriting...` | 换函数名或加 endpoint |
| 只有 POST 方法 | 直接打开页面报 405 | `methods=['GET', 'POST']` |
| form 取不到值 | 提交后字段全 None | 检查 HTML `name` 与代码字段名一致 |
| 没设 SECRET_KEY | session/flash 报错或失效 | 设置 `app.secret_key` |
| 生产环境开 debug | 出错页泄露源码、可被远程执行代码 | 生产用 waitress/gunicorn，永远 `debug=False` |
| 脚本里用 db 报错 | `Working outside of application context` | `with app.app_context():` 包起来 |
| 两个装饰器叠一个函数 | 路由只有最后一个生效 | 每个装饰器一行，函数体在最下 |
| 上传文件名危险 | 文件被写进奇怪路径 | 用 `secure_filename()` |
| 上传大文件报错 | 413 或内存暴涨 | 设 `MAX_CONTENT_LENGTH` |
| 模板变量未定义 | `UndefinedError` | 检查 render_template 传参名与模板变量一致 |

**排查万能法**：报错信息里找 `File "app.py", line XXX`，先看是哪个路由、哪一行，再对着 4.3/4.4 检查 request/response 用法。

---

# 第 8 章 学习路径与自测

**学习路径**（小白到精通）：
1. 照着案例 1 写一个迷你网站（1 天）
2. 模板 Jinja2 语法：循环/判断/继承（1 天）
3. request 全家桶 + 表单（1 天）
4. 数据库 Flask-SQLAlchemy（2 天）
5. 上下文机制 `app.app_context()`（半天）
6. flash/session/消息提示（半天）
7. 蓝图/工厂组织大项目（1 天）
8. 文件上传 + 安全（1 天）
9. REST API（1 天）
10. 生产部署 waitress/gunicorn（1 天）

**自测题**（答案在本章末尾）：

1. `request.form.get('a')` 和 `request.args.get('a')` 分别读哪里的数据？
2. 为什么两个视图函数不能重名？怎么解决？
3. 在后台线程里想查数据库，第一行要写什么？
4. `redirect(url_for('index'))` 做了什么？为什么不直接写网址？
5. debug=True 为什么不能上生产环境？
6. SECRET_KEY 是干什么的？不设会怎样？
7. 蓝图解决了什么问题？
8. 上传文件为什么要 `secure_filename`？
9. 怎么限制上传文件大小？
10. 综合：描述"表单提交 → 校验 → 存库 → flash 提示 → 重定向"的完整链路。

**答案**：
1. form 读表单 POST 字段；args 读网址问号参数。
2. Flask 用函数名当路由默认别名，重名会覆盖 → 换函数名或给 endpoint 起别名。
3. `with app.app_context():`。
4. 302 跳转到 index 路由对应的网址——路由改了网址也不用改代码。
5. 出错页会泄露堆栈和源码，且 debug 模式可能被远程执行代码。
6. 给 session 加密签名，防止伪造。不设 session/flash 全崩。
7. 把路由按模块分组，大项目不堆成一个大文件。
8. 防止路径穿越攻击（`../` 等危险字符把文件写到目录外）。
9. `app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024`。
10. 案例 3 链路：`request.form.get` → 非空校验 → `db.session.add + commit` → `flash` → `redirect(url_for(...))`。

---

> 下一篇：《Jinja2（独立版）》——模板引擎从零到精通。
