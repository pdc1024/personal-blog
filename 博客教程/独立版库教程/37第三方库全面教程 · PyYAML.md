# 第三方库全面教程 · PyYAML（独立版）

> 面向初学者：本教程**独立成篇**，假设你会基础 Python 和 JSON。术语第一次出现都有白话解释。
> 适用版本：PyYAML 6.x ｜ 配套知识：与《Flask》配合（配置文件）、与《Requests》配合（API 配置）。
> 学习目标：从"只会用 JSON 存配置"到"能用 YAML 写复杂配置、安全加载、多文档解析，并理解 YAML 与 JSON 的关系"。

---

# 第 1 章 这个库是什么

## 1.1 一句话认识 PyYAML

**PyYAML** 是 Python 的 **YAML 解析库**：把 YAML 格式的文本转成 Python 对象（字典/列表），或把 Python 对象转回 YAML。

```python
import yaml

config = yaml.safe_load("""
site:
  name: 我的网站
  port: 8000
  debug: false
""")
print(config)                    # {'site': {'name': '我的网站', 'port': 8000, 'debug': False}}
```

## 1.2 YAML 是什么

**YAML**（"YAML Ain't Markup Language"）是一种**人类友好的数据格式**，用来写配置。相比 JSON：

| | JSON | YAML |
|---|---|---|
| 注释 | ❌ 不支持 | ✅ `# 注释` |
| 可读性 | 括号多，繁琐 | 缩进排版，清爽 |
| 多行文本 | 麻烦 | ✅ 原生支持 |
| 复杂嵌套 | 括号地狱 | 缩进清晰 |

**注意**：YAML 是 JSON 的超集——**合法的 JSON 一定是合法的 YAML**。

## 1.3 什么时候用 YAML

- 项目配置文件（网站配置、依赖清单、CI 配置、Docker Compose、K8s 清单）。
- 需要注释和人工编辑的配置。
- API 接口返回 YAML（少见，但存在）。

---

# 第 2 章 核心概念与原理

## 2.1 缩进即结构

YAML 用**空格缩进**表示层级（**不能用 Tab！**）：

```yaml
server:            # 字典：server 的值是下面缩进的字典
  host: 0.0.0.0
  port: 8000
  features:        # 列表
    - login
    - upload
```

对应 Python：

```python
{"server": {"host": "0.0.0.0", "port": 8000,
            "features": ["login", "upload"]}}
```

## 2.2 数据类型

```yaml
# 标量
str_value: hello          # 字符串
int_value: 42             # 整数
float_value: 3.14         # 小数
bool_true: true           # 布尔
bool_false: false
null_value: null          # None
date_value: 2026-09-15    # 日期（自动转 datetime.date）

# 复合
list_value: [1, 2, 3]     # 行内列表
dict_value: {a: 1, b: 2}  # 行内字典
```

## 2.3 safe_load vs load（安全第一）

- **`yaml.safe_load()`**：只解析基础类型（dict/list/str/int/float/bool/None）——**安全，永远用它**。
- **`yaml.load()`**：可构造任意 Python 对象（包括执行代码）——**危险！** 不要加载不可信 YAML。

---

# 第 3 章 安装与版本

```bash
pip install pyyaml
```

- 当前稳定版 6.x。
- 导入名是 `yaml`。
- 验证：`python -c "import yaml; print(yaml.__version__)"`。

---

# 第 4 章 API 全面讲解

> 标注：✅ = 必会；➕ = 推荐；🧪 = 进阶

## 4.1 加载：safe_load（✅）

```python
import yaml

# 从字符串
data = yaml.safe_load("name: 张三\nage: 25\n")

# 从文件
with open("config.yaml", "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

print(data)   # {'name': '张三', 'age': 25}
```

## 4.2 转储：safe_dump（✅）

```python
import yaml

data = {"site": {"name": "我的网站", "port": 8000}, "tags": ["a", "b"]}

# 转字符串
s = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
print(s)

# 写文件
with open("config.yaml", "w", encoding="utf-8") as f:
    yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
```

