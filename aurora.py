# -*- coding: utf-8 -*-
"""aurora.py —— 流光（Aurora）背景与玻璃拟态绘制引擎

纯 ctypes + GDI，零第三方依赖。为 AlwaysOnTop 主窗口提供：

  · 流光渐变背景：多色斑柔和叠加，逐像素写入 32bpp DIB 后拉伸铺满窗口
  · 玻璃卡片：半透明填充 + 细描边 + 顶部高光，营造层次
  · 胶囊按钮 / 开关 / 圆角列表项 / 细滚动条
  · 轻量文本测量与绘制

所有颜色以 GDI COLORREF(0x00BBGGRR) 表示，对外统一用 rgb(r,g,b)。
"""
import ctypes
import ctypes.wintypes as wt
import math

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
msimg32 = ctypes.WinDLL("msimg32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)

LRESULT = ctypes.c_ssize_t


class RECT(ctypes.Structure):
    _fields_ = [("left", wt.LONG), ("top", wt.LONG),
                ("right", wt.LONG), ("bottom", wt.LONG)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", wt.LONG), ("cy", wt.LONG)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD),
                ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG),
                ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3)]


class SHFILEINFOW(ctypes.Structure):
    _fields_ = [("hIcon", wt.HICON), ("iIcon", ctypes.c_int),
                ("dwAttributes", wt.DWORD), ("szDisplayName", wt.WCHAR * 260),
                ("szTypeName", wt.WCHAR * 80)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", wt.BYTE), ("BlendFlags", wt.BYTE),
                ("SourceConstantAlpha", wt.BYTE), ("AlphaFormat", wt.BYTE)]


user32.GetDC.argtypes = [wt.HWND]
user32.GetDC.restype = ctypes.c_void_p
user32.ReleaseDC.argtypes = [wt.HWND, ctypes.c_void_p]
user32.DrawTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int,
                             ctypes.POINTER(RECT), wt.UINT]
user32.DrawTextW.restype = ctypes.c_int
user32.FillRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT), wt.HANDLE]
user32.FillRect.restype = ctypes.c_int
gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.CreateDIBSection.argtypes = [ctypes.c_void_p, ctypes.POINTER(BITMAPINFO),
                                   wt.UINT, ctypes.POINTER(ctypes.c_void_p),
                                   wt.HANDLE, wt.DWORD]
gdi32.CreateDIBSection.restype = wt.HANDLE
gdi32.SelectObject.argtypes = [ctypes.c_void_p, wt.HANDLE]
gdi32.SelectObject.restype = wt.HANDLE
gdi32.DeleteObject.argtypes = [wt.HANDLE]
gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
gdi32.CreateSolidBrush.argtypes = [wt.DWORD]
gdi32.CreateSolidBrush.restype = wt.HANDLE
gdi32.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wt.DWORD]
gdi32.CreatePen.restype = wt.HANDLE
gdi32.SetBkMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdi32.SetBkMode.restype = ctypes.c_int
gdi32.SetTextColor.argtypes = [ctypes.c_void_p, wt.DWORD]
gdi32.SetTextColor.restype = wt.DWORD
gdi32.RoundRect.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 6
gdi32.RoundRect.restype = wt.BOOL
gdi32.Ellipse.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 4
gdi32.Ellipse.restype = wt.BOOL
gdi32.MoveToEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
gdi32.MoveToEx.restype = wt.BOOL
gdi32.LineTo.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
gdi32.LineTo.restype = wt.BOOL
gdi32.Pie.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 4
gdi32.Pie.restype = wt.BOOL
gdi32.StretchBlt.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 4 + \
                            [ctypes.c_void_p] + [ctypes.c_int] * 4 + [wt.DWORD]
gdi32.StretchBlt.restype = wt.BOOL
gdi32.BitBlt.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 4 + \
                        [ctypes.c_void_p] + [ctypes.c_int] * 2 + [wt.DWORD]
