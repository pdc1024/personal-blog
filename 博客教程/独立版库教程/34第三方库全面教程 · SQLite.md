# 第三方库全面教程 · SQLite（独立版）

> 面向初学者：本教程**独立成篇**，假设你会基础 Python。术语第一次出现都有白话解释。
> 适用版本：Python 内置 sqlite3（3.4x）｜ 配套知识：与《Flask-SQLAlchemy》配合（ORM 底层就是它）。
> 学习目标：从"不知道数据库是什么"到"能直接用 SQL 完成建表、增删改查、索引、事务，理解数据库原理"。

---

# 第 1 章 这个库是什么

## 1.1 一句话认识 SQLite

**SQLite** 是**嵌入式关系型数据库**——一个文件就是一个完整数据库，不需要安装服务器，Python 自带 `sqlite3` 模块，import 就能用。

```python
import sqlite3

conn = sqlite3.connect("mydb.db")      # 连接（不存在会自动创建文件）
cursor = conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, name TEXT)")
conn.execute("INSERT INTO t (name) VALUES (?)", ("张三",))
conn.commit()                           # 提交
print(conn.execute("SELECT * FROM t").fetchall())
conn.close()
```

## 1.2 为什么到处都是 SQLite

- **零配置**：不用装服务、不用配账号密码，文件即数据库。
- **单文件**：整个数据库就是一个 .db 文件，复制即备份。
- **Python 内置**：`import sqlite3` 直接可用。
- 移动端（iOS/Android）、桌面软件、小网站的首选存储。

**局限**（什么时候该换 MySQL/PostgreSQL）：高并发写入（多用户同时写会锁库）、海量数据（几 GB 以上）、多机部署。单机中小型应用 SQLite 完全够。

## 1.3 关系型数据库的基本概念

| 术语 | 白话解释 |
|---|---|
| 表（table） | 像 Excel 的 Sheet，有行有列 |
| 行（row） | 一条数据 |
| 列（column） | 一个字段 |
| 主键（primary key） | 唯一标识一行的字段（身份证号） |
| 外键（foreign key） | 指向别的表主键的字段（关联用） |
| SQL | 操作数据库的语言 |

---

# 第 2 章 核心概念与原理

## 2.1 连接、游标、事务

- **连接（connection）**：程序和数据库文件之间的通道。
- **游标（cursor）**：执行 SQL 并取结果的"指针"。
- **事务（transaction）**：一组要么全成要么全败的操作；`commit()` 提交生效，`rollback()` 回滚撤销。

```python
conn = sqlite3.connect("mydb.db")
cur = conn.cursor()          # 拿游标
cur.execute("...")           # 执行 SQL
conn.commit()                # 写操作必须提交！
conn.close()                 # 用完关闭
```

## 2.2 参数化查询（防 SQL 注入的第一原则）

**绝对不要**用字符串拼接拼 SQL：

```python
# ❌ 危险：SQL 注入（输入 `'; DROP TABLE t; --` 会删表）
name = input("名字：")
conn.execute(f"SELECT * FROM t WHERE name='{name}'")

# ✅ 安全：参数占位符 ?（sqlite3 自动转义）
conn.execute("SELECT * FROM t WHERE name=?", (name,))
```

## 2.3 数据类型（SQLite 是"弱类型"）

| SQLite 类型 | 说明 |
|---|---|
| INTEGER | 整数 |
| REAL | 小数 |
| TEXT | 文本 |
| BLOB | 二进制 |
| NULL | 空 |

SQLite 灵活（不强制类型），但**建议遵守类型规范**，避免数据混乱。

---

# 第 3 章 安装与版本

**无需安装**——Python 标准库自带：

```python
import sqlite3
print(sqlite3.sqlite_version)    # 查看版本
```

---

# 第 4 章 API 全面讲解

> 标注：✅ = 必会；➕ = 推荐；🧪 = 进阶

## 4.1 连接与内存库（✅）

```python
import sqlite3

