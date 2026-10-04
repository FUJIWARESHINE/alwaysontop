# -*- coding: utf-8 -*-
"""
窗口置顶小工具 (AlwaysOnTop)

纯 Win32 + ctypes，零第三方依赖。
界面视觉对齐「文件批量重命名」：深色玻璃拟态 + 靛蓝/紫/青径向辉光（流光），
无边框自绘标题栏，所有设置收进右上角三条杠菜单。

功能：
  · 把任意窗口设为「始终在最前面」，双击列表项即可切换
  · 托盘常驻 + 全局快捷键 Ctrl+Alt+T（切换前台窗口）/ Ctrl+Alt+M（显示主窗口）
  · 开机自启：写 HKCU\\...\\Run，登录后自动启动并**直接收进托盘**
  · 置顶后自动转入后台（可选）

注意：独占全屏(exclusive fullscreen)游戏会独占显示输出，置顶无效；
      请改用「无边框 / 窗口化全屏」。
"""
import ctypes
import ctypes.wintypes as wt
import os
import sys
import time
import winreg

import appicon
import autostart
import theme as T
from aurora import (Canvas, RECT, POINT, rgb, mix, lighten, darken,
                    user32, gdi32, TRANSPARENT, NULL_BRUSH)

# ============================== 常量 ==============================
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
HWND_TOP = 0
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_APPWINDOW = 0x00040000

MOD_CONTROL = 0x0002
MOD_ALT = 0x0001
VK_T = 0x54
VK_M = 0x4D
HKID_TOGGLE = 1
HKID_SHOW = 2

SW_HIDE = 0
SW_SHOW = 5
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_MAXIMIZE = 3
SW_RESTORE = 9

WM_CREATE = 0x0001
WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_PAINT = 0x000F
WM_CLOSE = 0x0010
WM_COMMAND = 0x0111
WM_TIMER = 0x0113
WM_HOTKEY = 0x0312
WM_SETICON = 0x0080
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_LBUTTONDBLCLK_NC = 0x00A3
WM_MOUSEWHEEL = 0x020A
WM_MOUSELEAVE = 0x02A3
WM_NCCALCSIZE = 0x0083
WM_NCHITTEST = 0x0084
WM_NCLBUTTONDOWN = 0x00A1
WM_GETMINMAXINFO = 0x0024
WM_ERASEBKGND = 0x0014
WM_DPICHANGED = 0x02E0
WM_SETCURSOR = 0x0020
WM_SETFONT = 0x0030
WM_CTLCOLOREDIT = 0x0133
WM_CTLCOLORSTATIC = 0x0138
WM_KEYDOWN = 0x0100
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 1

WS_POPUP = 0x80000000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_CLIPCHILDREN = 0x02000000
WS_CLIPSIBLINGS = 0x04000000
WS_TABSTOP = 0x00010000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
ES_AUTOHSCROLL = 0x0080
ES_LEFT = 0x0000
CS_DBLCLKS = 0x0008

HTCLIENT = 1
HTCAPTION = 2
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17

MONITOR_DEFAULTTONEAREST = 2
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_BORDER_COLOR = 34
DWMWCP_ROUND = 2
DWMWA_COLOR_NONE = 0xFFFFFFFE

IDC_ARROW = 32512
IDC_HAND = 32649
IDC_IBEAM = 32513
IDI_APPLICATION = 32512

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
SHGFI_ICON = 0x000000100
SHGFI_LARGEICON = 0x000000000

# 控件 / 命令 ID
ID_SEARCH = 120
IDM_SHOW = 2001
IDM_REFRESH = 2002
IDM_CLEAR = 2003
IDM_AUTOTRAY = 2004
IDM_AUTOSTART = 2006
IDM_EXIT = 2005

EN_CHANGE = 0x0300

# 托盘
NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIM_SETVERSION = 0x00000004
NOTIFYICON_VERSION_4 = 4
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_INFO = 0x00000010
NIIF_INFO = 0x00000001
NIIF_NOSOUND = 0x00000010
NIIF_USER = 0x00000004

# 菜单
MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
MF_CHECKED = 0x00000008
MF_UNCHECKED = 0x00000000
TPM_LEFTALIGN = 0x0000
TPM_RIGHTBUTTON = 0x0002

TRACKMOUSEEVENT_TME_LEAVE = 0x00000002
SIZE_RESTORED = 1
SIZE_MAXIMIZED = 2

# 自绘命中区
HIT_NONE = 0
HIT_TOGGLE = 1
HIT_REFRESH = 2
HIT_CLEAR = 3
HIT_SCROLL = 4
HIT_MENUBTN = 5
HIT_THEME = 6
HIT_MIN = 7
HIT_MAX = 8
HIT_CLOSE = 9
HIT_MENU = 10
HIT_MENUCANCEL = 11
HIT_TITLE = 12


# ============================== DLL ==============================
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)
uxtheme = ctypes.WinDLL("uxtheme", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WndProcType = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)


# ============================== 结构体 ==============================
class PAINTSTRUCT(ctypes.Structure):
    """BeginPaint 的输出结构。

    注意：x64 下 sizeof 是 72 字节（hdc 指针 8 + fErase 4 + 对齐 4 +
    rcPaint 16 + fRestore 4 + fIncUpdate 4 + rgbReserved 32）。
    之前用 `create_string_buffer(64)` 当缓冲区，BeginPaint 每次都会多写
    8 字节，踩坏相邻的 Python 堆块 —— 表现为运行一会儿后在完全无关的
    地方随机崩溃（调试分配器可稳定复现 "bad trailing pad byte"）。
    """
    _fields_ = [
        ("hdc", wt.HDC), ("fErase", wt.BOOL), ("rcPaint", RECT),
        ("fRestore", wt.BOOL), ("fIncUpdate", wt.BOOL),
        ("rgbReserved", ctypes.c_byte * 32),
    ]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", WndProcType),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HANDLE), ("hIcon", wt.HANDLE), ("hCursor", wt.HANDLE),
        ("hbrBackground", wt.HANDLE), ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR), ("hIconSm", wt.HANDLE),
    ]


