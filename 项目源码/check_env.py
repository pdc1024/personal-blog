# -*- coding: utf-8 -*-
"""
一键环境/迁移检查脚本。
==========================

目的：
  在本机或迁移到新电脑后，运行 `python check_env.py` 自动检测：
    - Python 版本
    - 依赖是否齐全（requirements.txt）
    - blog.db / uploads / logs 目录与权限
    - 端口 5000 是否被占用
    - 当前是否管理员（用于添加防火墙规则）
    - 防火墙入站规则是否放行了博客端口（手机访问前提）
    - 运维脚本、守护脚本是否齐全
  最后输出一份 OK / WARN / FAIL 的彩色报告，并给出修复建议。

推荐：
  - 迁移到新电脑后，先 `pip install -r requirements.txt`，再运行本脚本。
  - 双击 check_env.bat（或命令行 python check_env.py）。
"""
import os
import sys
import re
import ctypes
import socket
import importlib
import subprocess

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# ---------- 极简彩色输出（不依赖 colorama） ----------
_COLOR = sys.platform == 'win32'
if _COLOR:
    try:
        kernel32 = ctypes.windll.kernel32
        # Enable VT processing (Windows 10+)
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        _COLOR = False


def _c(color, s):
    """ANSI color wrapper. Colors: g/green, r/red, y/yellow, b/blue, c/cyan, bold."""
    if not _COLOR:
        return s
    m = {
        'g': '32', 'green': '32',
        'r': '31', 'red': '31',
        'y': '33', 'yellow': '33',
        'b': '34', 'blue': '34',
        'c': '36', 'cyan': '36',
        'bold': '1',
        'gray': '90',
    }
    codes = [m[x] for x in color.split('+') if x in m]
    return f'\x1b[{";".join(codes)}m{s}\x1b[0m'


OK = _c('g', '[OK]')
WARN = _c('y', '[WARN]')
FAIL = _c('r', '[FAIL]')
INFO = _c('c', '[INFO]')
BOLD = lambda s: _c('bold', s)

# ---------- 结果收集 ----------
results = []
tips = []


def add(level, title, detail=''):
    results.append((level, title, detail))


def tip(msg):
    tips.append(msg)


# ---------- 检查函数 ----------
def check_python():
    ver = sys.version_info
    ver_str = f'{ver.major}.{ver.minor}.{ver.micro}'
    if ver.major == 3 and ver.minor >= 10:
        add('ok', f'Python {ver_str}', '满足 >= 3.10')
    else:
        add('fail', f'Python {ver_str}', '需要 Python 3.10+，请到 https://www.python.org 下载并勾选 "Add to PATH"')
        tip('安装 Python 3.10+：勾选 "Add Python to PATH"，安装后重新打开终端。')
    # 找 pythonw (无窗口守护用)
    try:
        import shutil
        pyw = shutil.which('pythonw') or shutil.which('pythonw.exe')
        if pyw:
            add('ok', f'pythonw.exe 可用', pyw)
        else:
            add('warn', '未找到 pythonw.exe', '守护启动时会退回 python.exe（仍能跑，但会占一个 cmd 窗口）。通常随标准 CPython 一同安装。')
    except Exception as e:
        add('warn', 'pythonw 检测失败', str(e))


def parse_requirements(path):
    """极简解析 requirements.txt，返回 [(pkg, version_spec or '')]。"""
    pkgs = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith('#'):
                    continue
                # 去掉 -r 等选项
                if s.startswith('-'):
                    continue
                m = re.match(r'([A-Za-z0-9_.\-]+)\s*(.*)', s)
                if m:
                    pkg = m.group(1)
                    spec = m.group(2).strip()
                    pkgs.append((pkg, spec))
    except FileNotFoundError:
        pass
    return pkgs


