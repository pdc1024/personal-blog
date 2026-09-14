# 第三方库全面教程 · SQLite（标准库）

> 面向初学者：SQLite 不是第三方库，是 Python 自带的"零配置数据库"。博客的 blog.db 就是它。学完这份教程，你能掌握参数化查询、事务、WAL、全文搜索等 SQLite 高级能力——不只会"复制 blog.db 当备份"。
> 适用版本：Python 内置 sqlite3 ｜ 博客项目：`blog.db`（通过 Flask-SQLAlchemy 间接使用）

---

# 第 1 章 这个库是什么

SQLite 是一个**嵌入式关系型数据库**。和 MySQL/PostgreSQL（要装服务器软件、要启动服务）不同，SQLite 就一个文件——你的全部数据都存在 `blog.db` 这一个文件里。

- **嵌入式**：没有独立的数据库进程，你的程序直接读写文件
- **零配置**：不需要装服务器、不需要用户名密码
- **单文件**：备份 = 复制一个文件；删掉 = 数据全没（会自动重建空库）

一句话：**SQLite 是博客的"记忆文件"**。Flask-SQLAlchemy 负责把 Python 代码翻译成 SQL，真正存数据的是 SQLite。

**为什么适合博客？** 个人博客数据量小（几万行以内）、单机使用、不需要多人并发写入——SQLite 又快又省事，是绝配。

---

# 第 2 章 核心概念与原理

## 2.1 数据是怎么存的

一个 `.db` 文件内部可以有多张**表**（table），每张表有**列**（字段）和**行**（一条记录）。博客的 blog.db 里有 7 张表：post、tag、comment、like、profile、friend_link、post_tags（关联表）。

## 2.2 锁与并发：为什么偶尔 "database is locked"

SQLite 支持多线程读，但**同一时刻只允许一个连接写**。写的时候会加"写锁"，其他写操作只能等：

- 默认等待 5 秒，超时就报 `database is locked`
- 博客配置 `timeout=30`：把等待上限提到 30 秒，减少报错

**两个连接同时写**（比如开了两个博客窗口）就容易锁。单机单实例使用基本不会遇到。

## 2.3 事务（Transaction）：要么全成，要么全不成

SQLite 天然支持**事务**：一批操作要么全部成功（commit），要么全部回滚（rollback）——不会出现"删了一半"的脏状态。博客的"先删点赞→评论→文章"如果中途失败，rollback 会让一切恢复原样。

## 2.4 参数化查询：防 SQL 注入的关键

把用户输入拼进 SQL 字符串 = 自杀（攻击者可注入 `'; DROP TABLE post;--`）。正确做法是用**占位符 `?`**，让 SQLite 自己处理转义：

```python
# ❌ 危险：拼接用户输入
cursor.execute(f"SELECT * FROM post WHERE title = '{title}'")

# ✅ 安全：参数化
cursor.execute("SELECT * FROM post WHERE title = ?", (title,))
```

（Flask-SQLAlchemy 底层已经用参数化，你直接写 sqlite3 时才需要自己注意。）

---

# 第 3 章 安装与版本

**不需要安装**——`import sqlite3` 直接用，Python 内置。

```bash
python -c "import sqlite3; print(sqlite3.sqlite_version)"   # 看 SQLite 版本
```

---

# 第 4 章 API 全面讲解

## 4.1 连接与基本操作

```python
import sqlite3

conn = sqlite3.connect('blog.db')     # 连接（文件不存在会自动创建）
conn.row_factory = sqlite3.Row        # 让查询结果能按列名访问（推荐）
cur = conn.cursor()                   # 游标：执行 SQL 的"手"

cur.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, name TEXT)")
conn.commit()                         # 建表也要提交才生效

cur.execute("INSERT INTO t (name) VALUES (?)", ('张三',))
conn.commit()                         # 写操作必须 commit

cur.execute("SELECT * FROM t WHERE name = ?", ('张三',))
row = cur.fetchone()                  # 取一行（Row 对象）
print(row['name'])                    # 按列名取值

conn.close()                          # 用完关闭（博客用连接池，见 4.4）
```

