# -*- coding: utf-8 -*-
"""ui.py —— 自绘界面：布局、流光背景、玻璃卡片、控件、命中测试。

全部在主窗口的客户区里手绘，不使用 ListView / Button 等子控件，
因此可以自由做圆角、渐变、玻璃层次。
"""
import ctypes
import math
import time

import theme as T
from aurora import (Aurora, RECT, rgb, mix, lighten, darken, fill_rect,
                    fill_round, blend_round, stroke_round, fill_round_grad,
                    hgradient_rect, text, measure, line, ellipse, user32, gdi32,
                    NULL_BRUSH, NULL_PEN)

DT_LEFT = 0x0000
DT_CENTER = 0x0001
DT_RIGHT = 0x0002
DT_VCENTER = 0x0004
DT_SINGLELINE = 0x0020
DT_END_ELLIPSIS = 0x8000
DT_NOPREFIX = 0x0800


def _rc(l, t, r, b):
    return RECT(int(l), int(t), int(r), int(b))


def _hit(x, y, rc):
    return rc.left <= x < rc.right and rc.top <= y < rc.bottom


class UI:
    """主窗口的界面层。"""

    def __init__(self, app):
        self.app = app
        self.aurora = Aurora()
        self.hit_regions = []      # [(kind, RECT, payload)]

    # ------------------------------------------------------------ 主题
    def pal(self):
        return T.DARK if self.app.g['dark'] else T.LIGHT

    def apply_theme(self):
        g = self.app.g
        dark = g['dark']
        self.aurora.set_colors(T.aurora_blobs(dark),
                               base=self.pal()['aurora_base'])

    # ------------------------------------------------------------ 布局
    def layout(self, w, h):
        """计算所有区域的矩形，写入 g['layout'] 并记录命中区。"""
        g = self.app.g
        sc = self.app.sc
        pal = self.pal()
        pad = sc(20)

        # —— 标题栏 ——
        cap_h = sc(46)
        close_w = sc(46)
        min_w = sc(40)

        # —— 顶部标题区（大标题 + 副标题）——
        head_y = cap_h + sc(6)
        head_h = sc(56)

        # —— 主操作行 ——
        act_y = head_y + head_h + sc(10)
        act_h = sc(38)
        btn_r = act_h // 2

        # —— 搜索框（与操作行同高，靠右）——
        search_w = sc(230)

        # —— 设置卡片（开关区）——
        set_y = act_y + act_h + sc(12)
        set_h = sc(62)

        # —— 列表卡片 ——
        list_y = set_y + set_h + sc(12)
        foot_h = sc(26)
        list_h = max(sc(120), h - list_y - foot_h - sc(8))
        list_r = _rc(pad, list_y, w - pad, list_y + list_h)

        # —— 底部状态 ——
        foot_y = list_y + list_h + sc(6)

        L = {
            'cap_h': cap_h,
            'close': _rc(w - close_w, 0, w, cap_h),
            'min': _rc(w - close_w - min_w, 0, w - close_w, cap_h),
            'head': _rc(pad, head_y, w - pad, head_y + head_h),
            'act_y': act_y, 'act_h': act_h, 'btn_r': btn_r,
            'set': _rc(pad, set_y, w - pad, set_y + set_h),
            'list': list_r,
            'foot': _rc(pad, foot_y, w - pad, foot_y + foot_h),
            'pad': pad,
        }

        # —— 操作行按钮（从左往右排）——
        x = pad
        bw_toggle = sc(126)
        bw_small = sc(42)
        gap = sc(8)
        L['btn_toggle'] = _rc(x, act_y, x + bw_toggle, act_y + act_h)
        x += bw_toggle + gap
        L['btn_refresh'] = _rc(x, act_y, x + bw_small, act_y + act_h)
        x += bw_small + gap
        L['btn_clear'] = _rc(x, act_y, x + bw_small, act_y + act_h)
        # 搜索框靠右
        L['search'] = _rc(w - pad - search_w, act_y,
                          w - pad, act_y + act_h)

        # —— 设置卡片里的两个开关 ——
        sw_w = sc(210)
        inner_x = L['set'].left + sc(16)
        row_h = sc(26)
        r1_y = L['set'].top + sc(7)
        L['sw_autotray'] = _rc(w - pad - sc(16) - sw_w, r1_y,
                               w - pad - sc(16), r1_y + row_h)
        L['sw_autostart'] = _rc(w - pad - sc(16) - sw_w, r1_y + row_h + sc(2),
                                w - pad - sc(16), r1_y + row_h * 2 + sc(2))
        # 左侧说明文字
        L['set_label'] = _rc(inner_x, L['set'].top + sc(8),
                             L['sw_autotray'].left - sc(16),
                             L['set'].top + sc(8) + sc(46))

        # —— 列表内部 ——
        lr = L['list']
        row_h_item = sc(50)
        head_h_item = sc(32)
        L['row_h'] = row_h_item
        L['list_head_h'] = head_h_item
        L['list_inner'] = _rc(lr.left + sc(1), lr.top + head_h_item,
                              lr.right - sc(1), lr.bottom - sc(1))
        L['list_h'] = L['list_inner'].bottom - L['list_inner'].top - sc(4)
        # 列表标题栏里的计数
        L['count'] = _rc(lr.left + sc(14), lr.top + 1,
                         lr.right - sc(14), lr.top + head_h_item)

        g['layout'] = L
        self._build_hits(L)
        self.app.clamp_scroll()
        return L

    def _build_hits(self, L):
        sc = self.app.sc
        H = []
        H.append((self.app.HIT_CLOSE, L['close'], None))
        H.append((self.app.HIT_MIN, L['min'], None))
        H.append((self.app.HIT_TITLE, _rc(0, 0, L['list'].right - sc(120),
                                          L['cap_h']), None))
        H.append((self.app.HIT_TOGGLE, L['btn_toggle'], None))
        H.append((self.app.HIT_REFRESH, L['btn_refresh'], None))
        H.append((self.app.HIT_CLEAR, L['btn_clear'], None))
        H.append((self.app.HIT_AUTOTRAY, L['sw_autotray'], None))
        H.append((self.app.HIT_AUTOSTART, L['sw_autostart'], None))
        H.append((self.app.HIT_SCROLL, L['list_inner'], None))
        self.hit_regions = H

    # ------------------------------------------------------------ 命中测试
    def hit_test(self, x, y):
        for kind, rc, payload in self.hit_regions:
            if _hit(x, y, rc):
                return kind, payload, rc
        return self.app.HIT_NONE, None, None

    def row_at(self, y):
        """屏幕 y -> 行索引（考虑滚动）。"""
        g = self.app.g
        L = g['layout']
        inner = L['list_inner']
        if not (inner.top <= y < inner.bottom):
            return -1
        rh = L['row_h']
        idx = (y - inner.top + g['scroll']) // rh
        if 0 <= idx < len(g['rows']):
            return idx
        return -1

    # ------------------------------------------------------------ 绘制
    def paint(self, hdc, w, h):
        g = self.app.g
        pal = self.pal()
        L = g['layout']
        t = (time_now() - g['t0'])

        # 1) 流光背景
        self.aurora.render(hdc, w, h, w=56, h=38, t=t)

        # 2) 顶部轻微暗角，让标题更清晰
        self._draw_header(hdc, L, pal)

        # 3) 标题栏按钮
        self._draw_caption(hdc, L, pal)

        # 4) 操作行
        self._draw_actions(hdc, L, pal)

        # 5) 设置卡片
        self._draw_settings(hdc, L, pal)

        # 6) 列表卡片
        self._draw_list(hdc, L, pal)

        # 7) 底部状态
        self._draw_footer(hdc, L, pal)

    # ---------------------------------------------------- 标题区
    def _draw_header(self, hdc, L, pal):
        g = self.app.g
        sc = self.app.sc
        r = L['head']
        text(hdc, g['font_cache']['h1'], pal['text'],
             r.left, r.top + sc(2), r.right - r.left, sc(28), "窗口置顶")
        text(hdc, g['font_cache']['small'], pal['text_dim'],
             r.left + sc(1), r.top + sc(30), r.right - r.left, sc(18),
             "把任意窗口钉在最上层 · Ctrl+Alt+T 快速切换")

    def _draw_caption(self, hdc, L, pal):
        g = self.app.g
        # 关闭
        rc = L['close']
        hot = g['hover'] == self.app.HIT_CLOSE
        if hot:
            fill_round(hdc, rc, lighten(pal['danger'], 0.0) if not g['dark']
                       else rgb(0xC4, 0x2B, 0x2B), 0)
        col = rgb(255, 255, 255) if hot else pal['text_dim']
        self._draw_x_icon(hdc, rc, col)
        # 最小化
        rc = L['min']
        if g['hover'] == self.app.HIT_MIN:
            fill_round(hdc, rc, pal['hover'], 0)
        self._draw_min_icon(hdc, rc, pal['text_dim'])

    def _draw_x_icon(self, hdc, rc, col):
        s = self.app.sc
        cx = (rc.left + rc.right) // 2
        cy = (rc.top + rc.bottom) // 2
        r = s(5)
        line(hdc, cx - r, cy - r, cx + r, cy + r, col, max(1, s(1)))
        line(hdc, cx - r, cy + r, cx + r, cy - r, col, max(1, s(1)))

    def _draw_min_icon(self, hdc, rc, col):
        s = self.app.sc
        cx = (rc.left + rc.right) // 2
        cy = (rc.top + rc.bottom) // 2
        r = s(5)
        line(hdc, cx - r, cy, cx + r, cy, col, max(1, s(1)))

    # ---------------------------------------------------- 操作行
    def _draw_actions(self, hdc, L, pal):
        g = self.app.g
        sc = self.app.sc
        sel = self.app.selected_row()

        # 主按钮：置顶/取消
        rc = L['btn_toggle']
        hot = g['hover'] == self.app.HIT_TOGGLE
        press = g['press'] == self.app.HIT_TOGGLE
        is_on = bool(sel and sel[4])
        acc = pal['accent']
        if is_on:
            c_top = lighten(acc, 0.10 if not press else 0.0)
            c_bot = darken(acc, 0.12 if not press else 0.02)
        else:
            c_top = lighten(acc, 0.22) if hot else lighten(acc, 0.12)
            c_bot = darken(acc, 0.02) if hot else darken(acc, 0.12)
        if press:
            c_top = darken(c_top, 0.10)
            c_bot = darken(c_bot, 0.10)
        fill_round_grad(hdc, rc, c_top, c_bot, L['btn_r'])
        label = "取消置顶" if is_on else "置顶窗口"
        ico = T.ICO_UNPIN if is_on else T.ICO_PIN
        self._draw_btn_content(hdc, rc, ico, label, pal['on_accent'],
                               g['font_cache']['body_sb'])

        # 圆形图标按钮
        self._draw_icon_btn(hdc, L['btn_refresh'], T.ICO_REFRESH,
                            self.app.HIT_REFRESH, pal)
        self._draw_icon_btn(hdc, L['btn_clear'], T.ICO_CLEAR,
                            self.app.HIT_CLEAR, pal)

        # 搜索框
        self._draw_search(hdc, L['search'], pal)

    def _draw_btn_content(self, hdc, rc, ico, label, fg, font):
        sc = self.app.sc
        iw, ih = measure(hdc, font, label)
        total = sc(18) + sc(6) + iw
        x = rc.left + (rc.right - rc.left - total) // 2
        cy = (rc.top + rc.bottom) // 2
        text(hdc, self.app.g['font_cache']['icon_sm'], fg,
             x, rc.top, sc(18), rc.bottom - rc.top, ico,
             DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
        text(hdc, font, fg, x + sc(18) + sc(6), rc.top, iw + sc(4),
             rc.bottom - rc.top, label)

    def _draw_icon_btn(self, hdc, rc, ico, kind, pal):
        g = self.app.g
        sc = self.app.sc
        hot = g['hover'] == kind
        press = g['press'] == kind
        cx = (rc.left + rc.right) // 2
        cy = (rc.top + rc.bottom) // 2
        rad = (rc.right - rc.left) // 2
        if hot:
            fill_round(hdc, rc, pal['hover'] if not press else pal['stroke'], rad)
        stroke_round(hdc, rc, pal['stroke'], rad)
        col = pal['text'] if hot else pal['text_dim']
        text(hdc, g['font_cache']['icon'], col,
             rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top, ico,
             DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)

    def _draw_search(self, hdc, rc, pal):
        g = self.app.g
        sc = self.app.sc
        rad = (rc.bottom - rc.top) // 2
        fill_round(hdc, rc, pal['field'], rad)
        stroke_round(hdc, rc, pal['stroke'], rad)
        col = pal['text_faint']
        text(hdc, g['font_cache']['icon_sm'], col,
             rc.left + sc(12), rc.top, sc(18), rc.bottom - rc.top, T.ICO_SEARCH,
             DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
        hint = g['filter'] or "搜索窗口…"
        col = pal['text'] if g['filter'] else pal['text_faint']
        text(hdc, g['font_cache']['body'], col,
             rc.left + sc(36), rc.top, rc.right - rc.left - sc(46),
             rc.bottom - rc.top, hint)

    # ---------------------------------------------------- 设置卡片
    def _draw_settings(self, hdc, L, pal):
        g = self.app.g
        sc = self.app.sc
        rc = L['set']
        r = sc(14)
        # 玻璃卡片：半透明感用「亮底 + 细描边」表达
        blend_round(hdc, rc, self._glass(pal), r, self._glass_alpha())
        stroke_round(hdc, rc, self._glass_edge(pal), r)

        # 左侧图标 + 说明
        ix = rc.left + sc(16)
        iy = rc.top + sc(15)
        ellipse_fg = pal['accent_soft']
        ellipse(hdc, ix + sc(11), iy + sc(11), sc(11), sc(11), ellipse_fg)
        text(hdc, g['font_cache']['icon'], pal['accent'],
             ix, iy, sc(22), sc(22), T.ICO_SETTINGS,
             DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
        text(hdc, g['font_cache']['body_sb'], pal['text'],
             ix + sc(30), rc.top + sc(12), sc(240), sc(18), "设置")
        text(hdc, g['font_cache']['small'], pal['text_dim'],
             ix + sc(30), rc.top + sc(30), sc(260), sc(18),
             "开机自动运行，置顶后自动转入后台")

        self._draw_switch(hdc, L['sw_autotray'], "置顶后转入后台",
                          g['autotray'], pal, self.app.HIT_AUTOTRAY)
        self._draw_switch(hdc, L['sw_autostart'], "开机自启",
                          g['autostart'], pal, self.app.HIT_AUTOSTART)

    def _draw_switch(self, hdc, rc, label, on, pal, kind):
        g = self.app.g
        sc = self.app.sc
        hot = g['hover'] == kind
        # 标签
        text(hdc, g['font_cache']['body'],
             pal['text'] if hot else pal['text_dim'],
             rc.left, rc.top, rc.right - rc.left - sc(52),
             rc.bottom - rc.top, label)
        # 开关轨道（右侧）
        tw = sc(38)
        th = sc(21)
        tr = _rc(rc.right - tw, rc.top + (rc.bottom - rc.top - th) // 2,
                 rc.right, rc.top + (rc.bottom - rc.top + th) // 2)
        rad = th // 2
        track = pal['accent'] if on else (pal['stroke'] if not hot
                                           else pal['text_faint'])
        fill_round(hdc, tr, track, rad)
        # 滑块
        kr = th // 2 - sc(2)
        kx = tr.right - kr - sc(2) if on else tr.left + kr + sc(2)
        ky = (tr.top + tr.bottom) // 2
        knob = pal['on_accent'] if not g['dark'] else rgb(255, 255, 255)
        ellipse(hdc, kx, ky, kr, kr, knob)

    def _glass(self, pal, k=1.0):
        """玻璃卡片底色：在底色与卡片色之间插值，k 越大越"实"。"""
        if self.app.g['dark']:
            # 深色：卡片比背景略亮，保持通透
            return mix(pal['bg'], pal['card'], min(1.0, 0.85 * k))
        # 浅色：卡片接近纯白
        return mix(pal['bg'], pal['card'], min(1.0, 0.92 * k))

    def _glass_alpha(self):
        """玻璃卡片不透明度：留出余量让流光背景透上来。"""
        return 150 if self.app.g['dark'] else 168

    def _glass_edge(self, pal):
        """玻璃卡片描边：深色下用微亮的白，浅色下用灰。"""
        if self.app.g['dark']:
            return mix(pal['stroke'], rgb(255, 255, 255), 0.10)
        return pal['stroke']

    # ---------------------------------------------------- 列表
    def _draw_list(self, hdc, L, pal):
        g = self.app.g
        sc = self.app.sc
        rc = L['list']
        r = sc(14)
        blend_round(hdc, rc, self._glass(pal), r, self._glass_alpha())
        stroke_round(hdc, rc, self._glass_edge(pal), r)

        # 列表标题行
        cr = L['count']
        total = len(g['rows'])
        pinned = sum(1 for x in g['rows'] if x[4])
        text(hdc, g['font_cache']['body_sb'], pal['text'],
             cr.left, cr.top, sc(200), cr.bottom - cr.top, "窗口列表")
        right = "%d 个窗口" % total
        if pinned:
            right = "%d 个 · %d 个已置顶" % (total, pinned)
        text(hdc, g['font_cache']['small'], pal['text_faint'],
             cr.left, cr.top, cr.right - cr.left, cr.bottom - cr.top, right,
             DT_RIGHT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
        line(hdc, rc.left + sc(12), cr.bottom, rc.right - sc(12), cr.bottom,
             pal['stroke_soft'], 1)

        inner = L['list_inner']
        if total == 0:
            self._draw_empty(hdc, inner, pal)
            return

        rh = L['row_h']
        saved = gdi32.SaveDC(ctypes.c_void_p(hdc))
        gdi32.IntersectClipRect(ctypes.c_void_p(hdc), inner.left, inner.top,
                                inner.right, inner.bottom)
        first = max(0, g['scroll'] // rh)
        last = min(total, (g['scroll'] + (inner.bottom - inner.top)) // rh + 1)
        for i in range(first, last):
            y = inner.top + i * rh - g['scroll']
            self._draw_row(hdc, _rc(inner.left, y, inner.right, y + rh),
                           i, pal)
        if saved:
            gdi32.RestoreDC(ctypes.c_void_p(hdc), saved)
        self._draw_scrollbar(hdc, L, pal)

    def _draw_row(self, hdc, rc, idx, pal):
        g = self.app.g
        sc = self.app.sc
        hwnd, title, exe, path, top = g['rows'][idx]
        sel = (idx == g['sel'])
        hot = (idx == g['hover_row'])
        rad = sc(9)
        pad = sc(8)
        row_h = rc.bottom - rc.top

        if sel:
            fill_round(hdc, rc, pal['active'], rad)
            stroke_round(hdc, rc, mix(pal['accent'], pal['stroke'], 0.45), rad)
        elif hot:
            fill_round(hdc, rc, pal['hover'], rad)

        # 左侧：已置顶的窗口加一条强调色竖条
        if top:
            bar = _rc(rc.left + sc(2), rc.top + sc(10), rc.left + sc(4),
                      rc.bottom - sc(10))
            fill_round(hdc, bar, pal['accent'], sc(1))

        # 程序图标
        isz = sc(20)
        ix = rc.left + pad + sc(6)
        iy = rc.top + (row_h - isz) // 2
        iidx = g['icon_cache'].get(path, -1)
        if iidx >= 0 and g['himl']:
            comctl32.ImageList_Draw(g['himl'], iidx, ctypes.c_void_p(hdc),
                                    ix, iy, 0)
        else:
            ellipse(hdc, ix + isz // 2, iy + isz // 2, sc(9), sc(9),
                    mix(pal['text_faint'], pal['stroke'], 0.5))

        tx = ix + isz + sc(12)
        # 右侧为置顶标记留位
        right_pad = sc(34) if top else sc(10)

        # 标题：占上半部分
        tfont = g['font_cache']['body_sb'] if top else g['font_cache']['body']
        text(hdc, tfont, pal['text'],
             tx, rc.top + sc(5), rc.right - tx - right_pad, sc(20), title,
             DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX)

        # 进程名：占下半部分
        text(hdc, g['font_cache']['tiny'], pal['text_faint'],
             tx, rc.top + sc(23), rc.right - tx - right_pad, sc(16), exe,
             DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX)

        # 右侧：置顶标记
        if top:
            mx = rc.right - pad - sc(16)
            my = (rc.top + rc.bottom) // 2
            ellipse(hdc, mx, my, sc(10), sc(10), pal['accent_soft'])
            text(hdc, g['font_cache']['icon_sm'], pal['accent'],
                 mx - sc(10), my - sc(10), sc(20), sc(20), T.ICO_PIN,
                 DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)

    def _draw_empty(self, hdc, inner, pal):
        g = self.app.g
        sc = self.app.sc
        cx = (inner.left + inner.right) // 2
        cy = (inner.top + inner.bottom) // 2
        ellipse(hdc, cx, cy - sc(22), sc(22), sc(22), pal['stroke_soft'])
        text(hdc, g['font_cache']['icon_xl'], pal['text_faint'],
             cx - sc(22), cy - sc(44), sc(44), sc(44), T.ICO_SEARCH,
             DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
        msg = "没有匹配的窗口" if g['filter'] else "暂无可置顶的窗口"
        text(hdc, g['font_cache']['body'], pal['text_dim'],
             cx - sc(140), cy + sc(6), sc(280), sc(20), msg,
             DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)

    def _draw_scrollbar(self, hdc, L, pal):
        g = self.app.g
        sc = self.app.sc
        if g['scroll_max'] <= 0:
            return
        inner = L['list_inner']
        track_h = inner.bottom - inner.top
        ratio = (inner.bottom - inner.top) / float(
            len(g['rows']) * L['row_h'])
        thumb_h = max(sc(28), int(track_h * ratio))
        max_scroll = g['scroll_max']
        frac = (g['scroll'] / float(max_scroll)) if max_scroll else 0
        ty = inner.top + int((track_h - thumb_h) * frac)
        tr = _rc(inner.right - sc(9), ty, inner.right - sc(4), ty + thumb_h)
        fill_round(hdc, tr, pal['text_faint'], (tr.right - tr.left) // 2)

    # ---------------------------------------------------- 底部状态
    def _draw_footer(self, hdc, L, pal):
        g = self.app.g
        sc = self.app.sc
        rc = L['foot']
        hint = g['hint'] or "双击列表项或按 Ctrl+Alt+T 切换置顶"
        text(hdc, g['font_cache']['small'], pal['text_faint'],
             rc.left, rc.top, rc.right - rc.left - sc(120),
             rc.bottom - rc.top, hint,
             DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX)
        text(hdc, g['font_cache']['tiny'], pal['text_faint'],
             rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top,
             "v2.0", DT_RIGHT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)


def time_now():
    return time.time()


# 让 SaveDC / IntersectClipRect / RestoreDC 有原型
gdi32.SaveDC.argtypes = [ctypes.c_void_p]
gdi32.SaveDC.restype = ctypes.c_int
gdi32.RestoreDC.argtypes = [ctypes.c_void_p, ctypes.c_int]
gdi32.RestoreDC.restype = ctypes.c_int
gdi32.IntersectClipRect.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 4
gdi32.IntersectClipRect.restype = ctypes.c_int
