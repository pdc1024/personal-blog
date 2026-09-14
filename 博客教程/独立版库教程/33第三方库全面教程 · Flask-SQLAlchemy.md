# 第三方库全面教程 · Flask-SQLAlchemy（独立版）

> 面向初学者：本教程**独立成篇**，假设你会基础 Python 和 Flask（不会可先看《Flask》教程）。术语第一次出现都有白话解释。
> 适用版本：Flask-SQLAlchemy 3.1 ｜ 配套知识：与《Flask》《SQLite》配合。
> 学习目标：从"不会写数据库代码"到"能用 ORM 完成增删改查、表关联、分页查询，并理解 SQLAlchemy 核心机制"。

---

# 第 1 章 这个库是什么

## 1.1 一句话认识 Flask-SQLAlchemy

**Flask-SQLAlchemy** 是 Flask 官方推荐的**数据库 ORM 扩展**。ORM（对象关系映射）的意思是：**把数据库表当成 Python 类，把表的每一行当成类的实例，把 SQL 语句变成 Python 方法调用**。

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydb.db"
db = SQLAlchemy(app)

class User(db.Model):                    # 表 users
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, default=18)
```

## 1.2 为什么用 ORM 而不是直接写 SQL

| | 直接写 SQL | ORM（SQLAlchemy） |
|---|---|---|
| 增删改查 | 手写 SQL 字符串 | `db.session.add(user)` |
| 防注入 | 自己注意占位符 | 自动参数化，天然防注入 |
| 换数据库 | 改所有 SQL | 只改连接串（SQLite→MySQL 一行搞定） |
| 对象化 | 拿到的是一行行元组 | 拿到的是 Python 对象（user.name） |

## 1.3 核心组成

- **`db.Model`**：模型基类（继承它 = 定义一个表）。
- **`db.Column`**：定义字段（列）。
- **`db.session`**：会话——所有写操作的"工作台"，`add`（加入）→ `commit`（提交）→ 真正生效。
- **`db.relationship`**：定义表之间的关系（一对多/多对多）。

---

# 第 2 章 核心概念与原理

## 2.1 模型（Model）= 表

```python
class User(db.Model):
    __tablename__ = "users"     # 表名（不写默认按类名转换）
    id = db.Column(db.Integer, primary_key=True)
```

**字段类型**：

| db.Column 类型 | 对应 SQL 类型 | 用途 |
|---|---|---|
| `Integer` | INTEGER | 整数 |
| `String(n)` | VARCHAR(n) | 短文本（必须给长度） |
| `Text` | TEXT | 长文本 |
| `Boolean` | BOOLEAN | 真/假 |
| `DateTime` | DATETIME | 时间 |
| `Float` | FLOAT | 小数 |
| `LargeBinary` | BLOB | 二进制（文件） |

**字段约束（Column 参数）**：

| 参数 | 作用 |
|---|---|
| `primary_key=True` | 主键（唯一标识） |
| `nullable=False` | 不允许为空 |
| `default=值` | 默认值（Python 侧生效） |
| `server_default=...` | 数据库侧默认值 |
| `unique=True` | 唯一约束 |
| `index=True` | 加索引（查询快） |
| `autoincrement=True` | 自增（主键默认） |

## 2.2 会话（session）：事务的载体

**事务（transaction）** 是一组"要么全成功、要么全失败"的数据库操作：

```python
db.session.add(u1)          # ① 加入会话（还没写库）
db.session.add(u2)
db.session.commit()         # ② 提交：真正写库（失败则全部回滚）
```

**白话**：session 是"草稿纸"，commit 是"誊写进数据库"。不 commit 一切白搭；commit 失败会自动回滚（不产生半截数据）。

## 2.3 一对多关系

```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    posts = db.relationship("Post", backref="author")   # 反向引用

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # 外键
```

- **ForeignKey**：指向另一张表的主键（user_id 存的是 User 的 id）。
- **relationship**：Python 侧的关系（`user.posts` 拿到该用户所有文章）。
- **backref**：反向引用（`post.author` 拿到作者对象）。

---

# 第 3 章 安装与版本

```bash
pip install flask-sqlalchemy
```

- 当前稳定版 3.1。
- 会自动安装 Flask 和 SQLAlchemy 2.x。
- 支持数据库：SQLite（零配置）、MySQL、PostgreSQL（换连接串即可）。

**连接串格式**：

```python
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydb.db"        # SQLite（相对路径）
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////绝对/路径/db.db" # SQLite 绝对路径
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://用户:密码@主机/库名"
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://用户:密码@主机/库名"
```

---

# 第 4 章 API 全面讲解

> 标注：✅ = 必会；➕ = 推荐；🧪 = 进阶

## 4.1 初始化与建表（✅）

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydb.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False   # 关闭警告
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

# 建表：必须在应用上下文里执行
with app.app_context():
    db.create_all()     # 已存在则跳过；只在首次运行需要
```