def check_requirements():
    path = os.path.join(BASE_DIR, 'requirements.txt')
    pkgs = parse_requirements(path)
    if not pkgs:
        add('fail', 'requirements.txt 未找到或为空', path)
        tip('请确认 requirements.txt 在项目根目录。')
        return
    ok = fail = 0
    missing = []
    for pkg, _spec in pkgs:
        # import 名字和 pip 名不统一时手动映射
        import_map = {
            'Flask': 'flask',
            'Flask-SQLAlchemy': 'flask_sqlalchemy',
            'Flask-Login': 'flask_login',
            'Werkzeug': 'werkzeug',
            'Markdown': 'markdown',
            'Pygments': 'pygments',
            'PyYAML': 'yaml',
            'python-dateutil': 'dateutil',
            'waitress': 'waitress',
            'python-dotenv': 'dotenv',
        }
        name = import_map.get(pkg, pkg.lower().replace('-', '_').replace('.', '_'))
        try:
            importlib.import_module(name)
            ok += 1
        except Exception:
            fail += 1
            missing.append(pkg)
    if fail == 0:
        add('ok', f'依赖 ({ok}/{ok + fail}) 全部安装', '共 %d 项' % (ok + fail))
    else:
        add('fail', f'依赖 ({ok}/{ok + fail}) 缺少 {fail} 项', '未安装: ' + ', '.join(missing))
        tip('运行：pip install -r requirements.txt')
        tip('  (国内源加速：pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/)')


def check_folders_and_files():
    must_exist = [
        ('app.py', '主程序'),
        ('config.py', '配置'),
        ('requirements.txt', '依赖'),
        ('templates/', '模板目录'),
    ]
    optional_create = [
        ('uploads/', '上传目录（文章导入/头像/背景）', True),
        ('uploads/avatars/', '头像目录', True),
        ('uploads/bg/', '背景图目录', True),
        ('logs/', '日志目录', True),
    ]
    for f, desc in must_exist:
        fp = os.path.join(BASE_DIR, f)
        if os.path.exists(fp):
            add('ok', f'{f} 存在', desc)
        else:
            add('fail', f'{f} 缺失', desc)
            tip(f'缺失核心文件 {f}，请确认整目录完整复制。')

    for f, desc, create in optional_create:
        fp = os.path.join(BASE_DIR, f)
        if os.path.exists(fp):
            add('ok', f'{f} 存在', desc)
        elif create:
            try:
                os.makedirs(fp, exist_ok=True)
                add('warn', f'{f} 已自动创建', desc + '（之前缺失，已创建空目录）')
            except OSError as e:
                add('fail', f'{f} 缺失且无法自动创建', str(e))
                tip(f'手动创建空目录 {f}')
        else:
            add('warn', f'{f} 缺失', desc)

    # blog.db: 缺失可接受（首次运行自动建），但写一个 warn
    db_path = os.path.join(BASE_DIR, 'blog.db')
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        add('ok', f'blog.db 存在', f'大小 {size_mb:.2f} MB（迁移时记得拷贝本文件！）')
    else:
        add('warn', 'blog.db 不存在', '首次启动会自动创建；迁移旧博客时请把 blog.db 拷贝过来。')
        tip('迁移：把旧机器上的 blog.db、uploads/ 目录拷贝到新项目同名位置即可恢复数据。')

    # 检查 scripts 清单
    scripts = ['run.bat', 'stop.bat', 'status.bat', 'restart.bat',
               'launcher.py', 'start_hidden.vbs',
               'status.py', 'stop.py', 'start_check.py',
               'open_firewall.bat', 'open_firewall.py']
    missing_s = [s for s in scripts if not os.path.exists(os.path.join(BASE_DIR, s))]
    if missing_s:
        add('warn', f'辅助脚本缺失 {len(missing_s)} 个', '缺失: ' + ', '.join(missing_s))
        tip('缺失脚本虽不影响直接 python app.py，但会缺少守护/防火墙放行能力。建议从完整项目补齐。')
    else:
        add('ok', f'辅助脚本齐全', f'共 {len(scripts)} 个：run/status/stop/restart + 守护/防火墙放行')


def check_port(port=5000):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        in_use = s.connect_ex(('127.0.0.1', port)) == 0
        s.close()
    except Exception:
        in_use = False
    if in_use:
        # 尝试判断是不是自己的博客在监听
        healthy = False
        try:
            import urllib.request
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2) as resp:
                healthy = resp.status == 200
        except Exception:
            pass
        if healthy:
            add('ok', f'端口 {port} 已监听', '并且 /health 返回 ok = 博客正在运行')
        else:
            add('warn', f'端口 {port} 被占用', '可能是博客进程仍存活但健康检查失败；或其他程序占用。启动前请确保端口空闲。')
            tip(f'解除占用：netstat -ano | findstr ":{port}" 找到 PID，再 taskkill /PID xxxx /F /T')
    else:
        add('ok', f'端口 {port} 空闲', '可直接启动博客')


