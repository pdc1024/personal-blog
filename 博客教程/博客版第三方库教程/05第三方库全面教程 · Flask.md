# 第三方库全面教程 · Flask

> 面向初学者：不假设你已懂任何 Web 知识，每个概念第一次出现都用大白话解释。学完这份教程，你能全面掌控 Flask，而不只是会博客项目里那几招。
> 适用版本：Flask 3.x ｜ 博客项目：`D:\blog_pkg\app.py`

---

# 第 1 章 这个库是什么

Flask 是 Python 世界里最流行的 **Web 微框架**。拆开说：

- **Web 框架**：别人写好的、专门用来"接收浏览器请求 → 处理 → 返回页面/数据"的一套工具。没有它，你要自己用 socket 解析 HTTP 协议（那个过程极其痛苦）。
- **微框架**：核心只做"请求路由 + 响应返回"两件事，数据库、登录、表单校验这些都不内置，要用的时候自己装扩展。好处是轻、灵活、学起来快。

一句话：**Flask 是博客项目的"骨架与指挥中心"**——所有网址（路由）由它登记，所有请求由它接住，所有页面由它调用模板渲染出来。

你不需要懂 HTTP 协议细节，但需要知道一个概念：**请求（request）** 是浏览器发给服务器的"我要看什么"，**响应（response）** 是服务器还回去的"这就是你要的内容"。

---

# 第 2 章 核心概念与原理

## 2.1 WSGI：Flask 与世界对话的"接口标准"

WSGI（读作"威斯忌"，Web Server Gateway Interface）是一个约定：**服务器（如 waitress）把请求交给 Flask 应用，Flask 把响应还给服务器**。因为大家都遵守这个约定，Flask 才能无缝换服务器（开发用内置的，生产用 waitress）。

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

**为什么需要这个机制？** Flask 是线程并发的——多个请求同时在跑。如果 `request` 是真全局变量，两个请求会互相覆盖。Flask 用"线程局部存储（thread-local）"让每个线程看到自己的 `request`。你只要记住结论：**在视图函数里随便用 `request`；在后台脚本/线程里想用 `db`、`current_app`，先包一层 `with app.app_context():`**。博客的周期同步线程就是这么做的。

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

博客项目规模适中（37 个路由）没拆蓝图，但你要知道这个机制——这是 Flask 官方推荐的大型项目组织方式。

---

# 第 3 章 安装与版本

```bash
pip install flask        # 装最新稳定版
pip install flask==3.0.3 # 指定版本
python -c "import flask; print(flask.__version__)"  # 验证装没装上
```

Flask 3.x 要求 Python 3.8+。Flask 自带两个"隐形同伴"：**Jinja2**（模板引擎）和 **Werkzeug**（WSGI 工具库）——安装 Flask 会自动带上，这就是为什么博客的 `requirements.txt` 里写了三个名字。

---

# 第 4 章 API 全面讲解

> 标注说明：✅ = 博客项目正在用；➕ = 很常用但项目没用到（推荐掌握）；🧪 = 进阶能力（了解即可）。

## 4.1 创建应用：Flask()

```python
from flask import Flask
app = Flask(__name__, 
            template_folder='templates',   # 模板目录（默认就叫 templates）
            static_folder='static')        # 静态资源目录（css/js/图片）
```

✅ 博客用法：`Flask(__name__, template_folder=..., static_folder=...)`，目录用 `Config.RESOURCE_DIR` 拼出来——因为打包后资源在 `_internal` 里，不能写死相对路径。

**`__name__` 是什么？** 传当前模块名，Flask 靠它定位资源。传 `__name__` 是标准写法，不用纠结。

## 4.2 路由：@app.route

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

✅ 博客用法：文章详情 `/post/<int:post_id>/`；点赞接口 `methods=['POST']`。

➕ **注意**：函数名不能重名！两个函数都用 `index` 会报 `AssertionError: View function mapping is overwriting`。

## 4.3 读取请求数据：request

`request` 是"当前请求"的入口，最常用的读取方式：

| 写法 | 读什么 | 例子 |
|---|---|---|
| `request.args.get('kw')` | **网址问号后面**的参数 | `/search?kw=python` |
| `request.form.get('title')` | **表单 POST** 的字段 | 发文章的表单 |
| `request.files.get('file')` | 上传的文件对象 | 上传图片 |
| `request.headers.get('User-Agent')` | 请求头 | 点赞指纹的一部分 |
| `request.method` | 请求方法（GET/POST） | 判断当前是哪种请求 |
| `request.json` 或 `request.get_json()` | **JSON 请求体** | AJAX 接口（博客的新手向导 API） |
| `request.remote_addr` | 访客 IP | 点赞指纹 |

✅ 博客用法：点赞指纹 = IP + User-Agent；新手向导 4 个 JSON API 用 `request.get_json()`。

➕ **坑**：`.get()` 取不到返回 `None` 不会崩；用 `request.form['key']` 取不到会抛 `KeyError`。**表单字段名必须和 HTML 的 `name` 属性一致**——这是新手最常见的"怎么取不到值"。

## 4.4 返回响应

