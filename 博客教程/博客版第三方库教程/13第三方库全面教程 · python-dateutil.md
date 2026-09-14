# 第三方库全面教程 · python-dateutil

> 面向初学者：博客导入文章时，各种格式的日期字符串靠它识别。学完这份教程，你会掌握"解析任意日期写法"、"月份加减"（timedelta 干不了的活）、"重复规则"和时区处理——Python 标准库 datetime 的四大短板，它全补齐了。
> 适用版本：python-dateutil 2.x ｜ 博客项目：`app.py` 导入文章的日期解析

---

# 第 1 章 这个库是什么

python-dateutil 是 Python 标准库 **datetime 的增强包**，专门解决标准库四个让人头疼的短板：

| 短板 | 标准库 datetime | dateutil 解决 |
|---|---|---|
| 字符串转日期 | 要手写 `strptime` 且格式写错就崩 | `parser.parse('2026年9月7日')` 智能识别 |
| 月份加减 | `timedelta(months=1)` 直接报错 | `relativedelta(months=1)` 正确进位 |
| 重复日程 | 完全没有 | `rrule` 生成"每天/每周/每月"规则 |
| 时区 | 只有笨重的 tzinfo 接口 | `tz.gettz('Asia/Shanghai')` 一行搞定 |

一句话：**dateutil 是 datetime 的"保姆"**——标准库只管基础，dateutil 管好用的部分。

---

# 第 2 章 核心概念与原理

## 2.1 parser：怎么做到"什么日期都能认"

`parser.parse()` 内部维护了一套灵活的解析规则：先把字符串拆成"年/月/日/时间/时区"片段，再按常见顺序组合，所以 `'2026-09-07'`、`'Sep 7, 2026'`、`'09/07/2026'`、`'2026年9月7日'` 都能识别。

**代价**：猜得多了，有时会"猜错"（比如 `'01/02/2026'` 到底是 1 月 2 日还是 2 月 1 日？）。所以有 `dayfirst` 参数让你告诉它你的习惯。

## 2.2 relativedelta 与 timedelta 的本质区别

`timedelta` 是"绝对时长"（86400 秒），**跨月/跨年时结果反直觉**：

```python
from datetime import datetime, timedelta
d = datetime(2026, 3, 31)
print(d + timedelta(days=30))   # 2026-04-30（碰巧对）
print(d + timedelta(months=1))  # ❌ TypeError：timedelta 没有 months！

from dateutil.relativedelta import relativedelta
print(d + relativedelta(months=1))  # 2026-04-30
print(d + relativedelta(months=1, days=2))  # 2026-05-02，可叠加
```

**核心认知**：relativedelta 是"日历时长"——按"月/年"这个单位计算，会正确处理 1 月 31 日 + 1 个月 = 2 月 28/29 日这类边界。

## 2.3 时区：dateutil 的 tz 模块

标准库时区要自己写 `tzinfo` 子类，dateutil 一行搞定：

```python
from dateutil import tz
tz.gettz('Asia/Shanghai')      # 按 IANA 时区名
tz.tzlocal()                   # 本机时区
tz.tzutc()                     # UTC
```

---

# 第 3 章 安装与版本

```bash
pip install python-dateutil
pip show python-dateutil   # 版本验证（模块名 import dateutil）
```

要求 Python 3.6+。注意 `pip install dateutil` 是另一个库（会被坑），包名必须是 `python-dateutil`。

---

# 第 4 章 API 全面讲解

## 4.1 parser.parse：智能日期解析（✅ 项目用到）

```python
from dateutil import parser

parser.parse('2026-09-07')          # datetime(2026, 9, 7, 0, 0)
parser.parse('Sep 7, 2026')         # 英文缩写月
parser.parse('2026/09/07 14:30')    # 带时间
parser.parse('2026年9月7日')        # 中文
parser.parse('now')                 # 当前时间
parser.parse('yesterday')           # 昨天（英文）

# 常用参数
parser.parse('01/02/2026', dayfirst=True)   # 按"日月年"解释 → 2 月 1 日
parser.parse('2026-09-07 没有日期格式', fuzzy=True)  # fuzzy 容错：跳过不认识的部分
parser.parse('14:30', default=datetime(2026, 1, 1))  # 缺的年月用 default 补
```

**博客用法**：

```python
try:
    post.created_at = date_parser.parse(str(date_str))
except Exception:
    pass    # 解析失败静默跳过，不打断批量导入
```

## 4.2 relativedelta：日历加减（➕ 强烈推荐）

```python
from datetime import datetime
from dateutil.relativedelta import relativedelta

d = datetime(2026, 1, 31)

d + relativedelta(months=1)          # 2026-02-28（自动处理月尾！）
d + relativedelta(years=1, months=2) # 2027-03-31
d - relativedelta(weeks=2)           # 2026-01-17
d + relativedelta(day=1)             # 当月 1 号：2026-01-01（day 是"设置日"不是"加天"）
d + relativedelta(weekday=relativedelta.FR)   # 下一个周五
d + relativedelta(months=1, weekday=relativedelta.SA(2))  # 下个月的第 2 个周六
```