gdi32.BitBlt.restype = wt.BOOL
gdi32.CreateFontW.argtypes = [ctypes.c_int] * 8 + [ctypes.c_int] * 5 + [ctypes.c_wchar_p]
gdi32.CreateFontW.restype = wt.HANDLE
gdi32.GetStockObject.argtypes = [ctypes.c_int]
gdi32.GetStockObject.restype = wt.HANDLE
gdi32.PatBlt.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 4 + [wt.DWORD]
gdi32.PatBlt.restype = wt.BOOL
gdi32.CreateSolidBrush.restype = wt.HANDLE
gdi32.CreatePen.restype = wt.HANDLE
gdi32.PatBlt.restype = wt.BOOL
gdi32.GetDeviceCaps.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdi32.GetDeviceCaps.restype = ctypes.c_int
gdi32.SetStretchBltMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdi32.SetStretchBltMode.restype = ctypes.c_int
msimg32.GradientFill.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 4 + \
                                [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p,
                                 ctypes.c_uint, ctypes.c_uint]
msimg32.GradientFill.restype = wt.BOOL
msimg32.AlphaBlend.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 4 + \
                              [ctypes.c_void_p] + [ctypes.c_int] * 4 + \
                              [ctypes.POINTER(BLENDFUNCTION)]
msimg32.AlphaBlend.restype = wt.BOOL

TRANSPARENT = 1
NULL_BRUSH = 5
NULL_PEN = 8
HALFTONE = 4
COLORONCOLOR = 3
SRCCOPY = 0x00CC0020
WHITENESS = 0x00FF0062
BLACKNESS = 0x00000042
BI_RGB = 0
GRADIENT_VERTICAL = 0
GRADIENT_HORIZONTAL = 1
ALPHA_IGNORE = 0
AC_SRC_OVER = 0


def rgb(r, g, b):
    """(r,g,b) -> COLORREF(0x00BBGGRR)"""
    return (b << 16) | (g << 8) | r


def mix(c1, c2, t):
    """按 t 混合两个 COLORREF"""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = c1 & 0xFF, (c1 >> 8) & 0xFF, (c1 >> 16) & 0xFF
    r2, g2, b2 = c2 & 0xFF, (c2 >> 8) & 0xFF, (c2 >> 16) & 0xFF
    return rgb(int(r1 + (r2 - r1) * t),
               int(g1 + (g2 - g1) * t),
               int(b1 + (b2 - b1) * t))


def lighten(c, t):
    return mix(c, rgb(255, 255, 255), t)


def darken(c, t):
    return mix(c, rgb(0, 0, 0), t)


class _MemCanvas:
    """一张 32bpp 离屏 DIB + 内存 DC，可在上面做像素级运算。"""

    def __init__(self, w, h, screen_dc=None):
        self.w = max(1, int(w))
        self.h = max(1, int(h))
        self.hdc = None
        self._bits = ctypes.c_void_p()
        self.hbm = None
        hdc = user32.GetDC(None) if screen_dc is None else screen_dc
        self.hdc = gdi32.CreateCompatibleDC(ctypes.c_void_p(hdc))
        user32.ReleaseDC(None, hdc)
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = self.w
        bmi.bmiHeader.biHeight = -self.h      # top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        self.hbm = gdi32.CreateDIBSection(
            self.hdc, ctypes.byref(bmi), 0, ctypes.byref(self._bits), None, 0)
        self.bits = self._bits
        gdi32.SelectObject(self.hdc, self.hbm)
        self.size = self.w * self.h

    @property
    def ptr(self):
        return self._bits

    def write_bytes(self, data):
        # data 是 bytearray，源地址用其内部缓冲，目标为 DIB 像素指针
        ctypes.memmove(ctypes.c_void_p(self._bits.value),
                       (ctypes.c_char * len(data)).from_buffer(data),
                       len(data))

    def blit(self, dst_dc, x, y, w, h):
        gdi32.StretchBlt(dst_dc, x, y, w, h, self.hdc,
                         0, 0, self.w, self.h, SRCCOPY)

    def dispose(self):
        if self.hdc:
            gdi32.DeleteDC(ctypes.c_void_p(self.hdc))
            self.hdc = None
        self.bits = None
        self.hbm = None