def check_admin():
    try:
        is_adm = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        is_adm = False
    if is_adm:
        add('ok', '当前为管理员权限', '可运行 open_firewall.bat 添加防火墙规则（让手机访问）')
    else:
        add('warn', '当前非管理员', 'open_firewall.bat 需要管理员权限。请右键"以管理员身份运行"。')
        tip('放行端口：右键 open_firewall.bat → 以管理员身份运行。')
    return is_adm


def check_firewall_rule():
    """检查防火墙入站规则是否放行了博客端口（手机访问前提）。"""
    port = os.environ.get('BLOG_PORT', '5000')
    rule_name = f'PersonalBlog_{port}'
    try:
        r = subprocess.run(
            ['netsh', 'advfirewall', 'firewall', 'show', 'rule',
             f'name={rule_name}'],
            capture_output=True, text=True, timeout=10,
            encoding='gbk', errors='replace')
        exists = r.returncode == 0 and rule_name in r.stdout
    except Exception:
        exists = False

    if exists:
        add('ok', f'防火墙规则 {rule_name}',
            f'端口 {port} 入站已放行，同一 WiFi 下的手机可访问')
    else:
        add('warn', f'防火墙规则 {rule_name} 未注册',
            f'手机在同一 WiFi 下无法访问。请以管理员身份运行 open_firewall.bat 放行端口 {port}。')
        tip(f'右键 open_firewall.bat -> 以管理员身份运行 -> 手机访问 http://<电脑IP>:{port}/')


def check_env_file():
    env_path = os.path.join(BASE_DIR, '.env')
    example_path = os.path.join(BASE_DIR, '.env.example')
    if os.path.exists(env_path):
        add('ok', '.env 文件存在', '本地配置将覆盖 config.py 默认值（推荐）')
    elif os.path.exists(example_path):
        add('warn', '.env 文件缺失，.env.example 存在',
            '建议复制 .env.example 为 .env 并修改 SECRET_KEY / ADMIN_* / BLOG_PORT 等。')
        tip('cp .env.example .env  （Windows 可 copy .env.example .env）')
    else:
        add('warn', '.env.example 不存在',
            '配置全部走 config.py 默认值，移植后生产环境建议显式改 SECRET_KEY / 管理员密码。')


def check_health_endpoint():
    """如果博客正在运行，顺手检查 /health。"""
    try:
        import urllib.request
        with urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2) as resp:
            body = resp.read().decode('utf-8', errors='ignore')
            add('ok', '/health 可达', body.strip())
            return
    except Exception:
        pass
    add('info', '/health 不可达', '博客未启动或防火墙阻挡。正常现象，启动后会自动恢复。')


# ---------- 汇总报告 ----------
def print_report():
    print()
    print('=' * 70)
    print(BOLD('  个人博客 — 环境 & 迁移检查报告'))
    print('=' * 70)
    print(f'  项目目录: {BASE_DIR}')
    print(f'  平台    : {sys.platform}  Python: {sys.version.split()[0]}')
    print()

    for level, title, detail in results:
        mark = {'ok': OK, 'warn': WARN, 'fail': FAIL, 'info': INFO}.get(level, INFO)
        line = f'  {mark} {title}'
        if detail:
            line += _c('gray', f'  — {detail}')
        print(line)
    print()
    if tips:
        print(_c('bold', '  修复建议 / 小贴士：'))
        for i, t in enumerate(tips, 1):
            print(f'    {i}. {t}')
        print()

    ok_count = sum(1 for l, *_ in results if l == 'ok')
    warn_count = sum(1 for l, *_ in results if l == 'warn')
    fail_count = sum(1 for l, *_ in results if l == 'fail')
    print('-' * 70)
    print(f'  汇总: {_c("g", f"OK {ok_count}")}   {_c("y", f"WARN {warn_count}")}   {_c("r", f"FAIL {fail_count}")}')
    if fail_count == 0 and warn_count == 0:
        print(_c('bold+g', '  完美！所有检查项通过，可以直接启动（双击 run.bat）。'))
    elif fail_count == 0:
        print(_c('bold+y', '  基本可用，有 WARN 请按需处理（不影响基础运行）。'))
    else:
        print(_c('bold+r', '  存在 FAIL 项，请按上方修复建议处理后再启动。'))
    print('=' * 70)
    return fail_count


def main():
    check_python()
    check_requirements()
    check_folders_and_files()
    check_env_file()
    check_port()
    check_admin()
    check_firewall_rule()
    check_health_endpoint()
    fails = print_report()
    return 1 if fails else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print('Interrupted.')
        sys.exit(130)
    except Exception as e:
        print(f'check_env 出错: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(2)
