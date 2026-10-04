# -*- coding: utf-8 -*-
"""ui.py —— 界面层：布局、玻璃面板、控件绘制、命中测试

结构对齐「文件批量重命名」：
  titlebar（logo + 应用名 + 右侧工具按钮 + 窗口按钮）
  toolbar（主操作按钮 / 次要按钮 / 右侧搜索框）
  panel（窗口列表卡片）
  statusbar（左侧提示 / 右侧统计）
  menu（右上角三条杠唤出的设置菜单，浮层）

全部绘制落在 aurora.Canvas 上（半透明合成由画布自己完成），
仅搜索框用真实 EDIT 子控件以支持输入法。
"""
import ctypes
import ctypes.wintypes as wt
import math
import time

import theme as T
from aurora import (Aurora, Canvas, RECT, rgb, mix, lighten, darken, fill_rect,
                    fill_round, grad_round, text, measure, line, ellipse,
                    user32, gdi32,
                    DT_LEFT, DT_CENTER, DT_RIGHT, DT_VCENTER, DT_SINGLELINE,
                    DT_END_ELLIPSIS, DT_NOPREFIX)

# 图像列表：必须声明完整原型。
# 之前这里每行都 `ctypes.WinDLL("comctl32")` 重新绑定且不带 argtypes，
# 于是 64 位 HIMAGELIST 被 ctypes 当成 c_int 截断成 32 位；句柄一失效，
# ImageList_Draw 就会写坏内存，表现为随后在完全无关的调用（如 DrawTextW）
# 里随机崩溃。这里用模块级绑定 + 完整原型，一次搞定。
_comctl32 = ctypes.WinDLL("comctl32")
_comctl32.ImageList_Draw.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                     ctypes.c_int, ctypes.c_int, wt.UINT]
_comctl32.ImageList_Draw.restype = wt.BOOL

# 布局常量（96 DPI 下的 CSS px）
TITLEBAR_H = 46
TOOLBAR_H = 54
STATUSBAR_H = 28
PAD = 14
LOGO = 26
WINBTN_W, WINBTN_H = 34, 30
BTN_H = 34
BTN_R = 11
ROW_H = 46
ICON_SZ = 20
BADGE_W = 68          # 置顶徽章宽
BADGE_H = 22          # 置顶徽章高
MENU_W = 220
MENU_ITEM_H = 30
MENU_SEP_H = 10
MENU_PAD = 5


def _rc(l, t, r, b):
    return RECT(int(l), int(t), int(r), int(b))


def _inside(x, y, rc):
    return rc.left <= x < rc.right and rc.top <= y < rc.bottom


