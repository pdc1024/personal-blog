# 第三方库全面教程 · Selenium

> 面向初学者：这是**零基础起步**的浏览器自动化库全套教程，假设你只会最基础 Python 语法。术语第一次出现都有白话解释。
> 适用版本：Selenium 4.x ｜ 配套知识：配合《Playwright》对比学习（两者能力重叠，选一主一辅）、配合《Requests/BeautifulSoup4》解析、配合《Pillow》处理截图。
> 学习目标：从"没碰过自动化"到"能用 Selenium 驱动真实浏览器完成登录、抓数据、测试、截图"，并理解它与 Playwright 的异同。

## 第 1 章 这个库是什么

### 1.1 一句话认识 Selenium

**Selenium** 是历史最悠久、生态最广的**浏览器自动化库**——它通过 **WebDriver**（浏览器驱动）遥控真实浏览器（Chrome、Edge、Firefox、Safari），让代码像真人一样点击、输入、翻页、截图。

```python
from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()           # 打开 Chrome
driver.get("https://example.com")     # 访问网址
print(driver.title)                   # 打印标题
driver.quit()                         # 关闭
```

### 1.2 Selenium vs Playwright（先看清江湖格局）

| 对比 | Selenium | Playwright |
| --- | --- | --- |
| 历史 | 2004 年至今，生态最大 | 2019 年微软出品，后起之秀 |
| 浏览器 | Chrome/Edge/Firefox/Safari | Chromium/Firefox/WebKit |
| 驱动管理 | 需下载 chromedriver（4.6+ 自动管理） | 自带内核 `playwright install` |
| 等待 | 显式等待（WebDriverWait） | 自动等待（更省心） |
| 定位 | find_element（By.ID 等） | Locator + get_by_role（更语义化） |
| 多标签/多上下文 | 支持但繁琐 | Context 隔离（更强） |
| 网络拦截 | 4.x 有（CDP 支持） | 原生强支持 |

**选择建议**：新项目优先 Playwright（体验更好）；但**存量项目大量用 Selenium**，且 Selenium 支持语言更多（Java/JS/C#/Python），面试与运维场景仍常见——**两个都会，用 Playwright 时也看得懂 Selenium 代码**。

### 1.3 能干嘛

自动化测试、爬 JS 网站、批量填表、网页截图、UI 回归——和 Playwright 应用场景一致，选一个顺手的主力即可。

## 第 2 章 核心概念与原理

### 2.1 WebDriver：Selenium 的"遥控器"

浏览器厂商提供 **WebDriver**（一个可执行程序，如 chromedriver.exe），它通过 JSON Wire 协议接收 Selenium 的指令并操作浏览器。**Selenium 4.6+ 自带 Selenium Manager**，会自动下载匹配的 driver，不再需要手动配置。

### 2.2 定位元素：find_element 家族

Selenium 用 `By` 枚举指定定位方式：

```python
from selenium.webdriver.common.by import By

driver.find_element(By.ID, "username")        # 按 id
driver.find_element(By.CLASS_NAME, "card")    # 按 class
driver.find_element(By.NAME, "password")      # 按 name 属性
driver.find_element(By.TAG_NAME, "h1")        # 按标签
driver.find_element(By.CSS_SELECTOR, "div.card h2 a")   # CSS 选择器
driver.find_element(By.XPATH, "//div[@class='card']//a")  # XPath
driver.find_element(By.LINK_TEXT, "登录")      # 按链接文字
driver.find_element(By.PARTIAL_LINK_TEXT, "登")# 按链接文字部分匹配
```

- `find_element` 找第一个，找不到抛 `NoSuchElementException`。
- `find_elements` 找全部（列表），找不到返回空列表（**不报错**）。

### 2.3 显式等待 vs 隐式等待（新手最易踩）

- **隐式等待**：`driver.implicitly_wait(10)` 设一次，之后每个 find 最多等 10 秒（页面元素晚出现也能找到）。简单但"一刀切"。
- **显式等待**：针对某个条件精确等待，可配超时和轮询频率，**推荐**：

```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 最多等 10 秒，直到"登录成功"文字可见
WebDriverWait(driver, 10).until(
    EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'登录成功')]"))
)
```

**不要用 `time.sleep(3)` 硬等**——时快时慢还不稳。

## 第 3 章 安装与版本

```bash
pip install selenium
```

- 当前稳定版 4.x。**4.6+ 无需手动下 chromedriver**（Selenium Manager 自动处理）。
- 需要已安装 Chrome/Edge 浏览器（Selenium 驱动你电脑上的浏览器，不像 Playwright 自带内核）。
- 验证：

