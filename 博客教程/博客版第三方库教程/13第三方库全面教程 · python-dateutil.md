# 第三方库全面教程 · python-dateutil

> 面向初学者到进阶者：博客批量导入文章时，各种格式的日期字符串靠它识别。
> 学完这份教程，你会掌握 parser 智能解析、relativedelta 日历加减、rrule 重复规则、tz 时区。
>
> 适用版本：python-dateutil 2.x ｜ 博客项目：`app.py` 导入文章日期解析

---

# 第 1 章 认识 dateutil

## 1.1 一句话定位

dateutil 是标准库 datetime 的增强包，补四个短板：

| 短板 | 标准库 | dateutil |
|---|---|---|
| 字符串解析 | strptime 死板 | parser.parse 智能识别 |
| 月份加减 | timedelta 不支持 | relativedelta |
| 重复规则 | 无 | rrule |
| 时区 | 笨重 | tz.gettz |

## 1.2 安装

```bash
pip install python-dateutil
# 注意包名是 python-dateutil，不是 dateutil
```

---

# 第 2 章 核心 API

## 2.1 parser.parse 智能解析

```python
from dateutil import parser

parser.parse('2026-09-07')
parser.parse('Sep 7, 2026')
parser.parse('2026年9月7日')
parser.parse('01/02/2026', dayfirst=True)   # 按日月年
```

## 2.2 relativedelta 日历加减

```python
from dateutil.relativedelta import relativedelta
from datetime import datetime

d = datetime(2026, 3, 31)
d + relativedelta(months=1)        # 2026-04-30
d + relativedelta(months=1, days=2)
d + relativedelta(weekday=relativedelta.FR)  # 下个周五
```

## 2.3 rrule 重复规则

```python
from dateutil.rrule import rrule, DAILY, WEEKLY
list(rrule(DAILY, count=5, dtstart=datetime(2026,9,1)))
list(rrule(WEEKLY, byweekday=[0,2,4], count=10, dtstart=...))
```

## 2.4 tz 时区

```python
from dateutil import tz
sh = tz.gettz('Asia/Shanghai')
ny = tz.gettz('America/New_York')
```

---

# 第 3 章 项目实战

## 3.1 批量导入日期兜底

```python
from dateutil import parser as dp
from datetime import datetime

def parse_date_or_now(s):
    if not s or not str(s).strip():
        return datetime.now()
    try:
        return dp.parse(str(s)).replace(tzinfo=None)
    except Exception:
        return datetime.now()
```

---

# 第 4 章 高频坑

| # | 坑 | 解决 |
|---|---|---|
| 1 | timedelta 加月份 | TypeError，用 relativedelta |
| 2 | 01/02 解析错 | dayfirst=True |
| 3 | 时区差 8 小时 | replace(tzinfo=None) |
| 4 | 装错包 | pip install python-dateutil |
| 5 | 坏数据崩导入 | try/except 兜底 |

---

# 第 5 章 自测

1. `timedelta(months=1)` 为什么报错？
2. `parse('01/02/2026')` 和 dayfirst 区别？
3. 为什么导入日期要 replace(tzinfo=None)？
4. relativedelta 的 `day=1` 参数？

**答案**：
1. timedelta 只支持秒/分/时/天/周；月份用 relativedelta。
2. 默认月日年；dayfirst=True 日月年。
3. 去掉时区，统一本地存。
4. 设置当月 1 号。

---

> 下一篇：waitress —— 生产级 WSGI 服务器全面教程