**⚠️ 关键**：`db.create_all()` 必须在 `with app.app_context():` 里（脚本/命令行场景）；**它只建新表，不改已有表结构**（改字段用迁移工具 Alembic，见第 6 章）。

## 4.2 增（Create）（✅）

```python
# 方式一：构造对象 + add + commit
user = User(name="张三")
db.session.add(user)
db.session.commit()

# 方式二：一次提交多个
db.session.add_all([User(name="李四"), User(name="王五")])
db.session.commit()

# 方式三：提交后立刻拿 id
db.session.add(user)
db.session.commit()
print(user.id)      # 提交后自增主键已回填
```

## 4.3 查（Read）（✅ 重点）

```python
# 全部
User.query.all()

# 按主键
User.query.get(1)              # SQLAlchemy 2.0 推荐：db.session.get(User, 1)
User.query.get_or_404(1)       # Flask 扩展：查不到抛 404（视图里用）

# 过滤
User.query.filter_by(name="张三").all()          # 等值（简写）
User.query.filter(User.age > 18).all()          # 条件（>=、<、<=、!=）
User.query.filter(User.name.like("%张%")).all() # 模糊
User.query.filter(User.name.in_(["张三", "李四"])).all()

# 排序
User.query.order_by(User.age.desc()).all()      # 倒序
User.query.order_by(User.age.asc()).all()

# 限量/偏移（分页）
User.query.limit(10).all()                      # 前 10 条
User.query.offset(20).limit(10).all()           # 跳过 20 取 10（第 3 页）

# 计数
User.query.count()
User.query.filter(User.age > 18).count()

# 取第一个/唯一
User.query.first()
User.query.filter_by(name="张三").first()
User.query.filter_by(name="张三").one()         # 必须有且只有一条，否则报错
```

## 4.4 改（Update）（✅）

```python
user = User.query.get(1)
user.name = "新名字"        # 改属性
db.session.commit()         # 提交生效

# 批量更新
User.query.filter(User.age < 18).update({"age": 18})
db.session.commit()
```

## 4.5 删（Delete）（✅）

```python
user = User.query.get(1)
db.session.delete(user)
db.session.commit()

# 批量删
User.query.filter(User.age > 100).delete()
db.session.commit()
```

## 4.6 关系查询（✅ 一对多）

```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    posts = db.relationship("Post", backref="author", lazy="dynamic")

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

# 正向：user.posts
user = User.query.get(1)
for p in user.posts:
    print(p.title)

# 反向：post.author
post = Post.query.get(1)
print(post.author.name)
```

**lazy 参数**：
- `lazy="select"`（默认）：访问时才查（懒加载）。
- `lazy="dynamic"`：返回查询对象，可以继续链式过滤（`user.posts.filter_by(...)`）。
- `lazy="joined"`：查主表时 JOIN 一起查（快，但可能冗余）。

**级联删除**：

```python
posts = db.relationship("Post", backref="author", cascade="all, delete-orphan")
# 删 user 时自动删它的 posts（delete-orphan：从关系移除也删）
```

## 4.7 分页 paginate（✅ Flask 专用福利）

```python
page = request.args.get("page", 1, type=int)     # 当前页
pagination = User.query.paginate(page=page, per_page=10, error_out=False)

pagination.items          # 当前页数据
pagination.page           # 当前页码
pagination.pages          # 总页数
pagination.total          # 总条数
pagination.has_prev       # 有没有上一页
pagination.has_next       # 有没有下一页
pagination.prev_num       # 上一页页码
pagination.next_num       # 下一页页码
```

