# 第三方库全面教程 · Requests

> 面向初学者：这是**零基础起步**的 HTTP 请求库全套教程，假设你只会最基础 Python 语法。术语第一次出现都有白话解释。
> 适用版本：Requests 2.3x ｜ 配套知识：配合《BeautifulSoup4》做爬虫、配合《Playwright》做"轻量接口 + 重量级浏览器"分工。
> 学习目标：从"不知道怎么让 Python 访问网页"到"熟练用 Requests 调接口、写爬虫、处理各种请求场景"。

## 第 1 章 这个库是什么

### 1.1 一句话认识 Requests

**Requests** 是 Python 里**发 HTTP 请求**的第一库。HTTP 请求就是"你的程序向某个网址要数据（GET）或提交数据（POST）"的动作——打开网页、查询天气接口、登录网站、上传文件，底层都是 HTTP 请求。

**为什么需要它**：Python 自带 urllib 也能发请求，但写法繁琐（编码处理、重定向、cookie 都要手动管）。Requests 把这些全部封装好，一句 `requests.get(url)` 就能拿到结果，被誉为"Python 最优雅的库"。

```python
import requests

resp = requests.get("https://api.github.com")   # 一行发请求
print(resp.status_code)                          # 200 = 成功
print(resp.json())                               # 直接拿到 JSON 数据
```

### 1.2 Requests vs 浏览器（和 Playwright 的分工）

| 对比 | Requests | 浏览器（Playwright） |
| --- | --- | --- |
| 是否渲染 JS | 否（只拿服务器原始响应） | 是（完整渲染页面） |
| 速度 | 极快 | 慢（要开浏览器） |
| 拿数据 | 接口 JSON / 静态 HTML | 动态渲染后的页面 |
| 适用 | 调 API、爬静态站、自动化测试接口 | 登录复杂站、爬 JS 站点、UI 测试 |

**黄金分工**：能用 Requests 拿到数据就绝不开浏览器（快 100 倍）；Requests 拿不到（JS 渲染）才上 Playwright。

### 1.3 能干嘛

1. 调用各种 API（天气、翻译、支付、大模型接口……都是 HTTP）
2. 写爬虫抓取网页数据（配合解析库）
3. 自动化测试接口（发请求验证返回）
4. 模拟登录、上传下载文件
5. 监控服务是否在线

## 第 2 章 核心概念与原理

### 2.1 HTTP 请求与响应：一次"网上要东西"的完整过程

```
你的程序 ──请求──▶ 服务器
   │ 方法(GET/POST)      │
   │ URL                 │
   │ 请求头 Headers      │
   │ 请求体 Body         │
   └────响应◀────────────┘
       状态码 200/404...
       响应头
       响应体（网页/JSON/文件）
```

**请求方法**（最常用两个）：
- **GET**：向服务器"要"数据（看网页、查接口）。参数拼在 URL 上：`?page=1&size=10`
- **POST**：向服务器"提交"数据（登录、发文章、上传）。数据放在请求体里，不暴露在 URL

### 2.2 状态码：服务器回话的"暗号"

| 状态码 | 含义 | 常见场景 |
| --- | --- | --- |
| 200 | 成功 | 一切正常 |
| 301/302 | 重定向（跳转到别的地址） | 网址变更、登录跳转 |
| 400 | 请求写错了 | 参数不对 |
| 401/403 | 没登录 / 没权限 | 需要认证、被反爬拦截 |
| 404 | 页面不存在 | 地址写错 |
| 429 | 请求太频繁被限流 | 爬太快 |
| 500/502/503 | 服务器出错 | 对方服务器问题，不是你的错 |

### 2.3 Session（会话）：保持登录状态的"连号牌"

HTTP 是无状态的——每次请求都是"陌生人"（服务器不记得你）。**Cookie** 是服务器发给你、你下次带回去的"身份牌"。

