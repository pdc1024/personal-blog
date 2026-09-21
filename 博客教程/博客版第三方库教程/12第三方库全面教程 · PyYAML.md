# 第三方库全面教程 · PyYAML

> 面向初学者：博客文章的 front-matter 和批量导入文件都是 YAML，PyYAML 负责解析。
> 学完这份教程，你能全面掌握 YAML 的读写、安全加载、自定义类型、多文档。
> 适用版本：PyYAML 6.x ｜ 博客项目：`app.py` 的 `parse_front_matter`（第 674 行）

---

# 第 1 章 这个库是什么

## 1.1 一句话定位

PyYAML 是 Python 的 **YAML 解析与生成库**。

**YAML** 是一种"给人看也给人写"的配置文件格式，靠缩进表示层级，比 JSON 少括号：

```yaml
title: 我的第一篇博客
tags: [python, flask]
published: true
views: 128
```

一句话：**PyYAML 是博客的"配置翻译官"**——把 YAML 文本翻译成 Python 字典，也能反向写。

## 1.2 YAML vs JSON

| 对比 | YAML | JSON |
|---|---|---|
| 注释 | 支持 `#` | 不支持 |
| 可读性 | 高 | 低 |
| 缩进 | 敏感 | 不敏感 |
| 转义 | 少 | 多 |
| 解析器 | PyYAML | 标准库 json |

配置文件用 YAML，数据交换用 JSON。

## 1.3 一个最小例子

```python
import yaml

text = "title: 你好\ntags: [a, b]\n"
data = yaml.safe_load(text)
print(data)   # {'title': '你好', 'tags': ['a', 'b']}
```

---

# 第 2 章 核心概念与原理

## 2.1 YAML 三种基本结构

| 结构 | 写法 | Python |
|---|---|---|
| 映射 | `key: value`（冒号后空格） | dict |
| 序列 | `- 项` | list |
| 标量 | `hello`/`42`/`true` | str/int/bool |

## 2.2 加载器与安全（最核心的坑）

| 加载器 | 能解析 | 安全？ |
|---|---|---|
| `safe_load` | 纯数据 | ✅ **永远用它** |
| `load` | 任意 Python 对象 | ❌ 危险！ |
| `FullLoader` / `UnsafeLoader` | 同 load | ⚠️ |

**为什么 load 危险？** YAML 支持 `!!python/object/apply:os.system` 标签，恶意 YAML 能执行系统命令——著名的 YAML 反序列化漏洞。

**铁律：解析不可信 YAML 永远用 safe_load。**

## 2.3 front-matter

文章 Markdown 开头的 `---` 包裹的 YAML：

```
---
title: 我的文章
category: 编程
tags: [python]
---
正文从这里开始……
```

博客的 `parse_front_matter()` 正则切出 `---` 之间部分 → `safe_load` → 失败兜底。

---

# 第 3 章 安装与版本

```bash
pip install pyyaml
pip show pyyaml
```

PyYAML 6.x 要求 Python 3.6+。

---

# 第 4 章 API 全面讲解

## 4.1 解析

```python
import yaml

data = yaml.safe_load("title: 你好\ntags: [a, b]\n")
# {'title': '你好', 'tags': ['a', 'b']}

# 空文本返回 None
assert yaml.safe_load('') is None

# 异常
try:
    yaml.safe_load('a: 1\n b: 2')   # 缩进错
except yaml.YAMLError as e:
    print('YAML 错误:', e)
```

## 4.2 生成

```python
data = {'site': '我的博客', 'tags': ['python', 'flask'], 'published': True}

print(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
# site: 我的博客
# tags:
# - python
# - flask
# published: true
```

**关键参数**：

| 参数 | 作用 |
|---|---|
| `allow_unicode=True` | 中文原样输出（默认转 \uXXXX） |
| `sort_keys=False` | 保持字段顺序（默认按字母） |
| `default_flow_style=False` | 展开多行（默认单行） |

## 4.3 多文档

一个文件用 `---` 分隔多份：

```python
multi = "---\na: 1\n---\na: 2\n"
for doc in yaml.safe_load_all(multi):
    print(doc)
```

## 4.4 自定义构造器（进阶）

```python
import datetime
import yaml

def date_constructor(loader, node):
    return datetime.date.fromisoformat(loader.construct_scalar(node))

yaml.add_constructor('!date', date_constructor, Loader=yaml.SafeLoader)

data = yaml.safe_load("birthday: !date 1990-01-01\n")
# {'birthday': datetime.date(1990, 1, 1)}
```

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客的 parse_front_matter（app.py 第 674 行）

```python
import re
import yaml

def parse_front_matter(text):
    if text.startswith('---'):
        m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', text, flags=re.S)
        if m:
            try:
                meta = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError:
                meta = {}
            return meta, m.group(2)
    return {}, text
```

**要点**：`re.S` 让 `.` 匹配换行；`safe_load` 安全；失败兜底 `{}` 不打断导入。

## 5.2 独立示例：用 YAML 存设置

```python
import os, yaml

PATH = 'settings.yaml'

def load():
    if not os.path.exists(PATH):
        return {'theme': 'dark'}
    with open(PATH, encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def save(s):
    with open(PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(s, f, allow_unicode=True, sort_keys=False)
```

---

# 第 6 章 高频坑与排查

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | 用 load 解析外部 YAML | 可能执行任意代码 | 永远 safe_load |
| 2 | 缩进错 | ScannerError | 只用空格，冒号后空格 |
| 3 | dump 中文乱码 | \uXXXX | allow_unicode=True |
| 4 | 字段顺序乱 | 输出按字母 | sort_keys=False |
| 5 | 空文本解析 | 返回 None | `or {}` |
| 6 | yes/no 被转 bool | 字符串变 True/False | 加引号 `'yes'` |
| 7 | Tab 缩进 | 报错 | 只用空格 |

---

# 第 7 章 学习路径与自测

## 7.1 学习路径

- 半天：写 YAML + safe_load；
- 半天：dump 三参数；
- 半天：多文档 load_all；
- 1 天：自定义构造器（进阶）。

## 7.2 自测题

1. 为什么解析 YAML 永远用 safe_load？
2. dump 中文乱码怎么办？
3. `yaml.safe_load('')` 返回什么？
4. YAML 缩进用什么？
5. 怎么放多份独立数据？
6. `'yes'` 和 `yes` 解析结果有什么区别？

## 7.3 答案

1. load 支持 `!!python/object` 标签，恶意 YAML 可执行代码；safe_load 只解析纯数据。
2. 加 `allow_unicode=True`。
3. 返回 None；取字段前 `or {}`。
4. 只用空格（Tab 报错）。
5. `---` 分隔，`safe_load_all` 逐个读。
6. `'yes'` 是字符串；`yes` 被 YAML 1.1 解析成 True。

## 7.4 进一步学习

- 官方文档：https://pyyaml.org/
- YAML 语法：https://yaml.org/

---

> 下一篇：python-dateutil —— 智能日期处理全面教程
