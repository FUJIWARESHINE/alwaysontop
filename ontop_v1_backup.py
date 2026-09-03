# -*- coding: utf-8 -*-
"""
窗口置顶小工具 (AlwaysOnTop)  —— 纯 Win32 + ctypes 实现，零第三方依赖。
只做一件事：把任意窗口设为「始终在最前面」，方便全屏打游戏时把 Edge 浮在上面看视频。
全局快捷键：Ctrl + Alt + T  -> 切换「当前最前台窗口」的置顶状态。
注意：独占全屏(exclusive fullscreen)游戏会独占显示输出，置顶无效；请改用「无边框/窗口化全屏」。
"""
import ctypes
import ctypes.wintypes as wt

# ---------------- 常量 ----------------
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
HWND_MESSAGE = -3
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
MOD_CONTROL = 0x0002
MOD_ALT = 0x0001
VK_T = 0x54
WM_COMMAND = 0x0111
WM_HOTKEY = 0x0312
WM_DESTROY = 0x0002
WM_SETFONT = 0x0030
SW_SHOW = 5
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_THICKFRAME = 0x00040000
WS_MAXIMIZEBOX = 0x00010000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_BORDER = 0x00800000
WS_VSCROLL = 0x00200000
LBS_NOTIFY = 0x0001
LBS_HASSTRINGS = 0x0040
LBN_DBLCLK = 2
BN_CLICKED = 0
LB_ADDSTRING = 0x0180
LB_RESETCONTENT = 0x0184
LB_GETCURSEL = 0x0188
LB_GETITEMDATA = 0x0199
LB_SETITEMDATA = 0x019A
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
DEFAULT_GUI_FONT = 17

ID_LIST = 100
ID_REFRESH = 101
ID_TOGGLE = 102
ID_EXIT = 103
ID_STATUS = 104
ID_HEADER = 105

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi
gdi32 = ctypes.windll.gdi32

# LRESULT 在 3.13 的 wintypes 中已移除，用指针宽度类型替代
LRESULT = ctypes.c_void_p

# 窗口过程类型 + 窗口类结构体（3.13 的 wintypes 已移除 WNDCLASSEXW）
WndProcType = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.UINT),
        ("style", wt.UINT),
        ("lpfnWndProc", WndProcType),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HANDLE),
        ("hIcon", wt.HANDLE),
        ("hCursor", wt.HANDLE),
        ("hbrBackground", wt.HANDLE),
        ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p),
        ("hIconSm", wt.HANDLE),
    ]


# ---------------- ctypes 原型 ----------------
user32.EnumWindows.argtypes = [
    ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]
user32.EnumWindows.restype = wt.BOOL
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wt.HWND, ctypes.c_wchar_p, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindowVisible.restype = wt.BOOL
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = wt.LONG
user32.SetWindowPos.argtypes = [
    wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wt.UINT]
user32.SetWindowPos.restype = wt.BOOL
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wt.HWND
user32.RegisterHotKey.argtypes = [wt.HWND, ctypes.c_int, wt.UINT, wt.UINT]
user32.RegisterHotKey.restype = wt.BOOL
user32.UnregisterHotKey.argtypes = [wt.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wt.BOOL
user32.GetMessageW.argtypes = [
    ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = [ctypes.POINTER(wt.MSG)]
user32.TranslateMessage.restype = wt.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wt.MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.CreateWindowExW.argtypes = [
    wt.DWORD, ctypes.c_wchar_p, ctypes.c_wchar_p, wt.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wt.HWND, wt.HMENU, wt.HANDLE, ctypes.c_void_p]
user32.CreateWindowExW.restype = wt.HWND
user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wt.ATOM
kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel32.GetModuleHandleW.restype = wt.HANDLE
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None
user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
user32.ShowWindow.restype = wt.BOOL
user32.UpdateWindow.argtypes = [wt.HWND]
user32.UpdateWindow.restype = wt.BOOL
user32.DestroyWindow.argtypes = [wt.HWND]
user32.DestroyWindow.restype = wt.BOOL
user32.SetWindowTextW.argtypes = [wt.HWND, ctypes.c_wchar_p]
user32.SetWindowTextW.restype = wt.BOOL
user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, ctypes.c_void_p, ctypes.c_void_p]
user32.SendMessageW.restype = ctypes.c_int64
gdi32.CreateFontW.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p]
gdi32.CreateFontW.restype = wt.HANDLE
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.CloseHandle.restype = wt.BOOL
psapi.GetModuleFileNameExW.argtypes = [
    wt.HANDLE, wt.HMODULE, ctypes.c_wchar_p, wt.DWORD]