**Session 对象**自动帮你保管 Cookie：用同一个 session 发多个请求，登录一次，后续请求都自动带登录状态。

```python
session = requests.Session()                    # 建一个"会话"
session.post("https://x.com/login", data={...}) # 登录（session 记住 cookie）
session.get("https://x.com/profile")            # 自动带 cookie，已经是登录状态
```

### 2.4 超时（timeout）：防止程序卡死

网络请求可能永远没响应。**必须设置 timeout**（超时秒数），超过就抛异常，程序不会卡死：

```python
requests.get(url, timeout=10)        # 10 秒没响应就报错
requests.get(url, timeout=(3, 10))   # 连接超时 3 秒，读取超时 10 秒（推荐）
```

## 第 3 章 安装与版本

```bash
pip install requests
```

Requests 是纯 Python 库，安装秒完成，**无任何依赖坑**。查看版本：`pip show requests`。当前稳定版 2.3x，API 十年没变过，学会终身受用。

## 第 4 章 API 全面讲解（✅ = 必会 ｜ ➕ = 推荐 ｜ 🧪 = 进阶）

### 4.1 GET 请求（✅ 最常用）

```python
import requests

# 最简形式
resp = requests.get("https://api.github.com/repos/python/cpython")

# 带查询参数（?key=value）——用 params 字典，不要手拼 URL
resp = requests.get("https://api.github.com/search/repositories",
                    params={"q": "python", "page": 2, "per_page": 10})

# 带请求头（伪装浏览器、指定格式）
resp = requests.get("https://x.com",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                             "Accept": "application/json"})

# 带超时（必须养成习惯）
resp = requests.get("https://x.com", timeout=10)
```

**为什么用 params 而不是手拼 URL**：字典会自动处理特殊字符转义（如中文、`&`、`?`），手拼容易出错。

### 4.2 响应对象：拿到结果后怎么读（✅）

```python
resp = requests.get("https://api.github.com", timeout=10)

resp.status_code        # 状态码：200 成功
resp.ok                 # True/False（200 返回 True，等价 status_code < 400）
resp.headers            # 响应头（字典）：resp.headers.get("Content-Type")
resp.url                # 最终请求的 URL（有重定向时看这个）
resp.text               # 响应正文（字符串）
resp.content            # 响应正文（bytes 字节，下载文件用这个）
resp.json()             # 把 JSON 正文解析成 Python 字典/列表
resp.encoding           # 编码方式（中文乱码时改这个）
resp.cookies            # 响应里的 cookie
resp.elapsed            # 请求耗时（秒），测试性能用
```

**关键点**：
- `resp.json()` 只有响应是 JSON 才能用，否则抛异常——先 `try/except` 或先看 `resp.text`。
- 中文乱码：`resp.encoding = "utf-8"` 后再 `resp.text`，或直接 `resp.content.decode("utf-8")`。

### 4.3 状态码检查：raise_for_status（✅ 强烈建议）

```python
resp = requests.get("https://x.com/api/data", timeout=10)
resp.raise_for_status()     # 状态码不是 2xx/3xx 就抛 HTTPError 异常
# 后面代码只有成功才会执行到
data = resp.json()
```

**为什么推荐**：不检查的话，404 返回的"错误页面文本"会被你当成正常数据继续处理，出错难排查。`raise_for_status()` 让错误立刻暴露。

### 4.4 POST 请求（✅ 登录/提交数据）

```python
# ① 表单提交（最常用，模拟填表）
resp = requests.post("https://x.com/login",
                     data={"username": "demo", "password": "123456"},
                     timeout=10)

# ② JSON 提交（调 API 接口）
resp = requests.post("https://x.com/api/articles",
                     json={"title": "你好", "content": "正文"},
                     timeout=10)

# ③ 同时带参数和头
resp = requests.post("https://x.com/api/upload",
                     json={...},
                     headers={"Authorization": "Bearer <token>"},
                     timeout=10)
```

