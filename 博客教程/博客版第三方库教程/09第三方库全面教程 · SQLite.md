# 第三方库全面教程 · SQLite（标准库）

> 面向初学者到进阶者：博客所有数据都在 `blog.db` 这一个文件里。
> 学完这份教程，你会掌握 sqlite3 模块的全部核心 API、事务、WAL、外键、FTS5、
> 在线备份、参数化查询、PRAGMA 调优，以及 SQLite 的并发模型和常见坑。
>
> 适用版本：Python 内置 sqlite3 ｜ 博客项目：`blog.db`（通过 Flask-SQLAlchemy 间接使用）
> 学习路线：认识 SQLite（第 1 章）→ 并发与事务（第 2 章）→ API 与 PRAGMA（第 3~4 章）→ 进阶（第 5~6 章）→ 实战与排坑（第 7~8 章）

---

# 第 1 章 认识 SQLite

## 1.1 一句话定位

SQLite 是一个**嵌入式关系型数据库**。和 MySQL/PostgreSQL（装服务器、连网络）不同，SQLite 就是一个文件。

- **嵌入式**：没有独立进程，你的程序直接读写文件；
- **零配置**：不装服务器、不要用户名密码；
- **单文件**：备份 = 复制文件；
- **跨平台**：同一个 .db 在 Windows/Mac/Linux 都能开。

一句话：**SQLite 是博客的记忆文件**。

## 1.2 为什么博客选 SQLite

| 场景 | SQLite | MySQL |
|---|---|---|
| 个人博客（万行级） | 快 | 杀鸡用牛刀 |
| 单机桌面 | 一个文件 | 要装服务 |
| 打包发朋友 | 30MB 绿色 | 朋友还要装 MySQL |
| 并发写 | 单写者 | 多写者 |

## 1.3 SQLite 的局限

- 不适合高并发写（同时一个写者）；
- 不要在网络盘上跑（文件锁不可靠）；
- 不适合 TB 级数据；
- ALTER TABLE 支持有限（不能直接改列类型）。

---

# 第 2 章 并发、锁与事务

## 2.1 锁模型

SQLite 支持多线程读，但**同一时刻只允许一个写**。写时加写锁，其他写等待：

- 默认等 5 秒，超时 `database is locked`；
- 博客配置 `timeout=30`。

## 2.2 WAL 模式（强烈推荐）

默认 journal 模式下，写会阻塞读。**WAL（Write-Ahead Logging）**让写先写日志，读不受影响：

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
```

启用后多出 `blog.db-wal`、`blog.db-shm`（正常）。备份要三文件一起或用 backup API。

## 2.3 事务

```python
try:
    conn.execute("BEGIN")
    conn.execute("INSERT ...")
    conn.execute("INSERT ...")
    conn.commit()
except:
    conn.rollback()
```

SQLite 天然 ACID：一批操作要么全成要么全不成。

**隐式提交坑**：CREATE/DROP/ALTER 会自动提交当前事务，中途失败留半成品。

## 2.4 外键约束

SQLite 默认**关闭外键**！每个连接都要开：

```sql
PRAGMA foreign_keys = ON;
```

否则 `ON DELETE CASCADE` 不生效。Flask-SQLAlchemy 不会自动帮你开。

---

# 第 3 章 sqlite3 模块 API

## 3.1 连接与游标

```python
import sqlite3

conn = sqlite3.connect('blog.db')
conn.row_factory = sqlite3.Row    # 查询结果按列名访问
cur = conn.cursor()
cur.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
conn.commit()
conn.close()
```

## 3.2 增删改查

```python
# 增
cur.execute("INSERT INTO t (name) VALUES (?)", ('张三',))
conn.commit()

# 批量
cur.executemany("INSERT INTO t (name) VALUES (?)", [('a',), ('b',)])

# 查
cur.execute("SELECT * FROM t WHERE id = ?", (1,))
row = cur.fetchone()
rows = cur.fetchall()

# 改
cur.execute("UPDATE t SET name = ? WHERE id = ?", ('新名', 1))
print(cur.rowcount)

# 删
cur.execute("DELETE FROM t WHERE id = ?", (1,))
```

## 3.3 参数化查询（安全铁律）

```python
# ❌ 危险
cur.execute(f"SELECT * FROM t WHERE name = '{name}'")

# ✅ 安全
cur.execute("SELECT * FROM t WHERE name = ?", (name,))
```

防 SQL 注入。`?` 是占位符，元组里的值自动转义。

## 3.4 上下文管理器

```python
with sqlite3.connect('blog.db') as conn:
    conn.execute("INSERT ...")
