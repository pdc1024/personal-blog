# 第三方库全面教程 · Flask-SQLAlchemy

> 面向初学者：这是博客项目里"数据层"的主角——6 张业务表的增删改查全靠它。学完这份教程，你能全面掌控 SQLAlchemy 的核心机制（ORM、Session、级联、迁移），而不只是会 `query.get_or_404`。
> 适用版本：Flask-SQLAlchemy 3.x（底层 SQLAlchemy 2.x）｜ 博客项目：`app.py` 数据模型 + `init_db`

---

# 第 1 章 这个库是什么

Flask-SQLAlchemy 是 **SQLAlchemy**（Python 最强数据库工具库）在 Flask 里的"官方适配版"，让你用**写 Python 类的方式操作数据库**。

核心概念先记两个：

- **ORM（对象关系映射）**：把"数据库表"映射成"Python 类"，把"一行数据"映射成"一个对象"，把"增删改查"变成 `db.session.add(...)`。你不用写 SQL 语句（当然也支持写）。
- **SQLAlchemy**：ORM 的引擎本体；Flask-SQLAlchemy 只是帮你把 SQLAlchemy 和 Flask 的应用上下文/配置接起来。

一句话：**Flask-SQLAlchemy 是博客的"记忆管家"**——文章、评论、点赞、友链全部通过它存取。

---

# 第 2 章 核心概念与原理

## 2.1 一条数据的完整旅程（Session 工作单元模式）

```
Python 代码创建对象（post = Post(title='你好')）
  ↓
db.session.add(post)      ← 加入"待办清单"（还没写数据库！）
  ↓
db.session.commit()       ← 一次性把所有待办写进数据库（事务提交）
  ↓
数据库真的有了这一行
```

**核心认知：`add()` 只是排队，`commit()` 才真正落库。** 忘了 commit，重启数据就丢了——这是新手第一坑。

Session（会话）是这个模式的"工作区"：它跟踪你所有 add/delete 的对象，commit 时统一写入，失败时可以 `rollback()` 全部撤回（像"全部撤销"按钮）。

## 2.2 查询为何用 query

```python
Post.query.filter_by(published=True).order_by(Post.created_at.desc()).all()
```

`Post.query` 是这个模型的"查询入口"。SQLAlchemy 把链式调用翻译成 SQL：

```sql
SELECT * FROM post WHERE published = 1 ORDER BY created_at DESC
```

**懒执行（Lazy Evaluation）**：写查询语句时数据库**什么都没干**，直到你调用 `.all()` / `.first()` 这些"终结方法"才真正执行。所以查询对象可以到处传、随时改。

## 2.3 关系（relationship）与级联（cascade）

博客里"文章 ↔ 评论"是一对多关系（对照真实模型）：

```python
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'),
                        index=True, nullable=False)   # 外键：评论属于哪篇文章
    # 在 Comment 侧用 backref 反向建 Post.comments 属性
    post = db.relationship('Post',
        backref=db.backref('comments', lazy='dynamic', cascade='all, delete-orphan'))
```

- `db.ForeignKey('post.id')`：数据库层面声明"评论属于文章"
- `cascade='all, delete-orphan'`：ORM 层面"删文章时，它名下的评论一起删"
- **`backref='comments'`**：自动给 Post 加一个 `post.comments` 属性（反查评论）
- **`lazy='dynamic'`**：`post.comments` 不是直接列表，而是一个"查询对象"，还能继续 `.filter_by(...).count()`——列表页统计评论数用它，省内存

**为什么删文章要显式按顺序删？** 项目里实际用的方案是：先删点赞 → 再删评论 → 最后删文章。如果模型关系/级联配置不全，直接删文章会撞上外键约束报 `NOT NULL constraint failed: comment.post_id`。

## 2.4 多对多（博客的标签就是典型）

文章 ↔ 标签是多对多，需要一个**中间表**：

```python
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True))

class Post(db.Model):
    tags = db.relationship('Tag', secondary=post_tags, backref='posts')
```

`secondary=post_tags` 告诉 ORM"通过中间表关联"。`post.tags` 拿到这篇文章的所有标签。

---

# 第 3 章 安装与版本

```bash
pip install flask-sqlalchemy
pip show flask-sqlalchemy   # 版本验证
```

