# -*- coding: utf-8 -*-
"""theme.py —— 设计令牌（对齐「文件批量重命名」的深色玻璃拟态视觉）

配色、圆角、字体、流光辉光全部集中在这里，绘制代码只按语义取色。

约定：
  · 实色     -> COLORREF(int)，直接用 GDI 填充
  · 半透明层 -> (COLORREF, alpha0_255)，用 AlphaBlend 叠加
"""
from aurora import rgb

# ------------------------------------------------------------------ 圆角
R_XL = 20      # 大卡片
R_LG = 15      # 面板
R_MD = 11      # 按钮 / 菜单
R_SM = 8       # 菜单项
R_XS = 7       # 标题栏小按钮

# ------------------------------------------------------------------ 字体
# GDI 里注册的家族名是 "Segoe UI Variable Text"（带 Text 后缀）；
# 裸的 "Segoe UI Variable" GDI 找不到，会静默回退到宋体。
FONT_UI = "Segoe UI Variable Text"
FONT_SB = "Segoe UI Semibold"     # 600 字重用这个真实家族，比合成粗体干净
FONT_ICON = "Segoe Fluent Icons"

# ------------------------------------------------------------------ 图标码位
# 均已用 SegoeIcons.ttf 逐字渲染核对过语义
ICO_MENU = "\ue700"        # 三条杠
ICO_SUN = "\ue706"
ICO_MOON = "\ue708"
ICO_SETTINGS = "\ue713"
ICO_SEARCH = "\ue721"      # 放大镜
ICO_REFRESH = "\ue72c"
ICO_CLEAR = "\ue74d"       # 垃圾桶
ICO_CLOSE = "\ue8bb"       # ✕
ICO_MIN = "\ue921"         # ─
ICO_MAX = "\ue922"         # □
ICO_RESTORE = "\ue923"     # ❐
ICO_PIN = "\ue718"         # 图钉
ICO_UNPIN = "\ue77a"       # 取消图钉
ICO_POWER = "\ue7e8"       # 电源
ICO_CHECK = "\ue73e"
ICO_CHEVRON = "\ue76c"
ICO_ARROW = "\ue72a"
ICO_BOLT = "\ue945"
ICO_LOCK = "\ue72e"
ICO_HOME = "\ue80f"

# ------------------------------------------------------------------ 色板
DARK = {
    # 基础
    "bg":        rgb(0x0A, 0x0E, 0x18),
    "fg":        rgb(0xEE, 0xF2, 0xFB),
    "fg_dim":    rgb(0xA7, 0xB2, 0xCC),
    "fg_mute":   rgb(0x78, 0x84, 0x9F),
    # 品牌色
    "brand":     rgb(0x63, 0x66, 0xF1),
    "brand_2":   rgb(0x8B, 0x5C, 0xF6),
    "cyan":      rgb(0x22, 0xD3, 0xEE),
    "ok":        rgb(0x34, 0xD3, 0x99),
    "warn":      rgb(0xFB, 0xBF, 0x24),
    "danger":    rgb(0xF8, 0x71, 0x71),
    "on_brand":  rgb(0xFF, 0xFF, 0xFF),

    # 半透明表面（COLORREF, alpha）
    "app_border":  (rgb(0xFF, 0xFF, 0xFF), 18),
    "titlebar":    (rgb(0x09, 0x0C, 0x16), 140),
    "toolbar":     (rgb(0x09, 0x0C, 0x16), 82),
    "panel":       (rgb(0xFF, 0xFF, 0xFF), 14),
    "panel_2":     (rgb(0xFF, 0xFF, 0xFF), 22),
    "panel_3":     (rgb(0xFF, 0xFF, 0xFF), 31),
    "field":       (rgb(0x0F, 0x14, 0x22), 150),
    "statusbar":   (rgb(0x09, 0x0C, 0x16), 102),
    "menu":        (rgb(0x10, 0x15, 0x24), 247),

    # 描边
    "stroke":      (rgb(0xFF, 0xFF, 0xFF), 26),
    "stroke_2":    (rgb(0xFF, 0xFF, 0xFF), 46),
    "row_line":    (rgb(0xFF, 0xFF, 0xFF), 15),

    # 交互态
    "hover":       (rgb(0xFF, 0xFF, 0xFF), 31),
    "brand_soft":  (rgb(0x63, 0x66, 0xF1), 46),
    "sel_line":    rgb(0x4F, 0x52, 0xE0),

    # 流光辉光：(颜色, 峰值alpha0_1, cx, cy, rx, ry)，坐标/半径按窗口比例
    # 三团径向辉光：位置/配色沿用「文件批量重命名」，强度略提高、
    # 圆心往窗口内收一点，让光晕在整个顶部与底部都读得出来（而不是只在角落）
    "glow": [
        (rgb(0x63, 0x66, 0xF1), 0.34, 0.14, -0.02, 0.74, 0.80),
        (rgb(0x8B, 0x5C, 0xF6), 0.26, 0.88, 0.02, 0.68, 0.74),
        (rgb(0x22, 0xD3, 0xEE), 0.18, 0.50, 1.02, 0.82, 0.82),
    ],
    "glow_base": rgb(0x0A, 0x0E, 0x18),
}