# with 退出自动 commit，异常自动 rollback
```

---

# 第 4 章 PRAGMA 调优

```sql
PRAGMA journal_mode = WAL;       -- 写不阻塞读
PRAGMA synchronous = NORMAL;     -- 与 WAL 搭配
PRAGMA foreign_keys = ON;        -- 外键（每个连接）
PRAGMA user_version = 1;         -- 迁移版本号
PRAGMA cache_size = -20000;      -- 20MB 缓存
PRAGMA page_size = 4096;
```

## 4.1 user_version：幂等迁移

```python
ver = conn.execute("PRAGMA user_version").fetchone()[0]
if ver < 1:
    conn.execute("ALTER TABLE post ADD COLUMN category TEXT")
    conn.execute("PRAGMA user_version = 1")
```

---

# 第 5 章 进阶：FTS5、备份、UPSERT

## 5.1 FTS5 全文搜索

```sql
CREATE VIRTUAL TABLE post_fts USING fts5(title, content);
INSERT INTO post_fts VALUES ('标题', '正文');
SELECT * FROM post_fts WHERE post_fts MATCH '博客';
```

比 LIKE 快几百倍。中文分词需外挂 jieba。

## 5.2 在线备份：backup API

```python
src = sqlite3.connect('blog.db')
dst = sqlite3.connect('blog_backup.db')
src.backup(dst)
```

事务级一致快照，比复制文件安全。

## 5.3 UPSERT（SQLite 3.24+）

```sql
INSERT INTO post (id, title) VALUES (?, ?)
ON CONFLICT(id) DO UPDATE SET title = excluded.title;
```

存在则更新，不存在则插入。

## 5.4 VACUUM

删大量数据后文件不收缩，执行 `VACUUM` 重建。

---

# 第 6 章 项目实战

## 6.1 博客连接配置（config.py）

```python
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(DATA_DIR, 'blog.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    'connect_args': {
        'check_same_thread': False,
        'timeout': 30,
    },
}
```

## 6.2 为什么数据库放 DATA_DIR

模板/静态是"只读资源"（升级覆盖），数据库是"用户数据"（升级不能丢）。分开存放，绿色版升级不丢数据。

## 6.3 独立示例：纯 sqlite3 记事本

```python
import sqlite3

conn = sqlite3.connect('notes.db')
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("""CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    content TEXT,
    created TEXT DEFAULT (datetime('now')))""")
conn.commit()

def add(c):
    conn.execute("INSERT INTO notes (content) VALUES (?)", (c,))
    conn.commit()

def search(kw):
    cur = conn.execute("SELECT * FROM notes WHERE content LIKE ? ORDER BY id DESC",
                       (f'%{kw}%',))
    return [dict(r) for r in cur.fetchall()]
```

---

# 第 7 章 高频坑与排查

| # | 坑 | 解决 |
|---|---|---|
| 1 | 忘 commit | 写操作后 commit |
| 2 | database is locked | timeout=30、WAL、单实例 |
| 3 | 外键不生效 | 每连接 PRAGMA foreign_keys=ON |
| 4 | WAL 只拷 .db | 三文件一起或 backup API |
| 5 | SQL 注入 | ? 占位符 |
| 6 | 多线程 | check_same_thread=False |
| 7 | 文件不收缩 | VACUUM |
| 8 | 网络盘跑 SQLite | 容易损坏，用本地盘 |
| 9 | 中文 LIKE 不命中 | 确认 UTF-8 |
| 10 | 隐式提交 | DDL 会自动 commit |
| 11 | 时间存本地还是 UTC | 存 UTC，显示转本地 |
| 12 | 大查询慢 | 加索引 |

---

# 第 8 章 学习路径与自测

## 8.1 学习路径

- 第 1 天：CRUD + 参数化；
- 第 2 天：事务 + PRAGMA；
- 第 3~4 天：WAL + 备份 + FTS5。

## 8.2 自测题

1. SQLite 为什么偶尔 locked？怎么缓解？
2. PRAGMA foreign_keys 为什么每连接都要？
3. WAL 模式备份要注意什么？
4. backup API 比复制文件好在哪？
5. UPSERT 语法？
6. VACUUM 做什么？
7. 为什么不要在网络盘跑 SQLite？
8. 存时间用 UTC 还是本地？

## 8.3 答案

1. 单写者；timeout=30、WAL、单实例。
2. SQLite 默认关外键，PRAGMA 按连接。
3. 三文件一起或 backup API。
4. 事务级一致，不拷到一半。
5. `INSERT ... ON CONFLICT DO UPDATE`。
6. 重建文件回收空闲空间。
7. 网络文件锁不可靠，容易损坏。
8. 存 UTC，显示转本地。

---

> 下一篇：python-markdown —— Markdown 转 HTML 全面教程
