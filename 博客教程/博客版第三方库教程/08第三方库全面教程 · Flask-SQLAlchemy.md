# 第三方库全面教程 · Flask-SQLAlchemy

> 面向初学者：这是博客项目里"数据层"的主角——6 张业务表的增删改查全靠它。
> 学完这份教程，你能全面掌控 ORM、Session、关系、级联、预加载、轻量迁移，而不只是会 `query.get_or_404`。
> 适用版本：Flask-SQLAlchemy 3.x（底层 SQLAlchemy 2.x）｜ 博客项目：`app.py` 数据模型 + `init_db`

---

# 第 1 章 这个库是什么

## 1.1 一句话定位

Flask-SQLAlchemy 是 **SQLAlchemy**（Python 最成熟的 ORM 库）在 Flask 里的"官方适配版"，让你用**写 Python 类的方式操作数据库**。

两个核心概念：

- **ORM（Object-Relational Mapping，对象关系映射）**：把"数据库表"映射成"Python 类"，把"一行数据"映射成"一个对象"，把"增删改查"变成 `db.session.add(...)`。你不用手写 SQL（当然也支持手写）。
- **SQLAlchemy**：ORM 的引擎本体；Flask-SQLAlchemy 只是帮你把 SQLAlchemy 和 Flask 的应用上下文、配置、请求生命周期接起来。

一句话：**Flask-SQLAlchemy 是博客的"记忆管家"**——文章、评论、点赞、友链、站点设置全部通过它存取。

## 1.2 为什么用 ORM 而不是裸 SQL

| 对比 | 裸 SQL | ORM |
|---|---|---|
| 写 CRUD | `INSERT INTO post (...) VALUES (...)` | `Post(title=...); db.session.add(post)` |
| 改字段名 | 全局搜替换 SQL | 改一个 Python 属性 |
| 防 SQL 注入 | 手动参数化 | 自动 |
| 换数据库 | SQL 方言要改 | 几乎不用改 |
| 调试 | 直接看 SQL | 要 `.statement` 才看得到 |
| 学习曲线 | 低 | 高（机制多） |

博客选 ORM 是因为：单机应用、SQLite，ORM 让代码更短更安全；性能瓶颈不在数据库层。

## 1.3 一个最小 ORM 例子

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///demo.db'
db = SQLAlchemy(app)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    db.session.add(Post(title='第一篇'))
    db.session.commit()
    print(Post.query.all())
```

跑起来 `demo.db` 就有了，文章也存进去了。

---

# 第 2 章 核心概念与原理

## 2.1 一条数据的完整旅程：Session 工作单元模式

```
Python 代码创建对象
  post = Post(title='你好')
  ↓
db.session.add(post)      ← 加入"待办清单"（还没写数据库！）
  ↓
（此时 post.id 还是 None）
  ↓
db.session.flush()        ← 可选：立刻把 SQL 发给数据库，但不提交事务
                           post.id 此刻有值
  ↓
db.session.commit()       ← 真正提交事务，数据落盘
  ↓
（任何时刻出错可以 rollback() 全部撤回）
数据库真的有了这一行
```

**核心认知**：`add()` 只是排队，`commit()` 才真正落库。忘了 commit，重启数据就丢——这是新手第一坑。

Session（会话）是这个模式的"工作区"：

- 跟踪你所有 add/delete 的对象；
- commit 时统一写数据库（事务）；
- 失败时 `rollback()` 全部撤回；
- 请求结束后 Flask 自动 `db.session.remove()`，防止连接泄漏。

## 2.2 查询为何用 query：链式 + 懒执行

```python
Post.query.filter_by(published=True).order_by(Post.created_at.desc()).limit(10).all()
```

SQLAlchemy 把链式调用翻译成 SQL：

```sql
SELECT * FROM post
WHERE published = 1
ORDER BY created_at DESC
LIMIT 10
```

**懒执行（Lazy Evaluation）**：写查询语句时数据库**什么都没干**，直到你调用 `.all()` / `.first()` / `.count()` 这些"终结方法"才真正执行。所以查询对象可以到处传、随时改：

```python
q = Post.query.filter_by(published=True)
if kw:
    q = q.filter(Post.title.contains(kw))    # 还没执行
posts = q.all()                              # 这里才真正查
```

## 2.3 关系（relationship）与外键

### 2.3.1 一对多：文章 ↔ 评论

```python
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'),
                        index=True, nullable=False)
    post = db.relationship('Post',
        backref=db.backref('comments', lazy='dynamic',
                           cascade='all, delete-orphan'))