Flask-SQLAlchemy 3.x 对应 SQLAlchemy 2.x，要求 Python 3.8+。

配置连接（博客 config.py 的做法）：

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///D:/blog_pkg/blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False   # 关掉浪费内存的修改追踪
db = SQLAlchemy(app)
```

**SQLite 连接串**：`sqlite:///绝对路径/blog.db`（三个斜杠 + 绝对路径）。博客还配了 `connect_args={'check_same_thread': False, 'timeout': 30}`——多线程必需，写锁等待 30 秒。

---

# 第 4 章 API 全面讲解

## 4.1 定义模型（建表）

```python
class Post(db.Model):
    __tablename__ = 'post'                          # 表名（不写则默认类名小写）
    id = db.Column(db.Integer, primary_key=True)    # 主键
    title = db.Column(db.String(200), nullable=False)  # 必填字符串
    content = db.Column(db.Text, default='')        # 长文本
    published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    view_count = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), default='')
    tags = db.relationship('Tag', secondary=post_tags, backref='posts')
```

**列类型速查**：

| 类型 | 存什么 | 博客里 |
|---|---|---|
| `Integer` | 整数 | id、like_count |
| `String(长度)` | 短文本 | 标题、用户名 |
| `Text` | 长文本 | 文章正文 |
| `Boolean` | 真/假 | published |
| `DateTime` | 时间 | created_at |
| `Float` | 小数 | （未来评分功能） |

**列约束**：`primary_key`（主键）、`nullable=False`（必填）、`default=值`（默认值）、`unique=True`（唯一）。

## 4.2 写入：add / commit / delete

```python
# 新增
post = Post(title='新文章', content='...')
db.session.add(post)      # 排队
db.session.commit()       # 落库！post.id 此刻才有值

# 修改（找到对象 → 改属性 → commit）
post.title = '改个标题'
db.session.commit()

# 删除
db.session.delete(post)
db.session.commit()

# 出错回滚
try:
    db.session.commit()
except Exception:
    db.session.rollback()   # 撤销本次所有未提交改动
    raise
```

## 4.3 查询全家桶（✅ 博客大量使用）

| 方法 | 作用 | 例子 |
|---|---|---|
| `.get(id)` | 按主键查，没有返回 None | `Post.query.get(3)` |
| `.get_or_404(id)` | 按主键查，没有直接 404 | `Post.query.get_or_404(post_id)` |
| `.first()` / `.all()` | 取第一条 / 取全部 | 终结方法，触发真正查询 |
| `.filter_by(字段=值)` | 等值过滤（简单） | `filter_by(published=True)` |
| `.filter(条件)` | 灵活条件 | `filter(Post.title.ilike('%python%'))` |
| `.order_by(字段.desc())` | 排序 | `order_by(Post.created_at.desc())` |
| `.limit(n)` | 取前 n 条 | `.limit(5)` |
| `.count()` | 计数 | `Post.query.filter_by(published=True).count()` |
| `.paginate(page, per_page)` | 分页（返回对象含 .items/.pages） | 首页分页 |
| `.ilike('%xx%')` | 模糊搜索（不区分大小写） | 博客搜索 |

**链式组合**：

```python
posts = (Post.query
         .filter_by(published=True)
         .order_by(Post.created_at.desc())
         .limit(10)
         .all())
```

## 4.4 关系查询与预加载（进阶）

```python
post = Post.query.get(1)
post.comments          # 懒加载：第一次访问才查评论（N+1 问题源头）

# 预加载：一次查询把评论一起取出来（避免 N+1 查询爆炸）
from sqlalchemy.orm import joinedload
posts = Post.query.options(joinedload(Post.comments)).all()
```

**N+1 问题**：循环 100 篇文章、每篇访问一次 `post.comments` = 1 次主查询 + 100 次子查询。数据量大时明显变慢，`joinedload` 一次 JOIN 解决。

## 4.5 建表与轻量迁移（✅ 博客 init_db）

```python
db.create_all()    # 按模型建表（只建不存在的表，不修改旧表！）

# 旧表加新列 → 用 ALTER TABLE（create_all 不干这事）
from sqlalchemy import inspect, text
inspector = inspect(db.engine)
if 'category' not in [c['name'] for c in inspector.get_columns('post')]:
    db.session.execute(text("ALTER TABLE post ADD COLUMN category VARCHAR(50) DEFAULT ''"))
    db.session.commit()
```