class MINMAXINFO(ctypes.Structure):
    _fields_ = [("ptReserved", POINT), ("ptMaxSize", POINT),
                ("ptMaxPosition", POINT), ("ptMinTrackSize", POINT),
                ("ptMaxTrackSize", POINT)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", wt.DWORD)]


class NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [("rgrc", RECT * 3), ("lppos", ctypes.c_void_p)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uID", wt.UINT),
        ("uFlags", wt.UINT), ("uCallbackMessage", wt.UINT), ("hIcon", wt.HANDLE),
        ("szTip", wt.WCHAR * 128), ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD),
        ("szInfo", wt.WCHAR * 256), ("uVersion", wt.UINT),
        ("szInfoTitle", wt.WCHAR * 64), ("dwInfoFlags", wt.DWORD),
        ("guidItem", wt.DWORD * 16), ("hBalloonIcon", wt.HANDLE),
    ]


class TRACKMOUSEEVENT(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("dwFlags", wt.DWORD),
                ("hwndTrack", wt.HWND), ("dwHoverTime", wt.DWORD)]


# ============================== 函数原型 ==============================
user32.CreateWindowExW.argtypes = [wt.DWORD, ctypes.c_wchar_p, ctypes.c_wchar_p,
                                   wt.DWORD, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU,
                                   wt.HANDLE, ctypes.c_void_p]
user32.CreateWindowExW.restype = wt.HWND
user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wt.ATOM
user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, ctypes.c_void_p,
                                ctypes.c_void_p]
user32.SendMessageW.restype = ctypes.c_int64
user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = [ctypes.POINTER(wt.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wt.MSG)]
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
user32.ShowWindow.restype = wt.BOOL
user32.IsZoomed.argtypes = [wt.HWND]
user32.IsZoomed.restype = wt.BOOL
user32.IsIconic.argtypes = [wt.HWND]
user32.IsIconic.restype = wt.BOOL
user32.UpdateWindow.argtypes = [wt.HWND]
user32.DestroyWindow.argtypes = [wt.HWND]
user32.SetWindowTextW.argtypes = [wt.HWND, ctypes.c_wchar_p]
user32.GetWindowTextW.argtypes = [wt.HWND, ctypes.c_wchar_p, ctypes.c_int]
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wt.UINT]
user32.SetWindowPos.restype = wt.BOOL
user32.MoveWindow.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, wt.BOOL]
user32.MoveWindow.restype = wt.BOOL
user32.GetClientRect.argtypes = [wt.HWND, ctypes.POINTER(RECT)]
user32.GetClientRect.restype = wt.BOOL
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wt.BOOL
user32.BeginPaint.argtypes = [wt.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.BeginPaint.restype = wt.HDC
user32.EndPaint.argtypes = [wt.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetForegroundWindow.argtypes = [wt.HWND]
user32.SetForegroundWindow.restype = wt.BOOL
user32.GetForegroundWindow.restype = wt.HWND
user32.CreatePopupMenu.restype = wt.HANDLE
user32.AppendMenuW.argtypes = [wt.HMENU, wt.UINT, ctypes.c_uint64,
                               ctypes.c_wchar_p]
user32.TrackPopupMenu.argtypes = [wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, wt.HWND, ctypes.POINTER(RECT)]
user32.TrackPopupMenu.restype = wt.BOOL
user32.DestroyMenu.argtypes = [wt.HMENU]
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindowVisible.restype = wt.BOOL
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = wt.LONG
user32.RegisterHotKey.argtypes = [wt.HWND, ctypes.c_int, wt.UINT, wt.UINT]
user32.RegisterHotKey.restype = wt.BOOL
user32.UnregisterHotKey.argtypes = [wt.HWND, ctypes.c_int]
user32.LoadIconW.argtypes = [wt.HINSTANCE, wt.LPCWSTR]
user32.LoadIconW.restype = wt.HANDLE
user32.LoadCursorW.argtypes = [wt.HINSTANCE, wt.LPCWSTR]
user32.LoadCursorW.restype = wt.HANDLE
user32.SetCursor.argtypes = [wt.HANDLE]
user32.SetCursor.restype = wt.HANDLE
user32.DestroyIcon.argtypes = [wt.HANDLE]
user32.TrackMouseEvent.argtypes = [ctypes.POINTER(TRACKMOUSEEVENT)]
user32.TrackMouseEvent.restype = wt.BOOL
user32.ScreenToClient.argtypes = [wt.HWND, ctypes.POINTER(POINT)]
user32.ScreenToClient.restype = wt.BOOL
user32.ClientToScreen.argtypes = [wt.HWND, ctypes.POINTER(POINT)]
user32.ClientToScreen.restype = wt.BOOL
user32.SetTimer.argtypes = [wt.HWND, ctypes.c_uint64, wt.UINT, ctypes.c_void_p]
user32.SetTimer.restype = ctypes.c_uint64
user32.KillTimer.argtypes = [wt.HWND, ctypes.c_uint64]
user32.SetCapture.argtypes = [wt.HWND]
user32.SetCapture.restype = wt.HWND
user32.ReleaseCapture.restype = wt.BOOL
user32.InvalidateRect.argtypes = [wt.HWND, ctypes.POINTER(RECT), wt.BOOL]
user32.InvalidateRect.restype = wt.BOOL
user32.GetDpiForWindow.argtypes = [wt.HWND]
user32.GetDpiForWindow.restype = wt.UINT
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.MonitorFromWindow.argtypes = [wt.HWND, wt.DWORD]
user32.MonitorFromWindow.restype = wt.HANDLE
user32.GetMonitorInfoW.argtypes = [wt.HANDLE, ctypes.POINTER(MONITORINFO)]
user32.GetMonitorInfoW.restype = wt.BOOL
user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM),
                               wt.LPARAM]