# ---------------------------------------------------------------- 流光背景
class Aurora:
    """流光渐变背景。

    做法：在低分辨率缓冲上用「有限个高斯色斑 + 正弦漂移」算出每个像素的
    累加颜色，再由 StretchBlt 双线性放大到窗口。低分辨率 + 放大 = 天然柔化，
    比在高分辨率上做模糊快两个数量级，视觉上正是想要的丝绸质感。
    """

    # 默认色斑：(COLORREF, 基准x, 基准y, 半径, 强度, 漂移相位)
    BLOB_COLORS = None

    def __init__(self, cols=None, base=None):
        self.cols = cols or []
        self.base = base
        self.canvas = None
        self.t = 0.0

    def set_colors(self, cols, base=None):
        self.cols = cols
        if base is not None:
            self.base = base

    def _ensure(self, w, h):
        if self.canvas is None or self.canvas.w != w or self.canvas.h != h:
            if self.canvas:
                self.canvas.dispose()
            self.canvas = _MemCanvas(w, h)

    def render(self, hdc, dst_w, dst_h, w=64, h=44, t=None, alpha=255):
        """把流光背景画到 hdc 的 (0,0,dst_w,dst_h)。

        w/h 是计算分辨率（越低越柔和、越快），默认 64x44 已足够顺滑。
        """
        self._ensure(w, h)
        if t is not None:
            self.t = t
        buf = bytearray(w * h * 4)
        cols = self.cols
        base = self.base if self.base is not None else rgb(11, 14, 22)
        br, bg, bb = base & 0xFF, (base >> 8) & 0xFF, (base >> 16) & 0xFF

        # 预解算每个色斑的当前位置与强度系数
        blobs = []
        for (c, bx, by, rad, inten, phase, ax, ay, sp) in cols:
            cx = bx + ax * math.sin(self.t * sp + phase)
            cy = by + ay * math.cos(self.t * sp * 0.83 + phase)
            cr, cg, cb = c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF
            blobs.append((cx, cy, rad, inten, cr, cg, cb))

        p = 0
        for y in range(h):
            ny = (y + 0.5) / h
            for x in range(w):
                nx = (x + 0.5) / w
                r, g, b = br, bg, bb
                for (cx, cy, rad, inten, cr, cg, cb) in blobs:
                    dx = nx - cx
                    dy = (ny - cy) * 0.85
                    d2 = dx * dx + dy * dy
                    if d2 < rad * rad:
                        # smoothstep 衰减，比高斯更"软"，且无 exp() 开销
                        f = 1.0 - d2 / (rad * rad)
                        f = f * f * f * (f * (f * 6.0 - 15.0) + 10.0)
                        k = f * inten
                        r += cr * k
                        g += cg * k
                        b += cb * k
                # 极轻微竖向渐变，让背景更有纵深
                v = 1.0 - ny * 0.18
                r *= v
                g *= v
                b *= v
                if r > 255:
                    r = 255
                if g > 255:
                    g = 255
                if b > 255:
                    b = 255
                buf[p] = int(b)
                buf[p + 1] = int(g)
                buf[p + 2] = int(r)
                buf[p + 3] = 255
                p += 4

        self.canvas.write_bytes(buf)
        gdi32.SetStretchBltMode(ctypes.c_void_p(hdc), HALFTONE)
        self.canvas.blit(hdc, 0, 0, dst_w, dst_h)
        if alpha < 255:
            pass
        return self.canvas


# ---------------------------------------------------------------- 绘制工具
def solid_brush(color):
    return gdi32.CreateSolidBrush(color)


def fill_rect(hdc, rc, color):
    br = solid_brush(color)
    user32.FillRect(hdc, ctypes.byref(rc), br)
    gdi32.DeleteObject(br)


def fill_round(hdc, rc, color, radius):
    """圆角矩形纯色填充。"""
    br = solid_brush(color)
    old_b = gdi32.SelectObject(ctypes.c_void_p(hdc), br)
    old_p = gdi32.SelectObject(ctypes.c_void_p(hdc), gdi32.GetStockObject(NULL_PEN))
    gdi32.RoundRect(ctypes.c_void_p(hdc), rc.left, rc.top, rc.right, rc.bottom, radius, radius)
    gdi32.SelectObject(ctypes.c_void_p(hdc), old_p)
    gdi32.SelectObject(ctypes.c_void_p(hdc), old_b)
    gdi32.DeleteObject(br)