**参数**：
- `allow_unicode=True`：中文正常输出（不加会转成 `\uXXXX` 转义）。
- `sort_keys=False`：保持字典插入顺序（默认按字母排序）。
- `default_flow_style=False`：块状输出（默认就是块状）。
- `indent=2`：缩进（默认 2）。

## 4.3 多文档加载（➕）

一个 YAML 文件可用 `---` 分隔多个文档：

```yaml
# config.yaml
server:
  port: 8000
---
database:
  host: localhost
```

```python
import yaml

with open("config.yaml", encoding="utf-8") as f:
    docs = list(yaml.safe_load_all(f))     # 所有文档

print(docs[0])   # {'server': {'port': 8000}}
print(docs[1])   # {'database': {'host': 'localhost'}}
```

对应多文档转储：`yaml.safe_dump_all([doc1, doc2], f)`。

## 4.4 锚点与别名（🧪 YAML 特色）

```yaml
defaults: &defaults        # & 定义锚点
  timeout: 30
  retries: 3

server_a:
  <<: *defaults            # * 引用锚点（合并）
  port: 8000

server_b:
  <<: *defaults
  port: 9000
```

```python
# {'defaults': {'timeout': 30, 'retries': 3},
#  'server_a': {'timeout': 30, 'retries': 3, 'port': 8000},
#  'server_b': {'timeout': 30, 'retries': 3, 'port': 9000}}
```

**用途**：配置文件里复用公共片段，避免重复。

## 4.5 自定义构造器（🧪）

```python
import yaml

def env_constructor(loader, node):
    """支持 !env 标签：!env HOME → os.environ['HOME']"""
    import os
    key = loader.construct_scalar(node)
    return os.environ.get(key, "")

yaml.SafeLoader.add_constructor("!env", env_constructor)

data = yaml.safe_load("path: !env HOME")
print(data)   # {'path': 'C:\\Users\\Administrator'}
```

---

# 第 5 章 实战项目案例

## 案例 1（入门级）：应用配置中心

```python
"""从 YAML 读配置并驱动应用"""
import yaml

with open("app_config.yaml", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

print(f"应用名：{cfg['app']['name']}")
print(f"监听：{cfg['server']['host']}:{cfg['server']['port']}")
print(f"调试模式：{'开' if cfg['server']['debug'] else '关'}")
```

`app_config.yaml`：

```yaml
app:
  name: 我的应用
  version: 1.0.0
server:
  host: 127.0.0.1
  port: 8000
  debug: false
database:
  engine: sqlite
  path: data/app.db
logging:
  level: INFO
  file: logs/app.log
```

## 案例 2（进阶级）：Flask 项目配置分离

```python
"""用 YAML 管理 Flask 配置（环境隔离：开发/生产）"""
import yaml
from flask import Flask


def load_config(env="dev"):
    with open(f"config/{env}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

app = Flask(__name__)
cfg = load_config("dev")
app.config.update(
    SECRET_KEY=cfg["security"]["secret_key"],
    SQLALCHEMY_DATABASE_URI=cfg["database"]["uri"],
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=cfg["security"]["max_upload_mb"] * 1024 * 1024,
)
```

`config/dev.yaml`：

```yaml
database:
  uri: sqlite:///dev.db
security:
  secret_key: dev-secret-123
  max_upload_mb: 5
```

## 案例 3（综合）：**配置文件 + 多文档 + 锚点 的完整工具**

```python
"""通用配置工具：加载 + 校验 + 合并默认值"""
import yaml
from pathlib import Path


def load_config(path, default_path=None):
    """加载配置，并和默认配置深度合并（缺的字段用默认值）"""
    defaults = {}
    if default_path and Path(default_path).exists():
        defaults = yaml.safe_load(Path(default_path).read_text(encoding="utf-8")) or {}

    data = {}
    if Path(path).exists():
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

    # 简单深合并：默认值兜底
    def deep_merge(base, extra):
        for k, v in (extra or {}).items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                deep_merge(base[k], v)
            else:
                base[k] = v
        return base

    return deep_merge(defaults, data)


def dump_config(data, path):
    """写配置（备份旧文件）"""
    p = Path(path)
    if p.exists():
        p.rename(p.with_suffix(".yaml.bak"))
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                 encoding="utf-8")
    print(f"已写入 {path}")


# 使用：只写需要的字段，其余用默认
cfg = load_config("user_config.yaml", "default_config.yaml")
print(cfg["server"]["port"])       # 用户没写就用默认
```