**`data` vs `json` 的区别**：`data={}` 发送的是表单格式（application/x-www-form-urlencoded）；`json={}` 发送的是 JSON 格式（application/json）。**后端要求哪种就用哪种**，用错了对方解析不到数据。

### 4.5 其他方法（➕）

```python
requests.put(url, json={...})       # 更新资源（整个替换）
requests.patch(url, json={...})     # 局部更新
requests.delete(url)                # 删除资源
requests.head(url)                  # 只拿响应头（检查链接是否有效，超快）
requests.options(url)               # 查看服务器支持哪些方法
```

### 4.6 Session 复用（➕ 登录态/连接复用）

```python
session = requests.Session()

# 登录
session.post("https://x.com/login", data={"u": "a", "p": "b"}, timeout=10)

# 后续请求自动带 cookie
resp1 = session.get("https://x.com/my/page", timeout=10)
resp2 = session.get("https://x.com/my/data", timeout=10)

# Session 还复用底层 TCP 连接（同一主机多次请求更快）
# 用完关闭（释放连接池）
session.close()
```

### 4.7 文件下载与上传（✅）

```python
# 下载文件（图片/压缩包/PDF）：用 content 写二进制
resp = requests.get("https://x.com/logo.png", timeout=30)
with open("logo.png", "wb") as f:
    f.write(resp.content)

# 大文件下载：用 stream 流式保存，不占内存
resp = requests.get("https://x.com/big.zip", stream=True, timeout=60)
with open("big.zip", "wb") as f:
    for chunk in resp.iter_content(chunk_size=8192):   # 8KB 一块一块写
        f.write(chunk)

# 上传文件（multipart 表单）
resp = requests.post("https://x.com/upload",
                     files={"file": open("report.pdf", "rb")},
                     timeout=60)
```

### 4.8 代理与 SSL（➕ 进阶网络）

```python
# 走代理（公司内网/爬虫常用）
resp = requests.get("https://x.com",
                    proxies={"http": "http://127.0.0.1:7890",
                             "https": "http://127.0.0.1:7890"},
                    timeout=10)

# 忽略 SSL 证书错误（测试自签证书网站）——生产环境不要随便关！
resp = requests.get("https://self-signed.test", verify=False, timeout=10)
# 关闭 InsecureRequestWarning 警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

### 4.9 异常处理（✅ 必须会）

```python
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

try:
    resp = requests.get("https://x.com/api", timeout=(3, 10))
    resp.raise_for_status()
    data = resp.json()
except Timeout:
    print("请求超时")
except ConnectionError:
    print("网络不通/连不上服务器")
except RequestException as e:      # 所有 requests 异常的基类，兜底
    print("请求失败：", e)
```

**异常继承关系**：`RequestException` 是所有请求异常的父类——最稳的写法是只捕 `RequestException` 兜底，再单独捕具体的 `Timeout`/`ConnectionError` 做不同处理。

### 4.10 重试（🧪 进阶）

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3,                     # 最多重试 3 次
              backoff_factor=1,            # 间隔 1s、2s、4s 递增
              status_forcelist=[500, 502, 503])   # 这些状态码才重试
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://", adapter)
```

## 第 5 章 实战项目案例（从小白到大神）

### 案例 1（入门级）：天气查询脚本 —— 调公开 API

```python
import requests

resp = requests.get("https://api.open-meteo.com/v1/forecast",
                    params={"latitude": 23.13, "longitude": 113.26,   # 广州
                            "current_weather": "true"},
                    timeout=10)
resp.raise_for_status()
data = resp.json()
cur = data["current_weather"]
print("广州当前温度：", cur["temperature"], "°C")
print("风速：", cur["windspeed"], "km/h")
```

**要点**：params 传参、raise_for_status 检查、json() 解析。

### 案例 2（进阶级）：带登录态的会员数据采集 + 保存

