# -*- coding: utf-8 -*-
"""aurora.py —— 流光背景与玻璃拟态绘制引擎（纯 ctypes + GDI，零第三方依赖）

核心设计：
  · 全部绘制落在自有 32bpp 离屏画布（Canvas）上，最后一次性 BitBlt 到窗口，
    既无闪烁，也让"逐像素半透明合成"成为可能。
  · 半透明合成**不依赖 AlphaBlend** —— 实测该函数在部分会话/环境（无真实显示
    适配器、受限窗口站）下会返回失败，导致玻璃面板整个消失。这里改用
    「逐通道 LUT + bytes.translate」在 C 层完成，速度与可靠性都更好。
  · 流光背景：三团径向辉光叠在深色底上（对齐「文件批量重命名」的 body::before），
    低分辨率逐像素计算后 StretchBlt 放大，得到丝滑无 banding 的柔光。

颜色统一用 GDI COLORREF(0x00BBGGRR)；需要透明度时传 (COLORREF, alpha)。
"""
import ctypes
import ctypes.wintypes as wt
import math

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
msimg32 = ctypes.WinDLL("msimg32", use_last_error=True)


# ------------------------------------------------------------------ 结构体
class RECT(ctypes.Structure):
    _fields_ = [("left", wt.LONG), ("top", wt.LONG),
                ("right", wt.LONG), ("bottom", wt.LONG)]


class POINT(ctypes.Structure):
    _fields_ = [("x", wt.LONG), ("y", wt.LONG)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD),
                ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG),
                ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3)]


class TRIVERTEX(ctypes.Structure):
    _fields_ = [("x", wt.LONG), ("y", wt.LONG),
                ("Red", ctypes.c_ushort), ("Green", ctypes.c_ushort),
                ("Blue", ctypes.c_ushort), ("Alpha", ctypes.c_ushort)]


class GRADIENT_RECT(ctypes.Structure):
    _fields_ = [("UpperLeft", wt.ULONG), ("LowerRight", wt.ULONG)]


class SHFILEINFOW(ctypes.Structure):
    _fields_ = [("hIcon", wt.HANDLE), ("iIcon", ctypes.c_int),
                ("dwAttributes", wt.DWORD), ("szDisplayName", wt.WCHAR * 260),
                ("szTypeName", wt.WCHAR * 80)]


# ------------------------------------------------------------------ 原型
user32.GetDC.argtypes = [wt.HWND]
user32.GetDC.restype = ctypes.c_void_p
user32.ReleaseDC.argtypes = [wt.HWND, ctypes.c_void_p]
user32.FillRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT), wt.HANDLE]
user32.FillRect.restype = ctypes.c_int
user32.DrawTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int,
                             ctypes.POINTER(RECT), wt.UINT]
user32.DrawTextW.restype = ctypes.c_int

gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
gdi32.DeleteDC.restype = wt.BOOL
gdi32.CreateDIBSection.argtypes = [ctypes.c_void_p, ctypes.POINTER(BITMAPINFO),
                                   wt.UINT, ctypes.POINTER(ctypes.c_void_p),
                                   wt.HANDLE, wt.DWORD]
gdi32.CreateDIBSection.restype = wt.HANDLE
gdi32.SelectObject.argtypes = [ctypes.c_void_p, wt.HANDLE]
gdi32.SelectObject.restype = wt.HANDLE
gdi32.DeleteObject.argtypes = [wt.HANDLE]
gdi32.DeleteObject.restype = wt.BOOL
gdi32.CreateSolidBrush.argtypes = [wt.DWORD]
gdi32.CreateSolidBrush.restype = wt.HANDLE
gdi32.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wt.DWORD]
gdi32.CreatePen.restype = wt.HANDLE
gdi32.GetStockObject.argtypes = [ctypes.c_int]
gdi32.GetStockObject.restype = wt.HANDLE
gdi32.SetBkMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdi32.SetBkMode.restype = ctypes.c_int
gdi32.SetTextColor.argtypes = [ctypes.c_void_p, wt.DWORD]
gdi32.SetTextColor.restype = wt.DWORD
gdi32.RoundRect.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 6
gdi32.RoundRect.restype = wt.BOOL
gdi32.Ellipse.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 4
gdi32.Ellipse.restype = wt.BOOL
gdi32.MoveToEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                           ctypes.c_void_p]
gdi32.MoveToEx.restype = wt.BOOL
gdi32.LineTo.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
gdi32.LineTo.restype = wt.BOOL
gdi32.BitBlt.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 4 + \
                        [ctypes.c_void_p] + [ctypes.c_int] * 2 + [wt.DWORD]