user32.EnumWindows.restype = wt.BOOL
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]

kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel32.GetModuleHandleW.restype = wt.HANDLE
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.CloseHandle.argtypes = [wt.HANDLE]
psapi.GetModuleFileNameExW.argtypes = [wt.HANDLE, wt.HMODULE,
                                       ctypes.c_wchar_p, wt.DWORD]
psapi.GetModuleFileNameExW.restype = wt.DWORD

shell32.Shell_NotifyIconW.argtypes = [wt.DWORD,
                                      ctypes.POINTER(NOTIFYICONDATAW)]
shell32.Shell_NotifyIconW.restype = wt.BOOL
shell32.SHGetFileInfoW.argtypes = [ctypes.c_wchar_p, wt.DWORD,
                                   ctypes.c_void_p, wt.UINT, wt.UINT]
shell32.SHGetFileInfoW.restype = ctypes.c_void_p

comctl32.ImageList_Create.argtypes = [ctypes.c_int, ctypes.c_int, wt.UINT,
                                      ctypes.c_int, ctypes.c_int]
comctl32.ImageList_Create.restype = wt.HANDLE
comctl32.ImageList_AddIcon.argtypes = [wt.HANDLE, wt.HANDLE]
comctl32.ImageList_AddIcon.restype = ctypes.c_int
comctl32.ImageList_Draw.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                    ctypes.c_int, ctypes.c_int, wt.UINT]
comctl32.ImageList_Draw.restype = wt.BOOL

uxtheme.SetWindowTheme.argtypes = [wt.HWND, ctypes.c_wchar_p, ctypes.c_wchar_p]
uxtheme.SetWindowTheme.restype = ctypes.c_long

dwmapi.DwmSetWindowAttribute.argtypes = [wt.HWND, wt.DWORD, ctypes.c_void_p,
                                         wt.DWORD]
dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long


# ============================== 全局状态 ==============================
def app_version():
    """读取构建时注入的版本号。

    CI 在打包前会写一个 version.txt 并用 --add-data 打进 exe；
    源码直接运行时读同目录下的 version.txt，读不到就回退成 dev。
    状态栏会显示它 —— 这样「你手上跑的是哪一版」一眼可辨，
    排查问题时不用再猜。
    """
    cands = []
    base = getattr(sys, "_MEIPASS", None)
    if base:
        cands.append(os.path.join(base, "version.txt"))
    try:
        here = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        here = os.getcwd()
    cands.append(os.path.join(here, "version.txt"))
    for path in cands:
        try:
            with open(path, encoding="utf-8") as f:
                v = f.read().strip()
            if v:
                return v
        except Exception:
            continue
    return "dev"


g = {
    'version': app_version(),
    'hwnd_main': None,
    'hwnd_search': None,
    'scale': 1.0,
    'dark': True,
    'rows': [],
    'filter': '',
    'sel': -1,
    'hover': HIT_NONE,
    'hover_row': -1,
    'hover_menu': -1,
    'press': HIT_NONE,
    'autotray': True,
    'autostart': False,
    'hidden': False,
    'menu_open': False,
    'maximized': False,
    'icon_cache': {},
    'tray_added': False,
    'first_hide': True,
    'hicon': None,
    'himl': None,
    'font_cache': {},
    'scroll': 0,
    'scroll_max': 0,
    'layout': {},
    'hint': '',
    't0': time.time(),
    # 拖动窗口用
    'drag': None,
}


def is_light_theme():
    try:
        k = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        v, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
        winreg.CloseKey(k)
        return bool(v)
    except Exception:
        return False


def sc(v):
    return int(round(v * g['scale']))


def invalidate():
    user32.InvalidateRect(g.get('hwnd_main'), None, False)


def set_hint(msg):
    g['hint'] = msg
    invalidate()


# ============================== 核心：窗口枚举与置顶 ==============================
def get_title(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def get_exe_path(pid):
    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False,
                             pid)
    if not h:
        return ""
    buf = ctypes.create_unicode_buffer(1024)
    try:
        psapi.GetModuleFileNameExW(h, None, buf, 1024)
    except Exception:
        kernel32.CloseHandle(h)
        return ""
    kernel32.CloseHandle(h)
    return buf.value


def is_topmost(hwnd):
    return (user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOPMOST) != 0


def set_topmost(hwnd, on):
    user32.SetWindowPos(hwnd, HWND_TOPMOST if on else HWND_NOTOPMOST,
                        0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    return on


def enum_windows(own_hwnd):
    result = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd) or hwnd == own_hwnd:
            return True
        title = get_title(hwnd)
        if not title:
            return True
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        path = get_exe_path(pid.value)
        if not path:
            return True
        result.append((int(hwnd), title, path.split("\\")[-1], path))
        return True

    enum_windows._cb = cb
    user32.EnumWindows(cb, 0)
    return result


def icon_index_for_path(path):
    if not path:
        return -1
    if path in g['icon_cache']:
        return g['icon_cache'][path]
    from aurora import SHFILEINFOW
    shfi = SHFILEINFOW()
    res = shell32.SHGetFileInfoW(path, 0, ctypes.byref(shfi),
                                 ctypes.sizeof(SHFILEINFOW),
                                 SHGFI_ICON | SHGFI_LARGEICON)
    idx = -1
    if res and shfi.hIcon:
        idx = comctl32.ImageList_AddIcon(g['himl'], shfi.hIcon)
        user32.DestroyIcon(shfi.hIcon)
    g['icon_cache'][path] = idx
    return idx


