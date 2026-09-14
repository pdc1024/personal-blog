# 第三方库全面教程 · Pytest

> 面向初学者：这是**零基础起步**的测试框架全套教程，假设你只会最基础 Python 语法和函数。术语第一次出现都有白话解释。
> 适用版本：Pytest 8.x ｜ 配套知识：配合《Playwright/Selenium》（自动化测试标配）、配合《Requests》（接口测试）、配合《Openpyxl/Pandas》（测试数据与报告）。
> 学习目标：从"写完代码手动点一遍"到"用 pytest 自动化验证一切，一条命令跑完全部检查并自动出报告"。

## 第 1 章 这个库是什么

### 1.1 一句话认识 Pytest

**Pytest** 是 Python **最主流的测试框架**：你写普通函数 + 一个 `assert`（断言，判断"是不是"），pytest 自动找到它们、逐个运行、把失败原因清楚地报出来。

```python
# test_math.py
def test_add():
    assert 1 + 1 == 2          # 断言成立 → 测试通过

def test_fail():
    assert 2 * 3 == 7          # 断言失败 → 测试失败，pytest 告诉你哪错了
```

运行：`pytest`（自动找 test_*.py 文件里的 test_* 函数，全部跑一遍）。

### 1.2 为什么需要它

- **防回归**：改了一个功能，旧功能坏了都不知道——测试帮你兜底。
- **验证自动化**：Playwright/Selenium/Requests 的脚本可以写成测试，一键全跑、失败留证。
- **测试即文档**：别人看你的测试就知道你的代码"应该有什么行为"。
- 语法极简：会写 `assert` 就会写测试（不像 unittest 要写 class）。

### 1.3 和 assert 的关系

pytest 的底层就是 **assert 语句**（Python 内置的"断言"：条件为假就抛异常）。pytest 做的三件事：
1. **自动发现**：递归找 `test_*.py` / `*_test.py` 文件，文件里 `test_*` 函数。
2. **增强报错**：断言失败时显示两边的值（`assert 6 == 7` → 告诉你左边 6 右边 7）。
3. **丰富能力**：fixture（准备/清理）、参数化、插件生态。

## 第 2 章 核心概念与原理

### 2.1 测试文件与函数的命名规则（约定即配置）

pytest 靠**文件名和函数名前缀**自动发现测试，不需要注册：

```
项目/
├── test_math.py        ← 文件名以 test_ 开头（或 _test.py 结尾）
│   ├── def test_add()      ← 函数名以 test_ 开头
│   └── def test_sub()
└── src/...
```

默认发现规则：`test_*.py`、`*_test.py`，文件内 `test_*` 函数、`Test*` 类的方法。

### 2.2 断言失败长什么样（看懂了就会读测试）

```
_____________________________ test_fail _____________________________
    def test_fail():
>       assert 2 * 3 == 7
E       assert 6 == 7
```

- `>` 指向出错代码行，`E` 是失败详情——一眼看出"左边 6，右边 7"。
- 失败会**自动截图上下文**（配合 pytest-playwright 时是页面截图）。

### 2.3 Fixture（夹具）：测试的"准备与收拾"

**Fixture** 是 pytest 的灵魂：给测试**准备环境**（登录、开浏览器、建数据库），测试结束后**自动清理**。

```python
import pytest

@pytest.fixture
def user():
    print("准备：创建用户")
    u = {"name": "demo", "token": "abc123"}
    yield u                       # yield 之前是准备，之后是清理
    print("清理：删除用户")

def test_login(user):             # 参数名写 user，pytest 自动注入
    assert user["token"] == "abc123"
```

**白话理解**：fixture 就是"测试的出场设置和退场收拾"，用 `yield` 分成两段。

## 第 3 章 安装与版本

```bash
pip install pytest
```

当前稳定版 8.x。验证：`pytest --version`。常用插件（按需装）：
- `pytest-playwright`：Playwright 的 pytest 集成（page fixture 自动给）
- `pytest-xdist`：并行执行
- `pytest-html`：生成 HTML 测试报告
- `pytest-cov`：覆盖率统计

## 第 4 章 API 全面讲解（✅ = 必会 ｜ ➕ = 推荐 ｜ 🧪 = 进阶）

### 4.1 基本断言（✅）