gdi32.BitBlt.restype = wt.BOOL
gdi32.StretchBlt.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 4 + \
                            [ctypes.c_void_p] + [ctypes.c_int] * 4 + [wt.DWORD]
gdi32.StretchBlt.restype = wt.BOOL
gdi32.SetStretchBltMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdi32.SetStretchBltMode.restype = ctypes.c_int
gdi32.SaveDC.argtypes = [ctypes.c_void_p]
gdi32.SaveDC.restype = ctypes.c_int
gdi32.RestoreDC.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdi32.RestoreDC.restype = ctypes.c_int
gdi32.IntersectClipRect.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 4
gdi32.IntersectClipRect.restype = ctypes.c_int
gdi32.CreateFontW.argtypes = [ctypes.c_int] * 8 + [ctypes.c_int] * 5 + \
                             [ctypes.c_wchar_p]
gdi32.CreateFontW.restype = wt.HANDLE

msimg32.GradientFill.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wt.ULONG,
                                 ctypes.c_void_p, wt.ULONG, wt.ULONG]
msimg32.GradientFill.restype = wt.BOOL

# ------------------------------------------------------------------ 常量
TRANSPARENT = 1
NULL_BRUSH = 5
NULL_PEN = 8
SRCCOPY = 0x00CC0020
HALFTONE = 4
BI_RGB = 0
GRADIENT_FILL_RECT_H = 0
GRADIENT_FILL_RECT_V = 1

DT_LEFT = 0x0000
DT_CENTER = 0x0001
DT_RIGHT = 0x0002
DT_VCENTER = 0x0004
DT_SINGLELINE = 0x0020
DT_END_ELLIPSIS = 0x8000
DT_NOPREFIX = 0x0800
DT_CALCRECT = 0x0400


def rgb(r, g, b):
    """(r, g, b) -> COLORREF(0x00BBGGRR)"""
    return (b << 16) | (g << 8) | r


def mix(c1, c2, t):
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


def color_of(c):
    return c[0] if isinstance(c, tuple) else c


def alpha_of(c, default=255):
    return c[1] if isinstance(c, tuple) else default