conn = sqlite3.connect("mydb.db")     # 文件库（不存在自动建）
conn = sqlite3.connect(":memory:")    # 内存库（关连接就没了，测试用）
```

**连接参数**：

```python
conn = sqlite3.connect("mydb.db",
    timeout=30,          # 锁等待 30 秒（默认 5 秒）
    check_same_thread=False,  # 允许跨线程使用（多线程 Web 服务必需！）
)
```

## 4.2 执行 SQL 的几种方式（✅）

```python
conn = sqlite3.connect("mydb.db")
cur = conn.cursor()

# 建表（IF NOT EXISTS 防重复）
cur.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER DEFAULT 18,
    email TEXT UNIQUE
)""")

# 增
cur.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("张三", 25))
conn.commit()                          # 写操作必须 commit

# 查（三种取结果方式）
cur.execute("SELECT * FROM users")
rows = cur.fetchall()                  # 全部：[(1, '张三', 25, None), ...]
row = cur.fetchone()                   # 一条：None 或元组
rows2 = cur.fetchmany(10)              # 10 条

# 改
cur.execute("UPDATE users SET age=? WHERE name=?", (26, "张三"))
conn.commit()

# 删
cur.execute("DELETE FROM users WHERE id=?", (1,))
conn.commit()

conn.close()
```

## 4.3 row_factory：让结果变成字典（✅ 强烈推荐）

默认 fetchall 返回**元组**（`(1, '张三')`），字段多了容易搞混。设成字典：

```python
conn.row_factory = sqlite3.Row      # 既能按下标也能按名字取
cur = conn.execute("SELECT id, name FROM users")
for r in cur.fetchall():
    print(r["id"], r["name"])       # 按字段名取值
    print(dict(r))                  # 转成真字典
```

## 4.4 事务控制（✅ 数据安全核心）

```python
try:
    conn.execute("INSERT INTO users (name) VALUES (?)", ("张三",))
    conn.execute("INSERT INTO users (name) VALUES (?)", ("李四",))
    conn.commit()                    # 全部成功 → 提交
except Exception:
    conn.rollback()                  # 任一失败 → 全部回滚
    raise
```

**自动提交模式**（简化事务）：

```python
conn = sqlite3.connect("mydb.db", isolation_level=None)  # 自动提交
conn.execute("INSERT ...")           # 不用手动 commit
```

## 4.5 常用 SQL 语法速查（➕）

```sql
-- 查询
SELECT * FROM users;
SELECT name, age FROM users WHERE age > 20 ORDER BY age DESC LIMIT 10;
SELECT COUNT(*) FROM users;
SELECT age, COUNT(*) FROM users GROUP BY age;        -- 分组统计

-- 模糊
SELECT * FROM users WHERE name LIKE '%张%';

-- 关联（JOIN）
SELECT u.name, o.title FROM users u
  JOIN posts o ON o.user_id = u.id;

-- 索引（查询快）
CREATE INDEX idx_users_age ON users(age);

-- 改表结构
ALTER TABLE users ADD COLUMN phone TEXT;
```

## 4.6 错误处理（➕）

```python
import sqlite3

try:
    conn.execute("INSERT INTO users (name) VALUES (?)", (None,))  # NOT NULL 违反
except sqlite3.IntegrityError as e:
    print("完整性约束违反：", e)     # 主键重复/非空/唯一
except sqlite3.OperationalError as e:
    print("操作错误（表不存在/锁）", e)
```

## 4.7 备份与导出（🧪）

```python
# 备份到新文件
dst = sqlite3.connect("backup.db")
conn.backup(dst)
dst.close()

# 导出 SQL 脚本
with open("dump.sql", "w", encoding="utf-8") as f:
    for line in conn.iterdump():
        f.write(line + "\n")
```

---

# 第 5 章 实战项目案例

## 案例 1（入门级）：通讯录

```python
import sqlite3

conn = sqlite3.connect("contacts.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    remark TEXT DEFAULT ''
)""")

def add(name, phone, remark=""):
    cur.execute("INSERT INTO contacts (name, phone, remark) VALUES (?,?,?)",
                (name, phone, remark))
    conn.commit()
    print(f"已添加：{name}")