psapi.GetModuleFileNameExW.restype = wt.DWORD

g = {}  # 运行时全局：hwnd_main, hwnd_list, hwnd_status, font


def get_title(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def get_exe_name(pid):
    h = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        return "?"
    buf = ctypes.create_unicode_buffer(1024)
    psapi.GetModuleFileNameExW(h, None, buf, 1024)
    kernel32.CloseHandle(h)
    path = buf.value
    return path.split("\\")[-1] if path else "?"


def is_topmost(hwnd):
    return (user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOPMOST) != 0


def toggle_topmost(hwnd):
    if is_topmost(hwnd):
        user32.SetWindowPos(
            hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        return False
    user32.SetWindowPos(
        hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    return True


def enum_windows(own_hwnd):
    result = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if hwnd == own_hwnd:
            return True
        if user32.GetWindowTextLengthW(hwnd) == 0:
            return True
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe = get_exe_name(pid.value)
        result.append((int(hwnd), get_title(hwnd), exe))
        return True

    enum_windows._cb = cb  # 保活
    user32.EnumWindows(cb, 0)
    return result


def set_status(text):
    if g.get('hwnd_status'):
        user32.SetWindowTextW(g['hwnd_status'], text)


def refresh():
    lb = g.get('hwnd_list')
    if not lb:
        return
    user32.SendMessageW(lb, LB_RESETCONTENT, 0, 0)
    wins = enum_windows(g['hwnd_main'])
    for hwnd, title, exe in wins:
        mark = "* " if is_topmost(hwnd) else "  "
        edge = " [Edge]" if exe.lower() == "msedge.exe" else ""
        s = mark + title[:60] + edge + "  (" + exe + ")"
        buf = ctypes.create_unicode_buffer(s)
        idx = user32.SendMessageW(lb, LB_ADDSTRING, 0, ctypes.addressof(buf))
        user32.SendMessageW(lb, LB_SETITEMDATA, idx, hwnd)
    set_status("就绪。选中窗口后点「置顶/取消」，或按 Ctrl+Alt+T")


def toggle_selected():
    lb = g.get('hwnd_list')
    if not lb:
        return
    cur = int(user32.SendMessageW(lb, LB_GETCURSEL, 0, 0))
    if cur < 0:
        set_status("请先在列表里选中一个窗口")
        return
    hwnd = user32.SendMessageW(lb, LB_GETITEMDATA, cur, 0)
    state = toggle_topmost(hwnd)
    set_status("已%s：%s" % ("置顶" if state else "取消置顶", get_title(hwnd)))
    refresh()


def on_hotkey():
    fg = user32.GetForegroundWindow()
    if fg:
        state = toggle_topmost(fg)
        set_status("快捷键：已%s当前最前台窗口" % ("置顶" if state else "取消置顶"))
        refresh()


def wndproc(hwnd, msg, wparam, lparam):
    if msg == WM_COMMAND:
        cid = wparam & 0xFFFF
        notify = (wparam >> 16) & 0xFFFF
        if cid == ID_REFRESH:
            refresh()
        elif cid == ID_TOGGLE:
            toggle_selected()
        elif cid == ID_EXIT:
            user32.DestroyWindow(g['hwnd_main'])
        elif cid == ID_LIST and notify == LBN_DBLCLK:
            toggle_selected()
        return 0
    if msg == WM_HOTKEY:
        on_hotkey()
        return 0
    if msg == WM_DESTROY:
        user32.UnregisterHotKey(g['hwnd_main'], 1)
        user32.PostQuitMessage(0)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


wndproc_cb = WndProcType(wndproc)
CLASS_NAME = "AlwaysOnTopMainWnd"


def main():
    hinst = kernel32.GetModuleHandleW(None)
    cls = WNDCLASSEXW()
    cls.cbSize = ctypes.sizeof(WNDCLASSEXW)
    cls.lpfnWndProc = wndproc_cb
    cls.hInstance = hinst
    cls.lpszClassName = CLASS_NAME
    user32.RegisterClassExW(ctypes.byref(cls))

    style = WS_OVERLAPPEDWINDOW & ~WS_THICKFRAME & ~WS_MAXIMIZEBOX
    hwnd_main = user32.CreateWindowExW(
        0, CLASS_NAME, "窗口置顶小工具", style,
        100, 100, 470, 560, None, None, hinst, None)
    if not hwnd_main:
        return
    g['hwnd_main'] = hwnd_main

    font = gdi32.CreateFontW(
        -12, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 0, 0, "Microsoft YaHei")
    g['font'] = font

    def ctrl(clsname, text, x, y, w, h, id_):
        hctl = user32.CreateWindowExW(
            0, clsname, text,
            WS_CHILD | WS_VISIBLE | WS_BORDER if clsname == "EDIT" else WS_CHILD | WS_VISIBLE,
            x, y, w, h, hwnd_main, id_, hinst, None)
        user32.SendMessageW(hctl, WM_SETFONT, font, 1)
        return hctl

    user32.CreateWindowExW(
        0, "STATIC", "可见窗口列表（* 已置顶，[Edge] 为 Edge 浏览器）：",
        WS_CHILD | WS_VISIBLE, 12, 12, 446, 22, hwnd_main, ID_HEADER, hinst, None)
    g['hwnd_list'] = user32.CreateWindowExW(
        0, "LISTBOX", None,
        WS_CHILD | WS_VISIBLE | WS_BORDER | WS_VSCROLL | LBS_NOTIFY | LBS_HASSTRINGS,
        12, 40, 446, 420, hwnd_main, ID_LIST, hinst, None)
    user32.SendMessageW(g['hwnd_list'], WM_SETFONT, font, 1)
    g['hwnd_refresh'] = user32.CreateWindowExW(
        0, "BUTTON", "刷新", WS_CHILD | WS_VISIBLE, 12, 472, 90, 30,
        hwnd_main, ID_REFRESH, hinst, None)
    user32.SendMessageW(g['hwnd_refresh'], WM_SETFONT, font, 1)
    g['hwnd_toggle'] = user32.CreateWindowExW(
        0, "BUTTON", "置顶/取消选中", WS_CHILD | WS_VISIBLE, 120, 472, 170, 30,
        hwnd_main, ID_TOGGLE, hinst, None)
    user32.SendMessageW(g['hwnd_toggle'], WM_SETFONT, font, 1)
    g['hwnd_exit'] = user32.CreateWindowExW(
        0, "BUTTON", "退出", WS_CHILD | WS_VISIBLE, 310, 472, 90, 30,
        hwnd_main, ID_EXIT, hinst, None)
    user32.SendMessageW(g['hwnd_exit'], WM_SETFONT, font, 1)
    g['hwnd_status'] = user32.CreateWindowExW(
        0, "STATIC", "就绪。选中窗口后点「置顶/取消」，或按 Ctrl+Alt+T",
        WS_CHILD | WS_VISIBLE, 12, 508, 446, 30, hwnd_main, ID_STATUS, hinst, None)
    user32.SendMessageW(g['hwnd_status'], WM_SETFONT, font, 1)

    if not user32.RegisterHotKey(hwnd_main, 1, MOD_CONTROL | MOD_ALT, VK_T):
        set_status("提示：Ctrl+Alt+T 被占用，热键不可用，请改用界面按钮")

    user32.SetWindowPos(
        hwnd_main, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    user32.ShowWindow(hwnd_main, SW_SHOW)
    user32.UpdateWindow(hwnd_main)
    refresh()

    msg = wt.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


if __name__ == "__main__":
    main()
