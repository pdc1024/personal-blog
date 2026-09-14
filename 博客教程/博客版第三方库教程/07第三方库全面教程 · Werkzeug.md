# 第三方库全面教程 · Werkzeug

> 面向初学者：Werkzeug 是 Flask 的"隐形引擎"，你几乎不直接写它，但它一直在背后干活。学完这份教程，你不仅能明白 Flask 的底层原理，还能直接用它解决密码哈希、上传安全等实际问题。
> 适用版本：Werkzeug 3.x ｜ 博客项目：`app.py` 里 `from werkzeug.utils import secure_filename`

---

# 第 1 章 这个库是什么

Werkzeug（德语，"工具"的意思）是 Flask 的**底层工具库**。Flask 处理请求时，真正干粗活的其实是它：

- 解析 HTTP 请求（把乱七八糟的原始请求变成好用的 `request` 对象）
- 匹配路由（判断 `/post/3/` 该交给哪个函数）
- 构造 HTTP 响应
- 提供一堆安全工具（文件名消毒、密码哈希）

一句话：**Flask 是前台，Werkzeug 是后台机房**。博客项目直接用到它的地方只有 `secure_filename()`，但它的能力远不止这个。

---

# 第 2 章 核心概念与原理

## 2.1 WSGI：Werkzeug 的老本行

Werkzeug 最初就是给 Python 写 WSGI 工具而生的。**WSGI** 是"服务器 ↔ 应用"之间的接口约定（Flask 教程讲过）。Werkzeug 实现了这个约定的完整工具链：

```
waitress（服务器）
  ↓ 原始 HTTP 字节流
Werkzeug 的 Request 类解析 → request.args/form/files 都从这来
  ↓ 你的视图函数处理
Werkzeug 的 Response 类包装 → 变成合法 HTTP 响应
  ↓
还给 waitress
```

**这就是为什么 Flask 说 "依赖 Werkzeug"**——没有 Werkzeug，Flask 自己连请求都读不了。

## 2.2 安全两件套：文件名消毒 + 密码哈希

Werkzeug 提供两个"一学就会、一用就安全"的工具，是所有 Web 项目的必备：

1. **`secure_filename()`**：把用户上传的文件名里的危险字符（`..`、`/`、`\`、控制字符）清理掉，**防止路径穿越攻击**——攻击者用 `../../etc/passwd` 当文件名，就可能把文件写到服务器任意位置。
2. **`generate_password_hash()` / `check_password_hash()`**：给密码做"加盐哈希"存储。存的是不可逆的哈希串（而不是明文），登录时只比对哈希。**每个用户密码自动加随机盐**，同一密码两次哈希结果不同，防彩虹表破解。

## 2.3 线程局部存储（Local / LocalProxy）

Flask 的 `request` 之所以"每个请求各看各的"，靠的是 Werkzeug 的 **Local**（线程局部）和 **LocalProxy**（延迟代理）。你不需要会用它们，但要知道：**Flask 的全局 `request` 不是普通全局变量**——这解释了为什么后台线程里要包 `app.app_context()`。

---

# 第 3 章 安装与版本

```bash
pip install werkzeug
pip show werkzeug   # 版本验证
```

安装 Flask 时自动带上。Werkzeug 3.x 要求 Python 3.8+。

---

# 第 4 章 API 全面讲解

## 4.1 上传安全：secure_filename（✅ 项目用到）

```python
from werkzeug.utils import secure_filename

name = secure_filename('我的 头像.png')
# 结果类似：'wo_de_tou_xiang_png' —— 中文/空格被转成下划线

# 博客的写法（防同名覆盖）：
save_name = str(int(time.time())) + '_' + secure_filename(file.filename)
```

**特点**：把非 ASCII 字符转成下划线（中文会丢）、去掉危险路径符号。**注意**：它会把中文文件名"洗掉"，如果你要保留原名，得自己写规则（比如 base64 编码原名）。

配套三连（上传文件的完整安全流程）：

```python
file = request.files.get('file')     # 1. 拿到上传文件
if not file or not file.filename:
    return '没选文件'
safe = secure_filename(file.filename)  # 2. 消毒文件名
file.save(os.path.join(UPLOAD_DIR, safe))  # 3. 保存（路径必须用 os.path.join 拼！）
```

## 4.2 密码哈希：生成与校验（➕ 强烈推荐掌握）

```python
from werkzeug.security import generate_password_hash, check_password_hash

# 注册时：只存哈希，不存明文
hashed = generate_password_hash('mypassword123')
# 结果形如：scrypt:32768:8:1$...（包含算法、盐和哈希，看不出原密码）

# 登录时：比对
if check_password_hash(hashed, 'mypassword123'):
    print('密码正确')
else:
    print('密码错误')
```

**为什么重要？** 数据库泄露时，明文密码会被拿去撞库（用户常一个密码到处用）。存哈希后攻击者拿到也只是乱码。博客项目因为移除了登录功能没用它，但**任何带账号的 Python Web 项目都应该用这两个函数**。

## 4.3 Request / Response 对象（了解）

```python
from werkzeug.wrappers import Request, Response

# Flask 里的 request 就是 Request 类的实例（增强版）
request.args      # 问号参数（MultiDict，见 4.4）
request.form      # 表单数据
request.files     # 上传文件
request.headers   # 请求头
request.cookies   # 浏览器 cookie
request.json      # JSON 请求体