## 4.8 多对多关系（🧪）

```python
# 中间表（join table）：只存两个外键
tags = db.Table("post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("post.id")),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id")),
)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30))
    posts = db.relationship("Post", secondary=tags, backref="tags")
```

## 4.9 原生 SQL 与事务控制（🧪）

```python
# 直接跑 SQL
result = db.session.execute(db.text("SELECT * FROM user WHERE age > :a"), {"a": 18})

# 手动事务
try:
    db.session.add(user)
    db.session.commit()
except Exception:
    db.session.rollback()     # 出错回滚，防脏数据
    raise
```

---

# 第 5 章 实战项目案例

## 案例 1（入门级）：文章与评论（完整增删改查）

```python
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blog.db"
db = SQLAlchemy(app)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=db.func.now())
    comments = db.relationship("Comment", backref="post",
                               cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)

@app.route("/api/posts", methods=["GET"])
def list_posts():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return jsonify([{"id": p.id, "title": p.title} for p in posts])

@app.route("/api/posts", methods=["POST"])
def create_post():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "标题不能为空"}), 400
    post = Post(title=title, body=data.get("body", ""))
    db.session.add(post)
    db.session.commit()
    return jsonify({"id": post.id}), 201

@app.route("/api/posts/<int:pid>", methods=["DELETE"])
def delete_post(pid):
    post = db.session.get(Post, pid)
    if not post:
        return jsonify({"error": "不存在"}), 404
    db.session.delete(post)          # 级联删除评论（cascade）
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/api/posts/<int:pid>/comments", methods=["POST"])
def add_comment(pid):
    post = db.session.get(Post, pid)
    if not post:
        return jsonify({"error": "不存在"}), 404
    content = ((request.get_json() or {}).get("content") or "").strip()
    if not content:
        return jsonify({"error": "评论不能为空"}), 400
    db.session.add(Comment(post_id=pid, content=content))
    db.session.commit()
    return jsonify({"ok": True}), 201

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
```

## 案例 2（进阶级）：带分页和搜索的列表页

```python
@app.route("/api/posts")
def api_posts():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    kw = (request.args.get("kw") or "").strip()

    q = Post.query
    if kw:
        q = q.filter(Post.title.like(f"%{kw}%"))     # 模糊搜索
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "items": [{"id": p.id, "title": p.title} for p in pagination.items],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "has_next": pagination.has_next,
    })
```

## 案例 3（综合）：**用户 + 文章 + 评论 + 标签（四表关系项目）**

```python
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///social.db"
db = SQLAlchemy(app)

# 中间表：文章-标签 多对多
post_tags = db.Table("post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("post.id")),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id")),
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    posts = db.relationship("Post", backref="author", cascade="all, delete-orphan")

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tags = db.relationship("Tag", secondary=post_tags, backref="posts")
    comments = db.relationship("Comment", backref="post", cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)

@app.route("/api/posts/<int:pid>")
def post_detail(pid):
    post = db.session.get(Post, pid)
    if not post:
        return jsonify({"error": "不存在"}), 404
    return jsonify({
        "id": post.id,
        "title": post.title,
        "author": post.author.name,                    # 反向引用
        "tags": [t.name for t in post.tags],           # 多对多
        "comments": [c.content for c in post.comments],  # 一对多
        "comment_count": len(post.comments),
    })

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
```

**本案例覆盖**：一对多（用户→文章、文章→评论）、多对多（文章↔标签）、级联删除、反向引用——**这是关系型数据库建模的完整图谱**。

---

# 第 6 章 进阶内容（大神之路）

## 6.1 数据库迁移（Alembic）：改表结构的正规军

`db.create_all()` 不能改已有表结构。生产项目用 Flask-Migrate（基于 Alembic）：

```bash
pip install flask-migrate
```

```python
from flask_migrate import Migrate
migrate = Migrate(app, db)
```

```bash
flask db init          # 初始化迁移目录
flask db migrate -m "加字段"   # 生成迁移脚本（改 models 后跑）
flask db upgrade       # 应用迁移
flask db downgrade     # 回滚
```

## 6.2 连接池与性能配置