```python
def test_assertions():
    assert 1 + 1 == 2                     # 相等
    assert "py" in "python"               # 包含
    assert [1, 2] == [1, 2]               # 列表相等（顺序敏感）
    assert {"a": 1} == {"a": 1}           # 字典相等
    assert 5 > 3                          # 比较
    assert result is None                 # 是 None
    assert not flag                       # 否定

    # 浮点比较（用 pytest.approx，别用 ==）
    assert 0.1 + 0.2 == pytest.approx(0.3)

    # 异常断言：确认"应该抛异常"
    import pytest
    with pytest.raises(ValueError):
        int("abc")                        # 抛 ValueError 才通过
```

### 4.2 运行与选择（✅）

```bash
pytest                          # 跑全部
pytest test_math.py             # 跑指定文件
pytest test_math.py::test_add   # 跑指定函数
pytest -k "login or register"   # 按名字模糊筛选
pytest -m "slow"                # 按标记筛选
pytest -x                       # 第一个失败就停（调试用）
pytest --maxfail=3              # 最多允许 3 个失败
pytest -q                       # 安静模式（只显示 . 和 F）
pytest -v                       # 详细模式（每个测试一行）
pytest -s                       # 显示 print 输出（默认吞掉）
pytest --lf                     # 只重跑上次失败的
```

**输出符号**：`.` 通过、`F` 失败、`E` 报错、`s` 跳过。

### 4.3 Fixture 详解（✅ 必会）

```python
import pytest

@pytest.fixture
def db():
    conn = {"connected": True}        # 准备
    yield conn                        # 测试期间使用
    conn["connected"] = False         # 清理

@pytest.fixture(scope="session")      # 作用域：整个测试会话只建一次
def config():
    return {"base_url": "https://example.com"}

@pytest.fixture(scope="module")       # 一个模块共享
@pytest.fixture(scope="class")
@pytest.fixture(scope="function")     # 默认：每个测试函数都新建

# 自动使用（不需要参数注入）
@pytest.fixture(autouse=True)
def setup_cleanup():
    print("每个测试前自动执行")
    yield
    print("每个测试后自动执行")

# 多个 fixture 组合
@pytest.fixture
def logged_session(db, config):      # 依赖其他 fixture
    return {"db": db, "session_id": "s1"}
```

**作用域（scope）选择**：
- `function`（默认）：每个测试都新建——**隔离最好**。
- `module`：一个文件共享。
- `session`：整个运行只建一次——**最快**（如只启动一次浏览器）。

### 4.4 参数化：一个测试跑多组数据（➕ 超实用）

```python
import pytest

@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (10, 20, 30),
    (0, 0, 0),
    (-1, 1, 0),
])
def test_add(a, b, expected):
    assert a + b == expected        # 4 组数据 = 4 个测试用例
```

**应用场景**：接口测试传不同参数、登录测试多组账号密码、边界值测试（空、超长、特殊字符）。

### 4.5 标记（Mark）：分类管理（➕）

```python
import pytest

@pytest.mark.slow                    # 慢测试标记
def test_big_data():
    ...

@pytest.mark.skip(reason="接口还没好")   # 跳过
def test_not_ready():
    ...

@pytest.mark.skipif(sys.platform == "win32", reason="只在 Linux 跑")  # 条件跳过
def test_linux_only():
    ...

@pytest.mark.xfail(reason="已知 bug，允许失败")   # 预期失败（已知问题）
def test_known_bug():
    ...
```

运行：`pytest -m "not slow"`（跳过慢测试）。

### 4.6 临时目录与系统临时文件（➕）

```python
def test_write_file(tmp_path):        # tmp_path 是 pytest 内置 fixture
    f = tmp_path / "data.txt"         # 自动创建临时目录，测完自动清理
    f.write_text("hello", encoding="utf-8")
    assert f.read_text(encoding="utf-8") == "hello"
```

### 4.7 conftest.py：共享 fixture 的"全局配置文件"（➕）

`conftest.py` 放在目录里，该目录及子目录的所有测试都能用里面定义的 fixture，**无需 import**：

```python
# conftest.py
import pytest

@pytest.fixture
def base_url():
    return "https://example.com"
```

## 第 5 章 实战项目案例（从小白到大神）

### 案例 1（入门级）：工具函数测试

