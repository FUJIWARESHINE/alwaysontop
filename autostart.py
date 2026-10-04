# -*- coding: utf-8 -*-
"""autostart.py —— Windows 开机自启（登录后启动）管理

写入 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run，
不需要管理员权限。exe 路径从正在运行的进程推导，因此源码运行（python ontop.py）
与 PyInstaller 打包（xxx.exe）都能正确注册。

启动参数用 --tray，程序启动后直接进托盘、不弹主窗口，避免开机时闪一下。
"""
import os
import sys
import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "AlwaysOnTopTool"


def _exe_path():
    """当前实际运行的解释器/可执行文件路径。"""
    if getattr(sys, "frozen", False):
        return sys.executable
    return sys.executable          # python.exe / pythonw.exe


def _launch_cmd():
    """注册到 Run 键的命令行。打包后直接跑 exe；源码运行用 pythonw 静默启动。"""
    if getattr(sys, "frozen", False):
        return '"%s" --tray' % sys.executable
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "ontop.py"))
    # 优先 pythonw.exe，避免开机时弹出黑色控制台窗口
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    return '"%s" "%s" --tray' % (pyw, script)


def is_enabled():
    """当前是否已注册开机自启。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            val, _ = winreg.QueryValueEx(k, APP_NAME)
            return bool(val)
    except (FileNotFoundError, OSError):
        return False


def enable():
    """注册开机自启。"""
    cmd = _launch_cmd()
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, cmd)
    return cmd


def disable():
    """取消开机自启。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, APP_NAME)
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def set_enabled(on):
    """按目标状态开关自启，返回 (是否成功, 提示文案)。"""
    try:
        if on:
            enable()
            return True, "已开启开机自启，登录后自动运行"
        disable()
        return True, "已关闭开机自启"
    except OSError as e:
        return False, "设置失败：%s" % e


def current_cmd():
    """读取已注册的命令行（用于界面提示/排障）。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            val, _ = winreg.QueryValueEx(k, APP_NAME)
            return val
    except (FileNotFoundError, OSError):
        return ""


def launched_as_tray():
    """是否以 --tray 参数启动（开机自启路径）。"""
    return any(a == "--tray" or a == "-t" for a in sys.argv[1:])