```python
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 10,              # 连接池大小
    "pool_recycle": 3600,         # 连接 1 小时回收（防 MySQL 断连）
    "pool_pre_ping": True,        # 取连接前 ping（连接断了自动重连）
}
```

## 6.3 查询优化：eager loading

```python
# N+1 问题：循环里每篇文章都触发一次评论查询
for post in posts:                # 1 次
    post.comments                 # N 次！性能杀手

# 解决：joinedload 一次性 JOIN 查出
from sqlalchemy.orm import joinedload
posts = Post.query.options(joinedload(Post.comments)).all()
```

## 6.4 与纯 SQLAlchemy 2.0 的关系

Flask-SQLAlchemy 3.x 基于 SQLAlchemy 2.x。2.0 的新写法：`db.session.execute(db.select(User).where(...))`。老式 `User.query` 是 Flask 扩展保留的简写——**两者都可用，Flask 项目用 `User.query` 更顺手**。

---

# 第 7 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 忘 commit | 数据没存进去 | 写操作后必须 `db.session.commit()` |
| 表没建出来 | `no such table` | `with app.app_context(): db.create_all()` |
| 改字段不生效 | 新列不存在 | create_all 不改表；用 Flask-Migrate |
| Working outside of application context | 脚本里用 db 报错 | `with app.app_context():` 包起来 |
| 字符串长度超限 | 报错/截断 | String(n) 的 n 要给够 |
| 忘记 nullable=False | 空数据入库 | 必填字段加 `nullable=False` |
| 外键类型不匹配 | IntegrityError | 外键列类型必须和主键一致（Integer↔Integer） |
| 删了主表子表残留 | 孤儿数据 | relationship 加 `cascade="all, delete-orphan"` |
| 循环里查询巨慢 | 页面卡 | joinedload 预加载关系 |
| 并发写冲突 | OperationalError: database is locked | SQLite 加 `timeout=30`；或换 MySQL/PostgreSQL |
| 密码/敏感字段明文 | 泄露风险 | 配合《Werkzeug》密码哈希 |

---

# 第 8 章 学习路径与自测

**学习路径**：
1. 模型定义 + create_all（半天）
2. 增删改查四件套（1 天）
3. filter/filter_by/排序/limit（1 天）
4. 一对多关系 + backref（1 天）
5. 分页 paginate（半天）
6. 多对多 + 中间表（1 天）
7. 级联删除 + lazy（半天）
8. 案例 1→3 手写（2 天）
9. Alembic 迁移（1 天）
10. 性能优化（joinedload/连接池）（1 天）

**自测题**：
1. `db.session.add` 和 `db.session.commit` 各干什么？只 add 不 commit 会怎样？
2. `filter_by(name="a")` 和 `filter(User.name == "a")` 区别？
3. 视图里按主键查不到要直接 404，用什么？
4. `db.create_all()` 能改已有表结构吗？正规做法是什么？
5. 一对多关系里 `ForeignKey` 和 `relationship` 分别干什么？
6. `backref="author"` 是干什么的？
7. 级联删除怎么配？为什么需要？
8. 分页对象有哪些常用属性？
9. N+1 问题是什么？怎么解决？
10. 综合：设计"用户-文章-评论-标签"四表模型并写出关系。

**答案提示**：
1. add 加入会话（草稿）；commit 提交（真正写库）。只 add 不 commit 数据不落库。
2. filter_by 只支持等值简写；filter 支持任意条件表达式。
3. `Post.query.get_or_404(pid)`（或 `db.get_or_404(Post, pid)`）。
4. 不能，只建新表；用 Flask-Migrate（Alembic）。
5. ForeignKey 是数据库外键（存 id）；relationship 是 Python 侧关系（对象导航）。
6. 反向引用：`post.author` 直接拿到作者对象。
7. `relationship(..., cascade="all, delete-orphan")`；防止删主表留孤儿数据。
8. items/page/pages/total/has_prev/has_next/prev_num/next_num。
9. 循环里每行触发一次额外查询；用 `joinedload` 预加载。
10. 参考案例 3：User 1→N Post、Post 1→N Comment、Post N→N Tag（post_tags 中间表）。

---

> 下一篇：《SQLite（独立版）》——轻量数据库从零到精通。