def blend_round(hdc, rc, color, radius, alpha=255):
    """半透明圆角矩形：先在临时层画实色，再整体 AlphaBlend 到目标。

    这样流光背景能透出来，得到真正的玻璃卡片效果。
    """
    if alpha >= 255:
        fill_round(hdc, rc, color, radius)
        return
    w = rc.right - rc.left
    h = rc.bottom - rc.top
    if w <= 0 or h <= 0:
        return
    hdc_ref = gdi32.GetStockObject(NULL_BRUSH)
    layer = gdi32.CreateCompatibleDC(ctypes.c_void_p(hdc))
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = BI_RGB
    bits = ctypes.c_void_p()
    bmp = gdi32.CreateDIBSection(ctypes.c_void_p(hdc), ctypes.byref(bmi), 0,
                                 ctypes.byref(bits), None, 0)
    old = gdi32.SelectObject(ctypes.c_void_p(layer), bmp)
    # 清成全 0（AlphaBlend 的 AC_SRC_OVER + ALPHA_IGNORE 下，
    # 用 WHITENESS 在 32bpp DIB 上会填成 0xFFFFFF 导致整块发白）
    gdi32.PatBlt(ctypes.c_void_p(layer), 0, 0, w, h, BLACKNESS)
    # 再画实色圆角
    br = solid_brush(color)
    gdi32.SelectObject(ctypes.c_void_p(layer), br)
    pn = gdi32.CreatePen(0, 1, color)
    gdi32.SelectObject(ctypes.c_void_p(layer), pn)
    gdi32.RoundRect(ctypes.c_void_p(layer), 0, 0, w, h, radius * 2, radius * 2)
    bf = BLENDFUNCTION(AC_SRC_OVER, 0, alpha, ALPHA_IGNORE)
    msimg32.AlphaBlend(ctypes.c_void_p(hdc), rc.left, rc.top, w, h,
                       ctypes.c_void_p(layer), 0, 0, w, h, ctypes.byref(bf))
    gdi32.SelectObject(ctypes.c_void_p(layer), old)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(ctypes.c_void_p(layer))
    gdi32.DeleteObject(br)
    gdi32.DeleteObject(pn)


def stroke_round(hdc, rc, color, radius, width=1):
    """圆角矩形描边（不填充）。"""
    pn = gdi32.CreatePen(0, width, color)
    old_p = gdi32.SelectObject(ctypes.c_void_p(hdc), pn)
    old_b = gdi32.SelectObject(ctypes.c_void_p(hdc), gdi32.GetStockObject(NULL_BRUSH))
    gdi32.RoundRect(ctypes.c_void_p(hdc), rc.left, rc.top, rc.right, rc.bottom, radius, radius)
    gdi32.SelectObject(ctypes.c_void_p(hdc), old_b)
    gdi32.SelectObject(ctypes.c_void_p(hdc), old_p)
    gdi32.DeleteObject(pn)