LIGHT = {
    "bg":        rgb(0xEE, 0xF1, 0xF8),
    "fg":        rgb(0x10, 0x18, 0x28),
    "fg_dim":    rgb(0x47, 0x54, 0x67),
    "fg_mute":   rgb(0x7C, 0x88, 0xA1),
    "brand":     rgb(0x63, 0x66, 0xF1),
    "brand_2":   rgb(0x8B, 0x5C, 0xF6),
    "cyan":      rgb(0x22, 0xD3, 0xEE),
    "ok":        rgb(0x10, 0xB9, 0x81),
    "warn":      rgb(0xD9, 0x7A, 0x06),
    "danger":    rgb(0xDC, 0x26, 0x26),
    "on_brand":  rgb(0xFF, 0xFF, 0xFF),

    "app_border":  (rgb(0x0F, 0x17, 0x2A), 20),
    "titlebar":    (rgb(0xFF, 0xFF, 0xFF), 189),
    "toolbar":     (rgb(0xFF, 0xFF, 0xFF), 128),
    "panel":       (rgb(0xFF, 0xFF, 0xFF), 189),
    "panel_2":     (rgb(0xFF, 0xFF, 0xFF), 240),
    "panel_3":     (rgb(0x0F, 0x17, 0x2A), 18),
    "field":       (rgb(0xFF, 0xFF, 0xFF), 235),
    "statusbar":   (rgb(0xFF, 0xFF, 0xFF), 158),
    "menu":        (rgb(0xFF, 0xFF, 0xFF), 250),

    "stroke":      (rgb(0x0F, 0x17, 0x2A), 26),
    "stroke_2":    (rgb(0x0F, 0x17, 0x2A), 51),
    "row_line":    (rgb(0x0F, 0x17, 0x2A), 15),

    "hover":       (rgb(0x0F, 0x17, 0x2A), 18),
    "brand_soft":  (rgb(0x63, 0x66, 0xF1), 41),
    "sel_line":    rgb(0x4F, 0x46, 0xE5),

    "glow": [
        (rgb(0x63, 0x66, 0xF1), 0.26, 0.12, -0.02, 0.74, 0.80),
        (rgb(0x8B, 0x5C, 0xF6), 0.20, 0.90, 0.02, 0.68, 0.74),
        (rgb(0x22, 0xD3, 0xEE), 0.18, 0.50, 1.02, 0.82, 0.82),
    ],
    "glow_base": rgb(0xEE, 0xF1, 0xF8),
}


def palette(dark):
    return DARK if dark else LIGHT


def color_of(c):
    """取实色部分（透明层取 COLORREF）。"""
    return c[0] if isinstance(c, tuple) else c


def alpha_of(c, default=255):
    """取 alpha 部分（实色返回 default）。"""
    return c[1] if isinstance(c, tuple) else default


def rgba(c):
    """(COLORREF, alpha) -> (r, g, b, a)"""
    col, a = c
    return (col & 0xFF, (col >> 8) & 0xFF, (col >> 16) & 0xFF, a)


# ------------------------------------------------------------------ 字体表
def make_fonts(scale):
    """按 DPI 生成整套字体句柄。"""
    px = lambda v: -int(round(v * scale))
    F = _font
    return {
        "brand":     F(px(13), 600, FONT_SB),      # 标题栏应用名
        "brand_sub": F(px(10.5), 400, FONT_UI),    # 标题栏副标题
        "btn":       F(px(12.5), 600, FONT_UI),    # 按钮文字
        "body":      F(px(12.5), 400, FONT_UI),
        "body_sb":   F(px(12.5), 600, FONT_SB),
        "menu":      F(px(12), 400, FONT_UI),
        "menu_sb":   F(px(12), 600, FONT_SB),
        "status":    F(px(11), 400, FONT_UI),
        "status_sb": F(px(11), 600, FONT_SB),
        "row":       F(px(13), 500, FONT_UI),      # 列表主标题
        "row_sb":    F(px(13), 600, FONT_SB),
        "row_sub":   F(px(11), 400, FONT_UI),      # 列表进程名
        "icon":      F(px(15), 400, FONT_ICON),
        "icon_sm":   F(px(13), 400, FONT_ICON),
        "icon_md":   F(px(16), 400, FONT_ICON),
        "icon_lg":   F(px(19), 400, FONT_ICON),
    }


def _font(height, weight, family):
    """创建字体句柄。

    必须用带完整原型的 gdi32：CreateFontW 返回的是 HFONT，若不声明 restype，
    ctypes 会按默认的 c_int 截断成 32 位，句柄随即失效 —— 后果是
    SelectObject 静默失败，图标字体整片消失、中文回退到宋体。

    14 个参数依次为：
      nHeight nWidth nEscapement nOrientation fnWeight fdwItalic fdwUnderline
      fdwStrikeOut fdwCharSet fdwOutputPrecision fdwClipPrecision fdwQuality
      fdwPitchAndFamily lpszFace
    """
    import aurora
    return aurora.gdi32.CreateFontW(
        height, 0, 0, 0, weight, 0, 0, 0,
        1,           # DEFAULT_CHARSET
        0, 0,        # OUTPUT/CLIP precision = 默认
        5,           # CLEARTYPE_QUALITY
        0,           # DEFAULT_PITCH | FF_DONTCARE
        family,
    )