def refresh():
    """重新枚举窗口并应用搜索过滤。"""
    keep = None
    if 0 <= g['sel'] < len(g['rows']):
        keep = g['rows'][g['sel']][0]
    g['rows'] = []
    g['sel'] = -1
    flt = (g['filter'] or '').strip().lower()
    for hwnd, title, exe, path in enum_windows(g['hwnd_main']):
        if flt and flt not in title.lower() and flt not in exe.lower():
            continue
        g['rows'].append((hwnd, title, exe, path, is_topmost(hwnd)))
        if hwnd == keep:
            g['sel'] = len(g['rows']) - 1
    clamp_scroll()
    invalidate()


def clamp_scroll():
    L = g['layout']
    view = L.get('list_h', sc(300))
    total = len(g['rows']) * L.get('row_h', sc(46))
    g['scroll_max'] = max(0, total - view)
    g['scroll'] = max(0, min(g['scroll'], g['scroll_max']))


def selected_row():
    if 0 <= g['sel'] < len(g['rows']):
        return g['rows'][g['sel']]
    return None


def toggle_selected():
    row = selected_row()
    if not row:
        set_hint("请先在列表里选中一个窗口")
        return
    hwnd, title, exe, path, top = row
    set_topmost(hwnd, not top)
    refresh()
    if top:
        set_hint("已取消置顶：%s" % title)
    else:
        set_hint("已置顶：%s" % title)
        if g['autotray']:
            hide_to_tray(notify=True, title=title)


def toggle_row(idx):
    if 0 <= idx < len(g['rows']):
        g['sel'] = idx
        toggle_selected()


def clear_all():
    n = 0
    for hwnd, title, exe, path, top in list(g['rows']):
        if top:
            set_topmost(hwnd, False)
            n += 1
    refresh()
    set_hint("已取消 %d 个窗口的置顶" % n if n else "当前没有已置顶的窗口")


def on_hotkey_toggle():
    fg = user32.GetForegroundWindow()
    if not fg:
        return
    fg = int(fg)
    if fg == g.get('hwnd_main'):
        return
    state = not is_topmost(fg)
    set_topmost(fg, state)
    refresh()
    title = get_title(fg)
    if state:
        toast("已置顶", "%s\n已设为始终在最前" % title[:60])
    else:
        set_hint("已取消置顶：%s" % title)


# ============================== 托盘 ==============================
def tray_add():
    if g['tray_added']:
        return
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = g['hwnd_main']
    nid.uID = 1
    nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
    nid.uCallbackMessage = WM_TRAYICON
    # 图标必须有值，否则托盘里会完全看不到图标
    nid.hIcon = g['hicon'] or user32.LoadIconW(None,
                                               ctypes.c_wchar_p(IDI_APPLICATION))
    nid.szTip = "窗口置顶小工具"
    ok = shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
    if not ok:
        nid.cbSize = 956          # 兼容老尺寸定义
        ok = shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
    if ok:
        nid.uVersion = NOTIFYICON_VERSION_4
        shell32.Shell_NotifyIconW(NIM_SETVERSION, ctypes.byref(nid))
    g['tray_added'] = bool(ok)
    return ok


def tray_delete():
    if not g['tray_added']:
        return
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = g['hwnd_main']
    nid.uID = 1
    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
    g['tray_added'] = False


def tray_refresh_icon():
    """重新设置托盘图标（主题切换 / 图标重建后调用）。"""
    if not g['tray_added'] or not g['hicon']:
        return
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = g['hwnd_main']
    nid.uID = 1
    nid.uFlags = NIF_ICON
    nid.hIcon = g['hicon']
    shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))


def toast(title, msg):
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = g['hwnd_main']
    nid.uID = 1
    nid.uFlags = NIF_INFO
    nid.dwInfoFlags = NIIF_INFO | NIIF_NOSOUND
    nid.szInfoTitle = title[:63]
    nid.szInfo = msg[:255]
    try:
        if not shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid)):
            nid.cbSize = 956
            shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))
    except Exception:
        pass


def hide_to_tray(notify=False, title=""):
    if not g['tray_added']:
        tray_add()
    user32.ShowWindow(g['hwnd_main'], SW_HIDE)
    g['hidden'] = True
    if notify:
        toast("已转入后台运行",
              "%s 已置顶。\n程序已收进托盘，Ctrl+Alt+M 或双击托盘图标可重新打开。"
              % (title[:40] or "目标窗口"))
    elif g['first_hide']:
        g['first_hide'] = False
        toast("已在后台运行", "程序已收进系统托盘，全局快捷键仍然生效。")


def show_window_():
    user32.ShowWindow(g['hwnd_main'], SW_SHOW)
    user32.SetForegroundWindow(g['hwnd_main'])
    g['hidden'] = False
    refresh()


def show_tray_menu():
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    menu = user32.CreatePopupMenu()
    user32.AppendMenuW(menu, MF_STRING, IDM_SHOW, "打开主窗口")
    user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
    user32.AppendMenuW(menu, MF_STRING, IDM_REFRESH, "刷新列表")
    user32.AppendMenuW(menu, MF_STRING, IDM_CLEAR, "取消全部置顶")
    user32.AppendMenuW(menu,
                       MF_STRING | (MF_CHECKED if g['autotray']
                                    else MF_UNCHECKED),
                       IDM_AUTOTRAY, "置顶后自动转入后台")
    user32.AppendMenuW(menu,
                       MF_STRING | (MF_CHECKED if g['autostart']
                                    else MF_UNCHECKED),
                       IDM_AUTOSTART, "开机自启")
    user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
    user32.AppendMenuW(menu, MF_STRING, IDM_EXIT, "退出")
    user32.SetForegroundWindow(g['hwnd_main'])
    user32.TrackPopupMenu(menu, TPM_LEFTALIGN | TPM_RIGHTBUTTON, pt.x, pt.y,
                          0, g['hwnd_main'], None)
    user32.DestroyMenu(menu)


def toggle_autostart():
    want = not g['autostart']
    ok, msg = autostart.set_enabled(want)
    if ok:
        g['autostart'] = want
    toast("开机自启", msg)
    set_hint(msg)
    invalidate()


