# -*- coding: utf-8 -*-
"""
窗口置顶小工具 (AlwaysOnTop) —— Win11 文件管理器(Fluent) 风格 UI
纯 Win32 + ctypes 实现，零第三方依赖。

功能：
  · 类 Explorer 的列表视图（图标 + 标题 + 进程列，自绘选中/悬停圆角高亮）
  · 顶部命令栏（图标按钮 + 搜索框）、底部状态栏
  · 随系统明暗主题自动切换配色
  · 点击「置顶」后自动转入后台，托盘图标常驻
  · 全局快捷键 Ctrl+Alt+T 切换前台窗口置顶 / Ctrl+Alt+M 显示隐藏主窗口

注意：独占全屏(exclusive fullscreen)游戏会独占显示输出，置顶无效；
      请改用「无边框 / 窗口化全屏」。
"""
import ctypes
import ctypes.wintypes as wt
import winreg

# ============================== 常量 ==============================
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008

MOD_CONTROL = 0x0002
MOD_ALT = 0x0001
VK_T = 0x54
VK_M = 0x4D
HKID_TOGGLE = 1
HKID_SHOW = 2

SW_HIDE = 0
SW_SHOW = 5

WM_CREATE = 0x0001
WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_PAINT = 0x000F
WM_CLOSE = 0x0010
WM_ERASEBKGND = 0x0014
WM_SHOWWINDOW = 0x0018
WM_GETMINMAXINFO = 0x0024
WM_SETFONT = 0x0030
WM_NOTIFY = 0x004E
WM_COMMAND = 0x0111
WM_TIMER = 0x0113
WM_HOTKEY = 0x0312
WM_MOUSEMOVE = 0x0200
WM_MOUSELEAVE = 0x02A3
WM_SETICON = 0x0080
WM_CTLCOLORSTATIC = 0x0138
WM_CTLCOLOREDIT = 0x0133
WM_DRAWITEM = 0x002B
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 1

WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_TABSTOP = 0x00010000
WS_BORDER = 0x00800000
WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_CLIPSIBLINGS = 0x04000000
WS_CLIPCHILDREN = 0x02000000

BS_OWNERDRAW = 0x0000000B
SS_OWNERDRAW = 0x0000000D
ES_AUTOHSCROLL = 0x0080
ODT_BUTTON = 4
ODT_STATIC = 5
ODS_SELECTED = 0x0001
ODS_DISABLED = 0x0004
ODS_HOT = 0x0040

# ListView
WC_LISTVIEW = "SysListView32"
LVS_REPORT = 0x0001
LVS_SINGLESEL = 0x0004
LVS_SHOWSELALWAYS = 0x0008
LVS_SHAREIMAGELISTS = 0x0040
LVS_EX_FULLROWSELECT = 0x00000020
LVS_EX_DOUBLEBUFFER = 0x00010000
LVS_EX_LABELTIP = 0x00004000
LVM_FIRST = 0x1000
LVM_SETIMAGELIST = LVM_FIRST + 3
LVM_GETITEMCOUNT = LVM_FIRST + 4
LVM_DELETEALLITEMS = LVM_FIRST + 9
LVM_GETNEXTITEM = LVM_FIRST + 12
LVM_GETITEMW = LVM_FIRST + 75
LVM_SETITEMW = LVM_FIRST + 76
LVM_INSERTITEMW = LVM_FIRST + 77
LVM_INSERTCOLUMNW = LVM_FIRST + 97
LVM_SETCOLUMNW = LVM_FIRST + 96
LVM_GETHEADER = LVM_FIRST + 31
LVM_HITTEST = LVM_FIRST + 18
LVM_SETITEMSTATE = LVM_FIRST + 43
LVM_SETBKCOLOR = LVM_FIRST + 0
LVM_SETTEXTCOLOR = LVM_FIRST + 36
LVM_SETTEXTBKCOLOR = LVM_FIRST + 38
LVM_SETEXTENDEDLISTVIEWSTYLE = LVM_FIRST + 54
LVM_GETEXTENDEDLISTVIEWSTYLE = LVM_FIRST + 55
LVSIL_SMALL = 1
LVSIL_NORMAL = 0
LVIF_TEXT = 0x0001
LVIF_IMAGE = 0x0002
LVIF_PARAM = 0x0004
LVIF_STATE = 0x0008
LVIS_FOCUSED = 0x0001
LVIS_SELECTED = 0x0002
LVNI_SELECTED = 0x0002
LVHT_ONITEM = 0x000E
LVHT_ONITEMICON = 0x0002
LVHT_ONITEMLABEL = 0x0004
LVHT_ONITEMSTATEICON = 0x0008

NM_FIRST = 0
NM_CLICK = NM_FIRST - 2
NM_DBLCLK = NM_FIRST - 3
NM_RCLICK = NM_FIRST - 5
NM_CUSTOMDRAW = NM_FIRST - 12
LVN_FIRST = -100

CDDS_PREPAINT = 0x00000001
CDDS_ITEM = 0x00010000
CDDS_SUBITEM = 0x00020000
CDDS_ITEMPREPAINT = CDDS_ITEM | CDDS_PREPAINT
CDDS_ITEMPOSTPAINT = CDDS_ITEM | 0x00000002
CDRF_DODEFAULT = 0x00000000
CDRF_NEWFONT = 0x00000002
CDRF_SKIPDEFAULT = 0x00000004
CDRF_NOTIFYITEMDRAW = 0x00000020
CDRF_NOTIFYSUBITEMDRAW = 0x00000020
CDRF_NOTIFYPOSTPAINT = 0x00000010
CDIS_SELECTED = 0x0001
CDIS_HOT = 0x0040
CDIS_FOCUS = 0x0010

DT_LEFT = 0x0000
DT_CENTER = 0x0001
DT_VCENTER = 0x0004
DT_SINGLELINE = 0x0020
DT_END_ELLIPSIS = 0x8000
DT_NOPREFIX = 0x0800
DT_CALCRECT = 0x0400

# Header
HDM_FIRST = 0x1200

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
TPM_LEFTBUTTON = 0x0000
TPM_RETURNCMD = 0x0100
TPM_NONOTIFY = 0x0080

# GDI
TRANSPARENT = 1
OPAQUE = 2
NULL_BRUSH = 5
NULL_PEN = 8
DC_BRUSH = 18
BI_RGB = 0
DT_FLAGS = 0

# 通用控件
ICC_LISTVIEW_CLASSES = 0x00000001

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
SHGFI_ICON = 0x000000100
SHGFI_SMALLICON = 0x000000001
SHGFI_LARGEICON = 0x000000000

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2

# 控件 ID
ID_LIST = 100
ID_TOGGLE = 101
ID_REFRESH = 102
ID_CLEAR = 103
ID_TRAY = 104
ID_SEARCH = 105
ID_SEARCH_BG = 106
ID_STATUS = 107
ID_AUTOTRAY = 108
IDM_SHOW = 2001
IDM_REFRESH = 2002
IDM_CLEAR = 2003
IDM_AUTOTRAY = 2004
IDM_EXIT = 2005

# 图标字体（Win11 自带 Segoe Fluent Icons）
ICON_FONT = "Segoe Fluent Icons"
UI_FONT = "Segoe UI"
ICO_PIN = "\uE718"
ICO_UNPIN = "\uE77A"
ICO_REFRESH = "\uE72C"
ICO_DELETE = "\uE74D"
ICO_SEARCH = "\uE721"
ICO_HIDE = "\uE7B8"

# ============================== DLL ==============================
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)
uxtheme = ctypes.WinDLL("uxtheme", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

# LRESULT 用有符号指针宽度整数，方便窗口过程直接返回 0/1/CDRF_*
LRESULT = ctypes.c_ssize_t
NEG_ONE = ctypes.c_void_p(0xFFFFFFFFFFFFFFFF)
WndProcType = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)


# ============================== 结构体 ==============================
class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", WndProcType),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HANDLE), ("hIcon", wt.HANDLE), ("hCursor", wt.HANDLE),
        ("hbrBackground", wt.HANDLE), ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p), ("hIconSm", wt.HANDLE),
    ]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class NMHDR(ctypes.Structure):
    _fields_ = [("hwndFrom", ctypes.c_void_p), ("idFrom", ctypes.c_uint64),
                ("code", ctypes.c_int)]


class NMCUSTOMDRAW(ctypes.Structure):
    _fields_ = [("hdr", NMHDR), ("dwDrawStage", wt.DWORD), ("hdc", ctypes.c_void_p),
                ("rc", RECT), ("dwItemSpec", ctypes.c_uint64),
                ("uItemState", wt.UINT), ("lItemlParam", ctypes.c_int64)]