**核心三件套**：`connect()` → `cursor()` → `execute()`；写操作后 `commit()`；用完 `close()`。

## 4.2 增删改查完整语法

```python
# 增（executemany 批量插入，快得多）
cur.executemany("INSERT INTO t (name) VALUES (?)", [('a',), ('b',), ('c',)])
conn.commit()

# 查
cur.execute("SELECT id, name FROM t WHERE id > ? ORDER BY id DESC LIMIT 10", (0,))
rows = cur.fetchall()          # fetchall() 全部 / fetchone() 一条 / fetchmany(n) n条

# 改
cur.execute("UPDATE t SET name = ? WHERE id = ?", ('新名字', 1))
conn.commit()
print(cur.rowcount)            # 影响了多少行

# 删
cur.execute("DELETE FROM t WHERE id = ?", (1,))
conn.commit()
```

## 4.3 PRAGMA：SQLite 的"系统设置"

`PRAGMA` 是 SQLite 的特殊命令，查看/修改引擎行为：

```sql
PRAGMA journal_mode = WAL;      -- 开启 WAL 模式（推荐，见 4.5）
PRAGMA synchronous = NORMAL;    -- 与 WAL 搭配，性能与安全平衡
PRAGMA foreign_keys = ON;       -- 开启外键约束（SQLite 默认关！）
PRAGMA user_version = 3;        -- 自定版本号，配合迁移逻辑
```

**注意**：`PRAGMA foreign_keys = ON` 必须**每个连接**都设（SQLite 默认关闭外键，忘了开，`ON DELETE CASCADE` 不生效）。

## 4.4 事务与异常处理

```python
try:
    conn.execute("BEGIN")
    cur.execute("INSERT INTO t (name) VALUES (?)", ('x',))
    cur.execute("INSERT INTO t (name) VALUES (?)", ('y',))
    conn.commit()                       # 两个都成功 → 一起提交
except Exception:
    conn.rollback()                     # 任何一个失败 → 全部撤销
    raise
```

**隐式提交陷阱**：某些命令（CREATE、DROP、ALTER）会自动提交当前事务，中途出错会留下半成品——所以批处理要"先 BEGIN 再动手"。

## 4.5 WAL 模式：读写互不阻塞（➕ 强烈推荐）

默认模式（journal）下，写的时候读会被卡住。**WAL（Write-Ahead Logging）** 模式让"写"先写进一个临时日志文件，读者读旧数据不受影响，写完再合并——**读写并发不打架**：

```python
conn.execute("PRAGMA journal_mode=WAL")
```

启用后会多出 `blog.db-wal` 和 `blog.db-shm` 两个文件（正常现象）。**备份时要把三个文件一起拷，或用 SQLite 的备份 API**（见 4.7），只拷 .db 可能丢数据。

## 4.6 FTS5 全文搜索（🧪 进阶宝藏）

SQLite 内置全文搜索引擎 FTS5，**比 LIKE 快几百倍**，还支持中文分词（需分词器）：

```python
conn.execute("""
  CREATE VIRTUAL TABLE IF NOT EXISTS post_fts USING fts5(title, content)
""")
conn.execute("INSERT INTO post_fts (title, content) VALUES (?, ?)", ('你好', '博客正文'))
conn.commit()

# 搜索：MATCH 语法
cur = conn.execute("SELECT * FROM post_fts WHERE post_fts MATCH '博客'")
print(cur.fetchall())
```

**思路**：建一个 FTS 影子表，文章增删改时同步维护它；搜索走 FTS，浏览走原表。博客现在用 `ilike` 模糊搜索，文章多了以后可以升级到 FTS5。

## 4.7 备份：backup API（✅ 比复制文件靠谱）

```python
src = sqlite3.connect('blog.db')
dst = sqlite3.connect('blog_backup.db')
src.backup(dst)          # 在线安全备份（自动处理 WAL，不会拷到一半）
dst.close(); src.close()
```

