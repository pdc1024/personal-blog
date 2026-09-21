# 第三方库全面教程 · Flask-SQLAlchemy

> 面向初学者到进阶者：博客 6 张业务表的增删改查全靠它。
> 学完这份教程，你将掌握 ORM 模型定义、Session 工作单元、查询链、关系与级联、
> 预加载、分页、轻量迁移、原生 SQL、N+1 问题，并能对照博客 `app.py` 数据模型逐行读懂。
>
> 适用版本：Flask-SQLAlchemy 3.x（底层 SQLAlchemy 2.x）｜ 博客项目：`app.py` 第 437~608 行模型 + 第 2248 行 init_db
> 学习路线：ORM 概念（第 1~2 章）→ 模型与增删改查（第 3~4 章）→ 关系与进阶（第 5~6 章）→ 项目实战（第 7 章）→ API 与排坑（第 8~9 章）

---

# 第 1 章 认识 ORM

## 1.1 什么是 ORM

ORM（Object-Relational Mapping，对象关系映射）把数据库表映射成 Python 类，把一行数据映射成一个对象，把 SQL 变成方法调用：

```python
# 原生 SQL
db.execute("INSERT INTO post (title, content) VALUES (?, ?)", ('你好', '...'))

# ORM
post = Post(title='你好', content='...')
db.session.add(post)
db.session.commit()
```

一句话：**Flask-SQLAlchemy 是博客的记忆管家**——文章、评论、点赞、友链都通过它存取。

## 1.2 为什么用 ORM

| 对比 | 裸 SQL | ORM |
|---|---|---|
| CRUD | 写 SQL | 写 Python 对象 |
| 改字段名 | 全局搜替换 | 改类属性 |
| SQL 注入 | 手动参数化 | 自动 |
| 换数据库 | 方言要改 | 几乎不改 |
| 调试 | 直接看 SQL | 要开 echo |

## 1.3 Flask-SQLAlchemy 和 SQLAlchemy

- **SQLAlchemy**：Python 最成熟的 ORM，独立于 Flask；
- **Flask-SQLAlchemy**：Flask 集成层，把 SQLAlchemy 的 Session、引擎和 Flask 请求生命周期接起来。

请求结束自动 `db.session.remove()`，不用你手动关。

---

# 第 2 章 Session 工作单元模式

## 2.1 add / flush / commit

```
post = Post(title='你好')        # Python 对象，数据库里还没有
db.session.add(post)             # 加入"待办清单"
# 此时 post.id 还是 None
db.session.flush()               # SQL 发给数据库，但不提交事务
# 此时 post.id 有了
db.session.commit()              # 提交事务，数据落盘
```

**核心**：
- `add()` 只是排队；
- `flush()` 执行 SQL 但不提交（能拿到自增 ID）；
- `commit()` = flush + 提交；
- 出错 `rollback()` 全部撤销。

## 2.2 Session 是什么

Session 是一个"工作区"，跟踪当前会话里所有 add/modify/delete 的对象。commit 时统一写库，失败时整体回滚。

Flask-SQLAlchemy 把 Session 和请求绑定：每个请求一个 Session，请求结束自动 remove。

## 2.3 懒查询（Lazy Evaluation）

```python
q = Post.query.filter_by(published=True)
# 此时数据库什么都没干

if kw:
    q = q.filter(Post.title.contains(kw))   # 还没执行

posts = q.all()   # 这里才真正查
```

查询对象是"待执行"的，可以继续加条件，直到调用终结方法才执行。

**终结方法**：`all()`、`first()`、`get(id)`、`count()`、`one()`、`paginate()`。

---

# 第 3 章 定义模型

## 3.1 一个完整模型

```python
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Post(db.Model):
    __tablename__ = 'post'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    slug = db.Column(db.String(200), unique=True)
    content = db.Column(db.Text, default='')
    rendered_html = db.Column(db.Text, default='')
    summary = db.Column(db.String(300), default='')
    published = db.Column(db.Boolean, default=True, index=True)
    deleted = db.Column(db.Boolean, default=False, index=True)
    view_count = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), default='', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                            onupdate=datetime.utcnow)
```

**逐列讲**：

- `__tablename__`：表名；不写则用类名小写；
- `primary_key=True`：主键，自增；
- `nullable=False`：NOT NULL 约束；
- `index=True`：建索引；
- `unique=True`：唯一；
- `default=datetime.utcnow`：默认值（传函数，不是调用结果！）；
- `onupdate=datetime.utcnow`：行被 UPDATE 时自动更新。

## 3.2 列类型速查

| 类型 | SQL 类型 | 博客里 |
|---|---|---|
| `Integer` | INTEGER | id, view_count |
| `String(n)` | VARCHAR(n) | title, category |
| `Text` | TEXT | content, rendered_html |
| `Boolean` | BOOLEAN | published, deleted |
| `DateTime` | DATETIME | created_at |
| `Float` | REAL | （评分功能预留） |
| `LargeBinary` | BLOB | （图片二进制，博客用文件） |

## 3.3 博客的 6 张表

