# -*- coding: utf-8 -*-
"""
窗口置顶小工具 (AlwaysOnTop) —— Fluent 流光现代 UI

纯 Win32 + ctypes，零第三方依赖（图标生成用可选的 Pillow）。

功能：
  · 流光（Aurora）渐变背景 + 玻璃拟态卡片，全部 GDI 自绘
  · 类 Explorer 窗口列表，图标 + 标题 + 进程，圆角悬停/选中
  · 开机自启开关（写 HKCU\\...\\Run，无需管理员）
  · 随系统明暗主题切换
  · 点击「置顶」后自动转入托盘，全局快捷键 Ctrl+Alt+T / Ctrl+Alt+M

注意：独占全屏(exclusive fullscreen)游戏会独占显示输出，置顶无效；
      请改用「无边框 / 窗口化全屏」。
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time
import winreg

import autostart
import theme as T
from aurora import RECT, SHFILEINFOW, rgb, lighten, darken, user32, gdi32

# ============================== 常量 ==============================
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
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
SW_MINIMIZE = 6

WM_CREATE = 0x0001
WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_PAINT = 0x000F
WM_CLOSE = 0x0010
WM_ERASEBKGND = 0x0014
WM_SHOWWINDOW = 0x0018
WM_GETMINMAXINFO = 0x0024
WM_SETICON = 0x0080
WM_TIMER = 0x0113
WM_HOTKEY = 0x0312
WM_MOUSEMOVE = 0x0200
WM_MOUSELEAVE = 0x02A3
WM_MOUSEWHEEL = 0x020A
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_CAPTURECHANGED = 0x0215
WM_COMMAND = 0x0111
WM_RBUTTONUP = 0x0205
WM_LBUTTONDOWN_NC = 0x00A1
WM_NCHITTEST = 0x0084
WM_NCLBUTTONDOWN = 0x00A1
WM_NCLBUTTONDBLCLK = 0x00A3
WM_SYSCOMMAND = 0x0112
WM_DPICHANGED = 0x02E0
WM_SETCURSOR = 0x0020
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 1
WM_APPTHEME = WM_USER + 2

WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_CHILD = 0x40000000
WS_CLIPSIBLINGS = 0x04000000
WS_CLIPCHILDREN = 0x02000000
WS_TABSTOP = 0x00010000
WS_OVERLAPPEDWINDOW = 0x00CF0000
CS_DBLCLKS = 0x0008

HTCLIENT = 1
HTCAPTION = 2
HTMINBUTTON = 8
HTMAXBUTTON = 9
HTCLOSE = 20

SC_MINIMIZE = 0xF020
SC_CLOSE = 0xF060
SC_MAXIMIZE = 0xF030
SC_RESTORE = 0xF120

IDC_ARROW = 32512
IDC_HAND = 32649
IDC_SIZEALL = 32646

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
SHGFI_ICON = 0x000000100
SHGFI_SMALLICON = 0x000000001
SHGFI_LARGEICON = 0x000000000

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
DWMWCP_ROUND = 2
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWM_SYSTEMBACKDROP_TYPE = 38

# 托盘
NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_INFO = 0x00000010
NIIF_INFO = 0x00000001
NIIF_NOSOUND = 0x00000010

# 菜单
MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
MF_CHECKED = 0x00000008
MF_UNCHECKED = 0x00000000
TPM_LEFTALIGN = 0x0000
TPM_RIGHTBUTTON = 0x0002

TRACKMOUSEEVENT_TME_LEAVE = 0x00000002
MF_BYCOMMAND = 0x00000000

# 菜单/命令 ID
ID_TOGGLE = 101
ID_REFRESH = 102
ID_CLEAR = 103
ID_TRAY = 104
ID_AUTOTRAY = 108
ID_AUTOSTART = 109
IDM_SHOW = 2001
IDM_REFRESH = 2002
IDM_CLEAR = 2003
IDM_AUTOTRAY = 2004
IDM_AUTOSTART = 2006
IDM_EXIT = 2005

# 命中区域（自绘控件）
HIT_NONE = 0
HIT_TOGGLE = 1
HIT_REFRESH = 2
HIT_CLEAR = 3
HIT_TRAY = 4
HIT_AUTOTRAY = 5
HIT_AUTOSTART = 6
HIT_ROW = 7
HIT_SCROLL = 8
HIT_SCROLLTRACK = 9
HIT_TITLE = 10
HIT_CLOSE = 11
HIT_MIN = 12

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)
uxtheme = ctypes.WinDLL("uxtheme", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

LRESULT = ctypes.c_ssize_t
NEG_ONE = ctypes.c_void_p(0xFFFFFFFFFFFFFFFF)
WndProcType = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)


# ============================== 结构体 ==============================
class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", WndProcType),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HANDLE), ("hIcon", wt.HANDLE), ("hCursor", wt.HANDLE),
        ("hbrBackground", wt.HANDLE), ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR), ("hIconSm", wt.HANDLE),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", wt.LONG), ("y", wt.LONG)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uID", wt.UINT),
        ("uFlags", wt.UINT), ("uCallbackMessage", wt.UINT), ("hIcon", wt.HANDLE),
        ("szTip", wt.WCHAR * 128), ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD),
        ("szInfo", wt.WCHAR * 256), ("uVersion", wt.UINT),
        ("szInfoTitle", wt.WCHAR * 64), ("dwInfoFlags", wt.DWORD),
        ("guidItem", wt.DWORD * 16), ("hBalloonIcon", wt.HANDLE),
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wt.BOOL), ("xHotspot", wt.DWORD),
                ("yHotspot", wt.DWORD), ("hbmMask", wt.HANDLE),
                ("hbmColor", wt.HANDLE)]


class MINMAXINFO(ctypes.Structure):
    _fields_ = [("ptReserved", POINT), ("ptMaxSize", POINT),
                ("ptMaxPosition", POINT), ("ptMinTrackSize", POINT),
                ("ptMaxTrackSize", POINT)]


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
user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, ctypes.c_void_p, ctypes.c_void_p]
user32.SendMessageW.restype = ctypes.c_int64
user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = [ctypes.POINTER(wt.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wt.MSG)]
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
user32.ShowWindow.restype = wt.BOOL
user32.UpdateWindow.argtypes = [wt.HWND]
user32.DestroyWindow.argtypes = [wt.HWND]
user32.SetWindowTextW.argtypes = [wt.HWND, ctypes.c_wchar_p]
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wt.UINT]
user32.SetWindowPos.restype = wt.BOOL
user32.GetClientRect.argtypes = [wt.HWND, ctypes.POINTER(RECT)]
user32.GetClientRect.restype = wt.BOOL
user32.BeginPaint.argtypes = [wt.HWND, ctypes.c_void_p]
user32.BeginPaint.restype = ctypes.c_void_p
user32.EndPaint.argtypes = [wt.HWND, ctypes.c_void_p]
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wt.BOOL
user32.SetForegroundWindow.argtypes = [wt.HWND]
user32.SetForegroundWindow.restype = wt.BOOL
user32.GetForegroundWindow.restype = wt.HWND
user32.CreatePopupMenu.restype = wt.HANDLE
user32.AppendMenuW.argtypes = [wt.HMENU, wt.UINT, ctypes.c_uint64, ctypes.c_wchar_p]
user32.TrackPopupMenu.argtypes = [wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, wt.HWND, ctypes.POINTER(RECT)]
user32.TrackPopupMenu.restype = wt.BOOL
user32.DestroyMenu.argtypes = [wt.HMENU]
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindowVisible.restype = wt.BOOL
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wt.HWND, ctypes.c_wchar_p, ctypes.c_int]
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = wt.LONG
user32.RegisterHotKey.argtypes = [wt.HWND, ctypes.c_int, wt.UINT, wt.UINT]
user32.RegisterHotKey.restype = wt.BOOL
user32.UnregisterHotKey.argtypes = [wt.HWND, ctypes.c_int]
user32.CreateIconIndirect.argtypes = [ctypes.POINTER(ICONINFO)]
user32.CreateIconIndirect.restype = wt.HANDLE
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
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wt.BOOL
user32.GetMessagePos.restype = wt.DWORD
user32.GetDpiForWindow.argtypes = [wt.HWND]
user32.GetDpiForWindow.restype = wt.UINT
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.LoadCursorW.argtypes = [wt.HINSTANCE, wt.LPCWSTR]
user32.LoadCursorW.restype = wt.HANDLE
user32.SetCursor.argtypes = [wt.HANDLE]
user32.SetCursor.restype = wt.HANDLE
user32.GetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int]
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_ssize_t]
user32.IsZoomed.argtypes = [wt.HWND]
user32.IsZoomed.restype = wt.BOOL
user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM),
                               wt.LPARAM]
user32.EnumWindows.restype = wt.BOOL
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype = wt.DWORD

kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel32.GetModuleHandleW.restype = wt.HANDLE
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.CloseHandle.argtypes = [wt.HANDLE]
psapi.GetModuleFileNameExW.argtypes = [wt.HANDLE, wt.HMODULE,
                                       ctypes.c_wchar_p, wt.DWORD]
psapi.GetModuleFileNameExW.restype = wt.DWORD

gdi32.DeleteObject.argtypes = [wt.HANDLE]
gdi32.SelectObject.argtypes = [ctypes.c_void_p, wt.HANDLE]
gdi32.SelectObject.restype = wt.HANDLE
gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
gdi32.SetDCPenColor.argtypes = [ctypes.c_void_p, wt.DWORD]
gdi32.SetDCBrushColor.argtypes = [ctypes.c_void_p, wt.DWORD]

shell32.Shell_NotifyIconW.argtypes = [wt.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
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
comctl32.ImageList_Destroy.argtypes = [wt.HANDLE]

uxtheme.SetWindowTheme.argtypes = [wt.HWND, ctypes.c_wchar_p, ctypes.c_wchar_p]
uxtheme.SetWindowTheme.restype = ctypes.c_long

dwmapi.DwmSetWindowAttribute.argtypes = [wt.HWND, wt.DWORD, ctypes.c_void_p, wt.DWORD]
dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long


# ============================== 全局状态 ==============================
g = {
    'scale': 1.0,
    'dark': False,
    'pal': None,
    'rows': [],            # [(hwnd, title, exe, path, topmost)]
    'filter': '',
    'sel': -1,
    'hover': HIT_NONE,
    'hover_row': -1,
    'press': HIT_NONE,
    'press_row': -1,
    'autotray': True,
    'autostart': False,
    'hidden': False,
    'icon_cache': {},
    'tray_added': False,
    'first_hide': True,
    'hicon': None,
    'himl': None,
    'scroll': 0,
    'scroll_max': 0,
    'font_cache': {},
    't0': time.time(),
    'layout': {},
    'hint': '',
    'maximized': False,
}


def is_light_theme():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return True


def sc(v):
    return int(round(v * g['scale']))


def F(name):
    return g['font_cache'].get(name)


# ============================== 核心：窗口枚举与置顶 ==============================
def get_title(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def get_exe_path(pid):
    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        return ""
    buf = ctypes.create_unicode_buffer(1024)
    try:
        ctypes.windll.psapi.GetModuleFileNameExW(h, None, buf, 1024)
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
        if not user32.IsWindowVisible(hwnd):
            return True
        if hwnd == own_hwnd:
            return True
        title = get_title(hwnd)
        if not title:
            return True
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        path = get_exe_path(pid.value)
        if not path:
            return True
        exe = path.split("\\")[-1]
        result.append((int(hwnd), title, exe, path))
        return True

    enum_windows._cb = cb
    user32.EnumWindows(cb, 0)
    return result


def icon_index_for_path(path):
    if not path:
        return -1
    if path in g['icon_cache']:
        return g['icon_cache'][path]
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
    """重新枚举窗口，应用搜索过滤。"""
    keep = None
    if 0 <= g['sel'] < len(g['rows']):
        keep = g['rows'][g['sel']][0]

    wins = enum_windows(g['hwnd_main'])
    flt = (g['filter'] or '').strip().lower()
    g['rows'] = []
    g['sel'] = -1
    for hwnd, title, exe, path in wins:
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


def set_hint(msg):
    g['hint'] = msg
    invalidate()


def invalidate():
    user32.InvalidateRect(g.get('hwnd_main'), None, False)


def toggle_selected():
    row = selected_row()
    if not row:
        set_hint("请先选择一个窗口")
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
    if not (0 <= idx < len(g['rows'])):
        return
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


# ============================== 图标 ==============================
def resource_path(name):
    """定位未打包（脚本）或打包后（_MEIPASS / exe 目录）的资源文件。"""
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    cand = [os.path.join(here, name)]
    if getattr(sys, 'frozen', False):
        cand.append(os.path.join(getattr(sys, '_MEIPASS', ''), name))
        cand.append(os.path.join(os.path.dirname(sys.executable), name))
    for c in cand:
        if os.path.exists(c):
            return c
    return cand[0]


def draw_icon_rgba(px=32, accent=None):
    """从预渲染高清 master (icon.png) 取图，输出 top-down BGRA（alpha 预乘）。"""
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        im = Image.open(resource_path('icon.png')).convert('RGBA') \
             .resize((px, px), Image.LANCZOS)
    except Exception:
        return None
    raw = im.tobytes()
    n = len(raw) // 4
    out = bytearray(n * 4)
    for i in range(n):
        r, gg, b, a = raw[i*4], raw[i*4+1], raw[i*4+2], raw[i*4+3]
        out[i*4] = b * a // 255
        out[i*4 + 1] = gg * a // 255
        out[i*4 + 2] = r * a // 255
        out[i*4 + 3] = a
    return bytes(out)


def draw_icon_hicon(px=32):
    from aurora import BITMAPINFO, BITMAPINFOHEADER
    rgba = draw_icon_rgba(px)
    if not rgba:
        return None
    hdc_screen = user32.GetDC(None)
    bmi = BITMAPINFO()
    head = bmi.bmiHeader
    head.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    head.biWidth = px
    head.biHeight = -px
    head.biPlanes = 1
    head.biBitCount = 32
    head.biCompression = 0
    bits = ctypes.c_void_p()
    hbm = gdi32.CreateDIBSection(ctypes.c_void_p(hdc_screen),
                                 ctypes.byref(bmi), 0,
                                 ctypes.byref(bits), None, 0)
    user32.ReleaseDC(None, hdc_screen)
    if not hbm:
        return None
    ctypes.memmove(bits, rgba, len(rgba))
    mask = gdi32.CreateBitmap(px, px, 1, 1, None)
    ii = ICONINFO()
    ii.fIcon = True
    ii.hbmMask = mask
    ii.hbmColor = hbm
    hicon = user32.CreateIconIndirect(ctypes.byref(ii))
    gdi32.DeleteObject(mask)
    gdi32.DeleteObject(hbm)
    return hicon


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
    nid.hIcon = g['hicon']
    nid.szTip = "窗口置顶小工具"
    if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
        nid.cbSize = 952
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
    g['tray_added'] = True


def tray_delete():
    if not g['tray_added']:
        return
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = g['hwnd_main']
    nid.uID = 1
    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
    g['tray_added'] = False


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
            nid.cbSize = 952
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
              "%s 已置顶。\n程序已最小化到托盘，按 Ctrl+Alt+M 或双击托盘图标可重新打开。"
              % (title[:40] or "目标窗口"))
    elif g['first_hide']:
        g['first_hide'] = False
        toast("已在后台运行", "程序已最小化到系统托盘，全局快捷键仍然生效。")


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
                       MF_STRING | (MF_CHECKED if g['autotray'] else MF_UNCHECKED),
                       IDM_AUTOTRAY, "置顶后自动转入后台")
    user32.AppendMenuW(menu,
                       MF_STRING | (MF_CHECKED if g['autostart'] else MF_UNCHECKED),
                       IDM_AUTOSTART, "开机自启")
    user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
    user32.AppendMenuW(menu, MF_STRING, IDM_EXIT, "退出")
    user32.SetForegroundWindow(g['hwnd_main'])
    user32.TrackPopupMenu(menu, TPM_LEFTALIGN | TPM_RIGHTBUTTON,
                          pt.x, pt.y, 0, g['hwnd_main'], None)
    user32.DestroyMenu(menu)


def toggle_autostart():
    ok, msg = autostart.set_enabled(not g['autostart'])
    if ok:
        g['autostart'] = not g['autostart']
        toast("开机自启", msg)
    else:
        toast("开机自启", msg)
    set_hint(msg)
    invalidate()


# ============================== 应用对象 ==============================
class App:
    HIT_NONE = 0
    HIT_TOGGLE = 1
    HIT_REFRESH = 2
    HIT_CLEAR = 3
    HIT_TRAY = 4
    HIT_AUTOTRAY = 5
    HIT_AUTOSTART = 6
    HIT_ROW = 7
    HIT_SCROLL = 8
    HIT_TITLE = 10
    HIT_CLOSE = 11
    HIT_MIN = 12

    def __init__(self):
        self.g = g
        from ui import UI
        self.ui = UI(self)
        self.hwnd = None
        self.drag_start = None
        self.scrolled = False

    # --- 转发到模块级函数 ---
    def sc(self, v):
        return sc(v)

    def clamp_scroll(self):
        clamp_scroll()

    def selected_row(self):
        return selected_row()

    def apply_dark(self, dark):
        g['dark'] = dark
        self.ui.apply_theme()
        try:
            d = ctypes.c_int(1 if dark else 0)
            dwmapi.DwmSetWindowAttribute(self.hwnd,
                                         DWMWA_USE_IMMERSIVE_DARK_MODE,
                                         ctypes.byref(d), 4)
        except Exception:
            pass

    # ------------------------------------------------------------ 窗口过程
    def wndproc(self, hwnd, msg, wparam, lparam):
        g = self.g
        if msg == WM_CREATE:
            try:
                dpi = user32.GetDpiForWindow(hwnd)
                g['scale'] = (dpi / 96.0) if dpi else 1.0
            except Exception:
                g['scale'] = 1.0
            self.apply_dark(not is_light_theme())
            g['font_cache'] = T.make_fonts(g['scale'])
            self.apply_caption_colors()
            if not g.get('hicon'):
                g['hicon'] = draw_icon_hicon(32)
            if g['hicon']:
                user32.SendMessageW(hwnd, WM_SETICON, 0, g['hicon'])
                user32.SendMessageW(hwnd, WM_SETICON, 1, g['hicon'])
            return 0

        if msg == WM_DPICHANGED:
            g['scale'] = wparam / 96.0
            g['font_cache'] = T.make_fonts(g['scale'])
            r = ctypes.cast(lparam, ctypes.POINTER(RECT)).contents
            user32.SetWindowPos(hwnd, None, r.left, r.top,
                                r.right - r.left, r.bottom - r.top,
                                SWP_NOMOVE | SWP_NOZORDER)
            invalidate()
            return 0

        if msg == WM_NCHITTEST:
            # 自绘标题栏：让系统知道哪里可拖动、哪里是按钮
            p = POINT()
            p.x = ctypes.c_short(lparam & 0xFFFF).value
            p.y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
            user32.ScreenToClient(hwnd, ctypes.byref(p))
            L = g['layout']
            if L:
                x, y = p.x, p.y
                def inr(rc):
                    return rc.left <= x < rc.right and rc.top <= y < rc.bottom
                if inr(L['close']):
                    return HTCLOSE
                if inr(L['min']):
                    return HTMINBUTTON
                if y < L['cap_h']:
                    return HTCAPTION
            return HTCLIENT

        if msg == WM_NCLBUTTONDBLCLK:
            if wparam == HTCAPTION:
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        if msg == WM_NCLBUTTONDOWN:
            if wparam == HTCLOSE:
                hide_to_tray()
                return 0
            if wparam == HTMINBUTTON:
                hide_to_tray()
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        if msg == WM_LBUTTONDOWN:
            self.on_click(hwnd, lparam, False)
            return 0

        if msg == WM_LBUTTONDBLCLK:
            self.on_click(hwnd, lparam, True)
            return 0

        if msg == WM_LBUTTONUP:
            g['press'] = HIT_NONE
            invalidate()
            return 0

        if msg == WM_MOUSEMOVE:
            self.on_mousemove(hwnd, lparam)
            return 0

        if msg == WM_MOUSELEAVE:
            if g['hover'] != HIT_NONE or g['hover_row'] != -1:
                g['hover'] = HIT_NONE
                g['hover_row'] = -1
                invalidate()
            return 0

        if msg == WM_MOUSEWHEEL:
            delta = ctypes.c_short((wparam >> 16) & 0xFFFF).value
            L = g['layout']
            step = L.get('row_h', sc(46)) * 3
            g['scroll'] = max(0, min(g['scroll'] - (delta / 120) * step,
                                     g['scroll_max']))
            invalidate()
            return 0

        if msg == WM_PAINT:
            self.on_paint(hwnd)
            return 0

        if msg == WM_ERASEBKGND:
            return 1

        if msg == WM_SIZE:
            self.relayout()
            return 0

        if msg == WM_GETMINMAXINFO:
            mmi = ctypes.cast(lparam, ctypes.POINTER(MINMAXINFO)).contents
            mmi.ptMinTrackSize.x = sc(620)
            mmi.ptMinTrackSize.y = sc(520)
            return 0

        if msg == WM_TIMER:
            if wparam == 1:
                if not g['hidden'] and user32.IsWindowVisible(hwnd):
                    self.rebuild_icon_list()
                    refresh()
            elif wparam == 2:
                # 流光动画
                if not g['hidden'] and user32.IsWindowVisible(hwnd):
                    invalidate()
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
            if lparam == WM_RBUTTONUP:
                show_tray_menu()
            elif lparam == WM_LBUTTONDBLCLK:
                show_window_()
            elif lparam == WM_LBUTTONUP:
                show_window_()
            return 0

        if msg == WM_COMMAND:
            self.on_command(wparam)
            return 0

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

    # ------------------------------------------------------------ 交互
    def local_pos(self, hwnd, lparam):
        p = POINT()
        p.x = ctypes.c_short(lparam & 0xFFFF).value
        p.y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
        return p.x, p.y

    def on_mousemove(self, hwnd, lparam):
        g = self.g
        x, y = self.local_pos(hwnd, lparam)
        kind, payload, rc = self.ui.hit_test(x, y)
        row = self.ui.row_at(y) if kind == self.HIT_SCROLL else -1
        if kind != g['hover'] or row != g['hover_row']:
            g['hover'] = kind
            g['hover_row'] = row
            invalidate()
        # 光标
        cur = IDC_ARROW
        if kind in (self.HIT_TOGGLE, self.HIT_REFRESH, self.HIT_CLEAR,
                    self.HIT_CLOSE, self.HIT_MIN, self.HIT_AUTOTRAY,
                    self.HIT_AUTOSTART):
            cur = IDC_HAND
        elif kind == self.HIT_SCROLL:
            cur = IDC_ARROW
        user32.SetCursor(user32.LoadCursorW(None, ctypes.c_wchar_p(cur)))
        tme = TRACKMOUSEEVENT()
        tme.cbSize = ctypes.sizeof(TRACKMOUSEEVENT)
        tme.dwFlags = TRACKMOUSEEVENT_TME_LEAVE
        tme.hwndTrack = hwnd
        user32.TrackMouseEvent(ctypes.byref(tme))

    def on_click(self, hwnd, lparam, dbl):
        g = self.g
        x, y = self.local_pos(hwnd, lparam)
        kind, payload, rc = self.ui.hit_test(x, y)
        if kind == self.HIT_CLOSE:
            hide_to_tray()
            return
        if kind == self.HIT_MIN:
            hide_to_tray()
            return
        if kind == self.HIT_TOGGLE:
            if dbl:
                return
            g['press'] = kind
            toggle_selected()
            invalidate()
            return
        if kind == self.HIT_REFRESH:
            self.rebuild_icon_list()
            refresh()
            set_hint("列表已刷新")
            return
        if kind == self.HIT_CLEAR:
            clear_all()
            return
        if kind == self.HIT_AUTOTRAY:
            g['autotray'] = not g['autotray']
            set_hint("「置顶后转入后台」已%s" % ("开启" if g['autotray'] else "关闭"))
            invalidate()
            return
        if kind == self.HIT_AUTOSTART:
            toggle_autostart()
            return
        if kind == self.HIT_SCROLL:
            row = self.ui.row_at(y)
            if row >= 0:
                if dbl:
                    toggle_row(row)
                else:
                    g['sel'] = row
                    invalidate()
            return

    def on_command(self, wparam):
        g = self.g
        cid = wparam & 0xFFFF
        if cid == IDM_SHOW:
            show_window_()
        elif cid == IDM_REFRESH:
            refresh()
        elif cid == IDM_CLEAR:
            clear_all()
        elif cid == IDM_AUTOTRAY:
            g['autotray'] = not g['autotray']
            set_hint("「置顶后转入后台」已%s" % ("开启" if g['autotray'] else "关闭"))
            if not g['hidden']:
                invalidate()
        elif cid == IDM_AUTOSTART:
            toggle_autostart()
        elif cid == IDM_EXIT:
            user32.DestroyWindow(g['hwnd_main'])

    # ------------------------------------------------------------ 绘制
    def apply_caption_colors(self):
        pal = self.ui.pal()
        hwnd = self.hwnd
        try:
            # 标题栏与背景同色，做成「无边框」观感
            col = ctypes.c_int(pal['aurora_base'])
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR,
                                         ctypes.byref(col), 4)
            tcol = ctypes.c_int(pal['text'])
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR,
                                         ctypes.byref(tcol), 4)
            corner = ctypes.c_int(DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                                         ctypes.byref(corner), 4)
        except Exception:
            pass

    def rebuild_icon_list(self):
        g = self.g
        g['icon_cache'] = {}

    def relayout(self):
        rc = RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rc))
        w, h = rc.right, rc.bottom
        if w <= 0 or h <= 0:
            return
        self.ui.layout(w, h)

    def on_paint(self, hwnd):
        g = self.g
        ps = ctypes.create_string_buffer(64)
        hdc = user32.BeginPaint(hwnd, ps)
        rc = RECT()
        user32.GetClientRect(hwnd, ctypes.byref(rc))
        self.ui.paint(hdc, rc.right, rc.bottom)
        user32.EndPaint(hwnd, ps)


def main():
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

    hinst = kernel32.GetModuleHandleW(None)
    app = App()
    g['autostart'] = autostart.is_enabled()
    g['hwnd_main'] = None

    cls = WNDCLASSEXW()
    cls.cbSize = ctypes.sizeof(WNDCLASSEXW)
    cls.lpfnWndProc = WndProcType(app.wndproc)
    cls.hInstance = hinst
    cls.lpszClassName = CLASS_NAME
    cls.style = CS_DBLCLKS
    g['hicon'] = draw_icon_hicon(32)
    cls.hIcon = g['hicon']
    cls.hIconSm = g['hicon']
    cls.hbrBackground = None
    user32.RegisterClassExW(ctypes.byref(cls))

    # 图标列表
    g['himl'] = comctl32.ImageList_Create(sc(20), sc(20),
                                          0x00000020 | 0x00000001, 0, 64)

    style = WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN
    hwnd = user32.CreateWindowExW(
        0, CLASS_NAME, "窗口置顶小工具", style,
        CW_USEDEFAULT, CW_USEDEFAULT, sc(880), sc(660),
        None, None, hinst, None)
    if not hwnd:
        return
    app.hwnd = hwnd
    g['hwnd_main'] = hwnd

    app.relayout()
    tray_add()

    ok1 = user32.RegisterHotKey(hwnd, HKID_TOGGLE, MOD_CONTROL | MOD_ALT, VK_T)
    ok2 = user32.RegisterHotKey(hwnd, HKID_SHOW, MOD_CONTROL | MOD_ALT, VK_M)
    if not ok1:
        set_hint("提示：Ctrl+Alt+T 被其它程序占用，前台置顶快捷键不可用")

    start_hidden = autostart.launched_as_tray()
    if start_hidden:
        user32.ShowWindow(hwnd, SW_HIDE)
        g['hidden'] = True
    else:
        user32.ShowWindow(hwnd, SW_SHOWNORMAL)
    user32.UpdateWindow(hwnd)
    refresh()
    user32.SetTimer(hwnd, 1, 2500, None)
    user32.SetTimer(hwnd, 2, 40, None)      # 流光动画 ~25fps

    msg = wt.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


CLASS_NAME = "AlwaysOnTopAuroraWnd"
CW_USEDEFAULT = 0x80000000

if __name__ == "__main__":
    main()