视图函数可以返回多种东西，Flask 自动帮你包装成 Response：

| 返回 | Flask 的处理 |
|---|---|
| 字符串 `'hello'` | 200 + text/html |
| `render_template('index.html', **数据)` | 渲染模板后返回 |
| `redirect(url_for('index'))` | 302 跳转（配合 `url_for` 反推网址） |
| `abort(404)` | 抛 404 错误（配合 `@app.errorhandler(404)` 显示友好页） |
| `jsonify({...})` | 200 + application/json（AJAX 接口专用） |
| 元组 `(内容, 状态码)` | 自定义状态码 |

✅ 博客用法：`jsonify` 给点赞接口返回 JSON；`render_template` 渲染所有页面。

## 4.5 请求钩子（before/after_request）

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

🧪 博客的 Gzip 压缩中间件（`after_request` 里判断是否压缩）就是这种思路。

## 4.6 会话与一次性提示

```python
from flask import session, flash
app.secret_key = '必须设置！'   # 会话加密密钥，不设 flash/session 全崩

session['user'] = 'admin'       # 写入会话（浏览器存加密 cookie）
flash('保存成功', 'success')    # 存一条一次性提示
```

✅ 博客用法：config.py 自动生成并持久化 `SECRET_KEY`（重启不丢，否则 session 的加密签名每次重启都失效，flash 提示等功能会受影响）。

## 4.7 全局模板变量：context_processor

```python
@app.context_processor
def inject_globals():
    return dict(site_name='我的博客', nav_links=[...])
```

✅ 博客用法：把站点名、导航、分类、评论数等"每个页面都要用"的数据注入模板——模板里不用每次传。

## 4.8 蓝图、应用工厂（进阶但重要）

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

# 第 5 章 实战示例

## 5.1 项目内示例：一个完整路由长什么样

博客 `app.py` 的点赞接口浓缩了 request + jsonify + 数据库三件事（对照真实逻辑）：

```python
@app.route('/post/<int:post_id>/like/', methods=['POST'])
def post_like(post_id):
    post = Post.query.get_or_404(post_id)
    if not post.published:
        return jsonify({'ok': False, 'error': '文章不可点赞'}), 404

    fp = like_fingerprint()     # 访客指纹 = IP + User-Agent 哈希（见工具函数）
    existing = Like.query.filter_by(post_id=post_id, fingerprint=fp).first()
    if existing:                # 点过了 → 取消
        db.session.delete(existing)
        db.session.commit()
        count = Like.query.filter_by(post_id=post_id).count()   # 重新数
        return jsonify({'ok': True, 'liked': False, 'count': count})
    like = Like(post_id=post_id, fingerprint=fp)
    db.session.add(like)        # 没点过 → 新增
    db.session.commit()
    count = Like.query.filter_by(post_id=post_id).count()
    return jsonify({'ok': True, 'liked': True, 'count': count})
```

**要点**：计数用"重新查数据库数一遍"而不是维护一个计数器列——数据永远准确，代价是多一次查询（博客数据量小，完全值得）。

## 5.2 独立示例：30 行写一个"待办事项"小网站

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

---

# 第 6 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 函数重名 | `AssertionError: View function mapping is overwriting...` | 换函数名或加 endpoint |
| 只有 POST 方法 | 直接打开页面报 405 | `methods=['GET', 'POST']` |
| form 取不到值 | 提交后字段全 None | 检查 HTML `name` 与代码字段名一致 |
| 没设 SECRET_KEY | session/flash 报错或失效 | 设置 `app.secret_key` |
| 生产环境开 debug | 出错页泄露源码、可被远程执行代码 | 生产用 waitress，永远 `debug=False` |
| 脚本里用 db 报错 | `Working outside of application context` | `with app.app_context():` 包起来 |
| 两个装饰器叠一个函数 | 路由只有最后一个生效 | 每个装饰器一行，函数体在最下 |

**排查万能法**：报错信息里找 `File "app.py", line XXX`，先看是哪个路由、哪一行，再对着 4.3/4.4 检查 request/response 用法。

---

# 第 7 章 学习路径与自测

**学习路径**：先照着 5.2 写一个迷你网站（1 天）→ 精读博客 app.py 的前台路由（2 天）→ 理解上下文机制（半天）→ 学蓝图/工厂组织大项目（1 天）。

**自测题**（答案在本章末尾）：

1. `request.form.get('a')` 和 `request.args.get('a')` 分别读哪里的数据？
2. 为什么两个视图函数不能重名？怎么解决？
3. 在后台线程里想查数据库，第一行要写什么？
4. `redirect(url_for('index'))` 做了什么？为什么不直接写网址？
5. debug=True 为什么不能上生产环境？

**答案**：
1. form 读表单 POST 字段；args 读网址问号参数。
2. Flask 用函数名当路由默认别名，重名会覆盖 → 换函数名或给 endpoint 起别名。
3. `with app.app_context():`。
4. 302 跳转到 index 路由对应的网址——路由改了网址也不用改代码。
5. 出错页会泄露堆栈和源码，且 debug 模式可能被远程执行代码。

---

> 下一篇：Jinja2 —— 模板引擎全面教程
