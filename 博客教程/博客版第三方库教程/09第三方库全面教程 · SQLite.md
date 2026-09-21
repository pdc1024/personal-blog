# 第三方库全面教程 · SQLite（标准库）

> 面向初学者：SQLite 不是第三方库，是 Python 自带的"零配置数据库"。博客的 blog.db 就是它。
> 学完这份教程，你能掌握参数化查询、事务、WAL、外键、FTS5、在线备份等 SQLite 高级能力。
> 适用版本：Python 内置 sqlite3 ｜ 博客项目：`blog.db`（通过 Flask-SQLAlchemy 间接使用）

---

# 第 1 章 这个库是什么

## 1.1 一句话定位

SQLite 是一个**嵌入式关系型数据库**。和 MySQL/PostgreSQL（要装服务器、启动服务、连网络）不同，SQLite 就是**一个文件**——你的全部数据都在 `blog.db` 这一个文件里。

- **嵌入式**：没有独立的数据库进程，你的程序直接读写文件；
- **零配置**：不需要装服务器、不需要用户名密码；
- **单文件**：备份 = 复制一个文件；删掉 = 数据全没（首次启动会自动建空库）；
- **跨平台**：同一个 .db 文件在 Windows/Mac/Linux 都能打开。

一句话：**SQLite 是博客的"记忆文件"**。Flask-SQLAlchemy 把 Python 代码翻译成 SQL，真正存数据的是 SQLite。

## 1.2 为什么博客选 SQLite

| 场景 | SQLite | MySQL/PG |
|---|---|---|
| 个人博客数据量（几万行） | 快、够 | 杀鸡用牛刀 |
| 单机桌面应用 | 一个文件，免安装 | 要装服务器 |
| 打包发给朋友 | 34MB 绿色版 | 朋友还要装 MySQL |
| 并发写入 | 单写者 | 多写者 |
| 备份 | 复制文件 | mysqldump |

个人博客数据量小、单机使用、不需要多人并发写入——SQLite 又快又省事。

## 1.3 SQLite 的局限（要知道）

- 不适合高并发写（同一时刻一个写者）；
- 不适合多台机器同时写一个文件（网络盘上跑 SQLite 容易坏）；
- 不适合 TB 级数据；
- ALTER TABLE 支持有限（不能直接改列类型，要建新表复制）。

博客场景完全不踩这些坑。

---

# 第 2 章 核心概念与原理

## 2.1 数据是怎么存的

一个 `.db` 文件内部有多张**表（table）**，每张表有**列（字段）**和**行（记录）**。博客的 blog.db 有 7 张表：

| 表 | 存什么 |
|---|---|
| `post` | 文章（标题、正文、时间、浏览数） |
| `tag` | 标签 |
| `post_tags` | 文章-标签多对多中间表 |
| `comment` | 评论 |
| `like` | 点赞 |
| `profile` | 站点设置 |
| `friend_link` | 友链 |

## 2.2 锁与并发：为什么偶尔 database is locked

SQLite 支持多线程**读**，但**同一时刻只允许一个连接写**。写的时候加"写锁"，其他写操作只能等：

- 默认等待 5 秒，超时报 `database is locked`；
- 博客配置 `timeout=30`：等待上限提到 30 秒；
- 两个实例同时写（开了两个博客窗口）容易锁。

WAL 模式（4.5 节）能进一步缓解读写互卡。

## 2.3 事务：要么全成，要么全不成

SQLite 天然支持**事务**：一批操作要么全部 commit，要么全部 rollback——不会出现"删了一半"的脏状态。

```python
try:
    db.execute("BEGIN")
    db.execute("DELETE FROM like WHERE post_id=?", (pid,))
    db.execute("DELETE FROM comment WHERE post_id=?", (pid,))
    db.execute("DELETE FROM post WHERE id=?", (pid,))
    db.commit()
except:
    db.rollback()
```

博客删文章就是靠事务保证"点赞、评论、文章"一起删或一起不删。

## 2.4 参数化查询：防 SQL 注入

把用户输入拼进 SQL 字符串 = 自杀：