def search(kw):
    rows = cur.execute(
        "SELECT * FROM contacts WHERE name LIKE ? OR phone LIKE ?",
        (f"%{kw}%", f"%{kw}%")).fetchall()
    for r in rows:
        print(f"{r['id']}｜{r['name']}｜{r['phone']}｜{r['remark']}")

add("张三", "13800000001")
add("李四", "13800000002", "同事")
search("138")
conn.close()
```

## 案例 2（进阶级）：带统计的文章表

```python
import sqlite3
from datetime import datetime

conn = sqlite3.connect("blog.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT,
    category TEXT DEFAULT '未分类',
    view_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
)""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_cat ON posts(category)")

def create_post(title, content, category):
    cur.execute("INSERT INTO posts (title, content, category, created_at) VALUES (?,?,?,?)",
                (title, content, category, datetime.now().isoformat()))
    conn.commit()

def incr_view(pid):
    cur.execute("UPDATE posts SET view_count = view_count + 1 WHERE id=?", (pid,))
    conn.commit()

def stats():
    rows = cur.execute("""SELECT category, COUNT(*) AS cnt, SUM(view_count) AS views
                          FROM posts GROUP BY category""").fetchall()
    for r in rows:
        print(f"{r['category']}：{r['cnt']} 篇，共 {r['views']} 次阅读")

create_post("Python 入门", "正文...", "教程")
create_post("Flask 实战", "正文...", "教程")
create_post("美食分享", "正文...", "生活")
incr_view(1); incr_view(1); incr_view(2)
stats()
conn.close()
```

## 案例 3（综合）：**连接池版多线程安全写入**（Web 服务场景）

```python
"""多线程环境下安全使用 SQLite：连接池 + check_same_thread=False + WAL 模式"""
import sqlite3
import threading
import queue

class SQLitePool:
    """简单连接池：多线程各拿各的连接"""
    def __init__(self, db_path, max_conn=5):
        self._pool = queue.Queue(max_conn)
        for _ in range(max_conn):
            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")    # WAL 模式：读写不互斥，并发更好
            conn.execute("PRAGMA busy_timeout=30000")  # 锁等待 30 秒
            self._pool.put(conn)

    def get(self):
        return self._pool.get()

    def put(self, conn):
        self._pool.put(conn)

pool = SQLitePool("app.db")

# 初始化表
conn = pool.get()
conn.execute("""CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    msg TEXT,
    ts TEXT DEFAULT (datetime('now'))
)""")
conn.commit()
pool.put(conn)

def write_log(msg):
    conn = pool.get()
    try:
        conn.execute("INSERT INTO logs (msg) VALUES (?)", (msg,))
        conn.commit()
    finally:
        pool.put(conn)          # 用完归还，绝不泄漏

# 并发写测试
threads = [threading.Thread(target=write_log, args=(f"日志-{i}",)) for i in range(20)]
for t in threads: t.start()
for t in threads: t.join()

conn = pool.get()
print("总日志数：", conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0])
conn.close()
```

**要点**：`check_same_thread=False`（跨线程）+ 连接池（每线程独立连接）+ WAL 模式（读写并发优化）+ `busy_timeout`（锁等待）——**这是 SQLite 多线程 Web 服务的标准配置**。

---

# 第 6 章 进阶内容（大神之路）

## 6.1 PRAGMA 优化指令

```python
conn.execute("PRAGMA journal_mode=WAL")      # 写读并行，防锁
conn.execute("PRAGMA synchronous=NORMAL")    # 平衡安全与速度
conn.execute("PRAGMA cache_size=-8000")      # 缓存 8MB（负数为 KB 单位）
conn.execute("PRAGMA foreign_keys=ON")       # 开启外键约束（默认关！）
```

## 6.2 外键与级联（需先开 foreign_keys）

```python
conn.execute("PRAGMA foreign_keys=ON")
conn.execute("""CREATE TABLE users (
    id INTEGER PRIMARY KEY, name TEXT)""")