**为什么比复制文件好？** 程序还在写库时直接复制 .db 可能拷到"写了一半"的数据。`backup()` 是事务级一致快照。

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客配置的连接参数（对照真实代码）

博客通过 Flask-SQLAlchemy 间接用 SQLite，连接串和参数（config.py）：

```python
# DATA_DIR：源码运行=项目目录；打包后=exe 所在目录（可写）
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(DATA_DIR, 'blog.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False      # 关掉浪费内存的修改追踪
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,                   # 取连接前先 ping，防"连接假死"
    'pool_recycle': 1800,                    # 连接 30 分钟回收，防长连接失效
    'connect_args': {
        'check_same_thread': False,          # Flask 多线程共用连接必需
        'timeout': 30,                       # 写锁等待上限，防 locked
    },
}
```

**为什么数据库放 DATA_DIR 而不是资源目录？** 模板/静态是"只读资源"（升级直接覆盖），数据库/上传是"用户数据"（升级不能丢）——分开存放，用户升级绿色版时直接覆盖 exe 和 _internal 也不会清空 blog.db。

## 5.2 独立示例：纯 sqlite3 写一个"记事本"（完整可跑）

```python
import sqlite3

conn = sqlite3.connect('notes.db')
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")     # 开 WAL，读写不互卡
conn.execute("""CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY, content TEXT NOT NULL, created TEXT DEFAULT (datetime('now')))""")
conn.commit()

def add(content):
    conn.execute("INSERT INTO notes (content) VALUES (?)", (content,))
    conn.commit()

def search(kw):
    cur = conn.execute("SELECT * FROM notes WHERE content LIKE ? ORDER BY id DESC",
                       (f'%{kw}%',))
    return [dict(r) for r in cur.fetchall()]

add('第一次用 sqlite3')
add('学会了参数化查询')
for n in search('sqlite3'):
    print(n['id'], n['created'], n['content'])
conn.close()
```

---

# 第 6 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 忘 commit | 数据没写入，重启还在 | 所有写操作后 commit（或退出前统一提交） |
| 数据库被锁 | `database is locked` | timeout=30、WAL 模式、别开双实例 |
| 文件损坏 | `file is not a database` | 别用同步中/拷贝中的 db；定期 backup API 备份 |
| 外键级联不生效 | 删了主表子表还在 | 每个连接 `PRAGMA foreign_keys=ON`（默认关） |
| 只拷 .db 备份 | 恢复后数据丢失 | WAL 模式下把 -wal/-shm 一起拷，或 backup API |
| SQL 注入 | 数据被删/被改 | 永远用 `?` 占位符，禁止拼接字符串 |

---

# 第 7 章 学习路径与自测

**学习路径**：先跑通增删改查 + 参数化（半天）→ 理解事务与 commit（半天）→ 开 WAL + 外键（半天）→ 学 FTS5 全文搜索（1 天）→ backup API 备份策略（半天）。

**自测题**：

1. 为什么 SQLite 偶尔报 `database is locked`？怎么缓解？
2. `PRAGMA foreign_keys=ON` 为什么要在每个连接都执行？
3. 参数化查询的 `?` 解决了什么安全问题？
4. WAL 模式下备份要注意什么？
5. 建表、删表、加列这类命令有什么特殊行为？

**答案**：
1. 同一时刻只允许一个写连接；超时（默认 5 秒）就报错。缓解：timeout=30、WAL、单实例。
2. SQLite 默认关闭外键约束，这个设置是按连接生效的，不设则 CASCADE 不触发。
3. 防 SQL 注入——占位符让 SQLite 自动转义用户输入。
4. WAL 会生成 -wal/-shm 文件，备份用 backup API 或三文件一起拷。
5. 它们会自动提交当前事务（隐式提交），中途失败会留下半成品。

---

> 下一篇：python-markdown —— Markdown 转 HTML 全面教程