```python
# ❌ 危险：用户输入 name = "' OR 1=1; DROP TABLE post;--"
cur.execute(f"SELECT * FROM post WHERE name = '{name}'")

# ✅ 安全：占位符
cur.execute("SELECT * FROM post WHERE name = ?", (name,))
```

Flask-SQLAlchemy 底层已自动参数化；直接用 sqlite3 时必须自己注意。

## 2.5 SQLite 类型系统（动态类型）

SQLite 是**动态类型**：列声明类型只是"类型亲和性"，不强制。

| 声明 | 亲和性 | 可存 |
|---|---|---|
| `INTEGER` | 整数 | 整数（文本也能塞） |
| `TEXT` | 文本 | 字符串 |
| `REAL` | 浮点 | 数字 |
| `BLOB` | 二进制 | 原样存 |
| `NUMERIC` | 数字 | 整数或浮点 |

**和 MySQL 不同**：SQLite 不严格检查类型，你可以往 INTEGER 列塞字符串。ORM 层做类型转换。

---

# 第 3 章 安装与版本

**不需要安装**——Python 内置：

```bash
python -c "import sqlite3; print(sqlite3.sqlite_version)"
# 3.4x.x 之类
```

不同 Python 版本带的 SQLite 版本不同，新版 Python 一般带新 SQLite。

---

# 第 4 章 API 全面讲解

## 4.1 连接与基本操作

```python
import sqlite3

conn = sqlite3.connect('blog.db')      # 文件不存在自动创建
conn.row_factory = sqlite3.Row         # 查询结果按列名访问（强烈推荐）
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, name TEXT)")
conn.commit()

cur.execute("INSERT INTO t (name) VALUES (?)", ('张三',))
conn.commit()

cur.execute("SELECT * FROM t WHERE name = ?", ('张三',))
row = cur.fetchone()
print(row['name'])

conn.close()
```

**核心三件套**：`connect()` → `cursor()` → `execute()`；写操作后 `commit()`；用完 `close()`。

### 4.1.1 上下文管理器（推荐写法）

```python
with sqlite3.connect('blog.db') as conn:
    conn.execute("INSERT ...")
# with 退出自动 commit，异常自动 rollback
```

## 4.2 增删改查

```python
# 增（单条）
cur.execute("INSERT INTO t (name) VALUES (?)", ('a',))

# 批量插入（快 10 倍）
cur.executemany("INSERT INTO t (name) VALUES (?)", [('b',), ('c',), ('d',)])

# 查
cur.execute("SELECT id, name FROM t WHERE id > ? ORDER BY id DESC LIMIT 10", (0,))
rows = cur.fetchall()      # 全部
row = cur.fetchone()       # 一条
rows = cur.fetchmany(5)    # 5 条

# 改
cur.execute("UPDATE t SET name = ? WHERE id = ?", ('新名', 1))
print(cur.rowcount)        # 影响行数

# 删
cur.execute("DELETE FROM t WHERE id = ?", (1,))

# 最后插入的自增 ID
print(cur.lastrowid)
```

**迭代游标**（大数据量省内存）：

```python
for row in cur.execute("SELECT * FROM t"):
    process(row)           # 逐行处理，不一次性加载全部
```

## 4.3 PRAGMA：SQLite 的"系统设置"

```sql
PRAGMA journal_mode = WAL;      -- 开启 WAL（推荐）
PRAGMA synchronous = NORMAL;    -- 与 WAL 搭配
PRAGMA foreign_keys = ON;       -- 外键约束（默认关！）
PRAGMA user_version = 3;        -- 自定义版本号（迁移用）
PRAGMA page_size = 4096;        -- 页大小
PRAGMA cache_size = -20000;     -- 20MB 缓存（负数=KB）
```

**关键陷阱**：`PRAGMA foreign_keys = ON` 必须**每个连接**都设——SQLite 默认关闭外键约束，忘了开，`ON DELETE CASCADE` 不生效。

## 4.4 事务与异常

```python
try:
    conn.execute("BEGIN")
    cur.execute("INSERT INTO t (name) VALUES (?)", ('x',))
    cur.execute("INSERT INTO t (name) VALUES (?)", ('y',))
    conn.commit()
except Exception:
    conn.rollback()
    raise
```