```python
from selenium import webdriver
driver = webdriver.Chrome()
driver.get("https://example.com")
print(driver.title)
driver.quit()
```

## 第 4 章 API 全面讲解（✅ = 必会 ｜ ➕ = 推荐 ｜ 🧪 = 进阶）

### 4.1 启动浏览器与选项（✅）

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless=new")            # 无头模式（新版写法）
options.add_argument("--window-size=1920,1080")   # 窗口大小（无头时必须设，否则元素可能缺失）
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")              # 服务器 Linux 常用
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")  # 改 UA
options.add_experimental_option("excludeSwitches", ["enable-automation"])  # 隐藏自动化提示

driver = webdriver.Chrome(options=options)
```

### 4.2 页面导航与信息（✅）

```python
driver.get("https://example.com")       # 打开网址（会等页面加载）
driver.title                            # 标题
driver.current_url                       # 当前 URL
driver.page_source                       # 完整 HTML 源码（交给 bs4 解析）
driver.get_window_size()                 # 窗口大小
driver.refresh()                         # 刷新
driver.back() / driver.forward()         # 后退/前进
driver.close()                           # 关闭当前标签页
driver.quit()                            # 关闭整个浏览器（结束必须！）
```

### 4.3 元素操作（✅）

```python
username = driver.find_element(By.ID, "username")
password = driver.find_element(By.NAME, "password")

username.send_keys("demo")               # 输入文字
username.clear()                         # 清空
password.send_keys("123456", Keys.ENTER) # 输入后回车
driver.find_element(By.ID, "submit").click()   # 点击

# 键盘
from selenium.webdriver.common.keys import Keys
element.send_keys(Keys.CONTROL, "a")     # 全选
element.send_keys(Keys.BACKSPACE)        # 删除

# 复选框/单选框
driver.find_element(By.ID, "agree").click()   # 勾选（click 即可切换）

# 下拉框
from selenium.webdriver.support.ui import Select
select = Select(driver.find_element(By.ID, "city"))
select.select_by_visible_text("广州")     # 按显示文本
select.select_by_value("gz")              # 按 value

# 属性与文本
element.text                              # 元素文本
element.get_attribute("href")             # 取属性
element.is_displayed()                    # 是否可见
element.is_enabled()                      # 是否可用
```

### 4.4 显式等待与条件（✅ 必须会）

```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

wait = WebDriverWait(driver, 10)   # 最多等 10 秒

wait.until(EC.presence_of_element_located((By.ID, "result")))        # 元素出现在 DOM
wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "card"))) # 元素可见
wait.until(EC.element_to_be_clickable((By.ID, "submit")))             # 元素可点击
wait.until(EC.text_to_be_present_in_element((By.ID, "status"), "完成")) # 文字变成
wait.until(EC.url_contains("order/success"))                          # URL 包含
wait.until(EC.number_of_elements_to_be((By.CLASS_NAME, "item"), 10))  # 元素数量

# 等元素消失（加载动画消失）
wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "loading")))
```

### 4.5 滚动与 JS 执行（➕）

```python
# 滚动到底部（无限加载页面常用）
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
# 滚动到元素可见
element = driver.find_element(By.ID, "footer")
driver.execute_script("arguments[0].scrollIntoView();", element)
# 直接执行任意 JS
driver.execute_script("return document.title")
```

### 4.6 截图（✅）

```python
driver.save_screenshot("screen.png")                    # 当前视口截图
element.screenshot("element.png")                       # 元素截图
driver.get_screenshot_as_png()                          # 返回二进制（配合 Pillow 处理）
```

### 4.7 多标签页（➕）

```python
driver.execute_script("window.open('https://example.com', '_blank');")
driver.switch_to.window(driver.window_handles[-1])      # 切到最新标签
print(driver.title)
driver.switch_to.window(driver.window_handles[0])       # 切回第一个标签
```

### 4.8 弹窗与 iframe（➕）

```python
# alert 弹窗
alert = driver.switch_to.alert
print(alert.text)
alert.accept()            # 确定
alert.dismiss()           # 取消

# iframe（页面嵌页面，元素要先切入才能找到）
driver.switch_to.frame("iframe-name")
driver.find_element(By.ID, "inner").click()
driver.switch_to.default_content()    # 切回主文档
```

### 4.9 文件上传与下载（➕）

```python
# 上传：input[type=file] 直接 send_keys 路径（Selenium 特色，很简单）
driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys("C:/data/a.csv")