**为什么叫"轻量迁移"？** 项目用"查列名→缺了就 ALTER 补"的幂等方式（跑多少次都安全）。正式大项目会用 Alembic 做版本化迁移，博客规模用不上。

---

# 第 5 章 实战示例

## 5.1 项目内示例：首页文章的完整查询

```python
page = request.args.get('page', 1, type=int)      # 页码参数，默认第 1 页
query = Post.query.filter_by(published=True)
# 关键词搜索
kw = (request.args.get('kw') or '').strip()
if kw:
    query = query.filter(db.or_(
        Post.title.ilike(f'%{kw}%'),
        Post.content.ilike(f'%{kw}%'),
        Post.summary.ilike(f'%{kw}%'),
    ))
# 排序 + 分页
pagination = query.order_by(Post.created_at.desc()).paginate(
    page=page, per_page=10, error_out=False)
posts = pagination.items
```

**要点**：`db.or_` 把多个条件 OR 起来；`paginate(error_out=False)` 页码超界时不报错返回空页。

## 5.2 独立示例：评论+文章的一对多完整演示

```python
# 假设模型已定义（Post ↔ Comment，cascade='all, delete-orphan'）
# 1. 写一篇文章并加两条评论
post = Post(title='SQLAlchemy 入门')
db.session.add(post)
db.session.flush()                       # 先拿到 post.id（不 commit 也能拿到）
db.session.add(Comment(content='好文！', post_id=post.id))
db.session.add(Comment(content='收藏了', post_id=post.id))
db.session.commit()

# 2. 通过关系取评论
post = Post.query.filter_by(title='SQLAlchemy 入门').first()
print([c.content for c in post.comments])   # ['好文！', '收藏了']

# 3. 删文章 → 评论自动级联删除
db.session.delete(post)
db.session.commit()
print(Comment.query.count())   # 0 —— 评论跟着没了
```

---

# 第 6 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 忘 commit | 数据没保存，重启就丢 | add 后一定 commit；批量操作统一提交 |
| 级联没配好删文章 | `NOT NULL constraint failed: comment.post_id` | 显式顺序删：先点赞→评论→文章，或配好 cascade |
| 脚本里用 db | `Working outside of application context` | `with app.app_context():` 包住 |
| 数据库被锁 | `database is locked` | 连接串加 `timeout=30`；别开两个实例 |
| 加列后报错 | `no such column: post.category` | `create_all` 不改旧表 → 用 ALTER 补列 |
| 改了模型没生效 | 表结构还是旧的 | 已有表要迁移，或删掉 blog.db 重建（数据会没！） |
| 查询半天不返回 | 忘了写终结方法（.all()/.first()） | 链式查询末尾必须有终结方法才执行 |

---

# 第 7 章 学习路径与自测

**学习路径**：先写一个"文章-评论"模型跑通增删改查（1 天）→ 吃透 add/commit/rollback 生命周期（半天）→ 学查询链和分页（1 天）→ 学关系/级联/多对多（1 天）→ 进阶预加载和迁移（1 天）。

**自测题**：

1. `db.session.add(post)` 之后、`commit()` 之前，数据库里有这条数据吗？
2. `create_all()` 能修改已有表吗？加新列该怎么办？
3. `post.comments` 第一次访问时发生了什么？什么叫 N+1 问题？
4. 删文章报 `comment.post_id` NOT NULL 错误，最可能是什么原因？
5. `filter_by(published=True)` 和 `filter(Post.published == True)` 的区别？

**答案**：
1. 没有，add 只是排队，commit 才落库。
2. 不能，只建新表；已有表加列用 ALTER TABLE（或迁移工具）。
3. 触发一次"查这篇文章评论"的 SQL；循环访问关系属性产生 1+N 次查询就是 N+1 问题，用 joinedload 预加载解决。
4. 评论的外键关系/级联没配好，或删除顺序不对——显式先删点赞→评论→文章。
5. 前者是简写、只能等值；后者支持任意表达式（大于、模糊、or_ 组合）。

---

> 下一篇：SQLite —— 数据库本体全面教程