# Response：status_code、headers、set_cookie() 等
resp = Response('hello', status=200)
resp.set_cookie('theme', 'dark', max_age=3600)   # 给浏览器写 cookie
```

## 4.4 MultiDict：一个键可以多个值的神奇字典

Werkzeug 的 `request.args` / `request.form` 不是普通 dict，而是 **MultiDict**——**同一个键可以存多个值**（比如多选下拉框）。

```python
request.args.get('tag')        # 取第一个
request.args.getlist('tag')    # 取全部 → ['python', 'flask']
```

**坑**：普通 dict 的 `request.args['key']` 取不到会抛 KeyError；`.get()` 返回 None。多选字段务必用 `getlist()`。

## 4.5 路由系统：Map / Rule（了解原理）

Flask 的路由匹配底层是 Werkzeug 的 `Map` + `Rule`：

```python
from werkzeug.routing import Map, Rule

url_map = Map([
    Rule('/', endpoint='index'),
    Rule('/post/<int:post_id>/', endpoint='post_detail'),
])
match = url_map.bind('127.0.0.1')
endpoint, args = match.match('/post/3/')
print(endpoint, args)   # post_detail {'post_id': 3}
```

理解这个原理后，你就明白 `<int:post_id>` 的转换器是谁实现的了——Werkzeug 的路由规则。

## 4.6 其他常用工具（🧪 了解）

| 工具 | 作用 |
|---|---|
| `werkzeug.utils.cached_property` | 属性只算一次并缓存（性能优化） |
| `werkzeug.local.LocalProxy` | 延迟代理（Flask 的 current_app 就是它） |
| `werkzeug.exceptions.HTTPException` | 所有 HTTP 异常的基类（404/500 都是它） |
| `werkzeug.middleware.proxy_fix.ProxyFix` | 处理反向代理（nginx 后面时修正来源 IP） |
| `werkzeug.serving.run_simple()` | Werkzeug 自带开发服务器（Flask app.run 的底层） |

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客背景图上传的安全保存（对照真实代码）

```python
from werkzeug.utils import secure_filename

bg_file = request.files.get('bg_image_file')
if bg_file and bg_file.filename:
    # ① 消毒 + 取后缀：secure_filename 防路径穿越，rsplit 拿到扩展名
    ext = secure_filename(bg_file.filename).rsplit('.', 1)[-1].lower()
    if ext in ALLOWED_BG_EXT:                 # ② 白名单校验扩展名
        # ③ 新文件名 = 前缀 + 时间戳 + 消毒后的原名（防重名，可读性好）
        save_name = f"bg_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(bg_file.filename)}"
        bg_file.save(os.path.join(BG_IMAGE_FOLDER, save_name))   # ④ os.path.join 拼路径
        profile.bg_image = f"/bg/{save_name}" # ⑤ 数据库只存相对网址，文件在 uploads/bg/
```

**逐行要点**：
- `secure_filename` 之后还**再取一次扩展名**并白名单校验——防"伪装图片的脚本文件"
- 时间戳前缀解决"同名覆盖"和"缓存不刷新"两个问题
- `os.path.join` 拼路径而不是字符串 `+`——防路径穿越的第二道保险
- 数据库存 `/bg/文件名` 相对网址，不存绝对路径——迁移机器不用改数据

## 5.2 独立示例：给博客加一个"密码保护"接口（完整可跑）

```python
from flask import Flask, request, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'change-me'

# 首次启动生成管理员密码哈希（正式项目存数据库）
ADMIN_HASH = generate_password_hash('admin123')

@app.route('/api/login', methods=['POST'])
def login():
    pw = (request.form.get('password') or '').strip()
    if check_password_hash(ADMIN_HASH, pw):    # 只比哈希，明文不落地
        session['admin'] = True
        return jsonify(ok=True)
    return jsonify(ok=False, msg='密码错误'), 403

@app.route('/api/logout')
def logout():
    session.pop('admin', None)
    return jsonify(ok=True)

if __name__ == '__main__':
    app.run(debug=True)
```

---

# 第 6 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 中文文件名被洗掉 | 上传后文件名变成一串下划线 | 安全设计；要保原名需自定义规则 |
| 不消毒直接拼路径 | 攻击者可上传 `../../evil` 覆盖任意文件 | 必须 `secure_filename` + `os.path.join` |
| 文件保存后 0 字节 | 先读了 `file.read()` 再 `save()` | 保存前 `file.seek(0)` 倒回指针 |
| 多选字段只取到一个 | `request.form.get('tag')` 返回第一个 | 用 `getlist('tag')` |
| 明文存密码 | 数据库泄露 = 密码泄露 | `generate_password_hash` 存储 |
| 忘记检查空文件名 | `secure_filename('')` 返回空串，路径变成目录 | 空结果兜底文件名 |

---

# 第 7 章 学习路径与自测

**学习路径**：先掌握 `secure_filename` 上传三连（半天）→ 学会密码哈希两件套（半天）→ 了解 Request/Response 和 MultiDict（1 天）→ 读一次 Flask 源码里怎么调 Werkzeug（可选进阶）。

**自测题**：

1. `secure_filename('../../etc/passwd')` 会发生什么？为什么安全？
2. 密码为什么要存哈希不存明文？"加盐"是什么？
3. 多选表单字段在 Flask 里怎么取？
4. 文件保存前读了内容导致 0 字节，怎么修？
5. 上传文件的全套安全步骤是哪三步？

**答案**：
1. 返回 `etc_passwd` 之类安全名，`..` 和斜杠被清掉——路径穿越失效。
2. 数据库泄露时明文可被撞库；加盐=每个密码混入随机串再哈希，同一密码结果不同，防彩虹表。
3. `request.form.getlist('字段名')`。
4. 保存前 `file.seek(0)` 把指针倒回开头。
5. 消毒文件名（secure_filename）→ 拼绝对路径（os.path.join）→ save。

---

> 下一篇：Flask-SQLAlchemy —— 数据库 ORM 全面教程