```

- `db.ForeignKey('post.id')**：数据库层面声明"评论属于文章"，建外键约束；
- `db.relationship('Post')`：ORM 层面的导航属性，`comment.post` 直接拿到文章对象；
- `backref='comments'`：自动给 Post 加一个 `post.comments` 属性；
- `lazy='dynamic'`：`post.comments` 不是列表，而是查询对象，能继续 `.filter_by(...).count()`；
- `cascade='all, delete-orphan'`：删文章时，它名下的评论一起删。

### 2.3.2 多对多：文章 ↔ 标签

需要一个中间表：

```python
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True))

class Post(db.Model):
    tags = db.relationship('Tag', secondary=post_tags, backref='posts')
```

`secondary=post_tags` 告诉 ORM"通过中间表关联"。`post.tags` 拿到这篇文章的所有标签。

### 2.3.3 lazy 的四种值

| 值 | 含义 |
|---|---|
| `select` | 第一次访问时 SELECT 查（默认） |
| `dynamic` | 返回查询对象，可继续链式调用 |
| `joined` | 主查询时 JOIN 一起取出（防 N+1） |
| `subquery` | 主查询后再用子查询一次性取出 |
| `noload` | 永不加载 |

博客用 `lazy='dynamic'` 是因为评论数统计频繁，不想每次都把评论对象全取出来。

## 2.4 N+1 问题与预加载

```python
posts = Post.query.limit(10).all()
for p in posts:
    print(p.comments.count())   # ← 每篇都触发一次 SQL
```

总共 1 + 10 = 11 次查询。100 篇就是 101 次。这就是 N+1 问题。

**预加载解决**：

```python
from sqlalchemy.orm import joinedload
posts = Post.query.options(joinedload(Post.comments)).limit(10).all()
# 1 条 SQL，JOIN 把评论一起取出来
```

或者 `selectinload`（适合多对多和大集合）：

```python
from sqlalchemy.orm import selectinload
posts = Post.query.options(selectinload(Post.tags)).all()
# 2 条 SQL：先查文章，再 WHERE post_id IN (...) 查标签
```

## 2.5 软删除 vs 物理删除

博客用**软删除**：不真删行，加 `deleted=True` 标记：

```python
class Post(db.Model):
    deleted = db.Column(db.Boolean, default=False)

# 删除时
post.deleted = True
db.session.commit()

# 查询时永远过滤
Post.query.filter_by(deleted=False).all()
```

**好处**：可恢复、同步好做（删了的标记推到远端）、审计完整。
**代价**：表会越来越大，所有查询都要带 `deleted=False`。

---

# 第 3 章 安装与版本

```bash
pip install flask-sqlalchemy
pip show flask-sqlalchemy
```

Flask-SQLAlchemy 3.x 对应 SQLAlchemy 2.x，要求 Python 3.8+。

## 3.1 连接配置

```python
# SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///D:/blog_pkg/blog.db'

# MySQL（生产）
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://user:pass@host/blog'

# PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@host/blog'
```

**关键配置**：

```python
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False   # 关掉浪费内存的修改追踪
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'check_same_thread': False, 'timeout': 30},
}
```

- `check_same_thread=False`：SQLite 默认只允许创建它的线程用；多线程桌面应用必须关；
- `timeout=30`：数据库被锁时等待 30 秒而不是立刻报错。

## 3.2 初始化

```python
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)
```

或者应用工厂模式：

```python
db = SQLAlchemy()              # 先创建，不绑 app
def create_app():
    app = Flask(__name__)
    db.init_app(app)           # 后绑定
    return app
```

---

# 第 4 章 API 全面讲解

## 4.1 定义模型（建表）

```python
class Post(db.Model):
    __tablename__ = 'post'                          # 表名
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, default='')
    published = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    view_count = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), default='', index=True)
    rendered_html = db.Column(db.Text, default='')  # 缓存渲染结果
```

**列类型速查**：

| 类型 | 存什么 | 博客里 |
|---|---|---|
| `Integer` | 整数 | id、view_count |
| `String(n)` | 短文本（定长上限） | 标题、分类 |
| `Text` | 长文本（不限长） | 正文、rendered_html |
| `Boolean` | 真/假 | published、deleted |
| `DateTime` | 时间 | created_at、updated_at |
| `Float` | 小数 | （未来评分） |
| `LargeBinary` | 二进制 | （图片二进制，博客用文件系统） |

**列约束**：

| 参数 | 作用 |
|---|---|
| `primary_key=True` | 主键 |
| `nullable=False` | 必填 |
| `default=值` | 默认值（Python 端默认） |
| `server_default` | 数据库端默认 |
| `unique=True` | 唯一 |
| `index=True` | 建索引 |

## 4.2 写入：add / commit / delete

