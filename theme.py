# -*- coding: utf-8 -*-
"""theme.py —— Fluent 流光主题：调色板、字体、色斑配置。

集中管理所有视觉常量，主绘制代码只按语义取色（surface/card/text/accent...），
换主题时只改这里。
"""
import ctypes

from aurora import rgb, mix, lighten, darken

# ----------------------------------------------------------------- 语义色板
LIGHT = {
    "bg":          rgb(0xF2, 0xF4, 0xF9),
    "card":        rgb(0xFF, 0xFF, 0xFF),
    "card_alt":    rgb(0xF7, 0xF9, 0xFC),
    "stroke":      rgb(0xE3, 0xE8, 0xF0),
    "stroke_soft": rgb(0xEC, 0xEF, 0xF5),
    "text":        rgb(0x14, 0x18, 0x20),
    "text_dim":    rgb(0x5C, 0x66, 0x78),
    "text_faint":  rgb(0x92, 0x9C, 0xAD),
    "accent":      rgb(0x0A, 0x63, 0xE9),
    "accent_soft": rgb(0xE3, 0xEE, 0xFF),
    "hover":       rgb(0xF0, 0xF4, 0xFA),
    "active":      rgb(0xE6, 0xEF, 0xFD),
    "on_accent":   rgb(0xFF, 0xFF, 0xFF),
    "field":       rgb(0xFF, 0xFF, 0xFF),
    "shadow":      rgb(0x1B, 0x25, 0x38),
    "danger":      rgb(0xD1, 0x34, 0x3C),
    "aurora_base": rgb(0xDF, 0xE6, 0xF4),
}

DARK = {
    "bg":          rgb(0x0B, 0x0E, 0x16),
    "card":        rgb(0x16, 0x1B, 0x26),
    "card_alt":    rgb(0x1B, 0x21, 0x2E),
    "stroke":      rgb(0x2A, 0x33, 0x45),
    "stroke_soft": rgb(0x21, 0x29, 0x38),
    "text":        rgb(0xF2, 0xF5, 0xFA),
    "text_dim":    rgb(0xA3, 0xAF, 0xC2),
    "text_faint":  rgb(0x6C, 0x78, 0x8C),
    "accent":      rgb(0x4D, 0x94, 0xFF),
    "accent_soft": rgb(0x1D, 0x2C, 0x47),
    "hover":       rgb(0x22, 0x2A, 0x39),
    "active":      rgb(0x1B, 0x2C, 0x47),
    "on_accent":   rgb(0xFF, 0xFF, 0xFF),
    "field":       rgb(0x13, 0x18, 0x22),
    "shadow":      rgb(0x00, 0x00, 0x00),
    "danger":      rgb(0xFF, 0x6B, 0x72),
    "aurora_base": rgb(0x0C, 0x10, 0x1A),
}

# ----------------------------------------------------------------- 字体
# 注意：SegUIVar.ttf 的家族名是 "Segoe UI Variable"（没有 Display/Text 后缀，
# 那是 DirectWrite 的写法）。写错名字 GDI 会静默回退到默认字体。
FONT_TITLE = "Segoe UI Variable"
FONT_UI = "Segoe UI Variable"
FONT_SB = "Segoe UI Semibold"
FONT_FALLBACK = "Segoe UI"
FONT_ICON = "Segoe Fluent Icons"

ICO_PIN = ""
ICO_UNPIN = ""
ICO_REFRESH = ""
ICO_CLEAR = ""
ICO_MIN = ""
ICO_CLOSE = ""
ICO_SEARCH = ""
ICO_SETTINGS = ""
ICO_CHECK = ""
ICO_POWER = ""
ICO_CHEVRON = ""
ICO_ARROW = ""


def make_fonts(scale):
    """按 DPI 生成整套字体句柄。

    Segoe UI Variable 支持字重轴，用 GDI 的 weight 参数即可拿到
    Light/Regular/Semibold/Bold 四档，比罗列多个家族名更可靠。
    """
    px = lambda v: -int(round(v * scale))
    F = _font
    return {
        # 大标题（Semibold）
        "h1":     F(px(21), 600, FONT_TITLE),
        "h2":     F(px(13), 600, FONT_UI),
        # 正文
        "body":   F(px(13.5), 400, FONT_UI),
        "body_sb": F(px(13.5), 600, FONT_UI),
        # 小字
        "small":  F(px(12), 400, FONT_UI),
        "tiny":   F(px(11), 400, FONT_UI),
        # 图标
        "icon":    F(px(15), 400, FONT_ICON),
        "icon_sm": F(px(13), 400, FONT_ICON),
        "icon_lg": F(px(17), 400, FONT_ICON),
        "icon_xl": F(px(20), 400, FONT_ICON),
    }


def _font(height, weight, family):
    gdi32 = ctypes.WinDLL("gdi32")
    return gdi32.CreateFontW(
        height, 0, 0, 0, weight, 0, 0, 0,
        1,          # DEFAULT_CHARSET
        0, 0, 5,    # CLEARTYPE_QUALITY, DEFAULT_PITCH|FF_DONTCARE
        family,
    )


# ----------------------------------------------------------------- 流光色斑
# (颜色, 基准x, 基准y, 半径, 强度, 相位, 横向振幅, 纵向振幅, 速度)
def aurora_blobs(dark=True):
    """流光色斑配置。坐标为窗口内相对位置，缓慢漂移形成丝绸般的光带。"""
    if dark:
        return [
            (rgb(0x2E, 0x7C, 0xF6), 0.18, 0.02, 0.62, 0.95, 0.0,  0.10, 0.07, 0.16),
            (rgb(0x7B, 0x4D, 0xF6), 0.86, 0.14, 0.58, 0.85, 1.7,  0.11, 0.09, 0.13),
            (rgb(0x0E, 0xA5, 0xE9), 0.55, 0.95, 0.66, 0.75, 3.1,  0.13, 0.08, 0.11),
            (rgb(0xF0, 0x4F, 0x8A), 0.05, 0.72, 0.44, 0.42, 4.4,  0.09, 0.10, 0.14),
        ]
    return [
        (rgb(0x4A, 0x9B, 0xF5), 0.16, 0.04, 0.66, 0.62, 0.0,  0.10, 0.07, 0.15),
        (rgb(0x9B, 0x7C, 0xF7), 0.84, 0.16, 0.60, 0.55, 1.7,  0.11, 0.09, 0.12),
        (rgb(0x38, 0xC8, 0xE8), 0.58, 0.94, 0.68, 0.45, 3.1,  0.13, 0.08, 0.10),
        (rgb(0xF7, 0x74, 0xB0), 0.06, 0.70, 0.46, 0.34, 4.4,  0.09, 0.10, 0.13),
    ]