**隐式提交陷阱**：CREATE、DROP、ALTER 等 DDL 命令会自动提交当前事务——中途出错会留下半成品。批处理要先 BEGIN。

## 4.5 WAL 模式：读写不互卡（强烈推荐）

默认 journal 模式下，写的时候读会被卡住。**WAL（Write-Ahead Logging）**让"写"先写进一个临时日志，读者读旧数据不受影响，写完再合并：

```python
conn.execute("PRAGMA journal_mode=WAL")
```

启用后会多出 `blog.db-wal` 和 `blog.db-shm` 两个文件（正常现象）。

**备份注意**：WAL 模式下只拷 .db 可能丢数据——要么用 backup API，要么三个文件一起拷。

## 4.6 FTS5 全文搜索（进阶宝藏）

SQLite 内置 FTS5，**比 LIKE 快几百倍**：

```python
conn.execute("""
  CREATE VIRTUAL TABLE post_fts USING fts5(title, content)
""")
conn.execute("INSERT INTO post_fts (title, content) VALUES (?, ?)", ('你好', '正文'))
conn.commit()

# 搜索
cur = conn.execute("SELECT * FROM post_fts WHERE post_fts MATCH '博客'")
```

**中文分词**：FTS5 默认 unicode61 分词，中文会按字切。要更好的中文分词需要外挂 jieba 等。博客目前用 `ilike`，文章多了可升级到 FTS5。

## 4.7 在线备份：backup API

```python
src = sqlite3.connect('blog.db')
dst = sqlite3.connect('blog_backup.db')
src.backup(dst)          # 事务级一致快照
dst.close(); src.close()
```

**比复制文件好**：程序还在写库时直接复制 .db 可能拷到"写了一半"的数据。`backup()` 保证一致性。

## 4.8 常用 SQL 技巧

```sql
-- UPSERT：存在则更新，不存在则插入（SQLite 3.24+）
INSERT INTO post (id, title) VALUES (?, ?)
  ON CONFLICT(id) DO UPDATE SET title = excluded.title;

-- 批量替换
UPDATE post SET content = REPLACE(content, 'a', 'b');

-- 分组统计
SELECT category, COUNT(*) FROM post GROUP BY category;

-- 连表
SELECT p.title, c.content FROM post p
  JOIN comment c ON c.post_id = p.id;
```

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客的连接配置（config.py）

```python
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(DATA_DIR, 'blog.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,          # 取连接前 ping，防假死
    'pool_recycle': 1800,           # 30 分钟回收
    'connect_args': {
        'check_same_thread': False, # 多线程必需
        'timeout': 30,               # 写锁等待上限
    },
}
```

**为什么数据库放 DATA_DIR 而不是资源目录？** 模板/静态是"只读资源"（升级直接覆盖），数据库/上传是"用户数据"（升级不能丢）——分开存放，用户升级绿色版时覆盖 exe 和 _internal 也不会清空 blog.db。

## 5.2 独立示例：纯 sqlite3 记事本

```python
import sqlite3

conn = sqlite3.connect('notes.db')
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("""CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    content TEXT NOT NULL,
    created TEXT DEFAULT (datetime('now')))""")
conn.commit()

def add(content):
    conn.execute("INSERT INTO notes (content) VALUES (?)", (content,))
    conn.commit()

def search(kw):
    cur = conn.execute(
        "SELECT * FROM notes WHERE content LIKE ? ORDER BY id DESC",
        (f'%{kw}%',))
    return [dict(r) for r in cur.fetchall()]

add('第一次用 sqlite3')
add('学会了参数化查询')
for n in search('sqlite3'):
    print(n['id'], n['created'], n['content'])
conn.close()
```

## 5.3 独立示例：带迁移的建表