| 模型 | 表 | 作用 |
|---|---|---|
| `Post` | post | 文章 |
| `Tag` | tag | 标签 |
| `post_tags`（中间表） | post_tags | 文章-标签多对多 |
| `Comment` | comment | 评论 |
| `Like` | like | 点赞 |
| `Profile` | profile | 站点设置 |
| `FriendLink` | friend_link | 友链 |

## 3.4 配置连接

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///D:/blog_pkg/blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'check_same_thread': False, 'timeout': 30},
}
db.init_app(app)
```

`SQLALCHEMY_TRACK_MODIFICATIONS=False`：关掉 SQLAlchemy 对每个对象修改的追踪信号，省内存。

---

# 第 4 章 增删改查

## 4.1 新增

```python
post = Post(title='新文章', content='...')
db.session.add(post)
db.session.commit()
# post.id 此刻才有值
```

批量：

```python
db.session.add_all([Post(title=f'文章{i}') for i in range(10)])
db.session.commit()
```

## 4.2 查询

```python
# 主键
Post.query.get(3)             # 没有返回 None
Post.query.get_or_404(3)       # 没有 404

# 条件
Post.query.filter_by(published=True).all()
Post.query.filter(Post.published == True).all()

# 排序
Post.query.order_by(Post.created_at.desc()).all()

# 限制
Post.query.limit(10).all()

# 计数
Post.query.filter_by(published=True).count()

# 模糊
Post.query.filter(Post.title.ilike('%python%')).all()
```

## 4.3 链式组合

```python
query = Post.query.filter_by(published=True, deleted=False)
query = query.order_by(Post.created_at.desc())
pagination = query.paginate(page=1, per_page=10, error_out=False)
```

## 4.4 修改

```python
post = Post.query.get(3)
post.title = '新标题'
db.session.commit()
```

批量 UPDATE：

```python
Post.query.filter_by(category='tech').update({Post.category: '编程'})
db.session.commit()
```

## 4.5 删除

```python
post = Post.query.get(3)
db.session.delete(post)
db.session.commit()
```

## 4.6 异常处理

```python
try:
    db.session.commit()
except Exception:
    db.session.rollback()
    raise
```

**关键**：commit 失败后必须 rollback，否则 Session 进入坏状态，后续查询全报错。

## 4.7 分页

```python
pagination = Post.query.paginate(page=1, per_page=10, error_out=False)

pagination.items       # 当前页对象列表
pagination.page       # 当前页
pagination.pages      # 总页数
pagination.total      # 总条数
pagination.has_prev   # 有上一页
pagination.has_next    # 有下一页
pagination.iter_pages()  # 页码列表（带 None 表示省略）
```

---

# 第 5 章 关系与级联

## 5.1 一对多：文章 ↔ 评论

```python
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'),
                        index=True, nullable=False)
    content = db.Column(db.Text)
    post = db.relationship(
        'Post',
        backref=db.backref('comments', lazy='dynamic',
                           cascade='all, delete-orphan')
    )
```

- `db.ForeignKey('post.id')`：数据库外键；
- `db.relationship('Post')`：ORM 导航；
- `backref`：自动给 Post 加 `post.comments`；
- `lazy='dynamic'`：`post.comments` 是查询对象，可继续 filter/count；
- `cascade='all, delete-orphan'`：删文章时评论一起删。

## 5.2 多对多：文章 ↔ 标签

```python
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True))

class Post(db.Model):
    tags = db.relationship('Tag', secondary=post_tags, backref='posts')
```

## 5.3 lazy 的五种值

| 值 | 行为 |
|---|---|
| `select` | 第一次访问时 SELECT |
| `dynamic` | 返回查询对象 |
| `joined` | JOIN 一起取 |
| `subquery` | 子查询一起取 |
| `noload` | 永不加载 |

## 5.4 N+1 问题与预加载

```python
posts = Post.query.limit(10).all()
for p in posts:
    print(p.comments.count())   # 每篇一次查询
# 1 + 10 = 11 次
```

**预加载解决**：

```python
from sqlalchemy.orm import joinedload, selectinload

# JOIN 一次取出
posts = Post.query.options(joinedload(Post.comments)).all()

# 或第二条 SQL IN 查询（适合多对多）
posts = Post.query.options(selectinload(Post.tags)).all()
```

## 5.5 软删除

博客不真删行，加 `deleted` 标记：

```python
post.deleted = True
db.session.commit()

# 永远过滤
Post.query.filter_by(deleted=False).all()
```

好处：可恢复、同步好做。代价：所有查询都要带 `deleted=False`。

---

# 第 6 章 进阶：迁移、原生 SQL、索引

## 6.1 create_all 与轻量迁移

```python
db.create_all()    # 只建不存在的表，不改旧表
db.drop_all()      # 危险
```

**给旧表加列**（博客 init_db 的做法）：

```python
from sqlalchemy import inspect, text

inspector = inspect(db.engine)
cols = [c['name'] for c in inspector.get_columns('post')]
if 'category' not in cols:
    db.session.execute(text(
        "ALTER TABLE post ADD COLUMN category VARCHAR(50) DEFAULT ''"
    ))
    db.session.commit()
