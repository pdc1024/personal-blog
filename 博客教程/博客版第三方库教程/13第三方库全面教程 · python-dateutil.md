# 第三方库全面教程 · python-dateutil

> 面向初学者：博客导入文章时，各种格式的日期字符串靠它识别。
> 学完这份教程，你会掌握"解析任意日期写法"、"月份加减"、"重复规则"和时区处理——标准库 datetime 的四大短板它全补齐了。
> 适用版本：python-dateutil 2.x ｜ 博客项目：`app.py` 导入文章的日期解析

---

# 第 1 章 这个库是什么

## 1.1 一句话定位

python-dateutil 是 Python 标准库 **datetime 的增强包**，专门解决四个短板：

| 短板 | 标准库 datetime | dateutil 解决 |
|---|---|---|
| 字符串转日期 | 手写 strptime，格式错就崩 | `parser.parse('2026年9月7日')` 智能识别 |
| 月份加减 | `timedelta(months=1)` 报错 | `relativedelta(months=1)` 正确进位 |
| 重复日程 | 完全没有 | `rrule` 生成每天/每周规则 |
| 时区 | 笨重的 tzinfo | `tz.gettz('Asia/Shanghai')` |

一句话：**dateutil 是 datetime 的"保姆"**。

## 1.2 一个最小例子

```python
from dateutil import parser
d = parser.parse('2026年9月7日')
print(d)   # 2026-09-07 00:00:00
```

---

# 第 2 章 核心概念与原理

## 2.1 parser：怎么"什么日期都能认"

内部维护一套灵活规则：先把字符串拆成"年/月/日/时间/时区"片段，再按常见顺序组合。代价是偶尔猜错（`01/02/2026` 是 1 月 2 日还是 2 月 1 日？），用 `dayfirst` 参数告诉它习惯。

## 2.2 relativedelta vs timedelta

```python
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

d = datetime(2026, 3, 31)
d + timedelta(days=30)        # 2026-04-30
# d + timedelta(months=1)    # ❌ TypeError

d + relativedelta(months=1)   # 2026-04-30
d + relativedelta(months=1, days=2)  # 2026-05-02
```

**核心**：relativedelta 是"日历时长"，正确处理 1 月 31 日 + 1 个月 = 2 月 28/29 日。

## 2.3 时区

```python
from dateutil import tz
sh = tz.gettz('Asia/Shanghai')
ny = tz.gettz('America/New_York')
```

---

# 第 3 章 安装与版本

```bash
pip install python-dateutil
pip show python-dateutil
```

**注意**：包名是 `python-dateutil`，`pip install dateutil` 是另一个包（会被坑）。

---

# 第 4 章 API 全面讲解

## 4.1 parser.parse：智能解析

```python
from dateutil import parser

parser.parse('2026-09-07')
parser.parse('Sep 7, 2026')
parser.parse('2026/09/07 14:30')
parser.parse('2026年9月7日')
parser.parse('now')
parser.parse('yesterday')

# 参数
parser.parse('01/02/2026', dayfirst=True)   # 按日月年
parser.parse('14:30', default=datetime(2026,1,1))  # 缺的年月补
```

## 4.2 relativedelta：日历加减

```python
d + relativedelta(months=1)
d + relativedelta(years=1, months=2)
d - relativedelta(weeks=2)
d + relativedelta(day=1)              # 当月 1 号
d + relativedelta(weekday=relativedelta.FR)  # 下个周五
```

## 4.3 rrule：重复规则

```python
from dateutil.rrule import rrule, DAILY, WEEKLY

list(rrule(DAILY, count=5, dtstart=datetime(2026,9,1)))
# 每天一次共 5 次

list(rrule(WEEKLY, byweekday=[0,2,4], count=10,
           dtstart=datetime(2026,9,1)))
# 周一三五
```

## 4.4 tz：时区

```python
from dateutil import tz
sh = tz.gettz('Asia/Shanghai')
d = datetime(2026,9,7,12, tzinfo=sh)
print(d.astimezone(tz.gettz('America/New_York')))
```

---

# 第 5 章 实战示例

## 5.1 项目内示例：批量导入日期兜底

```python
from dateutil import parser as dp
from datetime import datetime

def parse_date_or_now(s):
    if not s or not str(s).strip():
        return datetime.now()
    try:
        d = dp.parse(str(s))
        return d.replace(tzinfo=None)   # 去时区，避免归档差 8 小时
    except Exception:
        return datetime.now()
```

## 5.2 独立示例：归档按月分组

```python
from datetime import datetime
from collections import defaultdict
posts = [datetime(2026,9,1), datetime(2026,8,15), datetime(2026,1,3)]
groups = defaultdict(list)
for d in posts:
    groups[(d.year, d.month)].append(d)
```

---

# 第 6 章 高频坑与排查

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | timedelta 加月份 | TypeError | 用 relativedelta |
| 2 | 01/02 解析错 | 月日反 | dayfirst=True |
| 3 | 带时区字符串 | 差 8 小时 | replace(tzinfo=None) |
| 4 | 纯数字被误解析 | 奇怪日期 | 先判断类型再 parse |
| 5 | 装错包 | import dateutil 失败 | pip install python-dateutil |
| 6 | 解析失败中断导入 | 一条坏数据崩 | try/except 兜底 |

---

# 第 7 章 学习路径与自测

## 7.1 学习路径

- 半天：parse 各种日期；
- 半天：relativedelta 加减；
- 半天：时区；
- 1 天：rrule（日程应用）。

## 7.2 自测题

1. `timedelta(months=1)` 为什么报错？
2. `parse('01/02/2026')` 和 `dayfirst=True` 区别？
3. 带 `+00:00` 的日期为什么差 8 小时？
4. rrule 的 count 和 until 区别？
5. 为什么博客日期解析要 try/except？
6. relativedelta 的 `day=1` 参数是什么意思？

## 7.3 答案

1. timedelta 只支持秒/分/时/天/周；月份用 relativedelta。
2. 默认月日年（1 月 2 日）；dayfirst=True 日月年（2 月 1 日）。
3. UTC 时间被当本地存；replace(tzinfo=None) 或统一本地时区。
4. count 限次数；until 限截止日。
5. 批量导入一条坏数据不能拖垮整个导入。
6. "设置当月 1 号"而不是"加 1 天"。

## 7.4 进一步学习

- 官方文档：https://dateutil.readthedocs.io/

---

> 下一篇：waitress —— 生产级 WSGI 服务器全面教程