```python
# my_utils.py
def parse_price(s):
    """'¥15.5K' → 15.5（数字）"""
    return float(s.replace("¥", "").replace("K", "").replace("k", ""))

def filter_adult(people, age_limit=18):
    return [p for p in people if p["age"] >= age_limit]
```

```python
# test_my_utils.py
import pytest
from my_utils import parse_price, filter_adult

def test_parse_price_normal():
    assert parse_price("¥15.5K") == 15.5

def test_parse_price_lowercase_k():
    assert parse_price("8k") == 8

@pytest.mark.parametrize("s", ["", "abc", None])     # 异常输入要报错
def test_parse_price_bad_input(s):
    with pytest.raises((ValueError, TypeError)):
        parse_price(s)

def test_filter_adult():
    people = [{"name": "张三", "age": 20}, {"name": "李四", "age": 16}]
    assert [p["name"] for p in filter_adult(people)] == ["张三"]
```

### 案例 2（进阶级）：Requests 接口测试

```python
# conftest.py
import pytest
import requests

@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.post("https://example.com/login",
           json={"username": "demo", "password": "demo123"}, timeout=10)
    yield s
    s.close()
```

```python
# test_api.py
import pytest

def test_list_articles(session):
    resp = session.get("https://example.com/api/articles?page=1", timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) > 0

@pytest.mark.parametrize("page", [1, 2, 3])
def test_pagination(session, page):
    resp = session.get(f"https://example.com/api/articles?page={page}", timeout=10)
    assert resp.status_code == 200
    assert resp.json()["page"] == page

def test_create_and_delete_article(session):
    # 创建
    resp = session.post("https://example.com/api/articles",
                        json={"title": "测试文章", "content": "内容"}, timeout=10)
    assert resp.status_code == 201
    aid = resp.json()["id"]
    # 查询
    assert session.get(f"https://example.com/api/articles/{aid}", timeout=10).status_code == 200
    # 删除（清理）
    assert session.delete(f"https://example.com/api/articles/{aid}", timeout=10).status_code == 204
```

### 案例 3（综合）：**Playwright + Pytest 端到端测试**（含失败截图）

```bash
pip install pytest-playwright
playwright install chromium
```

```python
# conftest.py（pytest-playwright 自动提供 page fixture，以下是可选自定义）
import pytest

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "locale": "zh-CN"}
```

```python
# test_shop_flow.py
from playwright.sync_api import expect

def test_login_flow(page):
    """登录流程端到端测试"""
    page.goto("https://example.com/login")
    page.get_by_label("用户名").fill("demo")
    page.get_by_label("密码").fill("demo123")
    page.get_by_role("button", name="登录").click()
    expect(page.get_by_text("欢迎回来")).to_be_visible()
    expect(page).to_have_url("**/home")

def test_search_and_add_to_cart(page):
    """搜索 → 加购流程"""
    page.goto("https://example.com/")
    page.get_by_placeholder("搜索商品").fill("Python 书")
    page.get_by_placeholder("搜索商品").press("Enter")
    expect(page.locator(".product")).to_have_count(10)
    page.locator(".product").first.get_by_role("button", name="加入购物车").click()
    expect(page.get_by_text("已加入购物车")).to_be_visible()

@pytest.mark.parametrize("keyword", ["Python", "Java", "Go"])
def test_search_keywords(page, keyword):
    """参数化：多个搜索词"""
    page.goto("https://example.com/")
    page.get_by_placeholder("搜索商品").fill(keyword)
    page.get_by_placeholder("搜索商品").press("Enter")
    expect(page.locator(".result-count")).to_be_visible()
```

运行 `pytest`：每个测试自动开新浏览器页面；**失败自动截图**存到 `test-results/`；配 `pytest-html` 生成报告：

```bash
pip install pytest-html
pytest --html=report.html --self-contained-html
```

## 第 6 章 进阶内容（大神之路）

### 6.1 并行执行（pytest-xdist）

```bash
pip install pytest-xdist
pytest -n 4          # 4 个进程并行跑（Playwright 测试天然适合）
```

### 6.2 测试数据工厂（fixture 组合拳）

```python
@pytest.fixture
def make_user():
    """工厂 fixture：返回一个函数，每次调用造一个新用户"""
    created = []
    def _make(name="demo"):
        u = {"name": name, "token": f"token-{len(created)}"}
        created.append(u)
        return u
    yield _make
    # 清理所有创建的用户
    for u in created:
        print("删除用户", u["name"])
```