# ============================== 应用 ==============================
class App:
    # 命中区类型（供 ui 层引用）
    HIT_NONE = HIT_NONE
    HIT_TOGGLE = HIT_TOGGLE
    HIT_REFRESH = HIT_REFRESH
    HIT_CLEAR = HIT_CLEAR
    HIT_SCROLL = HIT_SCROLL
    HIT_MENUBTN = HIT_MENUBTN
    HIT_THEME = HIT_THEME
    HIT_MIN = HIT_MIN
    HIT_MAX = HIT_MAX
    HIT_CLOSE = HIT_CLOSE
    HIT_MENU = HIT_MENU
    HIT_MENUCANCEL = HIT_MENUCANCEL
    HIT_TITLE = HIT_TITLE

    def __init__(self):
        self.g = g
        from ui import UI
        self.ui = UI(self)
        self.canvas = Canvas()
        self.hwnd = None
        self.dragging = False

    def sc(self, v):
        return sc(v)

    def clamp_scroll(self):
        clamp_scroll()

    def selected_row(self):
        return selected_row()

    # ------------------------------------------------------------ 主题
    def apply_dark(self, dark):
        g['dark'] = dark
        self.ui.apply_theme()
        if self.hwnd:
            try:
                d = ctypes.c_int(1 if dark else 0)
                dwmapi.DwmSetWindowAttribute(self.hwnd,
                                            DWMWA_USE_IMMERSIVE_DARK_MODE,
                                            ctypes.byref(d), 4)
            except Exception:
                pass

    def setup_dwm(self):
        hwnd = self.hwnd
        try:
            corner = ctypes.c_int(DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                                         ctypes.byref(corner), 4)
            # 无边框：去掉 DWM 自己画的那圈描边，改用客户区自绘的 1px
            none = ctypes.c_int(DWMWA_COLOR_NONE)
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_BORDER_COLOR,
                                         ctypes.byref(none), 4)
        except Exception:
            pass
        self.apply_dark(g['dark'])

    # ------------------------------------------------------------ 子控件
    def create_children(self):
        hwnd = self.hwnd
        hinst = kernel32.GetModuleHandleW(None)
        h = user32.CreateWindowExW(
            0, "EDIT", "",
            WS_CHILD | WS_VISIBLE | WS_TABSTOP | ES_AUTOHSCROLL | ES_LEFT,
            0, 0, 10, 10, hwnd, ID_SEARCH, hinst, None)
        g['hwnd_search'] = h
        if h:
            user32.SendMessageW(h, WM_SETFONT,
                                g['font_cache']['body'], ctypes.c_void_p(1))

    def sync_children(self):
        """把搜索框 EDIT 摆到自绘的搜索底框里。"""
        h = g.get('hwnd_search')
        L = g['layout']
        if not h or not L.get('search_edit'):
            return
        r = L['search_edit']
        user32.MoveWindow(h, r.left, r.top, r.right - r.left,
                          r.bottom - r.top, True)

    # ------------------------------------------------------------ 布局
    def relayout(self):
        if not self.hwnd:
            return
        rc = RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rc))
        if rc.right <= 0 or rc.bottom <= 0:
            return
        self.ui.layout(rc.right, rc.bottom)
        self.sync_children()

    def fit_window(self):
        """把窗口调到目标尺寸并居中（在消息循环跑起来后调用才稳）。"""
        hwnd = self.hwnd
        try:
            if user32.IsIconic(hwnd) or user32.IsZoomed(hwnd):
                return
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
            w = max(560, min(920, sw - 80))
            h = max(460, min(660, sh - 80))
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 3)
            user32.SetWindowPos(hwnd, HWND_TOP, x, y, w, h,
                                SWP_NOZORDER | SWP_NOACTIVATE)
            self.relayout()
        except Exception:
            pass

    def toggle_max(self):
        hwnd = self.hwnd
        if user32.IsZoomed(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        else:
            user32.ShowWindow(hwnd, SW_MAXIMIZE)

    # ------------------------------------------------------------ 菜单
    def toggle_menu(self, open_=None):
        g['menu_open'] = (not g['menu_open']) if open_ is None else open_
        g['hover_menu'] = -1
        self.relayout()
        invalidate()

    def run_menu_item(self, idx):
        items = self.ui.menu_items()
        if not (0 <= idx < len(items)):
            return
        it = items[idx]
        mid = it.get('id')
        if mid == 'autostart':
            toggle_autostart()
            self.relayout()          # 开关状态变了，重算菜单
            invalidate()
            return                       # 开关类不关菜单，方便连续操作
        if mid == 'autotray':
            g['autotray'] = not g['autotray']
            set_hint("「置顶后转入后台」已%s"
                     % ("开启" if g['autotray'] else "关闭"))
            self.relayout()
            invalidate()
            return
        self.toggle_menu(False)
        if mid == 'theme':
            self.apply_dark(not g['dark'])
            tray_refresh_icon()
            self.relayout()
            invalidate()
        elif mid == 'refresh':
            refresh()
            set_hint("列表已刷新")
        elif mid == 'clear':
            clear_all()
        elif mid == 'help':
            set_hint("快捷键：Ctrl+Alt+T 置顶当前窗口 · Ctrl+Alt+M 显示/隐藏主窗口")
        elif mid == 'tray':
            hide_to_tray()
        elif mid == 'exit':
            user32.DestroyWindow(self.hwnd)

    # ------------------------------------------------------------ 鼠标
    def pos_of(self, lparam):
        return (ctypes.c_short(lparam & 0xFFFF).value,
                ctypes.c_short((lparam >> 16) & 0xFFFF).value)

    def on_mousemove(self, lparam):
        x, y = self.pos_of(lparam)
        kind, payload, rc = self.ui.hit_test(x, y)
        row = self.ui.row_at(y) if kind == HIT_SCROLL else -1
        menu_hover = payload if kind == HIT_MENU else -1
        changed = (kind != g['hover'] or row != g['hover_row'] or
                   menu_hover != g['hover_menu'])
        g['hover'] = kind
        g['hover_row'] = row
        g['hover_menu'] = menu_hover
        if changed:
            invalidate()

        # 光标
        cur = IDC_ARROW
        if kind in (HIT_TOGGLE, HIT_REFRESH, HIT_CLEAR, HIT_MENUBTN, HIT_THEME,
                    HIT_MIN, HIT_MAX, HIT_CLOSE, HIT_MENU):
            cur = IDC_HAND
        elif kind == HIT_SCROLL and not g['menu_open']:
            cur = IDC_ARROW
        user32.SetCursor(user32.LoadCursorW(None, ctypes.c_wchar_p(cur)))

        tme = TRACKMOUSEEVENT()
        tme.cbSize = ctypes.sizeof(TRACKMOUSEEVENT)
        tme.dwFlags = TRACKMOUSEEVENT_TME_LEAVE
        tme.hwndTrack = self.hwnd
        user32.TrackMouseEvent(ctypes.byref(tme))

    def on_lbuttondown(self, lparam, dbl):
        x, y = self.pos_of(lparam)
        kind, payload, rc = self.ui.hit_test(x, y)

        # 菜单打开时点菜单外 → 关菜单
        if kind == HIT_MENUCANCEL:
            self.toggle_menu(False)
            return
        if kind == HIT_MENU:
            if not dbl:
                self.run_menu_item(payload)
            return

        g['press'] = kind
        if kind == HIT_CLOSE:
            hide_to_tray()
            return
        if kind == HIT_MIN:
            hide_to_tray()
            return
        if kind == HIT_MAX:
            self.toggle_max()
            return
        if kind == HIT_MENUBTN:
            self.toggle_menu()
            return
        if kind == HIT_THEME:
            self.apply_dark(not g['dark'])
            tray_refresh_icon()
            invalidate()
            return
        if kind == HIT_TOGGLE:
            if not dbl:
                toggle_selected()
            return
        if kind == HIT_REFRESH:
            g['icon_cache'] = {}
            refresh()
            set_hint("列表已刷新")
            return
        if kind == HIT_CLEAR:
            clear_all()
            return
        if kind == HIT_SCROLL:
            row = self.ui.row_at(y)
            if row >= 0:
                if dbl:
                    toggle_row(row)
                else:
                    g['sel'] = row
                    invalidate()
            return
        if kind == HIT_NONE:
            # 标题栏空白处 → 拖动窗口（交给系统移动循环，支持贴边分屏）
            L = g['layout']
            if L and y < L['titlebar_h']:
                if dbl:
                    self.toggle_max()
                    return
                user32.ReleaseCapture()
                user32.SendMessageW(self.hwnd, WM_NCLBUTTONDOWN,
                                    ctypes.c_void_p(HTCAPTION), ctypes.c_void_p(0))

    def on_mousewheel(self, wparam):
        delta = ctypes.c_short((wparam >> 16) & 0xFFFF).value
        step = g['layout'].get('row_h', sc(46)) * 3
        g['scroll'] = max(0, min(g['scroll'] - (delta / 120) * step,
                                 g['scroll_max']))
        invalidate()

    def on_command(self, wparam):
        cid = wparam & 0xFFFF
        notify = (wparam >> 16) & 0xFFFF
        if cid == ID_SEARCH and notify == EN_CHANGE:
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(g['hwnd_search'], buf, 256)
            if buf.value != g['filter']:
                g['filter'] = buf.value
                refresh()
            return
        if cid == IDM_SHOW:
            show_window_()
        elif cid == IDM_REFRESH:
            refresh()
        elif cid == IDM_CLEAR:
            clear_all()
        elif cid == IDM_AUTOTRAY:
            g['autotray'] = not g['autotray']
            set_hint("「置顶后转入后台」已%s"
                     % ("开启" if g['autotray'] else "关闭"))
        elif cid == IDM_AUTOSTART:
            toggle_autostart()
        elif cid == IDM_EXIT:
            user32.DestroyWindow(g['hwnd_main'])

    # ------------------------------------------------------------ 窗口过程
    def wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_CREATE:
            try:
                dpi = user32.GetDpiForWindow(hwnd)
                g['scale'] = (dpi / 96.0) if dpi else 1.0
            except Exception:
                g['scale'] = 1.0
            g['dark'] = not is_light_theme()
            g['hicon'] = make_hicon(32)
            if g['hicon']:
                user32.SendMessageW(hwnd, WM_SETICON, 0, g['hicon'])
                user32.SendMessageW(hwnd, WM_SETICON, 1, g['hicon'])
            g['font_cache'] = T.make_fonts(g['scale'])
            g['himl'] = comctl32.ImageList_Create(sc(20), sc(20),
                                                  0x00000020 | 0x00000001, 0, 64)
            self.setup_dwm()
            self.create_children()
            return 0

        if msg == WM_NCCALCSIZE:
            if wparam and user32.IsZoomed(hwnd):
                # 最大化时把客户区对齐到监视器工作区，避免盖住任务栏
                params = ctypes.cast(lparam,
                                     ctypes.POINTER(NCCALCSIZE_PARAMS)).contents
                mon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                if user32.GetMonitorInfoW(mon, ctypes.byref(mi)):
                    w = mi.rcWork
                    params.rgrc[0].left = w.left
                    params.rgrc[0].top = w.top
                    params.rgrc[0].right = w.right
                    params.rgrc[0].bottom = w.bottom
            return 0        # 客户区 = 整个窗口（无边框）

        if msg == WM_NCHITTEST:
            px = ctypes.c_short(lparam & 0xFFFF).value
            py = ctypes.c_short((lparam >> 16) & 0xFFFF).value
            pt = POINT(px, py)
            user32.ScreenToClient(hwnd, ctypes.byref(pt))
            if not user32.IsZoomed(hwnd):
                b = sc(6)
                rc = RECT()
                user32.GetClientRect(hwnd, ctypes.byref(rc))
                left = pt.x < b
                right = pt.x >= rc.right - b
                top = pt.y < b
                bottom = pt.y >= rc.bottom - b
                if top and left:
                    return HTTOPLEFT
                if top and right:
                    return HTTOPRIGHT
                if bottom and left:
                    return HTBOTTOMLEFT
                if bottom and right:
                    return HTBOTTOMRIGHT
                if left:
                    return HTLEFT
                if right:
                    return HTRIGHT
                if top:
                    return HTTOP
                if bottom:
                    return HTBOTTOM
            return HTCLIENT

        if msg == WM_LBUTTONDOWN:
            self.on_lbuttondown(lparam, False)
            return 0
        if msg == WM_LBUTTONDBLCLK:
            self.on_lbuttondown(lparam, True)
            return 0
        if msg == WM_LBUTTONUP:
            g['press'] = HIT_NONE
            invalidate()
            return 0
        if msg == WM_MOUSEMOVE:
            self.on_mousemove(lparam)
            return 0
        if msg == WM_MOUSELEAVE:
            if (g['hover'] != HIT_NONE or g['hover_row'] != -1 or
                    g['hover_menu'] != -1):
                g['hover'] = HIT_NONE
                g['hover_row'] = -1
                g['hover_menu'] = -1
                invalidate()
            return 0
        if msg == WM_MOUSEWHEEL:
            self.on_mousewheel(wparam)
            return 0

        if msg == WM_KEYDOWN:
            if wparam == 0x1B and g['menu_open']:        # ESC 关菜单
                self.toggle_menu(False)
                return 0
            if wparam == 0x1B and g['hwnd_search']:      # ESC 清空搜索
                user32.SetWindowTextW(g['hwnd_search'], "")
                return 0
            return 0

        if msg == WM_PAINT:
            self.on_paint(hwnd)
            return 0
        if msg == WM_ERASEBKGND:
            return 1

        if msg == WM_SIZE:
            g['maximized'] = (wparam == SIZE_MAXIMIZED)
            self.relayout()
            invalidate()
            return 0

        if msg == WM_GETMINMAXINFO:
            mmi = ctypes.cast(lparam, ctypes.POINTER(MINMAXINFO)).contents
            mmi.ptMinTrackSize.x = 560
            mmi.ptMinTrackSize.y = 460
            return 0

        if msg == WM_DPICHANGED:
            g['scale'] = wparam / 96.0
            g['font_cache'] = T.make_fonts(g['scale'])
            self.relayout()
            invalidate()
            return 0

        if msg == WM_TIMER:
            if wparam == 1:
                if not g['hidden'] and user32.IsWindowVisible(hwnd):
                    refresh()
            elif wparam == 2:
                if not g['hidden'] and user32.IsWindowVisible(hwnd):
                    invalidate()
            elif wparam == 3:
                user32.KillTimer(hwnd, 3)
                self.fit_window()
            return 0

        if msg == WM_HOTKEY:
            if wparam == HKID_TOGGLE:
                on_hotkey_toggle()
            elif wparam == HKID_SHOW:
                if g['hidden'] or not user32.IsWindowVisible(hwnd):
                    show_window_()
                else:
                    hide_to_tray()
            return 0

        if msg == WM_TRAYICON:
            ev = lparam & 0xFFFF
            if ev == WM_RBUTTONUP:
                show_tray_menu()
            elif ev in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                show_window_()
            return 0

        if msg == WM_COMMAND:
            self.on_command(wparam)
            return 0

        if msg == WM_CTLCOLOREDIT:
            # 让搜索框背景透出底下的自绘玻璃底框
            hdc = ctypes.c_void_p(wparam)
            gdi32.SetBkMode(hdc, TRANSPARENT)
            gdi32.SelectObject(hdc, g['font_cache']['body'])
            gdi32.SetTextColor(hdc, self.ui.pal()['fg'])
            return gdi32.GetStockObject(NULL_BRUSH)

        if msg == WM_CLOSE:
            hide_to_tray()
            return 0

        if msg == WM_DESTROY:
            user32.KillTimer(hwnd, 1)
            user32.KillTimer(hwnd, 2)
            user32.UnregisterHotKey(hwnd, HKID_TOGGLE)
            user32.UnregisterHotKey(hwnd, HKID_SHOW)
            tray_delete()
            user32.PostQuitMessage(0)
            return 0

        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def on_paint(self, hwnd):
        ps = PAINTSTRUCT()
        hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
        rc = RECT()
        user32.GetClientRect(hwnd, ctypes.byref(rc))
        w, h = max(1, rc.right), max(1, rc.bottom)
        cv = self.canvas
        try:
            cv.ensure(w, h)
            self.ui.paint(cv, w, h)
            cv.blit_to(hdc)          # 一次性输出，无闪烁
        except Exception:
            import traceback
            traceback.print_exc()
        user32.EndPaint(hwnd, ctypes.byref(ps))


# ============================== 入口 ==============================
CLASS_NAME = "AlwaysOnTopAuroraWnd"


def make_hicon(px=32):
    """生成应用图标（HICON）。任何情况下都返回有效句柄，避免托盘无图标。"""
    try:
        hi = appicon.hicon(px)
        if hi:
            return hi
    except Exception:
        pass
    return user32.LoadIconW(None, ctypes.c_wchar_p(IDI_APPLICATION))


def capture_window(hwnd, path):
    """把窗口客户区的真实内容存成 PNG（用于自截验证）。

    必须在窗口所属进程内调用：跨进程/跨窗口站抓不到内容。
    """
    from aurora import BITMAPINFO, BITMAPINFOHEADER
    rc = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rc))
    w, h = max(1, rc.right), max(1, rc.bottom)
    src = user32.GetDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(ctypes.c_void_p(src))
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0
    bits = ctypes.c_void_p()
    bmp = gdi32.CreateDIBSection(ctypes.c_void_p(src), ctypes.byref(bmi), 0,
                                 ctypes.byref(bits), None, 0)
    old = gdi32.SelectObject(ctypes.c_void_p(mdc), bmp)
    gdi32.BitBlt(ctypes.c_void_p(mdc), 0, 0, w, h, ctypes.c_void_p(src),
                 0, 0, 0x00CC0020)
    data = ctypes.string_at(bits, w * h * 4)
    user32.ReleaseDC(hwnd, src)
    gdi32.SelectObject(ctypes.c_void_p(mdc), old)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(ctypes.c_void_p(mdc))
    appicon.write_png(path, w, h, data)
    return w, h