conn.execute("""CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE)""")
# ON DELETE CASCADE：删用户自动删他的文章
```

## 6.3 全文搜索（FTS5）

```python
conn.execute("CREATE VIRTUAL TABLE posts_fts USING fts5(title, content)")
conn.execute("INSERT INTO posts_fts (title, content) VALUES (?, ?)", ("Python", "入门教程"))
rows = conn.execute("SELECT * FROM posts_fts WHERE posts_fts MATCH 'Python'").fetchall()
```

## 6.4 性能建议

- 大量插入用 `executemany`（一次传多条，快百倍）。
- 查询条件字段建索引。
- 只 SELECT 需要的列，别 `SELECT *`。
- 用 `conn.executescript(sql_script)` 批量执行建表脚本。

---

# 第 7 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 忘 commit | 数据没存 | 写操作后 `conn.commit()` |
| database is locked | 并发写入锁库 | timeout 加大 + WAL 模式 + busy_timeout |
| 多线程报错 | `SQLite objects created in a thread can only be used in that same thread` | `check_same_thread=False` + 连接池 |
| 外键不生效 | 删主表子表还在 | `PRAGMA foreign_keys=ON`（每次连接都要开） |
| SQL 注入 | 数据被删/被改 | 永远用 `?` 参数化 |
| 中文乱码 | 读写中文异常 | 连接后 `conn.text_factory = str`（Python3 默认正常）；文件 UTF-8 |
| 表已存在报错 | `table already exists` | 建表加 `IF NOT EXISTS` |
| 元组取值晕 | `(1, '张三')` 分不清字段 | `conn.row_factory = sqlite3.Row` |
| 改表结构失败 | 无法删列 | SQLite 支持有限；重建表 + 数据迁移 |
| 数据库文件损坏 | `database disk image is malformed` | 用 `.backup` 定期备份；恢复用 `PRAGMA integrity_check` |

---

# 第 8 章 学习路径与自测

**学习路径**：
1. 连接 + 建表 + 插入（半天）
2. SELECT/WHERE/ORDER BY/LIMIT（1 天）
3. UPDATE/DELETE + commit（半天）
4. 参数化防注入（半天，必配）
5. row_factory 字典模式（半天）
6. 事务与回滚（1 天）
7. 表关系 JOIN + 外键（1 天）
8. 索引与性能（半天）
9. 多线程安全（连接池 + WAL）（1 天）
10. 案例 1→3 手写（2 天）

**自测题**：
1. `fetchall`/`fetchone`/`fetchmany` 区别？
2. 为什么必须用 `?` 占位符而不是字符串拼接？
3. `commit` 和 `rollback` 各什么时候用？
4. `row_factory = sqlite3.Row` 有什么用？
5. `database is locked` 怎么解决？（三个手段）
6. 多线程用 SQLite 要哪两个关键设置？
7. 外键级联删除怎么开启和配置？
8. 索引有什么用？怎么建？
9. 内存库 `:memory:` 什么时候用？
10. 综合：设计文章表（含分类、浏览量、时间）并写出建表+统计 SQL。

**答案提示**：
1. fetchall 全取（列表）；fetchone 取一条；fetchmany(n) 取 n 条。
2. 占位符自动转义，防 SQL 注入；拼接会执行恶意 SQL。
3. 写操作成功后 commit 提交；出错时 rollback 回滚（配合 try/except）。
4. 让查询结果能按字段名取值（r["name"]），不再用索引。
5. timeout 加大、WAL 模式、busy_timeout 设置锁等待。
6. `check_same_thread=False` + 连接池（每线程独立连接）。
7. 每次连接 `PRAGMA foreign_keys=ON` + 表定义 `REFERENCES ... ON DELETE CASCADE`。
8. 加速查询；`CREATE INDEX idx_name ON table(col)`。
9. 测试/临时数据，关连接即消失，不需要落盘。
10. 参考案例 2：posts 表 + category/view_count/created_at + GROUP BY 统计。

---

> 下一篇：《python-markdown（独立版）》——Markdown 转 HTML 从零到精通。