```

正式项目用 Alembic 做版本化迁移（`flask db migrate` / `flask db upgrade`）。

## 6.2 原生 SQL

```python
result = db.session.execute(text("SELECT * FROM post WHERE id = :id"),
                            {'id': 3})
for row in result:
    print(row.title)

db.session.execute(text("UPDATE post SET view_count = view_count + 1 WHERE id = :id"),
                   {'id': post_id})
db.session.commit()
```

**永远用 `:参数` 占位符**，不要字符串拼接。

## 6.3 索引

```python
title = db.Column(db.String(200), index=True)

# 复合索引
db.Index('idx_post_cat_pub', 'category', 'published')
```

博客在 `published`、`category`、`post_id` 上都建了索引。

## 6.4 打印 SQL 调试

```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

---

# 第 7 章 项目实战

## 7.1 博客 Post 模型（app.py 第 437~460 行）

```python
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True)
    content = db.Column(db.Text, default='')
    rendered_html = db.Column(db.Text, default='')
    summary = db.Column(db.String(300), default='')
    published = db.Column(db.Boolean, default=True, index=True)
    deleted = db.Column(db.Boolean, default=False, index=True)
    view_count = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), default='', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                            onupdate=datetime.utcnow)
```

## 7.2 首页查询（app.py 第 1014 行）

```python
query = Post.query.filter_by(published=True, deleted=False)
if kw:
    query = query.filter(or_(
        Post.title.ilike(f'%{kw}%'),
        Post.content.ilike(f'%{kw}%'),
        Post.summary.ilike(f'%{kw}%'),
    ))
pagination = query.order_by(Post.created_at.desc()).paginate(
    page=page, per_page=10, error_out=False)
```

## 7.3 点赞切换（app.py 第 1185 行）

```python
existing = Like.query.filter_by(post_id=post_id, fingerprint=fp).first()
if existing:
    db.session.delete(existing)
else:
    db.session.add(Like(post_id=post_id, fingerprint=fp))
db.session.commit()
count = Like.query.filter_by(post_id=post_id).count()
```

## 7.4 删除文章（app.py 第 1635 行）

```python
Like.query.filter_by(post_id=post_id).delete()
Comment.query.filter_by(post_id=post_id).delete()
db.session.delete(post)
db.session.commit()
```

**为什么手动删点赞/评论？** 虽然模型配了 cascade，但 SQLite 外键默认不启用（要 PRAGMA foreign_keys=ON），显式删更稳妥。

---

# 第 8 章 API 速查与排坑

## 8.1 高频坑（14 条）

| # | 坑 | 解决 |
|---|---|---|
| 1 | 忘 commit | add 后一定 commit |
| 2 | Working outside of context | with app.app_context() |
| 3 | database is locked | timeout=30、WAL |
| 4 | create_all 不改旧表 | ALTER 补列 |
| 5 | 改模型没生效 | 删 db 重建或迁移 |
| 6 | N+1 慢 | joinedload/selectinload |
| 7 | 字符串拼接 SQL | :参数占位符 |
| 8 | default=[] | 用 default=list |
| 9 | commit 后 id 是 None | 先 flush |
| 10 | SQLite 多线程 | check_same_thread=False |
| 11 | rollback 后还报错 | try/except 里 rollback |
| 12 | filter_by 写错字段 | filter_by 用关键字；filter 用表达式 |
| 13 | 忘记终结方法 | 末尾 .all()/.first() |
| 14 | 软删除漏过滤 | 所有查询带 deleted=False |

---

# 第 9 章 学习路径与自测

## 9.1 学习路径

- 第 1~2 天：模型 + CRUD；
- 第 3~4 天：查询链 + 分页；
- 第 5~7 天：关系 + 级联；
- 第 2 周：预加载 + 迁移 + 原生 SQL。

## 9.2 自测题

1. `add()` 后、`commit()` 前，数据库里有这条数据吗？
2. `create_all()` 能修改旧表吗？
3. flush 和 commit 区别？
4. N+1 是什么？怎么解决？
5. `filter_by` 和 `filter` 区别？
6. 为什么 `default=[]` 是错的？
7. 怎么打印 SQLAlchemy 生成的 SQL？
8. joinedload 和 selectinload 区别？
9. 删文章为什么要先删点赞和评论？
10. 软删除有什么代价？

## 9.3 答案

1. 没有，add 只是排队。
2. 不能，只建新表。
3. flush 发 SQL 不提交；commit 提交事务。
4. 循环访问关系产生 1+N 次查询；预加载。
5. filter_by 用关键字；filter 用表达式。
6. 所有新行共享同一个列表；用 default=list。
7. 打开 sqlalchemy.engine 的 INFO 日志。
8. joinedload 用 JOIN；selectinload 用第二条 IN 查询。
9. 外键约束；显式删更稳。
10. 所有查询要带 deleted=False。

---

> 下一篇：SQLite —— 数据库本体全面教程