```python
# 新增
post = Post(title='新文章', content='...')
db.session.add(post)
db.session.commit()       # post.id 此刻才有值

# 修改（找到对象 → 改属性 → commit）
post.title = '改个标题'
db.session.commit()

# 批量新增
db.session.add_all([Post(title=f'文章{i}') for i in range(10)])
db.session.commit()

# 删除
db.session.delete(post)
db.session.commit()

# 出错回滚
try:
    db.session.commit()
except Exception:
    db.session.rollback()
    raise
```

**flush vs commit**：

- `flush()`：把 SQL 发给数据库，但不提交事务；对象能拿到自增 ID；
- `commit()`：flush + 提交事务，数据真正落盘。

## 4.3 查询全家桶

| 方法 | 作用 | 例子 |
|---|---|---|
| `.get(id)` | 按主键查，没有返回 None | `Post.query.get(3)` |
| `.get_or_404(id)` | 没有直接 404 | `Post.query.get_or_404(post_id)` |
| `.first()` / `.all()` | 第一条 / 全部 | 终结方法 |
| `.filter_by(字段=值)` | 等值过滤 | `filter_by(published=True)` |
| `.filter(条件)` | 灵活条件 | `filter(Post.title.ilike('%python%'))` |
| `.order_by(字段.desc())` | 排序 | |
| `.limit(n)` / `.offset(n)` | 分页 | |
| `.count()` | 计数 | |
| `.paginate(page, per_page)` | 分页对象 | 首页 |
| `.ilike('%xx%')` | 模糊搜索（不区分大小写） | |
| `.group_by(...)` / `.having(...)` | 分组统计 | |
| `.distinct(字段)` | 去重 | |

**条件组合**：

```python
from sqlalchemy import or_, and_
query = Post.query.filter(
    and_(Post.published == True,
         or_(Post.title.contains('Python'), Post.category == '技术'))
)
```

**聚合函数**：

```python
from sqlalchemy import func
Post.query.with_entities(func.count(Post.id)).scalar()
# SELECT COUNT(id) FROM post
```

## 4.4 分页：paginate

```python
page = request.args.get('page', 1, type=int)
pagination = Post.query.filter_by(published=True) \
                       .order_by(Post.created_at.desc()) \
                       .paginate(page=page, per_page=10, error_out=False)

# pagination.items：当前页的文章列表
# pagination.page：当前页码
# pagination.pages：总页数
# pagination.total：总条数
# pagination.has_prev / has_next
# pagination.iter_pages()：生成页码列表（带 None 表示省略）
```

模板里用 `iter_pages()` 生成页码链接。

## 4.5 建表与轻量迁移

```python
db.create_all()    # 按模型建表（只建不存在的表，不修改旧表！）
db.drop_all()      # 删所有表（危险）
```

**给旧表加新列**（博客的做法）：

```python
from sqlalchemy import inspect, text

inspector = inspect(db.engine)
existing_cols = [c['name'] for c in inspector.get_columns('post')]
if 'category' not in existing_cols:
    with db.engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE post ADD COLUMN category VARCHAR(50) DEFAULT ''"
        ))
```

**为什么叫"轻量迁移"？** 幂等——跑多少次都安全。正式大项目用 Alembic 做版本化迁移（`flask db migrate` / `flask db upgrade`）。

## 4.6 原生 SQL（🧪 复杂查询用）

```python
# 执行原生 SQL
result = db.session.execute(text("SELECT * FROM post WHERE id = :id"),
                            {'id': 3})
for row in result:
    print(row.title)

# 原生 INSERT/UPDATE/DELETE
db.session.execute(text("UPDATE post SET view_count = view_count + 1 WHERE id = :id"),
                   {'id': post_id})
db.session.commit()
```

**永远用 `:参数` 占位符**，不要字符串拼接——防 SQL 注入。

---

# 第 5 章 实战示例

## 5.1 项目内示例：首页文章查询（app.py 第 1014 行）

```python
@app.route('/')
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
        page=request.args.get('page', 1, type=int),
        per_page=10, error_out=False)
    return render_template('index.html', posts=pagination.items, pagination=pagination)
```

## 5.2 项目内示例：点赞计数（app.py 第 1185 行）

```python
@app.route('/post/<int:post_id>/like/', methods=['POST'])
def post_like(post_id):
    post = Post.query.get_or_404(post_id)
    fp = g.fingerprint
    existing = Like.query.filter_by(post_id=post_id, fingerprint=fp).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(Like(post_id=post_id, fingerprint=fp))
    db.session.commit()
    count = Like.query.filter_by(post_id=post_id).count()
    return jsonify({'ok': True, 'count': count})
```

**设计决策**：不维护 `like_count` 列，每次查 COUNT。数据准确，代价是多一次查询（博客规模值得）。

## 5.3 独立示例：文章-评论完整 CRUD

