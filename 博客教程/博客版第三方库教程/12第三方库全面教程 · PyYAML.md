# 第三方库全面教程 · PyYAML

> 面向初学者：博客文章的头部信息（front-matter）和批量导入文件都是 YAML 写的，PyYAML 负责解析。学完这份教程，你能全面掌握 YAML 的读写、安全加载、自定义类型——不只会 `yaml.safe_load`。
> 适用版本：PyYAML 6.x ｜ 博客项目：`app.py` 的 `parse_front_matter` + `uploads/sample_batch.yaml`

---

# 第 1 章 这个库是什么

PyYAML 是 Python 的 **YAML 解析与生成库**。

**YAML 是什么？** 一种"给人看也给人写"的配置文件格式，靠缩进表示层级，比 JSON 更少符号、可读性更强：

```yaml
# 一个 YAML 例子
title: 我的第一篇博客      # 字符串
tags: [python, flask]     # 列表
published: true           # 布尔
views: 128                # 整数
```

一句话：**PyYAML 是博客的"配置翻译官"**——把 YAML 文本翻译成 Python 字典/列表，也能反向把 Python 数据写成 YAML 文本。

---

# 第 2 章 核心概念与原理

## 2.1 YAML 的三种基本结构

| YAML 结构 | 写法 | 变成 Python |
|---|---|---|
| 映射（键值对） | `key: value`（冒号后必须有空格！） | `dict` |
| 序列（列表） | `- 项目`（每项以减号开头） | `list` |
| 标量（单个值） | `hello` / `42` / `true` | str / int / bool |

```yaml
# 嵌套组合示例
site:
  name: 我的博客
  pages: [about, archive]     # 行内列表
categories:
  - 编程
  - 生活
```

## 2.2 加载器与安全（PyYAML 最核心的坑）

PyYAML 有多个"加载器"，安全级别不同：

| 加载器 | 能解析什么 | 安全吗 |
|---|---|---|
| `yaml.safe_load` | 纯数据（dict/list/str/int/bool/None） | ✅ 安全，**永远用它** |
| `yaml.load` | 任意 Python 对象（含 `!!python/object`） | ❌ **危险**！可被构造执行任意代码 |
| `yaml.FullLoader` / `UnsafeLoader` | 同 load | ⚠️ 仅信任的数据用 |

**为什么 load 危险？** YAML 支持 `!!python/object/apply:os.system` 这类标签，恶意 YAML 能让解析器执行系统命令——**这就是著名的 YAML 反序列化漏洞**。记住一条铁律：**解析不可信 YAML 永远用 `safe_load`**。

## 2.3 为什么博客叫它"front-matter"

文章 Markdown 文件开头的 `---` 包裹的 YAML 段就是 front-matter（元数据）：

```
---
title: 我的文章
category: 编程
tags: [python]
---
文章正文从这里开始……
```

博客的 `parse_front_matter()` 做的事：正则切出 `---` 之间的部分 → `safe_load` 成字典 → 失败时兜底。

---

# 第 3 章 安装与版本

```bash
pip install pyyaml
pip show pyyaml    # 版本验证（模块名 import yaml）
```

PyYAML 6.x 要求 Python 3.6+。

---

# 第 4 章 API 全面讲解

## 4.1 解析：safe_load 与安全变体

```python
import yaml

text = "title: 你好\ntags: [a, b]\n"
data = yaml.safe_load(text)
# {'title': '你好', 'tags': ['a', 'b']}

# 解析失败会抛 yaml.YAMLError（统一异常基类）
try:
    data = yaml.safe_load('a: 1\n b: 2')   # 缩进错了
except yaml.YAMLError as e:
    print('YAML 写错了：', e)
```

**坑**：空文本 `safe_load('')` 返回 `None`（不是空字典）——取字段前先 `or {}`。

## 4.2 生成：dump 与 safe_dump

```python
data = {'site': '我的博客', 'tags': ['python', 'flask'], 'published': True}

# 直接 dump
print(yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False))
# site: 我的博客
# tags:
# - python
# - flask
# published: true

# safe_dump 更保守（不会输出危险标签），推荐
print(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
```

**关键参数**：

| 参数 | 作用 | 什么时候用 |
|---|---|---|
| `allow_unicode=True` | 中文原样输出（默认会转成 \uXXXX 乱码！） | 有中文必开 |
| `sort_keys=False` | 保持字段顺序（默认按字母排序） | 想要"按我写的顺序" |
| `default_flow_style=False` | 列表/字典展开成多行（默认单行 `[a, b]`） | 给人看的配置 |
| `default_flow_style=True` | 紧凑单行 | 存机器数据 |