class NMLVCUSTOMDRAW(ctypes.Structure):
    _fields_ = [("nmcd", NMCUSTOMDRAW), ("clrText", wt.DWORD), ("clrTextBk", wt.DWORD),
                ("iSubItem", ctypes.c_int), ("dwItemType", wt.DWORD),
                ("clrFace", wt.DWORD), ("iIconEffect", ctypes.c_int),
                ("iIconPhase", ctypes.c_int), ("iPartId", ctypes.c_int),
                ("iStateId", ctypes.c_int), ("rcText", RECT), ("uAlign", wt.UINT)]


class LVCOLUMNW(ctypes.Structure):
    _fields_ = [("mask", wt.UINT), ("fmt", ctypes.c_int), ("cx", ctypes.c_int),
                ("pszText", ctypes.c_wchar_p), ("cchTextMax", ctypes.c_int),
                ("iSubItem", ctypes.c_int), ("iImage", ctypes.c_int),
                ("iOrder", ctypes.c_int), ("cxMin", ctypes.c_int),
                ("cxDefault", ctypes.c_int), ("cxIdeal", ctypes.c_int)]


class LVITEMW(ctypes.Structure):
    _fields_ = [("mask", wt.UINT), ("iItem", ctypes.c_int), ("iSubItem", ctypes.c_int),
                ("state", wt.UINT), ("stateMask", wt.UINT),
                ("pszText", ctypes.c_wchar_p), ("cchTextMax", ctypes.c_int),
                ("iImage", ctypes.c_int), ("lParam", ctypes.c_int64),
                ("iIndent", ctypes.c_int), ("iGroupId", ctypes.c_int),
                ("cColumns", wt.UINT), ("puColumns", ctypes.c_void_p),
                ("piColFmt", ctypes.c_void_p), ("iGroup", ctypes.c_int)]


class LVHITTESTINFO(ctypes.Structure):
    _fields_ = [("pt", POINT), ("flags", wt.UINT), ("iItem", ctypes.c_int),
                ("iSubItem", ctypes.c_int), ("iGroup", ctypes.c_int)]


class DRAWITEMSTRUCT(ctypes.Structure):
    _fields_ = [("CtlType", wt.UINT), ("CtlID", wt.UINT), ("itemID", wt.UINT),
                ("itemAction", wt.UINT), ("itemState", wt.UINT),
                ("hwndItem", ctypes.c_void_p), ("hdc", ctypes.c_void_p),
                ("rcItem", RECT), ("itemData", ctypes.c_uint64)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("hWnd", ctypes.c_void_p), ("uID", wt.UINT),
                ("uFlags", wt.UINT), ("uCallbackMessage", wt.UINT),
                ("hIcon", ctypes.c_void_p), ("szTip", wt.WCHAR * 128),
                ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD),
                ("szInfo", wt.WCHAR * 256), ("uVersion", wt.UINT),
                ("szInfoTitle", wt.WCHAR * 64), ("dwInfoFlags", wt.DWORD),
                ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", ctypes.c_void_p)]


class ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wt.BOOL), ("xHotspot", wt.DWORD), ("yHotspot", wt.DWORD),
                ("hbmMask", ctypes.c_void_p), ("hbmColor", ctypes.c_void_p)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wt.WORD),
                ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3)]


class SHFILEINFOW(ctypes.Structure):
    _fields_ = [("hIcon", ctypes.c_void_p), ("iIcon", ctypes.c_int),
                ("dwAttributes", wt.DWORD), ("szDisplayName", wt.WCHAR * 260),
                ("szTypeName", wt.WCHAR * 80)]


class INITCOMMONCONTROLSEX(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("dwICC", wt.DWORD)]


class TRACKMOUSEEVENT(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("dwFlags", wt.DWORD),
                ("hwndTrack", ctypes.c_void_p), ("dwHoverTime", wt.DWORD)]


class MINMAXINFO(ctypes.Structure):
    _fields_ = [("ptReserved", POINT), ("ptMaxSize", POINT), ("ptMaxPosition", POINT),
                ("ptMinTrackSize", POINT), ("ptMaxTrackSize", POINT)]


# ============================== 函数原型 ==============================
user32.CreateWindowExW.argtypes = [wt.DWORD, ctypes.c_wchar_p, ctypes.c_wchar_p,
                                   wt.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, wt.HWND, wt.HMENU, wt.HANDLE,
                                   ctypes.c_void_p]
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
user32.TranslateMessage.restype = wt.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wt.MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
user32.ShowWindow.restype = wt.BOOL
user32.UpdateWindow.argtypes = [wt.HWND]
user32.UpdateWindow.restype = wt.BOOL
user32.DestroyWindow.argtypes = [wt.HWND]
user32.DestroyWindow.restype = wt.BOOL
user32.SetWindowTextW.argtypes = [wt.HWND, ctypes.c_wchar_p]
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wt.UINT]
user32.SetWindowPos.restype = wt.BOOL
user32.MoveWindow.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, wt.BOOL]
user32.MoveWindow.restype = wt.BOOL
user32.GetClientRect.argtypes = [wt.HWND, ctypes.POINTER(RECT)]
user32.GetClientRect.restype = wt.BOOL
user32.FillRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT), ctypes.c_void_p]
user32.FillRect.restype = ctypes.c_int
user32.DrawTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int,
                             ctypes.POINTER(RECT), wt.UINT]
user32.DrawTextW.restype = ctypes.c_int
user32.GetDC.argtypes = [wt.HWND]
user32.GetDC.restype = ctypes.c_void_p
user32.ReleaseDC.argtypes = [wt.HWND, ctypes.c_void_p]
user32.ReleaseDC.restype = ctypes.c_int
user32.GetWindowDC.argtypes = [wt.HWND]
user32.GetWindowDC.restype = ctypes.c_void_p
user32.BeginPaint.argtypes = [wt.HWND, ctypes.c_void_p]
user32.BeginPaint.restype = ctypes.c_void_p
user32.EndPaint.argtypes = [wt.HWND, ctypes.c_void_p]
user32.EndPaint.restype = wt.BOOL
user32.GetSysColor.argtypes = [ctypes.c_int]
user32.GetSysColor.restype = wt.DWORD
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wt.BOOL
user32.SetForegroundWindow.argtypes = [wt.HWND]
user32.SetForegroundWindow.restype = wt.BOOL
user32.GetForegroundWindow.restype = wt.HWND
user32.CreatePopupMenu.restype = wt.HANDLE
user32.AppendMenuW.argtypes = [wt.HMENU, wt.UINT, ctypes.c_uint64, ctypes.c_wchar_p]
user32.AppendMenuW.restype = wt.BOOL
user32.CheckMenuItem.argtypes = [wt.HMENU, wt.UINT, wt.UINT]
user32.CheckMenuItem.restype = wt.DWORD
user32.TrackPopupMenu.argtypes = [wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, wt.HWND, ctypes.POINTER(RECT)]
user32.TrackPopupMenu.restype = wt.BOOL
user32.DestroyMenu.argtypes = [wt.HMENU]
user32.DestroyMenu.restype = wt.BOOL
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindowVisible.restype = wt.BOOL
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wt.HWND, ctypes.c_wchar_p, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = wt.LONG
user32.RegisterHotKey.argtypes = [wt.HWND, ctypes.c_int, wt.UINT, wt.UINT]
user32.RegisterHotKey.restype = wt.BOOL
user32.UnregisterHotKey.argtypes = [wt.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wt.BOOL
user32.CreateIconIndirect.argtypes = [ctypes.POINTER(ICONINFO)]
user32.CreateIconIndirect.restype = wt.HANDLE
user32.DestroyIcon.argtypes = [wt.HANDLE]
user32.DestroyIcon.restype = wt.BOOL
user32.TrackMouseEvent.argtypes = [ctypes.POINTER(TRACKMOUSEEVENT)]
user32.TrackMouseEvent.restype = wt.BOOL
user32.ScreenToClient.argtypes = [wt.HWND, ctypes.POINTER(POINT)]
user32.ScreenToClient.restype = wt.BOOL
user32.SetTimer.argtypes = [wt.HWND, ctypes.c_uint64, wt.UINT, ctypes.c_void_p]
user32.SetTimer.restype = ctypes.c_uint64
user32.KillTimer.argtypes = [wt.HWND, ctypes.c_uint64]
user32.KillTimer.restype = wt.BOOL
user32.SetFocus.argtypes = [wt.HWND]
user32.SetFocus.restype = wt.HWND
user32.InvalidateRect.argtypes = [wt.HWND, ctypes.POINTER(RECT), wt.BOOL]
user32.InvalidateRect.restype = wt.BOOL
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wt.BOOL
user32.SetWindowLongW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = wt.LONG
user32.SetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_ssize_t]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.CallWindowProcW.argtypes = [ctypes.c_ssize_t, wt.HWND, wt.UINT,
                                   wt.WPARAM, wt.LPARAM]