class UI:
    def __init__(self, app):
        self.app = app
        self.aurora = Aurora()
        self.hits = []              # [(kind, RECT, payload)]
        self.menu_hits = []         # [(item_index, RECT)]

    # ------------------------------------------------------------ 主题
    def pal(self):
        return T.palette(self.app.g['dark'])

    def apply_theme(self):
        p = self.pal()
        self.aurora.set_colors(p['glow'], p['glow_base'])

    # ------------------------------------------------------------ 布局
    def layout(self, w, h):
        g = self.app.g
        sc = self.app.sc

        tb_h = sc(TITLEBAR_H)
        toolbar_h = sc(TOOLBAR_H)
        status_h = sc(STATUSBAR_H)
        pad = sc(PAD)
        bw, bh = sc(WINBTN_W), sc(WINBTN_H)

        L = {'w': w, 'h': h, 'pad': pad, 'titlebar_h': tb_h,
             'toolbar_h': toolbar_h, 'statusbar_h': status_h}

        # —— 标题栏 ——
        L['titlebar'] = _rc(0, 0, w, tb_h)
        lg = sc(LOGO)
        L['logo'] = _rc(pad, (tb_h - lg) // 2, pad + lg, (tb_h - lg) // 2 + lg)
        bx = L['logo'].right + sc(10)
        L['brand'] = _rc(bx, sc(6), bx + sc(260), sc(6) + sc(18))
        L['brand_sub'] = _rc(bx, sc(24), bx + sc(300), sc(24) + sc(16))

        # 窗口按钮（最右）
        rx = w - sc(6)
        L['close'] = _rc(rx - bw, (tb_h - bh) // 2, rx, (tb_h - bh) // 2 + bh)
        rx = L['close'].left - sc(2)
        L['max'] = _rc(rx - bw, L['close'].top, rx, L['close'].bottom)
        rx = L['max'].left - sc(2)
        L['min'] = _rc(rx - bw, L['close'].top, rx, L['close'].bottom)
        # 工具按钮（窗口按钮左侧）
        rx = L['min'].left - sc(8)
        L['menu_btn'] = _rc(rx - bw, L['close'].top, rx, L['close'].bottom)
        rx = L['menu_btn'].left - sc(2)
        L['theme_btn'] = _rc(rx - bw, L['close'].top, rx, L['close'].bottom)

        # —— 工具栏 ——
        ty = tb_h
        L['toolbar'] = _rc(0, ty, w, ty + toolbar_h)
        by = ty + (toolbar_h - sc(BTN_H)) // 2
        x = pad
        L['btn_toggle'] = _rc(x, by, x + sc(132), by + sc(BTN_H))
        x = L['btn_toggle'].right + sc(8)
        L['btn_refresh'] = _rc(x, by, x + sc(88), by + sc(BTN_H))
        x = L['btn_refresh'].right + sc(8)
        L['btn_clear'] = _rc(x, by, x + sc(114), by + sc(BTN_H))
        # 搜索框靠右；窄窗口时收缩，保证不与按钮重叠
        sw = sc(232)
        sx = w - pad - sw
        min_sx = L['btn_clear'].right + sc(10)
        if sx < min_sx:
            sx = min_sx
            sw = max(sc(110), w - pad - sx)
        L['search'] = _rc(sx, by, sx + sw, by + sc(BTN_H))
        L['search_edit'] = _rc(sx + sc(34), by + sc(1), sx + sw - sc(10),
                              by + sc(BTN_H) - sc(1))

        # —— 面板（列表卡片）——
        py = ty + toolbar_h + sc(12)
        foot_y = h - status_h
        list_h = max(sc(110), foot_y - py - sc(14))
        L['list'] = _rc(pad, py, w - pad, py + list_h)
        head_h = sc(34)
        L['list_head'] = _rc(L['list'].left, L['list'].top,
                             L['list'].right, L['list'].top + head_h)
        L['list_inner'] = _rc(L['list'].left + sc(1),
                              L['list'].top + head_h + sc(1),
                              L['list'].right - sc(1),
                              L['list'].bottom - sc(1))
        L['row_h'] = sc(ROW_H)
        L['list_h'] = L['list_inner'].bottom - L['list_inner'].top

        # —— 状态栏 ——
        L['statusbar'] = _rc(0, foot_y, w, h)
        L['status_left'] = _rc(pad, foot_y, w // 2, h)
        L['status_right'] = _rc(w // 2, foot_y, w - pad, h)

        g['layout'] = L
        self._build_hits(L)
        self._layout_menu(L)
        self.app.clamp_scroll()
        return L

    def _layout_menu(self, L):
        g = self.app.g
        sc = self.app.sc
        self.menu_hits = []
        if not g.get('menu_open'):
            L['menu'] = None
            return
        items = self.menu_items()
        w = sc(MENU_W)
        pad = sc(MENU_PAD)
        body = sum(sc(MENU_SEP_H) if it.get('sep') else sc(MENU_ITEM_H)
                   for it in items)
        h = body + pad * 2
        x = max(sc(6), min(L['menu_btn'].right - w, L['w'] - w - sc(6)))
        y = L['titlebar'].bottom + sc(6)
        L['menu'] = _rc(x, y, x + w, y + h)

        cy = y + pad
        for i, it in enumerate(items):
            ih = sc(MENU_SEP_H) if it.get('sep') else sc(MENU_ITEM_H)
            if not it.get('sep'):
                self.menu_hits.append(
                    (i, _rc(x + pad, cy, x + w - pad, cy + ih)))
            cy += ih

    def _build_hits(self, L):
        A = self.app
        self.hits = [
            (A.HIT_CLOSE, L['close'], None),
            (A.HIT_MAX, L['max'], None),
            (A.HIT_MIN, L['min'], None),
            (A.HIT_MENUBTN, L['menu_btn'], None),
            (A.HIT_THEME, L['theme_btn'], None),
            (A.HIT_TOGGLE, L['btn_toggle'], None),
            (A.HIT_REFRESH, L['btn_refresh'], None),
            (A.HIT_CLEAR, L['btn_clear'], None),
            (A.HIT_SCROLL, L['list_inner'], None),
        ]

    # ------------------------------------------------------------ 菜单模型
    def menu_items(self):
        g = self.app.g
        return [
            {'id': 'autostart', 'icon': T.ICO_POWER, 'text': '开机自启',
             'switch': g['autostart']},
            {'id': 'autotray', 'icon': T.ICO_MIN, 'text': '置顶后转入后台',
             'switch': g['autotray']},
            {'sep': True},
            {'id': 'theme',
             'icon': T.ICO_MOON if g['dark'] else T.ICO_SUN,
             'text': '浅色主题' if g['dark'] else '深色主题'},
            {'id': 'refresh', 'icon': T.ICO_REFRESH, 'text': '刷新列表'},
            {'id': 'clear', 'icon': T.ICO_CLEAR, 'text': '取消全部置顶'},
            {'sep': True},
            {'id': 'help', 'icon': T.ICO_CHECK, 'text': '快捷键说明',
             'note': 'Ctrl+Alt+T'},
            {'id': 'tray', 'icon': T.ICO_MIN, 'text': '收进托盘运行'},
            {'id': 'exit', 'icon': T.ICO_CLOSE, 'text': '退出'},
        ]

    # ------------------------------------------------------------ 命中测试
    def hit_test(self, x, y):
        if self.app.g.get('menu_open'):
            for idx, rc in self.menu_hits:
                if _inside(x, y, rc):
                    return self.app.HIT_MENU, idx, rc
            return self.app.HIT_MENUCANCEL, None, None
        for kind, rc, payload in self.hits:
            if _inside(x, y, rc):
                return kind, payload, rc
        return self.app.HIT_NONE, None, None

    def row_at(self, y):
        g = self.app.g
        L = g['layout']
        inner = L['list_inner']
        if not (inner.top <= y < inner.bottom):
            return -1
        idx = (y - inner.top + g['scroll']) // L['row_h']
        return idx if 0 <= idx < len(g['rows']) else -1

    # ------------------------------------------------------------ 绘制入口
    def paint(self, cv, w, h):
        g = self.app.g
        p = self.pal()
        L = g['layout']
        t = time.time() - g['t0']

        self.aurora.render(cv.hdc, w, h, w=88, h=60, t=t)
        self._app_border(cv, L, p)
        self._titlebar(cv, L, p)
        self._toolbar(cv, L, p)
        self._list(cv, L, p)
        self._statusbar(cv, L, p)
        self._menu(cv, L, p)

    def _hline(self, cv, x1, x2, y, c):
        cv.blend_rect(_rc(x1, y, x2, y + 1), c[0], c[1])

    def _app_border(self, cv, L, p):
        c = p['app_border']
        w, h = L['w'], L['h']
        cv.blend_rect(_rc(0, 0, w, 1), c[0], c[1])
        cv.blend_rect(_rc(0, h - 1, w, h), c[0], c[1])
        cv.blend_rect(_rc(0, 0, 1, h), c[0], c[1])
        cv.blend_rect(_rc(w - 1, 0, w, h), c[0], c[1])

    # ---------------------------------------------------- 标题栏
    def _titlebar(self, cv, L, p):
        g = self.app.g
        sc = self.app.sc
        F = g['font_cache']
        rc = L['titlebar']

        c = p['titlebar']
        cv.blend_rect(rc, c[0], c[1])
        self._hline(cv, 0, L['w'], rc.bottom - 1, p['stroke'])

        lg = L['logo']
        grad_round(cv.hdc, lg, p['brand'], p['brand_2'], sc(8))
        text(cv.hdc, F['icon'], rgb(255, 255, 255), lg.left, lg.top,
             lg.right - lg.left, lg.bottom - lg.top, T.ICO_PIN,
             DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)

        text(cv.hdc, F['brand'], p['fg'], L['brand'].left, L['brand'].top,
             L['brand'].right - L['brand'].left,
             L['brand'].bottom - L['brand'].top, "窗口置顶")
        text(cv.hdc, F['brand_sub'], p['fg_mute'], L['brand_sub'].left,
             L['brand_sub'].top, L['brand_sub'].right - L['brand_sub'].left,
             L['brand_sub'].bottom - L['brand_sub'].top, "把任意窗口钉在最上层")

        self._winbtn(cv, L['menu_btn'], T.ICO_MENU, self.app.HIT_MENUBTN, p,
                     active=g.get('menu_open'))
        self._winbtn(cv, L['theme_btn'],
                     T.ICO_MOON if g['dark'] else T.ICO_SUN,
                     self.app.HIT_THEME, p)
        self._winbtn(cv, L['min'], T.ICO_MIN, self.app.HIT_MIN, p)
        self._winbtn(cv, L['max'],
                     T.ICO_RESTORE if g.get('maximized') else T.ICO_MAX,
                     self.app.HIT_MAX, p)
        self._winbtn(cv, L['close'], T.ICO_CLOSE, self.app.HIT_CLOSE, p,
                     danger=True)

    def _winbtn(self, cv, rc, ico, kind, p, danger=False, active=False):
        g = self.app.g
        sc = self.app.sc
        hot = (g['hover'] == kind) or active
        rad = sc(T.R_XS)
        if hot:
            c = p['danger'] if danger else p['panel_3'][0]
            a = 230 if danger else p['panel_3'][1]
            cv.blend_round(rc, c, rad, a)
        col = rgb(255, 255, 255) if (hot and danger) else \
            (p['fg'] if hot else p['fg_dim'])
        text(cv.hdc, g['font_cache']['icon_md'], col, rc.left, rc.top,
             rc.right - rc.left, rc.bottom - rc.top, ico,
             DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)

    # ---------------------------------------------------- 工具栏
    def _toolbar(self, cv, L, p):
        g = self.app.g
        F = g['font_cache']
        rc = L['toolbar']
        c = p['toolbar']
        cv.blend_rect(rc, c[0], c[1])
        self._hline(cv, 0, L['w'], rc.bottom - 1, p['stroke'])

        sel = self.app.selected_row()
        is_on = bool(sel and sel[4])

        b = L['btn_toggle']
        hot = g['hover'] == self.app.HIT_TOGGLE
        press = g['press'] == self.app.HIT_TOGGLE
        c1 = lighten(p['brand'], 0.10 if hot else 0.0)
        c2 = lighten(p['brand_2'], 0.10 if hot else 0.0)
        if press:
            c1, c2 = darken(c1, 0.10), darken(c2, 0.10)
        self._button(cv, b, p, primary=True,
                     icon=T.ICO_UNPIN if is_on else T.ICO_PIN,
                     label="取消置顶" if is_on else "置顶窗口", c1=c1, c2=c2)

        self._button(cv, L['btn_refresh'], p, icon=T.ICO_REFRESH, label="刷新",
                     hover=g['hover'] == self.app.HIT_REFRESH)
        self._button(cv, L['btn_clear'], p, icon=T.ICO_CLEAR, label="取消全部",
                     hover=g['hover'] == self.app.HIT_CLEAR,
                     enabled=any(r[4] for r in g['rows']))
        self._search(cv, L, p)

    def _button(self, cv, rc, p, primary=False, hover=False, c1=None, c2=None,
                icon=None, label="", enabled=True):
        g = self.app.g
        sc = self.app.sc
        F = g['font_cache']
        rad = sc(BTN_R)

        if primary and enabled:
            grad_round(cv.hdc, rc, c1 or p['brand'], c2 or p['brand_2'], rad)
            fg = p['on_brand']
        else:
            fill = p['panel_2'] if (hover and enabled) else p['panel']
            edge = p['stroke_2'] if (hover and enabled) else p['stroke']
            if not enabled:
                fill = (fill[0], max(8, fill[1] // 2))
                edge = (edge[0], max(8, edge[1] // 2))
            cv.panel(rc, rad, fill, edge)
            fg = p['fg'] if enabled else p['fg_mute']

        iw = sc(15)
        tw = measure(cv.hdc, F['btn'], label)[0] if label else 0
        gap = sc(7) if (icon and label) else 0
        total = (iw if icon else 0) + gap + tw
        x = rc.left + (rc.right - rc.left - total) // 2
        if icon:
            text(cv.hdc, F['icon'], fg, x, rc.top, iw, rc.bottom - rc.top,
                 icon, DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
            x += iw + gap
        if label:
            text(cv.hdc, F['btn'], fg, x, rc.top, tw + sc(4),
                 rc.bottom - rc.top, label)

    def _search(self, cv, L, p):
        g = self.app.g
        sc = self.app.sc
        F = g['font_cache']
        rc = L['search']
        cv.panel(rc, sc(BTN_R), p['field'], p['stroke'])
        text(cv.hdc, F['icon_sm'], p['fg_mute'], rc.left + sc(11), rc.top,
             sc(20), rc.bottom - rc.top, T.ICO_SEARCH,
             DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
        if not g['filter']:
            e = L['search_edit']
            text(cv.hdc, F['body'], p['fg_mute'], e.left, rc.top,
                 e.right - e.left, rc.bottom - rc.top, "搜索窗口…")

    # ---------------------------------------------------- 列表
    def _list(self, cv, L, p):
        g = self.app.g
        sc = self.app.sc
        F = g['font_cache']
        rc = L['list']

        cv.panel(rc, sc(T.R_LG), p['panel'], p['stroke'])

        head = L['list_head']
        text(cv.hdc, F['body_sb'], p['fg'], head.left + sc(14), head.top,
             sc(220), head.bottom - head.top, "窗口列表")
        total = len(g['rows'])
        pinned = sum(1 for r in g['rows'] if r[4])
        right = "%d 个窗口" % total
        if pinned:
            right += " · %d 个已置顶" % pinned
        text(cv.hdc, F['status'], p['fg_mute'], head.left, head.top,
             head.right - head.left - sc(14), head.bottom - head.top, right,
             DT_RIGHT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
        self._hline(cv, rc.left + sc(1), rc.right - sc(1), head.bottom,
                    p['row_line'])

        inner = L['list_inner']
        if total == 0:
            self._empty(cv, inner, p)
            return

        rh = L['row_h']
        saved = gdi32.SaveDC(ctypes.c_void_p(cv.hdc))
        gdi32.IntersectClipRect(ctypes.c_void_p(cv.hdc), inner.left, inner.top,
                                inner.right, inner.bottom)
        first = max(0, g['scroll'] // rh)
        last = min(total, (g['scroll'] + (inner.bottom - inner.top)) // rh + 1)
        for i in range(first, last):
            y = inner.top + i * rh - g['scroll']
            self._row(cv, _rc(inner.left + sc(6), y + sc(2),
                              inner.right - sc(6), y + rh - sc(2)), i, p)
        if saved:
            gdi32.RestoreDC(ctypes.c_void_p(cv.hdc), saved)
        self._scrollbar(cv, L, p)

    def _row(self, cv, rc, idx, p):
        g = self.app.g
        sc = self.app.sc
        F = g['font_cache']
        hwnd, title, exe, path, top = g['rows'][idx]
        sel = (idx == g['sel'])
        hot = (idx == g['hover_row'])
        rad = sc(T.R_SM)

        if sel:
            c = p['brand_soft']
            cv.blend_round(rc, c[0], rad, c[1])
            bar = _rc(rc.left + sc(1), rc.top + sc(8), rc.left + sc(3),
                      rc.bottom - sc(8))
            fill_round(cv.hdc, bar, p['sel_line'], sc(1))
        elif hot:
            c = p['panel_3']
            cv.blend_round(rc, c[0], rad, c[1])

        cy = (rc.top + rc.bottom) // 2
        isz = sc(ICON_SZ)
        ix = rc.left + sc(10)
        iy = cy - isz // 2
        iidx = g['icon_cache'].get(path, -1)
        if iidx >= 0 and g['himl']:
            _comctl32.ImageList_Draw(g['himl'], iidx,
                                     ctypes.c_void_p(cv.hdc), ix, iy, 0)
        else:
            ellipse(cv.hdc, ix + isz // 2, cy, isz // 2 - sc(2),
                    isz // 2 - sc(2), mix(p['brand'], p['fg_mute'], 0.5))

        tx = ix + isz + sc(12)
        # 已置顶的行右侧要放「图钉 + 置顶」徽章，标题/进程名给它让出宽度
        rp = sc(BADGE_W + 18) if top else sc(6)
        text(cv.hdc, F['row_sb'] if (sel or top) else F['row'],
             p['fg'] if not sel else rgb(255, 255, 255),
             tx, rc.top + sc(4), rc.right - tx - rp, sc(19), title,
             DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS |
             DT_NOPREFIX)
        text(cv.hdc, F['row_sub'], p['fg_mute'], tx, rc.top + sc(23),
             rc.right - tx - rp, sc(15), exe,
             DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS |
             DT_NOPREFIX)

        if top:
            # ---- 置顶标识：图钉 + 「置顶」胶囊徽章 ----
            # 之前只画了一个 13px 的图钉字形，太细太淡，几乎看不见；
            # 改成带品牌色底与描边的徽章，右对齐，一眼可辨。
            bh = sc(BADGE_H)
            bx = rc.right - sc(10) - sc(BADGE_W)
            by = cy - bh // 2
            br = _rc(bx, by, bx + sc(BADGE_W), by + bh)
            cv.panel(br, sc(7),
                     (p['brand'], 44),            # 底色：品牌色淡填充
                     (p['brand'], 104))           # 1px 品牌色描边
            text(cv.hdc, F['icon_md'], p['brand'],
                 bx + sc(7), by, sc(17), bh, T.ICO_PIN,
                 DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
            text(cv.hdc, F['status_sb'], p['brand'],
                 bx + sc(26), by, sc(BADGE_W) - sc(32), bh, "置顶",
                 DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)

    def _empty(self, cv, inner, p):
        g = self.app.g
        sc = self.app.sc
        cx = (inner.left + inner.right) // 2
        cy = (inner.top + inner.bottom) // 2 - sc(10)
        ellipse(cv.hdc, cx, cy, sc(26), sc(26), p['panel_3'][0])
        text(cv.hdc, g['font_cache']['icon_lg'], p['fg_mute'],
             cx - sc(24), cy - sc(24), sc(48), sc(48), T.ICO_SEARCH,
             DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
        msg = "没有匹配的窗口" if g['filter'] else "暂无可置顶的窗口"
        text(cv.hdc, g['font_cache']['body'], p['fg_dim'],
             cx - sc(160), cy + sc(36), sc(320), sc(20), msg,
             DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)
        text(cv.hdc, g['font_cache']['status'], p['fg_mute'],
             cx - sc(200), cy + sc(56), sc(400), sc(18), "双击列表项即可置顶 / 取消",
             DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)

    def _scrollbar(self, cv, L, p):
        g = self.app.g
        sc = self.app.sc
        if g['scroll_max'] <= 0:
            return
        inner = L['list_inner']
        track = inner.bottom - inner.top
        ratio = track / float(max(1, len(g['rows']) * L['row_h']))
        th = max(sc(30), int(track * ratio))
        frac = g['scroll'] / float(g['scroll_max'])
        ty = inner.top + int((track - th) * frac)
        tr = _rc(inner.right - sc(10), ty, inner.right - sc(5), ty + th)
        # fg_mute 是实色（非透明元组），滚动条单独给个半透明
        cv.blend_round(tr, p['fg_mute'], (tr.right - tr.left) // 2, 140)

    # ---------------------------------------------------- 状态栏
    def _statusbar(self, cv, L, p):
        g = self.app.g
        F = g['font_cache']
        rc = L['statusbar']
        c = p['statusbar']
        cv.blend_rect(rc, c[0], c[1])
        self._hline(cv, 0, L['w'], rc.top, p['stroke'])

        hint = g['hint'] or "双击列表项或按 Ctrl+Alt+T 切换置顶"
        sl = L['status_left']
        text(cv.hdc, F['status'], p['fg_mute'], sl.left, sl.top,
             sl.right - sl.left, sl.bottom - sl.top, hint,
             DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS |
             DT_NOPREFIX)
        sr = L['status_right']
        text(cv.hdc, F['status_sb'], p['fg_dim'], sr.left, sr.top,
             sr.right - sr.left, sr.bottom - sr.top,
             "%d 个窗口" % len(g['rows']),
             DT_RIGHT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)

    # ---------------------------------------------------- 菜单（浮层）
    def _menu(self, cv, L, p):
        g = self.app.g
        sc = self.app.sc
        F = g['font_cache']
        rc = L.get('menu')
        if not rc:
            return

        cv.panel(rc, sc(T.R_MD), p['menu'], p['stroke_2'])

        items = self.menu_items()
        for idx, irc in self.menu_hits:
            it = items[idx]
            hot = (g['hover'] == self.app.HIT_MENU and
                   g.get('hover_menu') == idx)
            if hot:
                c = p['brand_soft']
                cv.blend_round(irc, c[0], sc(T.R_SM), c[1])
            fg = p['fg'] if hot else p['fg_dim']
            icon_col = p['brand_2'] if hot else p['fg_mute']

            ix = irc.left + sc(10)
            text(cv.hdc, F['icon_sm'], icon_col, ix, irc.top, sc(16),
                 irc.bottom - irc.top, it['icon'],
                 DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)

            rw = 0
            if 'switch' in it:
                rw = sc(34 + 12)
            elif it.get('note'):
                rw = measure(cv.hdc, F['status'], it['note'])[0] + sc(12)
            text(cv.hdc, F['menu'], fg, ix + sc(26), irc.top,
                 irc.right - ix - sc(26) - rw, irc.bottom - irc.top,
                 it['text'],
                 DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS |
                 DT_NOPREFIX)

            if 'switch' in it:
                self._switch(cv, irc, bool(it['switch']), p)
            elif it.get('note'):
                text(cv.hdc, F['status'], p['fg_mute'], irc.left, irc.top,
                     irc.right - sc(10), irc.bottom - irc.top, it['note'],
                     DT_RIGHT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX)

        cy = rc.top + sc(MENU_PAD)
        for it in items:
            ih = sc(MENU_SEP_H) if it.get('sep') else sc(MENU_ITEM_H)
            if it.get('sep'):
                self._hline(cv, rc.left + sc(8), rc.right - sc(8),
                            cy + ih // 2, p['stroke'])
            cy += ih

    def _switch(self, cv, item_rc, on, p):
        """菜单项右侧开关（对齐 CSS .switch：34x19，启用态用主题渐变）。"""
        sc = self.app.sc
        tw, th = sc(34), sc(19)
        top = item_rc.top + (item_rc.bottom - item_rc.top - th) // 2
        tr = _rc(item_rc.right - sc(10) - tw, top, item_rc.right - sc(10),
                 top + th)
        rad = th // 2
        if on:
            grad_round(cv.hdc, tr, p['brand'], p['brand_2'], rad)
        else:
            c = p['panel_3']
            cv.blend_round(tr, c[0], rad, max(46, c[1]))
        kr = rad - sc(2)
        kx = tr.right - rad if on else tr.left + rad
        ky = (tr.top + tr.bottom) // 2
        ellipse(cv.hdc, kx, ky, kr, kr, rgb(255, 255, 255))