```python
def migrate(conn):
    conn.execute("PRAGMA user_version = 0")
    ver = conn.execute("PRAGMA user_version").fetchone()[0]

    if ver < 1:
        conn.execute("ALTER TABLE post ADD COLUMN category TEXT DEFAULT ''")
        conn.execute("PRAGMA user_version = 1")
    if ver < 2:
        conn.execute("ALTER TABLE post ADD COLUMN view_count INTEGER DEFAULT 0")
        conn.execute("PRAGMA user_version = 2")
    conn.commit()
```

`user_version` 是 SQLite 自带的版本号字段，博客用它做幂等迁移。

---

# 第 6 章 高频坑与排查

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | 忘 commit | 数据没写入 | 所有写操作后 commit |
| 2 | 数据库被锁 | database is locked | timeout=30、WAL、单实例 |
| 3 | 文件损坏 | file is not a database | 别拷同步中的 db；定期 backup API |
| 4 | 外键级联不生效 | 删主表子表还在 | 每个连接 PRAGMA foreign_keys=ON |
| 5 | WAL 只拷 .db | 恢复后数据丢失 | backup API 或三文件一起拷 |
| 6 | SQL 注入 | 数据被删改 | 永远 `?` 占位符 |
| 7 | 多线程报错 | SQLite objects created in a thread | check_same_thread=False |
| 8 | 中文 LIKE 不命中 | 搜不到 | 确认编码 UTF-8；FTS5 更好 |
| 9 | ALTER 改列类型 | 不支持 | 建新表→复制数据→删旧表→改名 |
| 10 | 磁盘满 | 写失败 | 监控 db 文件大小；定期 VACUUM |
| 11 | 时间格式混乱 | 显示错时区 | 存 UTC，显示时转本地 |
| 12 | 大查询慢 | 秒回变几秒 | 加索引（CREATE INDEX） |

**VACUUM**：删了大量数据后文件不会自动缩小，执行 `VACUUM` 重建文件。

---

# 第 7 章 学习路径与自测

## 7.1 学习路径

**第 1 天：基础**
- connect/cursor/execute；
- 增删改查 + 参数化；
- 目标：写一个纯 sqlite3 的小工具。

**第 2 天：事务与配置**
- BEGIN/COMMIT/ROLLBACK；
- WAL、foreign_keys、timeout；
- 目标：给小工具加事务保护。

**第 3~4 天：进阶**
- backup API；
- FTS5 全文搜索；
- user_version 迁移；
- 索引优化。

## 7.2 自测题

1. 为什么 SQLite 偶尔报 database is locked？怎么缓解？
2. `PRAGMA foreign_keys=ON` 为什么每个连接都要执行？
3. 参数化查询的 `?` 解决什么安全问题？
4. WAL 模式下备份要注意什么？
5. DDL 命令有什么特殊行为？
6. SQLite 怎么判断当前 schema 版本？
7. 删了 1000 行后 db 文件为什么没变小？怎么修？
8. 怎么在不停止程序的情况下备份 SQLite？
9. SQLite 支持 SELECT FOR UPDATE 吗？
10. 为什么不要在网络盘上跑 SQLite？

## 7.3 答案

1. 同一时刻只允许一个写连接；超时（默认 5 秒）就报错。缓解：timeout=30、WAL、单实例。
2. SQLite 默认关闭外键，PRAGMA 按连接生效，不设 CASCADE 不触发。
3. 防 SQL 注入——占位符让 SQLite 自动转义用户输入。
4. WAL 会生成 -wal/-shm 文件；备份用 backup API 或三文件一起拷。
5. CREATE/DROP/ALTER 会自动提交当前事务（隐式提交），中途失败留半成品。
6. `PRAGMA user_version`。
7. SQLite 删行只是标记空闲，不收缩文件；执行 `VACUUM` 重建。
8. 用 `src.backup(dst)` 在线 API，事务级一致。
9. 不支持，SQLite 用文件锁代替行锁。
10. 网络盘文件锁不可靠，容易损坏数据库；SQLite 设计为本地文件。

## 7.4 进一步学习

- 官方文档：https://www.sqlite.org/docs.html
- SQLite 语法：https://www.sqlite.org/lang.html
- FTS5：https://www.sqlite.org/fts5.html

---

> 下一篇：python-markdown —— Markdown 转 HTML 全面教程