user32.CallWindowProcW.restype = LRESULT
user32.GetMessagePos.restype = wt.DWORD
user32.GetDpiForWindow.argtypes = [wt.HWND]
user32.GetDpiForWindow.restype = wt.UINT

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
kernel32.CloseHandle.restype = wt.BOOL
psapi.GetModuleFileNameExW.argtypes = [wt.HANDLE, wt.HMODULE,
                                       ctypes.c_wchar_p, wt.DWORD]
psapi.GetModuleFileNameExW.restype = wt.DWORD

gdi32.CreateFontW.argtypes = [ctypes.c_int] * 8 + [ctypes.c_int] * 5 + [ctypes.c_wchar_p]
gdi32.CreateFontW.restype = wt.HANDLE
gdi32.CreateSolidBrush.argtypes = [wt.DWORD]
gdi32.CreateSolidBrush.restype = wt.HANDLE
gdi32.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wt.DWORD]
gdi32.CreatePen.restype = wt.HANDLE
gdi32.SelectObject.argtypes = [ctypes.c_void_p, wt.HANDLE]
gdi32.SelectObject.restype = wt.HANDLE
gdi32.DeleteObject.argtypes = [wt.HANDLE]
gdi32.DeleteObject.restype = wt.BOOL
gdi32.SetBkMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdi32.SetBkMode.restype = ctypes.c_int
gdi32.SetTextColor.argtypes = [ctypes.c_void_p, wt.DWORD]
gdi32.SetTextColor.restype = wt.DWORD
gdi32.RoundRect.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
gdi32.RoundRect.restype = wt.BOOL
gdi32.Rectangle.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                            ctypes.c_int, ctypes.c_int]
gdi32.Rectangle.restype = wt.BOOL
gdi32.Ellipse.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                          ctypes.c_int, ctypes.c_int]
gdi32.Ellipse.restype = wt.BOOL
gdi32.MoveToEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                           ctypes.POINTER(POINT)]
gdi32.MoveToEx.restype = wt.BOOL
gdi32.LineTo.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
gdi32.LineTo.restype = wt.BOOL
gdi32.CreateDIBSection.argtypes = [ctypes.c_void_p, ctypes.POINTER(BITMAPINFO),
                                   wt.UINT, ctypes.POINTER(ctypes.c_void_p),
                                   wt.HANDLE, wt.DWORD]
gdi32.CreateDIBSection.restype = wt.HANDLE
gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
gdi32.DeleteDC.restype = wt.BOOL
gdi32.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, wt.UINT, wt.UINT,
                               ctypes.c_void_p]
gdi32.CreateBitmap.restype = wt.HANDLE
gdi32.GetStockObject.argtypes = [ctypes.c_int]
gdi32.GetStockObject.restype = wt.HANDLE
gdi32.SetDCPenColor.argtypes = [ctypes.c_void_p, wt.DWORD]
gdi32.SetDCPenColor.restype = wt.DWORD
gdi32.SetDCBrushColor.argtypes = [ctypes.c_void_p, wt.DWORD]
gdi32.SetDCBrushColor.restype = wt.DWORD
gdi32.GetDeviceCaps.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdi32.GetDeviceCaps.restype = ctypes.c_int

shell32.Shell_NotifyIconW.argtypes = [wt.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
shell32.Shell_NotifyIconW.restype = wt.BOOL
shell32.SHGetFileInfoW.argtypes = [ctypes.c_wchar_p, wt.DWORD,
                                   ctypes.POINTER(SHFILEINFOW), wt.UINT, wt.UINT]
shell32.SHGetFileInfoW.restype = ctypes.c_void_p

comctl32.InitCommonControlsEx.argtypes = [ctypes.POINTER(INITCOMMONCONTROLSEX)]
comctl32.InitCommonControlsEx.restype = wt.BOOL
comctl32.ImageList_Create.argtypes = [ctypes.c_int, ctypes.c_int, wt.UINT,
                                      ctypes.c_int, ctypes.c_int]
comctl32.ImageList_Create.restype = wt.HANDLE
comctl32.ImageList_AddIcon.argtypes = [wt.HANDLE, wt.HANDLE]
comctl32.ImageList_AddIcon.restype = ctypes.c_int
comctl32.ImageList_Draw.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                    ctypes.c_int, ctypes.c_int, wt.UINT]
comctl32.ImageList_Draw.restype = wt.BOOL
comctl32.ImageList_Destroy.argtypes = [wt.HANDLE]
comctl32.ImageList_Destroy.restype = wt.BOOL

uxtheme.SetWindowTheme.argtypes = [wt.HWND, ctypes.c_wchar_p, ctypes.c_wchar_p]
uxtheme.SetWindowTheme.restype = ctypes.c_long

dwmapi.DwmSetWindowAttribute.argtypes = [wt.HWND, wt.DWORD, ctypes.c_void_p, wt.DWORD]
dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long
dwmapi.DwmGetColorizationColor.argtypes = [ctypes.POINTER(wt.DWORD),
                                           ctypes.POINTER(wt.BOOL)]
dwmapi.DwmGetColorizationColor.restype = ctypes.c_long

# ============================== 全局状态 ==============================
g = {
    'scale': 1.0,
    'dark': False,
    'accent': 0x0078D4,
    'rows': [],          # [(hwnd, title, exe_name, path, topmost)]
    'filter': '',
    'hover': -1,
    'autotray': True,
    'hidden': False,
    'icon_cache': {},
    'tray_added': False,
    'first_hide': True,
    'columns': ['', '名称', '进程'],
    'col_widths': [40, 0, 150],   # 中间列自动填充
    'brushes': {},
    'pens': {},
    'fonts': {},
}


# ============================== 主题 ==============================
def rgb(r, g_, b):
    return (b << 16) | (g_ << 8) | r


def is_light_theme():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return True


