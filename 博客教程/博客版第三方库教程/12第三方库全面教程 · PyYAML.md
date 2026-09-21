# 第三方库全面教程 · PyYAML

> 面向初学者到进阶者：博客文章 front-matter 和批量导入文件都是 YAML。
> 学完这份教程，你会掌握 safe_load 安全铁律、dump 三参数、多文档、自定义构造器。
>
> 适用版本：PyYAML 6.x ｜ 博客项目：`app.py` 第 674 行 `parse_front_matter`

---

# 第 1 章 认识 YAML

## 1.1 一句话定位

YAML 是"给人看的配置格式"，靠缩进表示层级：

```yaml
title: 我的文章
tags: [python, flask]
published: true
```

一句话：**PyYAML 把 YAML 文本翻译成 Python 字典**。

## 1.2 YAML vs JSON

| 对比 | YAML | JSON |
|---|---|---|
| 注释 | `#` | 无 |
| 可读性 | 高 | 低 |
| 缩进 | 敏感 | 不敏感 |

---

# 第 2 章 加载器与安全

## 2.1 三种加载器

| 加载器 | 能解析 | 安全？ |
|---|---|---|
| `safe_load` | 纯数据 | ✅ 永远用它 |
| `load` | 任意 Python 对象 | ❌ 危险 |
| `FullLoader` | 同 load | ⚠️ |

**铁律**：解析不可信 YAML 永远 `safe_load`。`load` 支持 `!!python/object/apply:os.system`，恶意文件能执行命令。

---

# 第 3 章 API

## 3.1 解析

```python
import yaml
data = yaml.safe_load("title: 你好\ntags: [a, b]\n")
# {'title': '你好', 'tags': ['a', 'b']}
```

## 3.2 生成

```python
yaml.safe_dump(data,
               allow_unicode=True,    # 中文不转 \uXXXX
               sort_keys=False,       # 保持字段顺序
               default_flow_style=False)
```

## 3.3 多文档

```python
for doc in yaml.safe_load_all(text):
    ...
```

## 3.4 自定义构造器

```python
def date_ctor(loader, node):
    return datetime.date.fromisoformat(loader.construct_scalar(node))

yaml.add_constructor('!date', date_ctor, Loader=yaml.SafeLoader)
```

---

# 第 4 章 项目实战

## 4.1 博客 parse_front_matter（app.py 第 674 行）

```python
import re, yaml

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

---

# 第 5 章 高频坑

| # | 坑 | 解决 |
|---|---|---|
| 1 | 用 load 解析外部 YAML | 永远 safe_load |
| 2 | 缩进错 | 只用空格 |
| 3 | 中文乱码 | allow_unicode=True |
| 4 | 字段顺序乱 | sort_keys=False |
| 5 | 空文本 | 返回 None，or {} |
| 6 | yes/no 变 bool | 加引号 `'yes'` |

---

# 第 6 章 自测

1. 为什么永远 safe_load？
2. dump 中文乱码怎么办？
3. `safe_load('')` 返回什么？
4. 怎么放多份独立数据？

**答案**：
1. load 能反序列化任意 Python 对象，恶意 YAML 可执行代码。
2. allow_unicode=True。
3. None，取字段前 or {}。
4. `---` 分隔，safe_load_all。

---

> 下一篇：python-dateutil —— 智能日期处理全面教程