**和 timedelta 混用**：`d + timedelta(days=3) + relativedelta(months=1)` 可以一起加。

## 4.3 rrule：重复规则（🧪 日程神器）

`rrule` 生成"满足某规则的日期序列"——日历应用、定时提醒的核心：

```python
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY
from datetime import datetime

# 每天一次，共 5 次
list(rrule(DAILY, count=5, dtstart=datetime(2026, 9, 1)))
# [9/1, 9/2, 9/3, 9/4, 9/5]

# 每周一、三、五，持续到月底
list(rrule(WEEKLY, byweekday=[0, 2, 4], dtstart=datetime(2026, 9, 1), until=datetime(2026, 9, 30)))

# 每月最后一天
list(rrule(MONTHLY, bymonthday=-1, count=3, dtstart=datetime(2026, 1, 1)))
```

**常用参数**：`count`（次数）、`until`（截止日）、`interval`（间隔，如每 2 周）、`bysetpos`（第几个）、`byweekday`（周几，0=周一）。`rruleset` 还能合并多条规则（如"工作日 + 特定假日排除"）。

## 4.4 tz：时区处理

```python
from dateutil import tz
from datetime import datetime

sh = tz.gettz('Asia/Shanghai')
ny = tz.gettz('America/New_York')

d = datetime(2026, 9, 7, 12, 0, tzinfo=sh)
print(d.astimezone(ny))     # 自动换算时区：2026-09-06 23:00-04:00
```

**博客归档差 8 小时的经典问题**：导入时如果字符串带了 `+00:00`（UTC），存进 SQLite 的 naive datetime 会比本地早 8 小时。处理：`d.replace(tzinfo=None)` 丢掉时区，或统一用本地时区。

## 4.5 easter（彩蛋）与 parser 的 info 参数（了解）

```python
from dateutil.easter import easter
print(easter(2026))   # 2026 年复活节日期（有意思但很少用到）
```

---

# 第 5 章 实战示例

## 5.1 项目内示例：批量导入的日期兜底策略

```python
from dateutil import parser as date_parser
from datetime import datetime

def parse_date_or_now(date_str):
    """日期解析：能认就认，认不出就用当前时间，绝不中断导入"""
    if not date_str or not str(date_str).strip():
        return datetime.now()          # 空值 → 当前时间
    try:
        d = date_parser.parse(str(date_str))
        return d.replace(tzinfo=None)  # 去时区，避免归档差 8 小时
    except Exception:
        return datetime.now()          # 解析失败 → 当前时间兜底
```

## 5.2 独立示例：归档按月分组 + "近 30 天"统计

```python
from datetime import datetime
from dateutil.relativedelta import relativedelta

posts = [datetime(2026, 9, 1), datetime(2026, 8, 15), datetime(2026, 1, 3)]

# 按年月分组（归档页核心逻辑）
from collections import defaultdict
groups = defaultdict(list)
for d in posts:
    groups[(d.year, d.month)].append(d)
print(dict(groups))   # {(2026, 9): [...], (2026, 8): [...], (2026, 1): [...]}

# "近 30 天" 的起始点（月份加减的经典场景）
cutoff = datetime.now() - relativedelta(months=1)
recent = [d for d in posts if d >= cutoff]
print(recent)
```

---

# 第 6 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| timedelta 加月份 | `TypeError: 'months' is an invalid keyword` | 用 `relativedelta(months=...)` |
| 01/02/2026 解析错 | 月和日搞反 | `parser.parse(s, dayfirst=True)` 告诉它习惯 |
| 带时区的字符串 | 归档时间差 8 小时 | 存库前 `.replace(tzinfo=None)` 或统一本地时区 |
| 纯数字被误解析 | `'123'` 变成奇怪日期 | 先判断类型/长度再决定是否 parse |
| parse 抛异常 | 一条坏数据中断导入 | try/except 兜底 + 返回默认值 |
| 装了错误的包 | `import dateutil` 失败 | 包名是 `python-dateutil`（不是 dateutil） |

---

# 第 7 章 学习路径与自测

**学习路径**：先会 parse 各种日期（半天）→ 学会 relativedelta 加减（半天）→ 时区处理（半天）→ rrule 重复规则（1 天，做日程/提醒功能时必学）。

**自测题**：

1. `timedelta(months=1)` 为什么报错？替代方案是什么？
2. `parser.parse('01/02/2026')` 和 `dayfirst=True` 的区别？
3. 导入带 `+00:00` 时区的日期，为什么归档会差 8 小时？怎么修？
4. rrule 的 `count` 和 `until` 有什么区别？
5. 为什么博客的日期解析要 try/except 包起来？

**答案**：
1. timedelta 只支持秒/分/时/天/周；月份用 `relativedelta(months=1)`。
2. 默认按"月日年"解释（1 月 2 日）；dayfirst=True 按"日月年"（2 月 1 日）。
3. UTC 时间被当成本地时间存；`.replace(tzinfo=None)` 或统一转本地时区。
4. count 限制总次数；until 限制截止日期。
5. 批量导入一条坏数据不能拖垮整个导入，解析失败静默兜底。

---

> 下一篇：waitress —— 生产级 WSGI 服务器全面教程