# ------------------------------------------------------------------ 画布
class Canvas:
    """32bpp top-down 离屏画布。

    所有绘制先落到这里，最后 BitBlt 到窗口。
    半透明合成走逐通道 LUT（bytes.translate，C 速度），不依赖 AlphaBlend。
    """

    def __init__(self):
        self.w = 0
        self.h = 0
        self.stride = 0
        self.hdc = None
        self.hbm = None
        self._bits = ctypes.c_void_p()
        self._lut_cache = {}
        self._cov_cache = {}
        self._ring_cache = {}

    def ensure(self, w, h):
        w, h = max(1, int(w)), max(1, int(h))
        if self.w == w and self.h == h and self.hdc:
            return
        self.dispose()
        self.w, self.h = w, h
        self.stride = w * 4
        screen = user32.GetDC(None)
        self.hdc = gdi32.CreateCompatibleDC(ctypes.c_void_p(screen))
        user32.ReleaseDC(None, screen)
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        self.hbm = gdi32.CreateDIBSection(self.hdc, ctypes.byref(bmi), 0,
                                          ctypes.byref(self._bits), None, 0)
        gdi32.SelectObject(ctypes.c_void_p(self.hdc), self.hbm)

    def dispose(self):
        if self.hdc:
            gdi32.DeleteDC(ctypes.c_void_p(self.hdc))
            self.hdc = None
        self.hbm = None
        self._bits = ctypes.c_void_p()
        self.w = self.h = 0

    # ---------------------------------------------------------- 原始字节
    def _read(self, off, n):
        buf = bytearray(n)
        if n <= 0:
            return buf
        ctypes.memmove((ctypes.c_char * n).from_buffer(buf),
                       ctypes.c_void_p(self._bits.value + off), n)
        return buf

    def _write(self, off, buf):
        n = len(buf)
        if n <= 0:
            return
        ctypes.memmove(ctypes.c_void_p(self._bits.value + off),
                       (ctypes.c_char * n).from_buffer(buf), n)

    def poke(self, x, y, b, g, r, a=255):
        off = y * self.stride + x * 4
        self._write(off, bytearray((b, g, r, a)))

    # ---------------------------------------------------------- LUT
    def _luts(self, color, alpha):
        """返回 (lut_b, lut_g, lut_r)：把背景通道映射为「叠上 color@alpha」的结果。"""
        key = (color & 0xFFFFFF, int(alpha))
        v = self._lut_cache.get(key)
        if v is not None:
            return v
        a = int(alpha) / 255.0
        inv = 1.0 - a
        # COLORREF 低位是 R（0x00BBGGRR），别按字面当成 B
        cr, cg, cb = color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF
        mk = lambda cc: bytes(
            min(255, max(0, int(x * inv + cc * a + 0.5))) for x in range(256))
        v = (mk(cb), mk(cg), mk(cr))
        if len(self._lut_cache) > 256:
            self._lut_cache.clear()
        self._lut_cache[key] = v
        return v

    def _apply(self, seg, lb, lg, lr):
        """对一段连续 BGRA 做逐通道 LUT 叠加（原地修改并返回）。

        注意：seg 必须是可写切片本身；若传入的是 blk[a:b] 这类副本，
        调用方必须把返回值写回原缓冲，否则改动会丢失。
        """
        seg[0::4] = bytes(seg[0::4]).translate(lb)
        seg[1::4] = bytes(seg[1::4]).translate(lg)
        seg[2::4] = bytes(seg[2::4]).translate(lr)
        return seg

    def _corner_cov(self, r_c):
        """半径 r_c 的圆角覆盖率表（按半径缓存）。

        四个角是对称的：以「距该角的两条外边各 i / j 像素」为局部坐标，
        像素中心 (i+0.5, j+0.5) 到圆心 (r_c, r_c) 的距离就决定了覆盖率，
        与是哪个角无关，只需在半径首次出现时算一次 sqrt。
        返回 [(i, j, cov), ...]，只含 cov < 1 的像素（=1 的保留 LUT 结果）。
        """
        v = self._cov_cache.get(r_c)
        if v is not None:
            return v
        items = []
        for j in range(r_c):
            dy = j + 0.5 - r_c
            for i in range(r_c):
                dx = i + 0.5 - r_c
                cov = r_c + 0.5 - math.sqrt(dx * dx + dy * dy)
                if cov < 1.0:
                    items.append((i, j, cov if cov > 0.0 else 0.0))
        self._cov_cache[r_c] = items
        return items

    def _apply_rect(self, blk, n, s_ofs, e_ofs, lb, lg, lr):
        """把 LUT 叠加到 blk 的第 [s_ofs, e_ofs) 列（整行切片坐标系）。

        blk 是「从 x=0 起的整行」缓冲区，所以 s_ofs / e_ofs 是**字节**偏移。
        逐行切片时每行只有几十字节，3090 行的面板就会产生上千次
        slice+translate（Python 层开销占主导）。这里按宽度分档：

        - 整行宽：一次 translate 搞定
        - 单列：用扩展切片（步长=stride）一次处理整列
        - 较宽：先整行 translate，再把左右边距按行还原（只做拷贝，不做 translate）
        - 较窄：回到逐行（这时拷贝量小，逐行更划算）
        """
        if e_ofs <= s_ofs or n <= 0:
            return
        stride = self.stride
        if s_ofs == 0 and e_ofs >= stride:
            self._apply(blk, lb, lg, lr)
            return
        if e_ofs - s_ofs == 4:
            # 单列：每行只有 4 字节，逐行毫无意义
            blk[s_ofs::stride] = bytes(blk[s_ofs::stride]).translate(lb)
            blk[s_ofs + 1::stride] = bytes(blk[s_ofs + 1::stride]).translate(lg)
            blk[s_ofs + 2::stride] = bytes(blk[s_ofs + 2::stride]).translate(lr)
            return
        if (e_ofs - s_ofs) * 4 >= stride:
            # 较宽：整行一次 LUT，再还原左右边距
            orig = bytes(blk)
            self._apply(blk, lb, lg, lr)
            for row in range(0, n, stride):
                if s_ofs:
                    blk[row:row + s_ofs] = orig[row:row + s_ofs]
                if e_ofs < stride:
                    blk[row + e_ofs:row + stride] = orig[row + e_ofs:row + stride]
            return
        for row in range(0, n, stride):
            blk[row + s_ofs:row + e_ofs] = self._apply(
                blk[row + s_ofs:row + e_ofs], lb, lg, lr)

    def _ring_cov(self, r_c):
        """半径 r_c 的 1px 圆环覆盖率表（外圆 r_c 减内圆 r_c-1）。

        panel 的内填矩形是「外框内缩 1px、半径减 1」，它的圆角圆心与外框
        的圆心重合，所以四角描边正好是同心圆之间的环，可直接查表。
        """
        v = self._ring_cache.get(r_c)
        if v is not None:
            return v
        items = []
        rin = r_c - 1
        for j in range(r_c):
            dy = j + 0.5 - r_c
            for i in range(r_c):
                dx = i + 0.5 - r_c
                d = math.sqrt(dx * dx + dy * dy)
                co = r_c + 0.5 - d
                ci = (rin + 0.5 - d) if rin > 0 else 0.0
                if co > 1.0:
                    co = 1.0
                elif co < 0.0:
                    co = 0.0
                if ci > 1.0:
                    ci = 1.0
                elif ci < 0.0:
                    ci = 0.0
                cov = co - ci
                if cov > 0.0:
                    items.append((i, j, cov))
        self._ring_cache[r_c] = items
        return items

    def blend_round_ring(self, rc, radius, color, alpha):
        """只画 1px 圆角边框：四条细带 + 四个 90° 圆环。

        面积是「周长」量级，远小于整块铺一遍描边色。
        """
        x0, y0 = max(0, rc.left), max(0, rc.top)
        x1, y1 = min(self.w, rc.right), min(self.h, rc.bottom)
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0 or alpha <= 0:
            return
        c = color_of(color)
        r_c = int(max(0, min(radius, w // 2, h // 2)))
        if r_c <= 0:
            self.blend_rect(RECT(x0, y0, x1, y0 + 1), c, alpha)
            self.blend_rect(RECT(x0, y1 - 1, x1, y1), c, alpha)
            if h > 2:
                self.blend_rect(RECT(x0, y0 + 1, x0 + 1, y1 - 1), c, alpha)
                self.blend_rect(RECT(x1 - 1, y0 + 1, x1, y1 - 1), c, alpha)
            return
        self.blend_rect(RECT(x0 + r_c, y0, x1 - r_c, y0 + 1), c, alpha)
        self.blend_rect(RECT(x0 + r_c, y1 - 1, x1 - r_c, y1), c, alpha)
        self.blend_rect(RECT(x0, y0 + r_c, x0 + 1, y1 - r_c), c, alpha)
        self.blend_rect(RECT(x1 - 1, y0 + r_c, x1, y1 - r_c), c, alpha)

        covs = self._ring_cov(r_c)
        if not covs:
            return
        cr_, cg_, cb_ = c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF
        a = int(alpha) / 255.0
        stride = self.stride
        rmax = r_c - 1
        for top in (True, False):
            for left in (True, False):
                bx = x0 if left else (x1 - r_c)
                by = y0 if top else (y1 - r_c)
                off = by * stride + bx * 4
                blk = self._read(off, r_c * stride)
                for i, j, cov in covs:
                    ky = j if top else (rmax - j)
                    kx = i if left else (rmax - i)
                    kk = a * cov
                    inv = 1.0 - kk
                    q = ky * stride + kx * 4
                    blk[q] = min(255, int(blk[q] * inv + cb_ * kk + 0.5))
                    blk[q + 1] = min(255, int(blk[q + 1] * inv
                                            + cg_ * kk + 0.5))
                    blk[q + 2] = min(255, int(blk[q + 2] * inv
                                            + cr_ * kk + 0.5))
                self._write(off, blk)

    # ---------------------------------------------------------- 半透明填充
    def blend_rect(self, rc, color, alpha):
        """矩形半透明叠加（按行连续，整块处理，最快）。"""
        x0, y0 = max(0, rc.left), max(0, rc.top)
        x1, y1 = min(self.w, rc.right), min(self.h, rc.bottom)
        if x1 <= x0 or y1 <= y0 or alpha <= 0:
            return
        c = color_of(color)
        if alpha >= 255:
            fill_rect(self.hdc, RECT(x0, y0, x1, y1), c)
            return
        lb, lg, lr = self._luts(c, alpha)
        off = y0 * self.stride
        n = (y1 - y0) * self.stride
        blk = self._read(off, n)
        self._apply_rect(blk, n, x0 * 4, x1 * 4, lb, lg, lr)
        self._write(off, blk)

    def blend_round(self, rc, color, radius, alpha):
        """半透明圆角矩形：主体走逐行 LUT（快），四角按圆覆盖率混合。

        坐标系必须统一到「像素中心 = 局部坐标 + 0.5」：圆心在 (r_c, r_c)、
        (w - r_c, h - r_c)。之前圆心写成了 r_c - 0.5，导致圆角被切在
        离角 r_c~r_c+5px 的位置——表现为顶边中间出现缺口，而四个角本身
        仍是直角（就是"右边又有圆角又有直边"的来源）。
        """
        x0, y0 = max(0, rc.left), max(0, rc.top)
        x1, y1 = min(self.w, rc.right), min(self.h, rc.bottom)
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0 or alpha <= 0:
            return
        c = color_of(color)
        r_c = int(max(0, min(radius, w // 2, h // 2)))
        if r_c == 0:
            self.blend_rect(rc, c, alpha)
            return

        lb, lg, lr = self._luts(c, alpha)
        off = y0 * self.stride
        n = h * self.stride
        blk = self._read(off, n)

        # 先留存四角**原始**像素：角部要按覆盖率重新混合；
        # 若在已叠加的结果上再叠一次，半透明圆角会明显偏深。
        #
        # 关键：blk 是「从 x=0 起的整行」切片，不是从 x0 起。
        # 因此这里的列号必须用**绝对列号**（x0 / x1-r_c），
        # 用相对列号会把圆角切到矩形中间去。
        corners = []
        for by in (0, h - r_c):                 # 行：相对 blk（blk 首行即 y0）
            for bx in (x0, x1 - r_c):           # 列：绝对
                rows = []
                for yy in range(r_c):
                    st = (by + yy) * self.stride + bx * 4
                    rows.append(blk[st:st + r_c * 4])
                corners.append((by, bx, rows))

        # 主体：按宽度分档做 LUT 叠加（见 _apply_rect）
        self._apply_rect(blk, n, x0 * 4, x1 * 4, lb, lg, lr)

        # 四角：按覆盖率（查缓存的表）从原始像素精确混合。
        # covs 的 (i, j) 是「距该角两条外边」的距离，四个角共用一张表，
        # 具体像素按 left/top 做镜像。
        cr_, cg_, cb_ = c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF
        a = int(alpha) / 255.0
        covs = self._corner_cov(r_c)
        ci = 0
        stride = self.stride
        for top in (True, False):
            for left in (True, False):
                by, bx, rows = corners[ci]
                ci += 1
                rmax = r_c - 1
                for i, j, cov in covs:
                    ky = j if top else (rmax - j)
                    kx = i if left else (rmax - i)
                    src_row = rows[ky]
                    t = kx * 4
                    kk = a * cov
                    inv = 1.0 - kk
                    q = (by + ky) * stride + (bx + kx) * 4
                    blk[q] = min(255, int(src_row[t] * inv + cb_ * kk + 0.5))
                    blk[q + 1] = min(255, int(src_row[t + 1] * inv
                                              + cg_ * kk + 0.5))
                    blk[q + 2] = min(255, int(src_row[t + 2] * inv
                                              + cr_ * kk + 0.5))
        self._write(off, blk)

    def panel(self, rc, radius, fill, stroke=None):
        """玻璃面板：内填 + 1px 描边。

        朴素做法是「整块铺一遍描边色，再内缩 1px 铺一遍填充色」，那要
        处理两倍面积（892x506 的列表卡片约 9.5ms）。这里把两次叠加
        合并为一次：内填用「先叠描边、再叠填充」的等效颜色/透明度
        (C, A) 一次画完，描边只在 1px 边框上补。面积从 2·w·h 降到
        w·h + 周长，视觉等价。

        等效叠加：先叠 (c1, a1) 再叠 (c2, a2)，等价于
            A = 1 - (1-a1)(1-a2)
            C·A = c1·a1·(1-a2) + c2·a2
        """
        if stroke is None:
            self.blend_round(rc, color_of(fill), radius, alpha_of(fill))
            return

        a1 = alpha_of(stroke) / 255.0
        a2 = alpha_of(fill) / 255.0
        A = 1.0 - (1.0 - a1) * (1.0 - a2)
        c1 = color_of(stroke)
        c2 = color_of(fill)
        inner = RECT(rc.left + 1, rc.top + 1, rc.right - 1, rc.bottom - 1)
        r_in = max(0, radius - 1)

        if A * 255.0 >= 1.0:
            def eq(sh):
                v = (((c1 >> sh) & 0xFF) * a1 * (1.0 - a2)
                     + ((c2 >> sh) & 0xFF) * a2) / A
                return int(min(255.0, max(0.0, v + 0.5)))
            C = eq(0) | (eq(8) << 8) | (eq(16) << 16)
            Aa = int(min(255.0, max(0.0, A * 255.0 + 0.5)))
            self.blend_round(inner, C, r_in, Aa)

        self.blend_round_ring(rc, radius, c1, alpha_of(stroke))


    # ---------------------------------------------------------- 输出
    def blit_to(self, dst_hdc, x=0, y=0):
        """把整块画布一次性拷到目标 DC（无中间态，不闪烁）。"""
        gdi32.BitBlt(ctypes.c_void_p(dst_hdc), x, y, self.w, self.h,
                     ctypes.c_void_p(self.hdc), 0, 0, SRCCOPY)


# ------------------------------------------------------------------ 流光背景
class Aurora:
    """三团径向辉光的流光背景。

    低分辨率逐像素算好辉光，再 StretchBlt 双线性放大铺满：
    模糊由放大天然完成，比在高分辨率上做高斯快两个数量级。
    """

    def __init__(self, glows=None, base=None):
        self.glows = glows or []
        self.base = base
        self.canvas = None
        self.t = 0.0

    def set_colors(self, glows, base):
        self.glows = glows
        self.base = base
        self.canvas = None

    def render(self, dst_hdc, dw, dh, w=88, h=60, t=None):
        if t is not None:
            self.t = t
        w = max(8, min(int(w), max(8, dw)))
        h = max(8, min(int(h), max(8, dh)))
        if self.canvas is None or self.canvas.w != w or self.canvas.h != h:
            if self.canvas:
                self.canvas.dispose()
            self.canvas = _Fresh(w, h)

        base = self.base if self.base is not None else rgb(10, 14, 24)
        br, bg, bb = base & 0xFF, (base >> 8) & 0xFF, (base >> 16) & 0xFF

        resolved = []
        for i, (c, a, cx, cy, rx, ry) in enumerate(self.glows):
            ph = i * 2.1
            dx = 0.014 * math.sin(self.t * 0.11 + ph)
            dy = 0.011 * math.cos(self.t * 0.09 + ph * 1.3)
            resolved.append((c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF,
                             a, cx + dx, cy + dy, rx, ry, 0.62))

        buf = bytearray(w * h * 4)
        p = 0
        for y in range(h):
            ny = (y + 0.5) / h
            for x in range(w):
                nx = (x + 0.5) / w
                r, g, b = br, bg, bb
                for (cr, cg, cb, a, cx, cy, rx, ry, stop) in resolved:
                    dx = (nx - cx) / rx
                    dy = (ny - cy) / ry
                    d2 = dx * dx + dy * dy
                    if d2 >= stop * stop:
                        continue
                    # CSS radial-gradient 是线性收边；这里 smoothstep 柔化，
                    # 观感更接近"丝绸光"
                    u = 1.0 - math.sqrt(d2) / stop
                    f = u * u * (3.0 - 2.0 * u)
                    aa = a * f
                    r += (cr - r) * aa
                    g += (cg - g) * aa
                    b += (cb - b) * aa
                buf[p] = int(b)
                buf[p + 1] = int(g)
                buf[p + 2] = int(r)
                buf[p + 3] = 255
                p += 4

        self.canvas.write(buf)
        self.canvas.blit(dst_hdc, dw, dh)


class _Fresh:
    """流光用的低分辨率画布。"""

    def __init__(self, w, h):
        self.w, self.h = w, h
        screen = user32.GetDC(None)
        self.hdc = gdi32.CreateCompatibleDC(ctypes.c_void_p(screen))
        user32.ReleaseDC(None, screen)
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        self._bits = ctypes.c_void_p()
        self.hbm = gdi32.CreateDIBSection(self.hdc, ctypes.byref(bmi), 0,
                                          ctypes.byref(self._bits), None, 0)
        gdi32.SelectObject(ctypes.c_void_p(self.hdc), self.hbm)

    def write(self, data):
        ctypes.memmove(ctypes.c_void_p(self._bits.value),
                       (ctypes.c_char * len(data)).from_buffer(data),
                       len(data))

    def blit(self, dst, dw, dh):
        gdi32.SetStretchBltMode(ctypes.c_void_p(dst), HALFTONE)
        gdi32.StretchBlt(ctypes.c_void_p(dst), 0, 0, dw, dh,
                         ctypes.c_void_p(self.hdc), 0, 0, self.w, self.h,
                         SRCCOPY)

    def dispose(self):
        if self.hdc:
            gdi32.DeleteDC(ctypes.c_void_p(self.hdc))
            self.hdc = None


# ------------------------------------------------------------------ 基础绘制
def fill_rect(hdc, rc, color):
    br = gdi32.CreateSolidBrush(color_of(color))
    user32.FillRect(ctypes.c_void_p(hdc), ctypes.byref(rc), br)
    gdi32.DeleteObject(br)


def fill_round(hdc, rc, color, radius):
    br = gdi32.CreateSolidBrush(color_of(color))
    old_b = gdi32.SelectObject(ctypes.c_void_p(hdc), br)
    old_p = gdi32.SelectObject(ctypes.c_void_p(hdc),
                               gdi32.GetStockObject(NULL_PEN))
    gdi32.RoundRect(ctypes.c_void_p(hdc), rc.left, rc.top, rc.right, rc.bottom,
                    radius, radius)
    gdi32.SelectObject(ctypes.c_void_p(hdc), old_p)
    gdi32.SelectObject(ctypes.c_void_p(hdc), old_b)
    gdi32.DeleteObject(br)


def grad_rect(hdc, rc, c1, c2, vertical=False):
    """两色线性渐变（TRIVERTEX + GRADIENT_RECT）。"""
    if rc.right <= rc.left or rc.bottom <= rc.top:
        return
    v = (TRIVERTEX * 2)()
    v[0].x, v[0].y = rc.left, rc.top
    v[1].x, v[1].y = rc.right, rc.bottom
    for i, c in enumerate((c1, c2)):
        v[i].Red = (c & 0xFF) * 257
        v[i].Green = ((c >> 8) & 0xFF) * 257
        v[i].Blue = ((c >> 16) & 0xFF) * 257
        v[i].Alpha = 0xFFFF
    m = (GRADIENT_RECT * 1)()
    m[0].UpperLeft = 0
    m[0].LowerRight = 1
    msimg32.GradientFill(ctypes.c_void_p(hdc), ctypes.byref(v), 2,
                         ctypes.byref(m), 1,
                         GRADIENT_FILL_RECT_V if vertical
                         else GRADIENT_FILL_RECT_H)


def grad_round(hdc, rc, c1, c2, radius, vertical=False):
    """圆角 + 渐变。GradientFill 不裁剪圆角，故先填底色再铺渐变，
    最后用底色把四角补回。"""
    fill_round(hdc, rc, c1, radius)
    if rc.right - rc.left < 4 or rc.bottom - rc.top < 4:
        return
    r = max(1, radius // 2)
    inner = RECT(rc.left + r, rc.top + r, rc.right - r, rc.bottom - r)
    grad_rect(hdc, inner, c1, c2, vertical)
    for cx, cy in ((rc.left + r, rc.top + r), (rc.right - r, rc.top + r),
                   (rc.left + r, rc.bottom - r), (rc.right - r, rc.bottom - r)):
        fill_round(hdc, RECT(cx - r, cy - r, cx + r, cy + r), c1, r)


def line(hdc, x1, y1, x2, y2, color, width=1):
    pn = gdi32.CreatePen(0, width, color_of(color))
    old_p = gdi32.SelectObject(ctypes.c_void_p(hdc), pn)
    gdi32.MoveToEx(ctypes.c_void_p(hdc), x1, y1, None)
    gdi32.LineTo(ctypes.c_void_p(hdc), x2, y2)
    gdi32.SelectObject(ctypes.c_void_p(hdc), old_p)
    gdi32.DeleteObject(pn)


def ellipse(hdc, cx, cy, rx, ry, color):
    br = gdi32.CreateSolidBrush(color_of(color))
    old_b = gdi32.SelectObject(ctypes.c_void_p(hdc), br)
    old_p = gdi32.SelectObject(ctypes.c_void_p(hdc),
                               gdi32.GetStockObject(NULL_PEN))
    gdi32.Ellipse(ctypes.c_void_p(hdc), cx - rx, cy - ry, cx + rx, cy + ry)
    gdi32.SelectObject(ctypes.c_void_p(hdc), old_p)
    gdi32.SelectObject(ctypes.c_void_p(hdc), old_b)
    gdi32.DeleteObject(br)


# ------------------------------------------------------------------ 文本
def text(hdc, font, color, x, y, w, h, s, flags=0):
    default = DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX
    gdi32.SetBkMode(ctypes.c_void_p(hdc), TRANSPARENT)
    gdi32.SelectObject(ctypes.c_void_p(hdc), font)
    gdi32.SetTextColor(ctypes.c_void_p(hdc), color_of(color))
    rc = RECT(int(x), int(y), int(x + w), int(y + h))
    return user32.DrawTextW(ctypes.c_void_p(hdc), s, -1, ctypes.byref(rc),
                            flags if flags else default)


def measure(hdc, font, s):
    gdi32.SelectObject(ctypes.c_void_p(hdc), font)
    rc = RECT(0, 0, 0, 0)
    user32.DrawTextW(ctypes.c_void_p(hdc), s, -1, ctypes.byref(rc),
                     DT_CALCRECT | DT_SINGLELINE | DT_NOPREFIX)
    return rc.right - rc.left, rc.bottom - rc.top
