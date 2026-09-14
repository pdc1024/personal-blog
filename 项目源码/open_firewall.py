"""添加 Windows 防火墙入站规则，放行博客端口（默认 5000）。

用途：让同一 WiFi 下的手机/平板能访问电脑上的博客。
需以管理员身份运行（右键 open_firewall.bat -> 以管理员身份运行）。

原理：run.bat 用 pythonw.exe 后台启动博客，和之前 python.exe 不是
同一个可执行文件，Windows 防火墙可能只放行了 python.exe 而拦截了
pythonw.exe，导致手机打不开页面。本脚本直接按端口放行，最稳妥。
"""
import os
import sys
import socket
import subprocess

PORT = os.environ.get('BLOG_PORT', '5000')
RULE_NAME = "PersonalBlog_%s" % PORT


def is_admin():
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def run(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='gbk', errors='replace')
    if check and r.returncode != 0:
        print("  [ERROR] %s" % " ".join(cmd))
        if r.stderr:
            print("          %s" % r.stderr.strip())
    return r


def get_lan_ip():
    """获取本机局域网 IP（供手机访问用）。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def main():
    print("=" * 55)
    print("  Personal Blog - Firewall Rule Setup")
    print("=" * 55)
    print("  Port      : %s (TCP, inbound)" % PORT)
    print("  Rule name : %s" % RULE_NAME)
    print()

    if not is_admin():
        print("[ERROR] Administrator rights required!")
        print("        Right-click open_firewall.bat -> Run as administrator")
        input("Press Enter to exit...")
        sys.exit(1)

    # 1. 先删除旧规则（如果存在），避免重复
    print("[1/2] Removing old rule (if exists)...")
    run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule',
         'name=%s' % RULE_NAME], check=False)

    # 2. 添加入站放行规则
    print("[2/2] Adding inbound allow rule for TCP %s..." % PORT)
    r = run(['netsh', 'advfirewall', 'firewall', 'add', 'rule',
             'name=%s' % RULE_NAME, 'dir=in', 'action=allow',
             'protocol=TCP', 'localport=%s' % PORT])

    if r.returncode == 0:
        lan_ip = get_lan_ip()
        print()
        print("[OK] Firewall rule added successfully!")
        print("     Port %s is now open for inbound TCP." % PORT)
        print()
        print("Now your phone (on the same WiFi) can access:")
        if lan_ip:
            print("     http://%s:%s/" % (lan_ip, PORT))
        else:
            print("     http://<your-pc-ip>:%s/" % PORT)
        print()
        print("Tips:")
        print("  - Phone and PC must be on the same WiFi/network")
        print("  - If still cannot access, check router AP isolation")
    else:
        print()
        print("[FAIL] Could not add firewall rule.")
        print("       Try running as administrator.")

    print()
    input("Press Enter to exit...")


if __name__ == '__main__':
    main()