```python
import requests

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

# ① 登录
login_resp = session.post("https://example.com/login",
                          data={"username": "demo", "password": "demo123"},
                          timeout=10)
login_resp.raise_for_status()
print("登录状态码：", login_resp.status_code)

# ② 拉取会员页数据（session 自动带登录 cookie）
resp = session.get("https://example.com/api/members",
                   params={"page": 1, "size": 50}, timeout=10)
resp.raise_for_status()
members = resp.json()["list"]

# ③ 保存
import json
with open("members.json", "w", encoding="utf-8") as f:
    json.dump(members, f, ensure_ascii=False, indent=2)
print("保存", len(members), "条会员数据")
```

### 案例 3（综合）：接口监控 + 重试 + 报警 + 报表

```python
"""简易服务健康监控：每轮检查 3 个接口，记录状态，超时/错误重试，输出日报"""
import csv
import time
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URLS = {
    "首页": "https://example.com/",
    "API": "https://example.com/api/health",
    "登录接口": "https://example.com/api/login",
}


def make_session():
    s = requests.Session()
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def check_one(session, name, url):
    start = time.time()
    try:
        resp = session.get(url, timeout=(3, 8))
        ok = resp.status_code < 400
        return {
            "时间": datetime.now().strftime("%H:%M:%S"),
            "接口": name, "状态码": resp.status_code,
            "耗时ms": round((time.time() - start) * 1000, 1),
            "结果": "✅ 正常" if ok else "⚠️ 异常",
        }
    except requests.Timeout:
        return {"时间": datetime.now().strftime("%H:%M:%S"), "接口": name,
                "状态码": "-", "耗时ms": round((time.time() - start) * 1000, 1),
                "结果": "❌ 超时"}
    except requests.RequestException as e:
        return {"时间": datetime.now().strftime("%H:%M:%S"), "接口": name,
                "状态码": "-", "耗时ms": round((time.time() - start) * 1000, 1),
                "结果": f"❌ {type(e).__name__}"}


def main():
    session = make_session()
    rows = [check_one(session, name, url) for name, url in URLS.items()]
    with open("健康日报.csv", "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["时间", "接口", "状态码", "耗时ms", "结果"])
        if f.tell() == 0:
            writer.writeheader()
        writer.writerows(rows)
    bad = [r for r in rows if r["结果"] != "✅ 正常"]
    print("检查完成：", "全部正常" if not bad else f"{len(bad)} 个异常")


if __name__ == "__main__":
    main()
```

**可扩展**：配定时任务（或用《Celery》/系统计划任务）每 5 分钟跑一次，异常时发邮件/钉钉通知——这就是真实运维监控的雏形。

## 第 6 章 进阶内容（大神之路）

### 6.1 结合 Playwright 的"登录态复用"

Playwright 登录后把 cookie 导出，Requests 直接复用（重型登录交给浏览器，轻量采集交给 Requests）：

```python
# Playwright 侧：登录后导出 cookie
# context.storage_state(path="state.json")

# Requests 侧：加载 cookie
import json
import requests

with open("state.json", encoding="utf-8") as f:
    state = json.load(f)
cookies = {c["name"]: c["value"] for c in state["cookies"]}
session = requests.Session()
session.cookies.update(cookies)
# 现在 requests 可以直接访问需要登录的接口（快且轻）
resp = session.get("https://example.com/api/data", timeout=10)
```

### 6.2 并发请求提速（ThreadPoolExecutor）

```python
from concurrent.futures import ThreadPoolExecutor
import requests

def fetch(url):
    return requests.get(url, timeout=10).json()

urls = [f"https://api.example.com/items/{i}" for i in range(20)]
with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(fetch, urls))   # 20 个请求并发，秒级完成
```

### 6.3 配合 BeautifulSoup4 做静态爬虫（见该库教程）

### 6.4 安全注意（重要）