# 下载：设置下载目录
options = Options()
options.add_experimental_option("prefs", {
    "download.default_directory": r"C:\data\downloads",
    "download.prompt_for_download": False,
})
```

### 4.10 移动端模拟（🧪）

```python
options = Options()
options.add_experimental_option("mobileEmulation", {"deviceName": "iPhone 13"})
driver = webdriver.Chrome(options=options)
```

## 第 5 章 实战项目案例（从小白到大神）

### 案例 1（入门级）：自动登录并验证

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

driver = webdriver.Chrome()
try:
    driver.get("https://example.com/login")
    driver.find_element(By.ID, "username").send_keys("demo")
    driver.find_element(By.ID, "password").send_keys("demo123")
    driver.find_element(By.ID, "submit").click()

    wait = WebDriverWait(driver, 10)
    wait.until(EC.text_to_be_present_in_element((By.ID, "welcome"), "欢迎"))
    print("登录成功，标题：", driver.title)
    driver.save_screenshot("login_ok.png")
finally:
    driver.quit()      # 必须关闭，防进程残留
```

### 案例 2（进阶级）：滚动加载页面的数据采集（Selenium + bs4）

```python
"""无限滚动页面：滚动 5 次后抓取全部卡片数据"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

driver = webdriver.Chrome()
try:
    driver.get("https://example.com/feed")
    # 循环滚动 5 次，每次等新内容加载
    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)                       # 滚动加载类场景必要的短暂等待
    html = driver.page_source               # 拿完整渲染后的 HTML

    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select("div.card"):
        items.append({
            "标题": card.select_one("h3").get_text(strip=True),
            "链接": card.select_one("a")["href"],
        })
    print("抓取", len(items), "条")
    import json
    with open("feed.json", "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
finally:
    driver.quit()
```

### 案例 3（综合）：**Selenium + Requests + bs4 + Pandas 采集与报表**

```python
"""电商商品采集：Selenium 登录拿动态页 → bs4 解析 → Requests 补接口 → pandas 统计 → CSV"""
import requests
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ① Selenium 登录 + 拿渲染后 HTML
driver = webdriver.Chrome()
try:
    driver.get("https://example.com/login")
    driver.find_element(By.ID, "username").send_keys("demo")
    driver.find_element(By.ID, "password").send_keys("demo123")
    driver.find_element(By.ID, "submit").click()
    WebDriverWait(driver, 10).until(EC.url_contains("home"))

    driver.get("https://example.com/products")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "product-card")))
    html = driver.page_source
finally:
    driver.quit()

# ② bs4 解析
soup = BeautifulSoup(html, "html.parser")
products = []
for card in soup.select(".product-card"):
    products.append({
        "名称": card.select_one(".name").get_text(strip=True),
        "价格": float(card.select_one(".price").get_text(strip=True).replace("¥", "")),
        "销量": int(card.select_one(".sales").get_text(strip=True)),
    })

# ③ Requests 补接口数据（如库存）
resp = requests.get("https://example.com/api/stock",
                    params={"ids": ",".join(str(i) for i in range(len(products)))},
                    timeout=10)
resp.raise_for_status()
stock_map = resp.json()

# ④ pandas 分析 + 导出
df = pd.DataFrame(products)
df["库存"] = df.index.map(stock_map)
df = df.dropna()
stats = df.groupby(pd.cut(df["价格"], bins=[0, 50, 100, 200, 10000],
                          labels=["<50", "50-100", "100-200", ">200"])).size()
print("商品总数：", len(df))
print(stats)
df.to_csv("products_report.csv", index=False, encoding="utf-8-sig")
```

## 第 6 章 进阶内容（大神之路）

### 6.1 Pytest 集成（selenium + pytest）

```python
# conftest.py
import pytest
from selenium import webdriver

@pytest.fixture
def driver():
    d = webdriver.Chrome()
    yield d
    d.quit()

# test_demo.py
def test_login(driver):
    driver.get("https://example.com/login")
    driver.find_element(By.ID, "username").send_keys("demo")
    driver.find_element(By.ID, "submit").click()
    assert "欢迎" in driver.page_source
```

### 6.2 失败自动截图（错误处理）

```python
import functools

def screenshot_on_error(func):
    @functools.wraps(func)
    def wrapper(driver, *a, **kw):
        try:
            return func(driver, *a, **kw)
        except Exception:
            driver.save_screenshot("error.png")
            raise
    return wrapper
```

### 6.3 页面对象模式（Page Object Model，测试工程标配）

把每个页面的定位和操作封装成类，页面变了只改一处：