def get_accent():
    """读取系统主题强调色，返回 GDI COLORREF"""
    color = wt.DWORD()
    opaque = wt.BOOL()
    try:
        if dwmapi.DwmGetColorizationColor(ctypes.byref(color),
                                          ctypes.byref(opaque)) == 0:
            c = color.value & 0x00FFFFFF
            r, gg, b = (c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF
            # 太暗/太亮的颜色在浅色背景下看不清，做一点限幅
            return rgb(r, gg, b)
    except Exception:
        pass
    return rgb(0x0F, 0x6C, 0xBD)


PALETTE_LIGHT = {
    'window': rgb(0xF3, 0xF3, 0xF3),
    'commandbar': rgb(0xFB, 0xFB, 0xFB),
    'list_bg': rgb(0xFF, 0xFF, 0xFF),
    'list_border': rgb(0xE0, 0xE0, 0xE0),
    'header_bg': rgb(0xFB, 0xFB, 0xFB),
    'header_text': rgb(0x61, 0x61, 0x61),
    'text': rgb(0x1B, 0x1B, 0x1B),
    'text_dim': rgb(0x61, 0x61, 0x61),
    'hover': rgb(0xF2, 0xF2, 0xF2),
    'selected': rgb(0xE4, 0xEE, 0xFA),
    'selected_border': rgb(0xC7, 0xDC, 0xF3),
    'btn_hover': rgb(0xF2, 0xF2, 0xF2),
    'btn_press': rgb(0xE6, 0xE6, 0xE6),
    'btn_border': rgb(0xE0, 0xE0, 0xE0),
    'divider': rgb(0xE5, 0xE5, 0xE5),
    'field_bg': rgb(0xFF, 0xFF, 0xFF),
    'status_bg': rgb(0xF3, 0xF3, 0xF3),
}
PALETTE_DARK = {
    'window': rgb(0x28, 0x28, 0x28),
    'commandbar': rgb(0x2B, 0x2B, 0x2B),
    'list_bg': rgb(0x1F, 0x1F, 0x1F),
    'list_border': rgb(0x3D, 0x3D, 0x3D),
    'header_bg': rgb(0x28, 0x28, 0x28),
    'header_text': rgb(0xB0, 0xB0, 0xB0),
    'text': rgb(0xF5, 0xF5, 0xF5),
    'text_dim': rgb(0xA8, 0xA8, 0xA8),
    'hover': rgb(0x33, 0x33, 0x33),
    'selected': rgb(0x33, 0x45, 0x5C),
    'selected_border': rgb(0x45, 0x5C, 0x76),
    'btn_hover': rgb(0x36, 0x36, 0x36),
    'btn_press': rgb(0x2E, 0x2E, 0x2E),
    'btn_border': rgb(0x3D, 0x3D, 0x3D),
    'divider': rgb(0x3D, 0x3D, 0x3D),
    'field_bg': rgb(0x2B, 0x2B, 0x2B),
    'status_bg': rgb(0x2B, 0x2B, 0x2B),
}


def theme():
    return PALETTE_DARK if g['dark'] else PALETTE_LIGHT


def make_resources():
    """创建随主题变化的 GDI 资源（画刷/画笔/字体）"""
    for h in g['brushes'].values():
        gdi32.DeleteObject(h)
    for h in g['pens'].values():
        gdi32.DeleteObject(h)
    t = theme()
    g['brushes'] = {
        'window': gdi32.CreateSolidBrush(t['window']),
        'commandbar': gdi32.CreateSolidBrush(t['commandbar']),
        'list_bg': gdi32.CreateSolidBrush(t['list_bg']),
        'hover': gdi32.CreateSolidBrush(t['hover']),
        'selected': gdi32.CreateSolidBrush(t['selected']),
        'btn_hover': gdi32.CreateSolidBrush(t['btn_hover']),
        'btn_press': gdi32.CreateSolidBrush(t['btn_press']),
        'field_bg': gdi32.CreateSolidBrush(t['field_bg']),
        'status_bg': gdi32.CreateSolidBrush(t['status_bg']),
        'header_bg': gdi32.CreateSolidBrush(t['header_bg']),
        'accent': gdi32.CreateSolidBrush(g['accent']),
    }
    g['pens'] = {
        'divider': gdi32.CreatePen(0, 1, t['divider']),
        'border': gdi32.CreatePen(0, 1, t['list_border']),
        'selected': gdi32.CreatePen(0, 1, t['selected_border']),
        'accent': gdi32.CreatePen(0, 1, g['accent']),
        'text_dim': gdi32.CreatePen(0, 1, t['text_dim']),
    }


def create_fonts(scale):
    for h in g['fonts'].values():
        gdi32.DeleteObject(h)
    px = lambda v: -int(round(v * scale))
    g['fonts'] = {
        # 正文
        'body': gdi32.CreateFontW(px(14), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, UI_FONT),
        # 小字/次要
        'small': gdi32.CreateFontW(px(12), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, UI_FONT),
        # 加粗（列标题 / 强调）
        'bold': gdi32.CreateFontW(px(14), 0, 0, 0, 600, 0, 0, 0, 1, 0, 0, 5, 0, UI_FONT),
        # 图标字体
        'icon': gdi32.CreateFontW(px(16), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, ICON_FONT),
        'icon_sm': gdi32.CreateFontW(px(14), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, ICON_FONT),
    }


def sc(v):
    """按 DPI 缩放"""
    return int(round(v * g['scale']))


# ============================== 核心功能 ==============================
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
        return ""
    kernel32.CloseHandle(h)
    return buf.value


def is_topmost(hwnd):
    return (user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOPMOST) != 0


def set_topmost(hwnd, on):
    user32.SetWindowPos(
        hwnd, HWND_TOPMOST if on else HWND_NOTOPMOST,
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
        exe = path.split("\\")[-1] if path else "?"
        # 过滤掉 Windows 自身的隐藏壳窗口
        if not path:
            return True
        result.append((int(hwnd), title, exe, path))
        return True

    enum_windows._cb = cb
    user32.EnumWindows(cb, 0)
    return result


def icon_index_for_path(path):
    """取程序小图标索引（带缓存），失败返回 -1"""
    if not path:
        return -1
    if path in g['icon_cache']:
        return g['icon_cache'][path]
    shfi = SHFILEINFOW()
    res = shell32.SHGetFileInfoW(path, 0, ctypes.byref(shfi),
                                 ctypes.sizeof(SHFILEINFOW),
                                 SHGFI_ICON | SHGFI_SMALLICON)
    idx = -1
    if shfi.hIcon:
        idx = comctl32.ImageList_AddIcon(g['himl'], shfi.hIcon)
        user32.DestroyIcon(shfi.hIcon)
    g['icon_cache'][path] = idx
    return idx


def refresh():
    """重新枚举窗口并填充列表"""
    lv = g.get('hwnd_list')
    if not lv:
        return
    keep_hwnd = get_selected_hwnd()
    user32.SendMessageW(lv, LVM_DELETEALLITEMS, 0, 0)
    g['rows'] = []

    filt = g['filter'].strip().lower()
    wins = enum_windows(g['hwnd_main'])
    new_sel = -1
    i = 0
    for hwnd, title, exe, path in wins:
        if filt and (filt not in title.lower() and filt not in exe.lower()):
            continue
        top = is_topmost(hwnd)
        g['rows'].append((hwnd, title, exe, path, top))
        img = icon_index_for_path(path)

        item = LVITEMW()
        item.mask = LVIF_TEXT | LVIF_PARAM | LVIF_IMAGE
        item.iItem = i
        item.iSubItem = 0
        buf0 = ctypes.create_unicode_buffer("")
        item.pszText = ctypes.cast(buf0, ctypes.c_wchar_p)
        item.lParam = hwnd
        item.iImage = img if img >= 0 else 0
        user32.SendMessageW(lv, LVM_INSERTITEMW, 0,
                            ctypes.cast(ctypes.byref(item), ctypes.c_void_p))

        for sub, text in ((1, title), (2, exe)):
            it = LVITEMW()
            it.mask = LVIF_TEXT
            it.iItem = i
            it.iSubItem = sub
            b = ctypes.create_unicode_buffer(text)
            it.pszText = ctypes.cast(b, ctypes.c_wchar_p)
            user32.SendMessageW(lv, LVM_SETITEMW, 0,
                                ctypes.cast(ctypes.byref(it), ctypes.c_void_p))

        if hwnd == keep_hwnd:
            new_sel = i
        i += 1

    if new_sel >= 0:
        select_item(new_sel)
    update_status()


def get_selected_hwnd():
    lv = g.get('hwnd_list')
    if not lv:
        return None
    idx = user32.SendMessageW(lv, LVM_GETNEXTITEM, -1, LVNI_SELECTED)
    if idx < 0 or idx >= len(g['rows']):
        return None
    return g['rows'][idx][0]


def select_item(idx):
    lv = g['hwnd_list']
    it = LVITEMW()
    it.mask = LVIF_STATE
    it.state = LVIS_SELECTED | LVIS_FOCUSED
    it.stateMask = LVIS_SELECTED | LVIS_FOCUSED
    it.iItem = idx
    it.iSubItem = 0
    user32.SendMessageW(lv, LVM_SETITEMSTATE, idx,
                        ctypes.cast(ctypes.byref(it), ctypes.c_void_p))


def update_status():
    total = len(g['rows'])
    pinned = sum(1 for r in g['rows'] if r[4])
    text = "共 %d 个窗口" % total
    if pinned:
        text += "  ·  %d 个已置顶" % pinned
    hw = g.get('hwnd_status')
    if hw:
        user32.SetWindowTextW(hw, text)
        user32.InvalidateRect(hw, None, True)


def toggle_selected():
    lv = g.get('hwnd_list')
    if not lv:
        return
    idx = user32.SendMessageW(lv, LVM_GETNEXTITEM, -1, LVNI_SELECTED)
    if idx < 0 or idx >= len(g['rows']):
        set_hint("请先在列表里选中一个窗口")
        return
    hwnd, title, exe, path, top = g['rows'][idx]
    set_topmost(hwnd, not top)
    refresh()
    if top:
        set_hint("已取消置顶：%s" % title)
    else:
        set_hint("已置顶：%s" % title)
        if g['autotray']:
            hide_to_tray(notify=True, title=title)


def clear_all():
    n = 0
    for hwnd, title, exe, path, top in g['rows']:
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
    if fg == g['hwnd_main']:
        return
    state = not is_topmost(fg)
    set_topmost(fg, state)
    refresh()
    title = get_title(fg)
    if state:
        toast("已置顶", "%s\n已设为始终在最前" % title[:60])
    else:
        set_hint("已取消置顶：%s" % title)


def set_hint(text):
    g['hint'] = text
    hw = g.get('hwnd_status2')
    if hw:
        user32.SetWindowTextW(hw, text)
        user32.InvalidateRect(hw, None, True)


# ============================== 托盘 ==============================
def _icon_f(px, frac):
    return int(round(px * frac))


def draw_icon_rgba(px=32, accent=None):
    """绘制图标并返回顶向下 (top-down) 的 RGBA 字节串，供 HICON / .ico 共用。

    视觉：强调色圆底 + 白色细描边环（深浅背景都清晰）+ 白色图钉
    + 底部一条白色"置顶基线"。"""
    accent = accent or g['accent']
    hdc_screen = user32.GetDC(None)
    bmi = BITMAPINFO()
    head = bmi.bmiHeader
    head.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    head.biWidth = px
    head.biHeight = -px          # top-down
    head.biPlanes = 1
    head.biBitCount = 32
    head.biCompression = BI_RGB
    bits = ctypes.c_void_p()
    hbm = gdi32.CreateDIBSection(hdc_screen, ctypes.byref(bmi), 0,
                                 ctypes.byref(bits), None, 0)
    if not hbm:
        user32.ReleaseDC(None, hdc_screen)
        return None
    memdc = gdi32.CreateCompatibleDC(hdc_screen)
    old = gdi32.SelectObject(memdc, hbm)

    # 圆底（强调色）
    brush = gdi32.CreateSolidBrush(accent)
    gdi32.SelectObject(memdc, brush)
    gdi32.SelectObject(memdc, gdi32.GetStockObject(NULL_PEN))
    gdi32.Ellipse(memdc, 0, 0, px, px)

    # 白色细描边环
    ring = gdi32.CreatePen(0, max(1, px // 16), rgb(255, 255, 255))
    gdi32.SelectObject(memdc, ring)
    gdi32.SelectObject(memdc, gdi32.GetStockObject(NULL_BRUSH))
    e = max(1, px // 22)
    gdi32.Ellipse(memdc, e, e, px - e, px - e)

    # 图钉（白色矢量图形）—— 不使用字体字形。
    # 原因：GDI 在 32-bit DIB 上渲染字体时，抗锯齿会产生半透明像素；
    # 而 ICO/XOR 的 alpha 处理会把它们误判为透明，导致小尺寸图标“撕裂”。
    # 改用确定的矢量图形后，每个像素要么纯白（不透明）要么透明黑，各尺寸都清晰。
    gdi32.SelectObject(memdc, gdi32.GetStockObject(NULL_PEN))
    pin = gdi32.CreateSolidBrush(rgb(255, 255, 255))
    gdi32.SelectObject(memdc, pin)
    cx = px / 2.0
    head_r = _icon_f(px, 0.24)          # 头圆半径
    head_cy = _icon_f(px, 0.40)         # 头圆圆心 y
    tip_y = _icon_f(px, 0.90)           # 针尖 y
    w = _icon_f(px, 0.11)               # 针体半宽
    # 圆头
    gdi32.Ellipse(memdc, int(cx - head_r), int(head_cy - head_r),
                  int(cx + head_r), int(head_cy + head_r))
    # 针体（三角：从头部两侧收拢到针尖）
    pts = (POINT * 3)(
        POINT(int(cx - w), int(head_cy + head_r * 0.5)),
        POINT(int(cx + w), int(head_cy + head_r * 0.5)),
        POINT(int(cx), int(tip_y)),
    )
    gdi32.Polygon.argtypes = [ctypes.c_void_p, ctypes.POINTER(POINT), ctypes.c_int]
    gdi32.Polygon.restype = ctypes.c_int
    gdi32.Polygon(memdc, pts, 3)
    gdi32.DeleteObject(pin)

    # 底部"置顶基线"
    base_pen = gdi32.CreatePen(0, max(1, px // 14), rgb(255, 255, 255))
    gdi32.SelectObject(memdc, base_pen)
    yb = _icon_f(px, 0.80)
    gdi32.MoveToEx(memdc, _icon_f(px, 0.20), yb, None)
    gdi32.LineTo(memdc, _icon_f(px, 0.80), yb)
    gdi32.DeleteObject(base_pen)
    gdi32.DeleteObject(ring)
    gdi32.DeleteObject(brush)

    gdi32.SelectObject(memdc, old)
    gdi32.DeleteDC(memdc)
    user32.ReleaseDC(None, hdc_screen)

    # GDI 不写 alpha → 手动补成不透明，并导出 BGRA 字节。
    # GDI 32-bit DIB 内存布局是 BGRA（最低字节是 B），不是 RGBA。
    # ICO XOR mask 也是 BGRA 顺序，所以可以直接喂给 pack_ico。
    arr = ctypes.cast(bits, ctypes.POINTER(ctypes.c_uint32))
    buf = bytearray(px * px * 4)
    for i in range(px * px):
        v = arr[i] & 0x00FFFFFF  # 保留 BGR
        if v:
            # 有颜色的像素：把 alpha 通道（最高字节）置为 0xFF（不透明）
            arr[i] = v | 0xFF000000
        # 否则（透明黑）：arr[i] 保持 0，alpha=0（完全透明）
        # 按 BGRA 顺序写入 buf（注意 +3 拿到的是 alpha 通道，无论 BGRA/RGBA 它都在 +3）
        buf[i * 4]     = arr[i] & 0xFF             # B
        buf[i * 4 + 1] = (arr[i] >> 8) & 0xFF      # G
        buf[i * 4 + 2] = (arr[i] >> 16) & 0xFF     # R
        buf[i * 4 + 3] = (arr[i] >> 24) & 0xFF     # A
    return bytes(buf)


def draw_icon_hicon(px=32, accent=None):
    """从 RGBA 生成 HICON（托盘 / 窗口 / 任务栏图标）。"""
    rgba = draw_icon_rgba(px, accent)
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
    head.biCompression = BI_RGB
    bits = ctypes.c_void_p()
    hbm = gdi32.CreateDIBSection(hdc_screen, ctypes.byref(bmi), 0,
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


def make_tray_icon(px=32):
    """托盘/任务栏图标（历史接口名，转发到统一绘制）"""
    return draw_icon_hicon(px)


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
        # 部分系统只认 V3 尺寸，退回再试一次
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
        toast("已在后台运行",
              "程序已最小化到系统托盘，全局快捷键仍然生效。")


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
    user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
    user32.AppendMenuW(menu, MF_STRING, IDM_EXIT, "退出")
    user32.SetForegroundWindow(g['hwnd_main'])
    user32.TrackPopupMenu(menu, TPM_LEFTALIGN | TPM_RIGHTBUTTON,
                          pt.x, pt.y, 0, g['hwnd_main'], None)
    user32.DestroyMenu(menu)


# ============================== 自绘 ==============================
def fill_rounded(hdc, rc, brush, pen, radius=4):
    old_b = gdi32.SelectObject(hdc, brush)
    old_p = gdi32.SelectObject(hdc, pen if pen else gdi32.GetStockObject(NULL_PEN))
    gdi32.RoundRect(hdc, rc.left, rc.top, rc.right, rc.bottom, radius, radius)
    gdi32.SelectObject(hdc, old_b)
    if pen:
        gdi32.SelectObject(hdc, old_p)


def draw_button(dis):
    t = theme()
    hdc = dis.hdc
    rc = dis.rcItem
    cid = dis.CtlID
    hot = bool(dis.itemState & ODS_HOT)
    pressed = bool(dis.itemState & ODS_SELECTED)
    disabled = bool(dis.itemState & ODS_DISABLED)

    if cid == ID_TOGGLE:
        # 主按钮：强调色底 + 白字
        bg = g['brushes']['accent'] if not pressed else g['brushes']['btn_press']
        fill_rounded(hdc, rc, bg, None, sc(4))
        fg = rgb(255, 255, 255) if not pressed else t['text']
    elif cid == ID_AUTOTRAY:
        if hot:
            fill_rounded(hdc, rc, g['brushes']['btn_hover'], None, sc(4))
        fg = t['text_dim'] if disabled else t['text']
    else:
        if pressed:
            fill_rounded(hdc, rc, g['brushes']['btn_press'], g['pens']['border'], sc(4))
        elif hot:
            fill_rounded(hdc, rc, g['brushes']['btn_hover'], g['pens']['border'], sc(4))
        fg = t['text_dim'] if disabled else t['text']

    gdi32.SetBkMode(hdc, TRANSPARENT)
    x = rc.left + sc(10)
    cy = (rc.top + rc.bottom) // 2

    if cid == ID_AUTOTRAY:
        # 复选框
        size = sc(15)
        box = RECT(x, cy - size // 2, x + size, cy - size // 2 + size)
        checked = g['autotray']
        if checked:
            fill_rounded(hdc, box, g['brushes']['accent'], None, sc(3))
            pen = gdi32.CreatePen(0, max(1, sc(2)), rgb(255, 255, 255))
            old_p = gdi32.SelectObject(hdc, pen)
            gdi32.MoveToEx(hdc, box.left + sc(3), cy, None)
            gdi32.LineTo(hdc, box.left + sc(6), box.bottom - sc(4))
            gdi32.LineTo(hdc, box.right - sc(3), box.top + sc(4))
            gdi32.SelectObject(hdc, old_p)
            gdi32.DeleteObject(pen)
        else:
            fill_rounded(hdc, box, g['brushes']['field_bg'], g['pens']['text_dim'], sc(3))
        tr = RECT(box.right + sc(8), rc.top, rc.right - sc(4), rc.bottom)
        gdi32.SelectObject(hdc, g['fonts']['small'])
        gdi32.SetTextColor(hdc, fg)
        user32.DrawTextW(hdc, "置顶后转入后台", -1, ctypes.byref(tr),
                         DT_LEFT | DT_VCENTER | DT_SINGLELINE)
        return

    defs = {
        ID_TOGGLE: (ICO_PIN, "置顶/取消"),
        ID_REFRESH: (ICO_REFRESH, "刷新"),
        ID_CLEAR: (ICO_DELETE, "全部取消"),
        ID_TRAY: (ICO_HIDE, "后台运行"),
    }
    icon, text = defs.get(cid, ("", ""))

    # 图标
    gdi32.SelectObject(hdc, g['fonts']['icon_sm'])
    gdi32.SetTextColor(hdc, fg)
    ir = RECT(x, rc.top, x + sc(22), rc.bottom)
    user32.DrawTextW(hdc, icon, -1, ctypes.byref(ir),
                     DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)

    # 文字
    gdi32.SelectObject(hdc, g['fonts']['body'])
    gdi32.SetTextColor(hdc, fg)
    tr = RECT(x + sc(22), rc.top, rc.right - sc(6), rc.bottom)
    user32.DrawTextW(hdc, text, -1, ctypes.byref(tr),
                     DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)


def draw_search_bg(dis):
    """搜索框容器（owner-draw STATIC）：圆角底 + 放大镜 + 占位文字"""
    t = theme()
    hdc = dis.hdc
    rc = dis.rcItem
    fill_rounded(hdc, rc, g['brushes']['field_bg'], g['pens']['border'], sc(4))
    gdi32.SetBkMode(hdc, TRANSPARENT)
    # 放大镜
    gdi32.SelectObject(hdc, g['fonts']['icon_sm'])
    gdi32.SetTextColor(hdc, t['text_dim'])
    ir = RECT(rc.left + sc(6), rc.top, rc.left + sc(26), rc.bottom)
    user32.DrawTextW(hdc, ICO_SEARCH, -1, ctypes.byref(ir),
                     DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
    # 占位文字（仅在未输入时显示，通过透明 EDIT 透出）
    if not g['filter']:
        gdi32.SelectObject(hdc, g['fonts']['small'])
        gdi32.SetTextColor(hdc, t['text_dim'])
        tr = RECT(rc.left + sc(26), rc.top, rc.right - sc(6), rc.bottom)
        user32.DrawTextW(hdc, "搜索窗口", -1, ctypes.byref(tr),
                         DT_LEFT | DT_VCENTER | DT_SINGLELINE)


def draw_list_item(lplvcd):
    """ListView 行自绘：圆角选中/悬停块 + 图标 + 文字"""
    cd = lplvcd.contents
    t = theme()
    hdc = cd.nmcd.hdc
    idx = cd.nmcd.dwItemSpec
    stage = cd.nmcd.dwDrawStage
    sub = cd.iSubItem

    if stage == CDDS_ITEMPREPAINT:
        # 画整行背景
        rc = cd.nmcd.rc
        selected = bool(cd.nmcd.uItemState & CDIS_SELECTED)
        hot = (idx == g['hover'])
        if selected:
            fill_rounded(hdc, RECT(rc.left, rc.top + 1, rc.right - 1, rc.bottom - 1),
                         g['brushes']['selected'], g['pens']['selected'], sc(4))
        elif hot:
            fill_rounded(hdc, RECT(rc.left, rc.top + 1, rc.right - 1, rc.bottom - 1),
                         g['brushes']['hover'], None, sc(4))
        return CDRF_NOTIFYSUBITEMDRAW

    if stage == (CDDS_ITEMPREPAINT | CDDS_SUBITEM):
        if idx >= len(g['rows']):
            return CDRF_SKIPDEFAULT
        hwnd, title, exe, path, top = g['rows'][idx]
        rc = cd.nmcd.rc
        selected = bool(cd.nmcd.uItemState & CDIS_SELECTED)
        gdi32.SetBkMode(hdc, TRANSPARENT)

        if sub == 0:
            if top:
                gdi32.SelectObject(hdc, g['fonts']['icon_sm'])
                gdi32.SetTextColor(hdc, g['accent'])
                r2 = RECT(rc.left, rc.top, rc.right, rc.bottom)
                user32.DrawTextW(hdc, ICO_PIN, -1, ctypes.byref(r2),
                                 DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
        elif sub == 1:
            # 程序图标
            iimg = g['icon_cache'].get(path, -1)
            if iimg >= 0 and g.get('himl'):
                iy = rc.top + ((rc.bottom - rc.top) - sc(16)) // 2
                comctl32.ImageList_Draw(g['himl'], iimg, hdc,
                                        rc.left + sc(6), iy, 0)
            # 标题
            gdi32.SelectObject(hdc, g['fonts']['body'])
            gdi32.SetTextColor(hdc, t['text'])
            tr = RECT(rc.left + sc(28), rc.top, rc.right - sc(8), rc.bottom)
            user32.DrawTextW(hdc, title, -1, ctypes.byref(tr),
                             DT_LEFT | DT_VCENTER | DT_SINGLELINE |
                             DT_END_ELLIPSIS | DT_NOPREFIX)
        elif sub == 2:
            gdi32.SelectObject(hdc, g['fonts']['small'])
            gdi32.SetTextColor(hdc, t['text_dim'])
            tr = RECT(rc.left + sc(8), rc.top, rc.right - sc(8), rc.bottom)
            user32.DrawTextW(hdc, exe, -1, ctypes.byref(tr),
                             DT_LEFT | DT_VCENTER | DT_SINGLELINE |
                             DT_END_ELLIPSIS | DT_NOPREFIX)
        return CDRF_SKIPDEFAULT

    return CDRF_DODEFAULT


def draw_header(lphd):
    """表头自绘：浅/深底 + 次色文字 + 底部分隔线"""
    cd = lphd.contents
    hdc = cd.nmcd.hdc
    t = theme()
    stage = cd.nmcd.dwDrawStage

    if stage == CDDS_PREPAINT:
        return CDRF_NOTIFYITEMDRAW

    if stage == CDDS_ITEMPREPAINT:
        rc = cd.nmcd.rc
        user32.FillRect(hdc, ctypes.byref(rc), g['brushes']['header_bg'])
        col = int(cd.nmcd.dwItemSpec)
        if col < len(g['columns']):
            gdi32.SetBkMode(hdc, TRANSPARENT)
            gdi32.SelectObject(hdc, g['fonts']['bold'])
            gdi32.SetTextColor(hdc, t['header_text'])
            tr = RECT(rc.left + sc(8), rc.top, rc.right - sc(6), rc.bottom)
            user32.DrawTextW(hdc, g['columns'][col], -1, ctypes.byref(tr),
                             DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
        # 底边分隔线
        old = gdi32.SelectObject(hdc, g['pens']['divider'])
        gdi32.MoveToEx(hdc, rc.left, rc.bottom - 1, None)
        gdi32.LineTo(hdc, rc.right, rc.bottom - 1)
        gdi32.SelectObject(hdc, old)
        return CDRF_SKIPDEFAULT

    return CDRF_DODEFAULT


# ============================== 布局 ==============================
def layout():
    rc = RECT()
    user32.GetClientRect(g['hwnd_main'], ctypes.byref(rc))
    w = rc.right - rc.left
    h = rc.bottom - rc.top
    if w <= 0 or h <= 0:
        return

    # 两行命令栏 + 底部状态栏（列表夹在中间）
    r1h = sc(30)                 # 行1：主操作按钮
    r2top = sc(40)               # 行2：次要设置按钮的 y
    r2h = sc(30)
    cmd_h = r2top + r2h + sc(4)  # 命令栏总高
    status_h = sc(30)
    pad = sc(12)
    y1 = sc(6)                   # 行1按钮顶部

    # —— 行1：置顶 / 刷新 / 全部取消（左对齐）——
    x = pad
    for cid, bwv in ((ID_TOGGLE, sc(112)), (ID_REFRESH, sc(84)),
                     (ID_CLEAR, sc(96))):
        user32.MoveWindow(g['hwnd_btn'][cid], x, y1, bwv, r1h, True)
        x += bwv + sc(6)

    # —— 行1：搜索框填满剩余右侧（宽度自适应，避免重叠）——
    search_w = (w - pad) - x
    if search_w < sc(150):
        search_w = sc(150)  # 极窄时保底（最小窗口已保证足够）
    sx = (w - pad) - search_w
    user32.MoveWindow(g['hwnd_btn'][ID_SEARCH_BG], sx, sc(10), search_w, sc(28), True)
    user32.MoveWindow(g['hwnd_btn'][ID_SEARCH], sx + sc(28), sc(15),
                      search_w - sc(38), sc(18), True)
    # 显式让搜索框容器重绘，保证 owner-draw 圆角背景一定绘制
    user32.InvalidateRect(g['hwnd_btn'][ID_SEARCH_BG], None, True)

    # —— 行2：后台运行 / 置顶后转入后台（左对齐）——
    xx = pad
    for cid, bwv in ((ID_TRAY, sc(96)), (ID_AUTOTRAY, sc(160))):
        user32.MoveWindow(g['hwnd_btn'][cid], xx, r2top, bwv, r2h, True)
        xx += bwv + sc(6)

    # —— 列表 ——
    lv_y = cmd_h
    lv_h = h - cmd_h - status_h - pad
    if lv_h < sc(120):
        lv_h = sc(120)
    user32.MoveWindow(g['hwnd_list'], pad, lv_y, w - pad * 2, lv_h, True)

    # 列宽：中间列自适应
    total = w - pad * 2
    c0 = sc(40)
    c2 = sc(150)
    c1 = max(sc(120), total - c0 - c2)
    for col, cw in ((0, c0), (1, c1), (2, c2)):
        lvc = LVCOLUMNW()
        lvc.mask = 0x0002  # LVCF_WIDTH
        lvc.cx = cw
        user32.SendMessageW(g['hwnd_list'], LVM_SETCOLUMNW, col,
                            ctypes.cast(ctypes.byref(lvc), ctypes.c_void_p))

    # —— 状态栏 ——
    sy = h - status_h
    left_w = (w - pad * 2) // 2
    user32.MoveWindow(g['hwnd_status'], pad, sy, left_w, status_h, True)
    user32.MoveWindow(g['hwnd_status2'], pad + left_w, sy,
                      w - pad * 2 - left_w, status_h, True)


# ============================== 窗口过程 ==============================
def wndproc(hwnd, msg, wparam, lparam):
    if msg == WM_CREATE:
        # DPI
        try:
            dpi = user32.GetDpiForWindow(hwnd)
            if dpi:
                g['scale'] = dpi / 96.0
        except Exception:
            g['scale'] = 1.0
        g['dark'] = not is_light_theme()
        g['accent'] = get_accent()
        make_resources()
        create_fonts(g['scale'])

        init = INITCOMMONCONTROLSEX()
        init.dwSize = ctypes.sizeof(INITCOMMONCONTROLSEX)
        init.dwICC = ICC_LISTVIEW_CLASSES
        comctl32.InitCommonControlsEx(ctypes.byref(init))

        # 深色标题栏 + 圆角
        try:
            dark = ctypes.c_int(1 if g['dark'] else 0)
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                                         ctypes.byref(dark), 4)
            corner = ctypes.c_int(DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                                         ctypes.byref(corner), 4)
        except Exception:
            pass

        if not g.get('hicon'):
            g['hicon'] = draw_icon_hicon(32)
        user32.SendMessageW(hwnd, WM_SETICON, 0, g['hicon'])
        user32.SendMessageW(hwnd, WM_SETICON, 1, g['hicon'])
        return 0

    if msg == WM_COMMAND:
        cid = wparam & 0xFFFF
        notify = (wparam >> 16) & 0xFFFF
        if cid == ID_SEARCH and notify == 0x0400:  # EN_CHANGE
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(g['hwnd_btn'][ID_SEARCH], buf, 256)
            g['filter'] = buf.value
            # 占位文字"搜索窗口"在有输入时要消失：使搜索框容器重绘
            user32.InvalidateRect(g['hwnd_btn'].get(ID_SEARCH_BG), None, True)
            refresh()
            return 0
        if cid == ID_REFRESH:
            refresh()
            set_hint("列表已刷新")
        elif cid == ID_TOGGLE:
            toggle_selected()
        elif cid == ID_CLEAR:
            clear_all()
        elif cid == ID_TRAY:
            hide_to_tray()
        elif cid == ID_AUTOTRAY:
            g['autotray'] = not g['autotray']
            user32.InvalidateRect(g['hwnd_btn'][ID_AUTOTRAY], None, True)
            set_hint("「置顶后转入后台」已%s" % ("开启" if g['autotray'] else "关闭"))
        elif cid == IDM_SHOW:
            show_window_()
        elif cid == IDM_REFRESH:
            refresh()
        elif cid == IDM_CLEAR:
            clear_all()
        elif cid == IDM_AUTOTRAY:
            g['autotray'] = not g['autotray']
            set_hint("「置顶后转入后台」已%s" % ("开启" if g['autotray'] else "关闭"))
        elif cid == IDM_EXIT:
            user32.DestroyWindow(hwnd)
        return 0

    if msg == WM_NOTIFY:
        nmh = ctypes.cast(lparam, ctypes.POINTER(NMHDR)).contents
        if nmh.code == NM_CUSTOMDRAW:
            if nmh.hwndFrom == g.get('hwnd_header'):
                return draw_header(
                    ctypes.cast(lparam, ctypes.POINTER(NMLVCUSTOMDRAW)))
            if nmh.hwndFrom == g.get('hwnd_list'):
                return draw_list_item(
                    ctypes.cast(lparam, ctypes.POINTER(NMLVCUSTOMDRAW)))
        elif nmh.code == NM_DBLCLK and nmh.hwndFrom == g.get('hwnd_list'):
            toggle_selected()
            return 0
        return 0

    if msg == WM_DRAWITEM:
        dis = ctypes.cast(lparam, ctypes.POINTER(DRAWITEMSTRUCT)).contents
        if dis.CtlType == ODT_BUTTON:
            if dis.hwndItem == g['hwnd_btn'].get(ID_SEARCH_BG):
                draw_search_bg(dis)
            else:
                draw_button(dis)
            return 1
        return 0

    if msg == WM_CTLCOLORSTATIC:
        hdc = wparam
        hw = ctypes.c_void_p(lparam).value
        gdi32.SetBkMode(hdc, TRANSPARENT)
        if hw == g.get('hwnd_status') or hw == g.get('hwnd_status2'):
            gdi32.SelectObject(hdc, g['fonts']['small'])
            gdi32.SetTextColor(hdc, theme()['text_dim'])
        return g['brushes']['window']

    if msg == WM_CTLCOLOREDIT:
        hdc = wparam
        gdi32.SetBkMode(hdc, TRANSPARENT)
        gdi32.SelectObject(hdc, g['fonts']['body'])
        gdi32.SetTextColor(hdc, theme()['text'])
        return gdi32.GetStockObject(NULL_BRUSH)

    if msg == WM_MOUSEMOVE:
        lv = g.get('hwnd_list')
        if lv:
            pt = POINT()
            ptx = ctypes.windll.user32.GetMessagePos()
            pt.x = ctypes.c_short(ptx & 0xFFFF).value
            pt.y = ctypes.c_short((ptx >> 16) & 0xFFFF).value
            user32.ScreenToClient(lv, ctypes.byref(pt))
            hti = LVHITTESTINFO()
            hti.pt = pt
            idx = user32.SendMessageW(lv, LVM_HITTEST, 0,
                                      ctypes.cast(ctypes.byref(hti), ctypes.c_void_p))
            if idx != g['hover']:
                g['hover'] = idx
                user32.InvalidateRect(lv, None, False)
            tme = TRACKMOUSEEVENT()
            tme.cbSize = ctypes.sizeof(TRACKMOUSEEVENT)
            tme.dwFlags = 0x00000002  # TME_LEAVE
            tme.hwndTrack = lv
            user32.TrackMouseEvent(ctypes.byref(tme))
        return 0

    if msg == WM_MOUSELEAVE:
        if g['hover'] != -1:
            g['hover'] = -1
            user32.InvalidateRect(g['hwnd_list'], None, False)
        return 0

    if msg == WM_ERASEBKGND:
        rc = RECT()
        user32.GetClientRect(hwnd, ctypes.byref(rc))
        user32.FillRect(wparam, ctypes.byref(rc), g['brushes']['window'])
        return 1

    if msg == WM_PAINT:
        ps = ctypes.create_string_buffer(64)
        hdc = user32.BeginPaint(hwnd, ps)
        rc = RECT()
        user32.GetClientRect(hwnd, ctypes.byref(rc))
        # 命令栏与列表之间的分隔线
        y = sc(74)
        old = gdi32.SelectObject(hdc, g['pens']['divider'])
        gdi32.MoveToEx(hdc, 0, y, None)
        gdi32.LineTo(hdc, rc.right, y)
        gdi32.SelectObject(hdc, old)
        user32.EndPaint(hwnd, ps)
        return 0

    if msg == WM_SIZE:
        if g.get('hwnd_list'):
            layout()
        return 0

    if msg == WM_GETMINMAXINFO:
        mmi = ctypes.cast(lparam, ctypes.POINTER(MINMAXINFO)).contents
        mmi.ptMinTrackSize.x = sc(560)
        mmi.ptMinTrackSize.y = sc(440)
        return 0

    if msg == WM_TIMER:
        if wparam == 1 and not g['hidden']:
            if user32.IsWindowVisible(hwnd):
                refresh()
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
        if lparam == 0x0205:  # WM_RBUTTONUP
            show_tray_menu()
        elif lparam == 0x0203:  # WM_LBUTTONDBLCLK
            show_window_()
        return 0

    if msg == WM_CLOSE:
        # 关闭按钮 = 转入后台，退出请从托盘菜单
        hide_to_tray()
        return 0

    if msg == WM_DESTROY:
        user32.KillTimer(hwnd, 1)
        user32.UnregisterHotKey(hwnd, HKID_TOGGLE)
        user32.UnregisterHotKey(hwnd, HKID_SHOW)
        tray_delete()
        user32.PostQuitMessage(0)
        return 0

    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


wndproc_cb = WndProcType(wndproc)
CLASS_NAME = "AlwaysOnTopFluentWnd"


def main():
    # 高 DPI 感知（Win10 1703+）
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

    hinst = kernel32.GetModuleHandleW(None)

    g['dark'] = not is_light_theme()
    g['accent'] = get_accent()
    make_resources()
    create_fonts(1.0)

    cls = WNDCLASSEXW()
    cls.cbSize = ctypes.sizeof(WNDCLASSEXW)
    cls.lpfnWndProc = wndproc_cb
    cls.hInstance = hinst
    cls.lpszClassName = CLASS_NAME
    # 给窗口类挂上图标 → 任务栏按钮稳定显示自定义图钉图标
    g['hicon'] = draw_icon_hicon(32)
    cls.hIcon = g['hicon']
    cls.hIconSm = draw_icon_hicon(16)
    cls.hbrBackground = g['brushes']['window']
    cls.style = 0x0002 | 0x0001  # CS_HREDRAW | CS_VREDRAW
    user32.RegisterClassExW(ctypes.byref(cls))

    style = WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN
    hwnd_main = user32.CreateWindowExW(
        0, CLASS_NAME, "窗口置顶小工具", style,
        100, 100, sc(760), sc(520), None, None, hinst, None)
    if not hwnd_main:
        return
    g['hwnd_main'] = hwnd_main

    # 图标字体可能不存在（老系统），做个兜底检测
    g['himl'] = comctl32.ImageList_Create(sc(16), sc(16), 0x00000020 | 0x00000001,
                                          0, 32)  # ILC_COLOR32 | ILC_MASK

    g['hwnd_btn'] = {}

    def mk(clsname, text, style_, cid, x=0, y=0, w=10, h=10):
        hctl = user32.CreateWindowExW(
            0, clsname, text, WS_CHILD | WS_VISIBLE | style_,
            x, y, w, h, hwnd_main, cid, hinst, None)
        g['hwnd_btn'][cid] = hctl
        return hctl

    mk("BUTTON", "置顶/取消", BS_OWNERDRAW, ID_TOGGLE)
    mk("BUTTON", "刷新", BS_OWNERDRAW, ID_REFRESH)
    mk("BUTTON", "全部取消", BS_OWNERDRAW, ID_CLEAR)
    mk("BUTTON", "后台运行", BS_OWNERDRAW, ID_TRAY)
    mk("BUTTON", "置顶后转入后台", BS_OWNERDRAW, ID_AUTOTRAY)

    # 列表（ListView，report 视图）
    lv = user32.CreateWindowExW(
        0, WC_LISTVIEW, None,
        WS_CHILD | WS_VISIBLE | WS_CLIPSIBLINGS | WS_TABSTOP |
        LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS,
        0, 0, 10, 10, hwnd_main, ID_LIST, hinst, None)
    g['hwnd_list'] = lv
    uxtheme.SetWindowTheme(lv, "Explorer", None)

    user32.SendMessageW(lv, LVM_SETIMAGELIST, LVSIL_SMALL, g['himl'])
    style_ex = LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_LABELTIP
    user32.SendMessageW(lv, 0x1036, 0, style_ex)  # LVM_SETEXTENDEDLISTVIEWSTYLE
    user32.SendMessageW(lv, 0x1037, style_ex, style_ex)  # 保留上述样式
    user32.SendMessageW(lv, 0x1000 + 1, 0, theme()['list_bg'])  # LVM_SETBKCOLOR
    user32.SendMessageW(lv, 0x1000 + 38, 0, theme()['list_bg'])  # LVM_SETTEXTBKCOLOR
    user32.SendMessageW(lv, 0x1000 + 36, 0, theme()['text'])    # LVM_SETTEXTCOLOR
    user32.SendMessageW(lv, WM_SETFONT, g['fonts']['body'], 1)

    for i, (name, wpx) in enumerate(zip(g['columns'], (sc(40), sc(360), sc(150)))):
        lvc = LVCOLUMNW()
        lvc.mask = 0x0001 | 0x0002 | 0x0004  # LVCF_TEXT | LVCF_WIDTH | LVCF_FMT
        lvc.fmt = 0
        lvc.cx = wpx
        lvc.iSubItem = i
        buf = ctypes.create_unicode_buffer(name)
        lvc.pszText = ctypes.cast(buf, ctypes.c_wchar_p)
        user32.SendMessageW(lv, LVM_INSERTCOLUMNW, i,
                            ctypes.cast(ctypes.byref(lvc), ctypes.c_void_p))

    g['hwnd_header'] = user32.SendMessageW(lv, LVM_GETHEADER, 0, 0)
    uxtheme.SetWindowTheme(g['hwnd_header'], "Explorer", None)

    # 搜索框（owner-draw BUTTON 容器 + 透明 EDIT 输入框）
    # 容器负责画圆角背景 + 放大镜 + 占位文字（EDIT 无边框、背景透明，浮在容器上）。
    # 注意：用 BUTTON(BS_OWNERDRAW) 而非 STATIC(SS_OWNERDRAW)——
    # Win32 中 owner-draw STATIC 不可靠（不触发/不绘制），且 WM_CTLCOLORSTATIC
    # 对 owner-draw 控件不发消息，导致容器背景透明、后面 ListView 透出，
    # 表现为“搜索框里看到列表文字”的重叠假象。BUTTON 的 owner-draw 在所有
    # Windows 版本都稳定触发 WM_DRAWITEM，和工具栏按钮一致。
    mk("BUTTON", None, BS_OWNERDRAW, ID_SEARCH_BG)
    mk("EDIT", None, ES_AUTOHSCROLL, ID_SEARCH)
    user32.SendMessageW(g['hwnd_btn'][ID_SEARCH], WM_SETFONT, g['fonts']['body'], 1)

    # 状态栏
    g['hwnd_status'] = user32.CreateWindowExW(
        0, "STATIC", "共 0 个窗口", WS_CHILD | WS_VISIBLE,
        0, 0, 10, 10, hwnd_main, ID_STATUS, hinst, None)
    user32.SendMessageW(g['hwnd_status'], WM_SETFONT, g['fonts']['small'], 1)
    g['hwnd_status2'] = user32.CreateWindowExW(
        0, "STATIC", "选中窗口后点「置顶/取消」，或按 Ctrl+Alt+T",
        WS_CHILD | WS_VISIBLE, 0, 0, 10, 10, hwnd_main, 0, hinst, None)
    user32.SendMessageW(g['hwnd_status2'], WM_SETFONT, g['fonts']['small'], 1)
    g['hint'] = "选中窗口后点「置顶/取消」，或按 Ctrl+Alt+T"

    layout()

    # 托盘
    tray_add()

    # 快捷键
    ok1 = user32.RegisterHotKey(hwnd_main, HKID_TOGGLE,
                                MOD_CONTROL | MOD_ALT, VK_T)
    ok2 = user32.RegisterHotKey(hwnd_main, HKID_SHOW,
                                MOD_CONTROL | MOD_ALT, VK_M)
    if not ok1:
        set_hint("提示：Ctrl+Alt+T 被其它程序占用，前台置顶快捷键不可用")

    user32.ShowWindow(hwnd_main, SW_SHOW)
    user32.UpdateWindow(hwnd_main)
    refresh()
    user32.SetTimer(hwnd_main, 1, 2500, None)

    msg = wt.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


if __name__ == "__main__":
    main()