- **不要**在代码里硬编码账号密码（用环境变量/配置文件）。
- 爬虫要控制频率、遵守对方 robots.txt 和条款，只采集合法数据。
- 不要用 Requests 对目标发起高频暴力请求（可能违法并给对方造成损失）。

## 第 7 章 高频坑与排查（新手必看）

| 坑 | 症状 | 解决 |
| --- | --- | --- |
| 没设 timeout | 程序卡住不退出 | 所有请求都带 `timeout=(3, 10)` |
| 中文乱码 | resp.text 乱码 | `resp.encoding = "utf-8"` 或 `resp.content.decode("utf-8")` |
| 不检查状态码 | 404 页面被当数据用 | 养成 `resp.raise_for_status()` 习惯 |
| resp.json() 报错 | JSONDecodeError | 返回的不是 JSON：先打印 resp.text 看实际内容 |
| 登录后下次请求又没登录 | 没保持 cookie | 用 Session 对象；别每次新建请求 |
| 被服务器 403 | 反爬 / 缺 UA | 带浏览器 UA 头；降低频率；必要时换 Playwright |
| data 和 json 混用 | 后端拿不到参数 | 看清后端要求：表单用 data，接口用 json |
| 下载大文件卡内存 | 内存暴涨 | 用 stream=True + iter_content 流式写 |
| 重定向后 URL 变了 | 拿到的是别的页面 | 看 resp.url；必要时 allow_redirects=False 手动处理 |
| 代理没生效 | 请求直连失败 | proxies 里 http/https 都写；或设环境变量 |

## 第 8 章 学习路径与自测

**学习路径**：
1. GET 请求 + 响应对象四件套（status_code/text/json/headers）（半天）
2. params / headers / timeout（半天）
3. POST 的 data 与 json（半天）
4. Session 登录态（半天）
5. raise_for_status + 异常处理（半天）
6. 文件下载上传（半天）
7. 案例 1→2 手写（1 天）
8. 配合 BeautifulSoup4 写爬虫（1-2 天）
9. 并发 + 重试（1 天）
10. 结合 Playwright 做"登录复用 + 轻量采集"组合（1 天，参考第 6 章 6.1）

**自测题**：
1. GET 和 POST 的区别？什么时候用哪个？
2. `resp.text` 和 `resp.content` 的区别？下载文件用哪个？
3. 为什么推荐 `raise_for_status()`？
4. 中文乱码怎么解决？
5. Session 解决什么问题？
6. `data={}` 和 `json={}` 的区别？
7. 不设 timeout 会发生什么？
8. 状态码 403 / 429 分别代表什么？怎么应对？
9. 怎么把 Playwright 的登录态给 Requests 用？
10. 大文件下载为什么用 stream？

**答案提示**：
1. GET 要数据（参数在 URL），POST 提交数据（参数在请求体）；取数据/看页面用 GET，登录/发文章/上传用 POST。
2. text 是解码后的字符串，content 是原始字节；下载文件用 content（或 stream 迭代）。
3. 非 2xx/3xx 直接抛异常，错误立刻暴露，不会把错误页当数据。
4. 设 `resp.encoding="utf-8"` 或用 `resp.content.decode("utf-8")`。
5. 自动保管 cookie（登录态）+ 复用 TCP 连接（更快）。
6. data 是表单格式，json 是 JSON 格式；按后端要求选。
7. 网络挂起时程序永久卡住；设 timeout 超时即报错。
8. 403=没权限/被反爬（换 UA、减速、换浏览器）；429=请求太频繁（限速、退避）。
9. Playwright 导出 storage_state（cookie），Requests 用 session.cookies.update 加载。
10. stream=True + iter_content(chunk) 逐块写盘，避免整个文件进内存。

<hr>

> 下一篇：《BeautifulSoup4》——Requests 拿到网页源码后，用它把数据"拆"出来，爬虫黄金搭档。