```python
class LoginPage:
    def __init__(self, driver):
        self.driver = driver
        self.username = (By.ID, "username")
        self.submit = (By.ID, "submit")

    def login(self, user, pwd):
        self.driver.find_element(*self.username).send_keys(user)
        self.driver.find_element(*self.password).send_keys(pwd)
        self.driver.find_element(*self.submit).click()
```

### 6.4 网格与并行（Grid）

Selenium Grid 可把测试分发到多台机器/多种浏览器并行跑（企业级 CI 常用）；轻量场景用 pytest-xdist 多进程即可。

### 6.5 与 Playwright 的迁移思路

同一套"定位→操作→等待→断言"心智，迁移只是 API 名变化（见 Playwright 教程 6.6 对照表）。

## 第 7 章 高频坑与排查（新手必看）

| 坑 | 症状 | 解决 |
| --- | --- | --- |
| 找不到元素 | `NoSuchElementException` | 用显式等待 WebDriverWait；先 page_source 看页面是否加载 |
| 元素被遮挡点不到 | `element not interactable` | 先滚动到可见；等可点击；检查是否有遮罩层 |
| driver 启动报错 | `SessionNotCreated` / 版本不匹配 | Selenium 4.6+ 自动管理；老环境手动更新 chromedriver |
| 忘了 quit | 一堆 chromedriver 进程 | try/finally 里 quit() |
| 无头模式拿不到元素 | headless 下元素缺失 | 加 `--window-size=1920,1080`；或用真实窗口调试 |
| 隐式+显式等待混用 | 等待时间异常 | 二选一；推荐只用显式等待 |
| 页面跳转后还在旧页操作 | 找不到新页元素 | 显式等待新页特征元素/URL |
| time.sleep 硬等 | 时快时慢 | 换 WebDriverWait + EC |
| iframe 里找不到元素 | 明明有却找不到 | 先 `switch_to.frame` 再找 |
| 新版无头报错 | `headless` 参数失效 | 用 `--headless=new` |
| 弹窗挡住操作 | 卡在弹窗 | switch_to.alert 处理；或 page.on 类机制 |
| 中文输入异常 | 输入变乱码/丢字 | send_keys 前 clear()；必要时用 JS 赋值 + 触发事件 |

## 第 8 章 学习路径与自测

**学习路径**：
1. 安装 + 打开网页拿标题（半天）
2. find_element 七种定位（1 天）
3. 输入/点击/下拉/复选框（1 天）
4. WebDriverWait + EC 显式等待（1 天，重点）
5. 截图 + 滚动 + JS 执行（半天）
6. 多标签 + iframe + 弹窗（半天）
7. 案例 1→3 手写（2 天）
8. Pytest 集成 + 页面对象模式（1-2 天）
9. 对比 Playwright 迁移（1 天）

**自测题**：
1. `find_element` 和 `find_elements` 找不到元素时分别怎样？
2. 隐式等待和显式等待的区别？推荐哪个？
3. 为什么无头模式要设 window-size？
4. iframe 里的元素怎么定位？
5. 滚动加载页面怎么采集？
6. 怎么拿页面完整 HTML 给 bs4？
7. 结束时忘了 quit 会怎样？
8. Selenium 和 Playwright 最核心的差别是什么？
9. 元素被遮挡点不到怎么处理？
10. 综合：Selenium 登录 → 抓动态列表 → pandas 统计 → CSV，每步用什么？

**答案提示**：
1. find_element 找不到抛 NoSuchElementException；find_elements 返回空列表。
2. 隐式等待全局统一轮询；显式等待针对条件精确等待。推荐显式（WebDriverWait + EC）。
3. 无头下默认视口可能很小（如 800x600），元素可能不渲染或被判定不可见。
4. `driver.switch_to.frame("名字/id/元素")` 切入，用完 `switch_to.default_content()` 切回。
5. `execute_script("window.scrollTo(0, document.body.scrollHeight)")` 循环滚动，等新内容出现后再抓。
6. `driver.page_source` 返回完整 HTML 字符串，直接 `BeautifulSoup(html, "html.parser")`。
7. 残留 chromedriver 进程占内存；用 try/finally 或 fixture 保证 quit。
8. Playwright 自动等待 + Locator 语义化 + Context 隔离；Selenium 需要手动显式等待、定位繁琐。
9. 滚动到可见、等待可点击、检查遮挡层；实在不行 JS click。
10. 参考案例 3：find_element/send_keys 登录 → page_source → bs4 → pandas DataFrame → to_csv。

<hr>

> 下一篇：《Pytest》——把自动化脚本升级成规范测试，失败自动留证据。