def fill_round_grad(hdc, rc, c_top, c_bot, radius):
    """圆角矩形 + 竖向线性渐变。

    GDI 的 GradientFill 只能填矩形，因此做法是：
    先用圆角矩形填底色，再用 GradientFill 在内缩区域铺渐变，
    最后把四角用底色补回（视觉上得到带渐变的圆角块）。
    """
    fill_round(hdc, rc, c_top, radius)
    if rc.bottom - rc.top < 4 or rc.right - rc.left < 4:
        return
    r = max(1, radius // 2)
    inner = RECT(rc.left + r, rc.top + r, rc.right - r, rc.bottom - r)
    _gradient_rect(hdc, inner, c_top, c_bot, vertical=True)
    # 四角补色：用底色画四个小圆角矩形盖住渐变溢出
    for cx, cy in ((rc.left + r, rc.top + r),
                   (rc.right - r, rc.top + r),
                   (rc.left + r, rc.bottom - r),
                   (rc.right - r, rc.bottom - r)):
        corner = RECT(cx - r, cy - r, cx + r, cy + r)
        fill_round(hdc, corner, c_top, r)


class GRADIENT_RECT(ctypes.Structure):
    _fields_ = [("lrTopLeft", wt.LONG), ("lrBottomRight", wt.LONG)]


def _gradient_rect(hdc, rc, c1, c2, vertical=True):
    """用 msimg32.GradientFill 铺一块两色线性渐变。

    GradientFill 的签名是 (hdc, x1, y1, x2, y2, pColor, cVertex,
    pGradient, cGradient, mode)；pGradient 可为 NULL，此时用默认的
    整块矩形渐变（TRIVIAL 模式）。
    """
    colors = (wt.DWORD * 2)(c1, c2)
    mode = GRADIENT_VERTICAL if vertical else GRADIENT_HORIZONTAL
    msimg32.GradientFill(ctypes.c_void_p(hdc),
                         rc.left, rc.top, rc.right, rc.bottom,
                         ctypes.cast(colors, ctypes.c_void_p), 2,
                         None, 0, mode)


def hgradient_rect(hdc, rc, c_left, c_right):
    """横向线性渐变填充矩形。"""
    _gradient_rect(hdc, rc, c_left, c_right, vertical=False)


def line(hdc, x1, y1, x2, y2, color, width=1):
    pn = gdi32.CreatePen(0, width, color)
    old_p = gdi32.SelectObject(ctypes.c_void_p(hdc), pn)
    gdi32.MoveToEx(ctypes.c_void_p(hdc), x1, y1, None)
    gdi32.LineTo(ctypes.c_void_p(hdc), x2, y2)
    gdi32.SelectObject(ctypes.c_void_p(hdc), old_p)
    gdi32.DeleteObject(pn)


def ellipse(hdc, cx, cy, rx, ry, color):
    br = solid_brush(color)
    old_p = gdi32.SelectObject(ctypes.c_void_p(hdc), gdi32.GetStockObject(NULL_PEN))
    gdi32.Ellipse(ctypes.c_void_p(hdc), cx - rx, cy - ry, cx + rx, cy + ry)
    gdi32.SelectObject(ctypes.c_void_p(hdc), old_p)
    gdi32.DeleteObject(br)


def blend_rect(hdc, src_dc, x, y, w, h, alpha=255):
    bf = BLENDFUNCTION(AC_SRC_OVER, 0, alpha, ALPHA_IGNORE)
    msimg32.AlphaBlend(ctypes.c_void_p(hdc), x, y, w, h,
                       ctypes.c_void_p(src_dc), 0, 0, w, h, ctypes.byref(bf))


def text(hdc, font, color, x, y, w, h, s, flags=0):
    """在 (x,y,w,h) 矩形里画文本。"""
    DT_LEFT = 0x0000
    DT_VCENTER = 0x0004
    DT_SINGLELINE = 0x0020
    DT_END_ELLIPSIS = 0x8000
    DT_NOPREFIX = 0x0800
    DT_CALCRECT = 0x0400
    default = DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX
    gdi32.SetBkMode(ctypes.c_void_p(hdc), TRANSPARENT)
    gdi32.SelectObject(ctypes.c_void_p(hdc), font)
    gdi32.SetTextColor(ctypes.c_void_p(hdc), color)
    rc = RECT(x, y, x + w, y + h)
    return user32.DrawTextW(ctypes.c_void_p(hdc), s, -1, ctypes.byref(rc),
                            flags if flags else default)


def measure(hdc, font, s, flags=0):
    DT_CALCRECT = 0x0400
    DT_SINGLELINE = 0x0020
    DT_NOPREFIX = 0x0800
    gdi32.SetBkMode(ctypes.c_void_p(hdc), TRANSPARENT)
    gdi32.SelectObject(ctypes.c_void_p(hdc), font)
    rc = RECT(0, 0, 0, 0)
    user32.DrawTextW(ctypes.c_void_p(hdc), s, -1, ctypes.byref(rc),
                     DT_CALCRECT | DT_SINGLELINE | DT_NOPREFIX |
                     (flags if flags else DT_SINGLELINE))
    return rc.right - rc.left, rc.bottom - rc.top