## 4.3 多文档：load_all / dump_all

一个 YAML 文件里可以用 `---` 分隔多份文档（博客的批量导入就是靠这个思路）：

```python
multi = "---\na: 1\n---\na: 2\n"
for doc in yaml.safe_load_all(multi):     # 返回生成器，逐个文档
    print(doc)   # {'a': 1}  {'a': 2}
```

## 4.4 自定义标签与构造器（🧪 进阶）

让 YAML 里出现自定义类型，比如日期：

```python
import datetime
import yaml

def date_constructor(loader, node):
    return datetime.date.fromisoformat(loader.construct_scalar(node))

yaml.add_constructor('!date', date_constructor, Loader=yaml.SafeLoader)

text = "birthday: !date 1990-01-01\n"
data = yaml.safe_load(text)
print(data['birthday'], type(data['birthday']))   # 1990-01-01 <class 'datetime.date'>
```

## 4.5 低级 API：compose / parse（了解）

```python
# compose：只解析成节点树（不做 Python 转换）
node = yaml.compose("a: 1")

# parse：逐事件流（用于自定义输出格式）
for event in yaml.parse("a: 1"):
    print(event.__class__.__name__)
```

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客的 front-matter 解析（对照真实代码）

```python
import re
import yaml

def parse_front_matter(text):
    """从 Markdown 文本里切出 --- 包裹的 YAML 元数据，返回 (meta, body)"""
    if text.startswith('---'):                        # 只有以 --- 开头才尝试切
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', text, flags=re.S)
        if match:
            try:
                meta = yaml.safe_load(match.group(1)) or {}   # 空内容兜底 {}
            except yaml.YAMLError:
                meta = {}                             # 解析失败不打断导入
            return meta, match.group(2)               # group(2) 是去掉头部后的正文
    return {}, text
```

**要点**：`re.S` 让 `.` 匹配换行；`safe_load` 永远安全；解析失败兜底为 `{}`——导入流程不因一个坏文件中断。

## 5.2 独立示例：用 YAML 存"设置"并安全读写

```python
import os
import yaml

SETTINGS_PATH = 'settings.yaml'

def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        return {'theme': 'dark', 'page_size': 10}
    with open(SETTINGS_PATH, encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def save_settings(settings):
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(settings, f, allow_unicode=True, sort_keys=False)

save_settings({'theme': 'light', 'page_size': 20, 'name': '我的博客'})
print(load_settings())
# {'theme': 'light', 'page_size': 20, 'name': '我的博客'}  ← 中文没乱码
```

---

# 第 6 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 用 load 解析外部 YAML | 可能执行任意代码 | 永远 `safe_load` |
| 缩进错 | `ScannerError` / `ParserError` | 只用空格缩进（别用 Tab）；冒号后必须有空格 |
| dump 中文乱码 | 变成 `\u4f60\u597d` | `allow_unicode=True` |
| 字段顺序乱了 | 输出被按字母排序 | `sort_keys=False` |
| 空文本解析 | 返回 `None`，取字段报错 | `safe_load(text) or {}` |
| 布尔值被转类型 | `'yes'/'no'/'on'` 变成 True/False | YAML 1.1 的旧行为；要字符串就加引号 `'yes'` |

---

# 第 7 章 学习路径与自测

**学习路径**：先会写 YAML + safe_load（半天）→ 学会 dump 三参数（半天）→ 多文档 load_all（半天）→ 自定义构造器（1 天，进阶）。

**自测题**：

1. 为什么解析 YAML 永远用 `safe_load` 不用 `load`？
2. `safe_dump(中文数据)` 输出乱码怎么办？
3. `yaml.safe_load('')` 返回什么？为什么处理？
4. YAML 里缩进用什么字符？
5. 一个 YAML 文件里怎么放多份独立数据？

**答案**：
1. load 支持 `!!python/object` 标签，恶意 YAML 可执行代码；safe_load 只解析纯数据。
2. 加 `allow_unicode=True`。
3. 返回 `None`；取字段前 `or {}` 兜底。
4. 只用空格（Tab 会报错）。
5. 用 `---` 分隔，`yaml.safe_load_all` 逐个读。

---

> 下一篇：python-dateutil —— 智能日期处理全面教程