### 6.3 断言等待（Playwright expect 与 pytest 无缝）

pytest-playwright 让 `expect(...).to_be_visible()` 成为 pytest 断言的一部分，失败自动重试 5 秒——**测试更稳，不再需要 time.sleep**。

### 6.4 CI 集成（GitHub Actions 示例）

```yaml
steps:
  - uses: actions/setup-python@v4
  - run: pip install pytest pytest-playwright
  - run: playwright install --with-deps chromium
  - run: pytest --html=report.html
  - uses: actions/upload-artifact@v3
    with:
      path: report.html
```

### 6.5 覆盖率（pytest-cov）

```bash
pip install pytest-cov
pytest --cov=myproject --cov-report=term-missing
# 显示每行代码有没有被测试覆盖到
```

## 第 7 章 高频坑与排查（新手必看）

| 坑 | 症状 | 解决 |
| --- | --- | --- |
| 测试没被发现 | 提示 no tests ran | 检查文件名 `test_*.py` 和函数名 `test_*` 前缀 |
| print 不显示 | 控制台没有输出 | `pytest -s` |
| fixture 参数名写错 | `fixture 'xx' not found` | 函数参数名必须和 fixture 函数名一致 |
| 测试之间互相影响 | 一个失败连累一堆 | 用 scope="function"（默认）隔离；别共享可变全局 |
| 浮点比较失败 | 0.30000000004 != 0.3 | 用 `pytest.approx` |
| 浏览器测试没截图 | 失败看不到现场 | pytest-playwright 默认截到 test-results/；确认装了插件 |
| fixture 清理没执行 | 数据残留 | yield 之后的代码才是清理；确保用 yield 不用 return |
| 参数化报错定位难 | 不知道哪组数据挂了 | 失败信息会显示参数值；可 `-k` 精确跑某组 |
| 跳过理由不显示 | 不知道为啥跳过 | `pytest -rs` 显示跳过原因 |
| 测试太慢 | 每个用例都重新登录 | scope="session" 复用登录态（注意隔离风险） |

## 第 8 章 学习路径与自测

**学习路径**：
1. 第一个测试 + pytest 运行（半天）
2. 各种断言 + approx（半天）
3. 运行参数（-k/-x/-s/-v）（半天）
4. Fixture 基础 + scope（1 天）
5. 参数化 parametrize（1 天）
6. 标记 skip/xfail（半天）
7. conftest.py 共享（半天）
8. Requests 接口测试（1 天）
9. pytest-playwright 端到端（2 天，重点）
10. xdist 并行 + CI + 覆盖率（1-2 天）

**自测题**：
1. pytest 怎么发现测试？文件名和函数名的规则？
2. `pytest -s`、`pytest -x`、`pytest -k`、`pytest --lf` 各干什么？
3. fixture 里 `yield` 前后分别是什么？
4. `scope="session"` 和默认 scope 的区别？
5. 怎么让一个测试跑 5 组数据？
6. `pytest.raises(ValueError)` 是干什么的？
7. 浮点断言为什么用 approx？
8. conftest.py 有什么用？
9. Playwright 测试失败怎么自动截图？
10. 综合：设计一个"登录 → 搜索 → 加购"的端到端测试用例。

**答案提示**：
1. 找 `test_*.py`/`*_test.py` 文件里的 `test_*` 函数（和 `Test*` 类的方法）。
2. -s 显示 print；-x 第一个失败就停；-k 按名字筛选；--lf 只跑上次失败的。
3. yield 之前是准备（测试前），之后是清理（测试后）。
4. 默认 function 每个测试新建；session 整个运行只建一次（快但共享状态）。
5. `@pytest.mark.parametrize("参数1,参数2", [组1, 组2, ...])`。
6. 断言"这段代码必须抛出指定异常"，没抛就测试失败。
7. 浮点运算有精度误差，== 会误判；approx 允许微小误差。
8. 目录级共享 fixture 的配置文件，子目录测试都能用，无需 import。
9. 装 pytest-playwright，失败自动存 test-results/ 截图（也可自定义截图钩子）。
10. 参考案例 3：page.goto → fill → click → expect(...).to_be_visible() 逐段断言。

<hr>

> 下一篇：《Pillow》——图像处理库：截图裁剪、验证码处理、图片拼接合成。