---

# 第 6 章 进阶内容（大神之路）

## 6.1 性能：大文件

- 用 `yaml.CLoader`（C 扩展，快 10 倍）：`yaml.load(..., Loader=yaml.CSafeLoader)`。
- 装 PyYAML 时带 C 扩展：`pip install pyyaml` 默认编译，确认 `yaml.__with_libyaml__`。

## 6.2 与 pydantic 配合（配置校验）

```python
from pydantic import BaseModel
import yaml

class ServerCfg(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000

data = yaml.safe_load("port: abc")
cfg = ServerCfg(**data)   # 类型错误直接抛异常，配置错误早发现
```

## 6.3 安全建议

- **永远 `safe_load`**，不信任的文件绝不用 `load`。
- 生产环境配置中的密钥不要硬编码进 YAML——用环境变量（见 4.5 的 `!env`）。

---

# 第 7 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| Tab 缩进报错 | `found character that cannot start any token` | YAML 只用空格缩进，禁用 Tab |
| 中文变 \uXXXX | safe_dump 输出转义 | `allow_unicode=True` |
| 键顺序乱 | 输出被排序 | `sort_keys=False` |
| 布尔值被当字符串 | `'true'` | YAML 里写 `true/false`（无引号） |
| 日期被转对象 | `2026-09-15` 变 datetime | 正常行为；不想转用引号 `"2026-09-15"` |
| safe_load 报错 | `could not determine a constructor` | 文件含自定义标签；用对应构造器或清理 |
| 多文档只读第一篇 | 少数据 | `safe_load_all` |
| 锚点合并失效 | 字段没合并 | `<<:` 语法 + `*锚点名` 配对 |
| 键重复 | 后面的覆盖前面的 | YAML 默认后者覆盖；用规范校验工具检测 |
| load 安全警告 | `FullLoader` 被弃用 | 全部改用 `safe_load` |

---

# 第 8 章 学习路径与自测

**学习路径**：
1. YAML 语法基础（缩进/类型/列表字典）（半天）
2. safe_load / safe_dump（半天）
3. allow_unicode / sort_keys 参数（半天）
4. 文件读写配置（半天）
5. 多文档 safe_load_all（半天）
6. 锚点与别名（1 天）
7. Flask 配置分离（1 天）
8. 默认值合并工具（1 天，案例 3）
9. 自定义标签 !env（进阶，1 天）

**自测题**：
1. `safe_load` 和 `load` 区别？为什么用 safe_load？
2. YAML 缩进用什么字符？为什么？
3. `allow_unicode=True` 干什么？
4. `sort_keys=False` 干什么？
5. 一个 YAML 文件多个文档怎么分隔？怎么读？
6. 锚点和别名语法是什么？有什么用？
7. YAML 和 JSON 是什么关系？
8. 日期 `2026-09-15` 会被解析成什么？不想解析怎么办？
9. 中文输出转义怎么解决？
10. 综合：写一份含嵌套字典、列表、注释的网站配置 YAML 并加载。

**答案提示**：
1. safe_load 只解析基础类型（安全）；load 可构造任意对象（危险）。永远 safe_load。
2. 空格（不能用 Tab）——Tab 在不同编辑器宽度不同，YAML 规范禁止。
3. 输出中文时不转义成 \uXXXX。
4. 保持字典插入顺序（默认按字母排序）。
5. `---` 分隔；`yaml.safe_load_all(f)`。
6. `&锚点名` 定义、`*锚点名` 引用、`<<:` 合并；复用公共配置片段。
7. YAML 是 JSON 超集，合法 JSON 都是合法 YAML。
8. 解析成 `datetime.date`；用引号 `"2026-09-15"` 保持字符串。
9. `yaml.safe_dump(data, allow_unicode=True)`。
10. 参考案例 1：server 嵌套 + features 列表 + `# 注释`，safe_load 读取。

---

> 下一篇：《python-dateutil（独立版）》——日期时间处理从零到精通。