def default_pos(w, h):
    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)
    return max(0, (sw - w) // 2), max(0, (sh - h) // 3)


_KEEP = []      # 保活引用（--shot 退出路径需要）


def main():
    # 控制台编码可能是 cp1252（Windows CI / 部分环境），此时任何中文输出都会抛
    # UnicodeEncodeError 把进程打挂。先把它调成 UTF-8 容错模式。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

    hinst = kernel32.GetModuleHandleW(None)
    g['autostart'] = autostart.is_enabled()

    app = App()
    app.hwnd = None

    cls = WNDCLASSEXW()
    cls.cbSize = ctypes.sizeof(WNDCLASSEXW)
    cls.lpfnWndProc = WndProcType(app.wndproc)
    cls.hInstance = hinst
    cls.lpszClassName = CLASS_NAME
    cls.style = CS_DBLCLKS
    g['hicon'] = make_hicon(32)
    cls.hIcon = g['hicon']
    cls.hIconSm = make_hicon(16)
    cls.hbrBackground = None
    user32.RegisterClassExW(ctypes.byref(cls))

    style = (WS_POPUP | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX |
             WS_CLIPCHILDREN)
    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)
    win_w = max(560, min(920, sw - 80))
    win_h = max(460, min(660, sh - 80))
    x, y = default_pos(win_w, win_h)
    hwnd = user32.CreateWindowExW(WS_EX_APPWINDOW, CLASS_NAME, "窗口置顶小工具",
                                  style, x, y, win_w, win_h,
                                  None, None, hinst, None)
    if not hwnd:
        return
    app.hwnd = hwnd
    g['hwnd_main'] = hwnd

    app.relayout()
    tray_add()

    ok1 = user32.RegisterHotKey(hwnd, HKID_TOGGLE, MOD_CONTROL | MOD_ALT, VK_T)
    user32.RegisterHotKey(hwnd, HKID_SHOW, MOD_CONTROL | MOD_ALT, VK_M)
    if not ok1:
        set_hint("提示：Ctrl+Alt+T 被其它程序占用，前台置顶快捷键不可用")

    start_hidden = autostart.launched_as_tray()
    if start_hidden:
        # 开机自启：直接收进托盘，不弹主窗口
        user32.ShowWindow(hwnd, SW_HIDE)
        g['hidden'] = True
    else:
        user32.ShowWindow(hwnd, SW_SHOWNORMAL)
        user32.SetForegroundWindow(hwnd)
    user32.UpdateWindow(hwnd)
    refresh()
    user32.SetTimer(hwnd, 1, 2500, None)      # 自动刷新列表
    user32.SetTimer(hwnd, 2, 40, None)        # 流光动画 ~25fps
    if not start_hidden:
        user32.SetTimer(hwnd, 3, 120, None)   # 一次性：校正窗口尺寸

    # 自截验证：把真实窗口内容存成 PNG 后退出（不进入消息循环）
    if "--shot" in sys.argv:
        i = sys.argv.index("--shot")
        path = sys.argv[i + 1] if i + 1 < len(sys.argv) else "shot.png"
        user32.ShowWindow(hwnd, SW_SHOWNORMAL)
        user32.SetForegroundWindow(hwnd)
        user32.UpdateWindow(hwnd)
        # 强制走一遍 WM_PAINT
        user32.InvalidateRect(hwnd, None, True)
        user32.UpdateWindow(hwnd)
        time.sleep(0.4)
        for _ in range(8):
            m = wt.MSG()
            while user32.PeekMessageW(ctypes.byref(m), None, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(m))
                user32.DispatchMessageW(ctypes.byref(m))
            user32.InvalidateRect(hwnd, None, False)
            user32.UpdateWindow(hwnd)
            time.sleep(0.08)
        w, h = capture_window(hwnd, path)
        with open("_shot.log", "w") as f:
            f.write("saved %s %dx%d\n" % (path, w, h))
        # 干净退出：不销毁窗口就 return 会让进程带着活动窗口/托盘图标结束，
        # Windows 在收尾时会直接把进程打崩（退出码 139）。
        user32.KillTimer(hwnd, 1)
        user32.KillTimer(hwnd, 2)
        user32.KillTimer(hwnd, 3)
        user32.UnregisterHotKey(hwnd, HKID_TOGGLE)
        user32.UnregisterHotKey(hwnd, HKID_SHOW)
        tray_delete()
        user32.DestroyWindow(hwnd)
        # 窗口类还注册着的话，解释器退出时会因为回调过程已被回收而崩
        _KEEP.append(app)                      # 保活，避免回调对象先被 GC
        user32.UnregisterClassW(CLASS_NAME, ctypes.c_void_p(hinst))
        # Python 的收尾阶段（GC ctypes 回调 + 卸载 DLL）在这类窗口场景下会崩，
        # 直接退出进程，跳过收尾——日志与 PNG 都已落盘。
        import os as _os
        _os._exit(0)

    msg = wt.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


if __name__ == "__main__":
    main()