```python
# 新增文章并加评论
post = Post(title='ORM 入门', content='...')
db.session.add(post)
db.session.flush()    # 拿到 post.id
db.session.add(Comment(content='好文！', post_id=post.id))
db.session.commit()

# 查询
post = Post.query.filter_by(title='ORM 入门').first()
print([c.content for c in post.comments])

# 更新
post.view_count += 1
db.session.commit()

# 删除（cascade 自动删评论）
db.session.delete(post)
db.session.commit()
```

---

# 第 6 章 高频坑与排查

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | 忘 commit | 数据没保存 | add 后一定 commit |
| 2 | 级联没配好删文章 | NOT NULL constraint failed | 显式顺序删，或配 cascade |
| 3 | 脚本里用 db | Working outside of application context | `with app.app_context():` |
| 4 | 数据库被锁 | database is locked | connect_args timeout=30；别开两个实例 |
| 5 | 加列后报错 | no such column | create_all 不改旧表，用 ALTER 补 |
| 6 | 改了模型没生效 | 表结构还是旧的 | 已有表要迁移，或删 db 重建 |
| 7 | 查询半天不返回 | 忘了写终结方法 | 末尾加 .all()/.first() |
| 8 | N+1 查询慢 | 列表页加载慢 | joinedload / selectinload 预加载 |
| 9 | 字符串拼接 SQL | SQL 注入 | 用 `:参数` 占位符 |
| 10 | session 跨请求残留 | 数据串了 | 请求结束 Flask 自动 remove；后台线程手动 remove |
| 11 | 事务没回滚 | 后续查询全报错 | try/except 里 rollback |
| 12 | default 用可变对象 | 所有实例共享同一列表 | `default=list` 传函数，不是 `default=[]` |
| 13 | 自增 ID 在 commit 前用 | None | 先 flush() |
| 14 | 多线程 SQLite | SQLite objects created in a thread | check_same_thread=False |

**调试 SQL**：

```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
# 现在终端会打印每条 SQL
```

---

# 第 7 章 学习路径与自测

## 7.1 学习路径

**第 1~2 天：基础 CRUD**
- 建一个 Post 模型，跑通增删改查；
- 理解 add/flush/commit/rollback；
- 目标：能独立写一个待办事项应用。

**第 3~4 天：查询与分页**
- 掌握 filter_by/filter/order_by/paginate；
- 学会 or_/and_ 组合条件；
- 目标：给博客加一个搜索页。

**第 5~7 天：关系与级联**
- 一对多、多对多；
- cascade 配置；
- 目标：给博客加评论功能。

**第 2 周：进阶**
- N+1 问题与预加载；
- 轻量迁移；
- 原生 SQL；
- 学 Alembic 做版本化迁移。

## 7.2 自测题

1. `db.session.add(post)` 后、`commit()` 前，数据库里有这条数据吗？
2. `create_all()` 能修改已有表吗？加新列怎么办？
3. `post.comments` 第一次访问时发生什么？N+1 是什么？
4. 删文章报 `comment.post_id` NOT NULL 错误，为什么？
5. `filter_by(published=True)` 和 `filter(Post.published == True)` 区别？
6. flush() 和 commit() 的区别？
7. 怎么打印 SQLAlchemy 生成的 SQL？
8. 为什么 `default=[]` 是错的？应该怎么写？
9. joinedload 和 selectinload 有什么区别？
10. SQLite 多线程为什么要 `check_same_thread=False`？

## 7.3 答案

1. 没有，add 只是排队，commit 才落库。
2. 不能，只建新表；已有表加列用 ALTER TABLE 或迁移工具。
3. 触发一次 SELECT 查这篇文章的评论；循环访问关系属性产生 1+N 次查询就是 N+1，用 joinedload/selectinload 解决。
4. 评论的外键关系/级联没配好，或删除顺序不对——显式先删点赞→评论→文章，或配好 cascade='all, delete-orphan'。
5. 前者是简写、只能等值；后者支持任意表达式（大于、模糊、or_ 组合）。
6. flush 把 SQL 发给数据库但不提交事务（对象能拿到自增 ID）；commit = flush + 提交事务，数据落盘。
7. `logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)`。
8. `default=[]` 是同一个列表对象，所有新行共享；应写 `default=list`（传函数）。
9. joinedload 用 LEFT OUTER JOIN 一次取出（适合一对多）；selectinload 发第二条 SQL `WHERE id IN (...)`（适合多对多和大集合，避免笛卡尔积）。
10. SQLite 默认连接对象不能跨线程用；桌面应用多线程访问数据库必须关，否则报错。

## 7.4 进一步学习

- 官方文档：https://flask-sqlalchemy.palletsprojects.com/
- SQLAlchemy 2.0：https://docs.sqlalchemy.org/
- Alembic 迁移：https://alembic.sqlalchemy.org/

---

> 下一篇：SQLite —— 数据库本体全面教程
