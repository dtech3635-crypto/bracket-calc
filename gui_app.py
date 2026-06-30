"""
沓座拡幅型 落橋防止装置ブラケット 構造計算
Tkinter デスクトップアプリ v3 ― 4面図レイアウト
"""

import math
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from bracket_calc import (
    BracketInput, get_allowable_stress, calc_load,
    check_bracket, check_anchor, judge, BracketResult,
)

# ===========================================================================
# ユーティリティ
# ===========================================================================

def ms(m: float) -> str:
    return "∞" if m == float("inf") else f"{m:.3f}"


# ===========================================================================
# 描画ヘルパー
# ===========================================================================

STEEL_TOP  = "#7bafd4"   # 天板・ベースPL
STEEL_RIB  = "#e0a040"   # リブ
STEEL_BOT  = "#7bafd4"   # 下版（同色系）
STEEL_LINE = "#1a3a5c"   # 輪郭線色


def _plate(c, x1, y1, x2, y2, fill=STEEL_TOP, outline=STEEL_LINE, lw=1.5):
    """ソリッド鋼板（線形ハッチなし）"""
    c.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=lw)


def _dim_h(c, x1, x2, y, label, gap=14):
    c.create_line(x1, y, x2, y, fill="#555", width=1, arrow=tk.BOTH)
    c.create_line(x1, y - 4, x1, y + 4, fill="#555", width=1)
    c.create_line(x2, y - 4, x2, y + 4, fill="#555", width=1)
    c.create_text((x1+x2)/2, y + gap, text=label, font=("Arial", 7), fill="#444")


def _dim_v(c, x, y1, y2, label, gap=14):
    c.create_line(x, y1, x, y2, fill="#555", width=1, arrow=tk.BOTH)
    c.create_line(x - 4, y1, x + 4, y1, fill="#555", width=1)
    c.create_line(x - 4, y2, x + 4, y2, fill="#555", width=1)
    c.create_text(x + gap + 10, (y1+y2)/2, text=label, font=("Arial", 7), fill="#444")


def _title(c, cw, text):
    c.create_text(cw/2, 11, text=text, font=("Arial", 9, "bold"), fill="#222")


def _anchor_cross(c, cx, cy, r, color="#993300"):
    """アンカー穴記号：⊕（円＋十字）"""
    c.create_oval(cx-r, cy-r, cx+r, cy+r, fill="white", outline=color, width=1.2)
    c.create_line(cx-r, cy, cx+r, cy, fill=color, width=1.0)
    c.create_line(cx, cy-r, cx, cy+r, fill=color, width=1.0)


# ===========================================================================
# 側面図（橋軸直角方向から見た側面）
# ===========================================================================

import math as _math

# ---------------------------------------------------------------------------
# 共通ヘルパー
# ---------------------------------------------------------------------------

def _poly(c, pts, fill, outline=STEEL_LINE, lw=1.5):
    flat = [v for p in pts for v in p]
    c.create_polygon(flat, fill=fill, outline=outline, width=lw, smooth=False)


def _rib_geom(inp):
    """リブの上・下のリーチ長を返す (mm)"""
    L_bot = inp.L_b_bot if inp.L_b_bot > 0 else inp.L_b
    L_rib_top = max(inp.L_b  - inp.chiri_top, 5.0)
    L_rib_bot = max(L_bot    - inp.chiri_bot, 5.0)
    return L_bot, L_rib_top, L_rib_bot


def draw_side(cv, inp: BracketInput):
    """
    側面図
    リブは台形（6角形）：壁側2コーナーにスカラップ、先端は斜辺（chiri差）。
    6角形の頂点：
      1(壁・天板下端+sc), 2(壁+sc・天板下端),
      3(Lrt・天板下端), 4(Lrb・下版上端),
      5(壁+sc・下版上端), 6(壁・下版上端-sc)
    """
    cv.delete("all")
    cw, ch = cv.winfo_width(), cv.winfo_height()
    if cw < 20 or ch < 20: return

    rh     = inp.h_rib if inp.has_rib else 0
    tb     = inp.t_bot
    T      = inp.t_pl
    H_tot  = T + rh + tb
    L_bot, L_rib_top, L_rib_bot = _rib_geom(inp)
    L_max  = max(inp.L_b, L_bot)

    pw = 42
    ml, mr, mt, mb = pw+16, 88, 52, 46
    sx = (cw - ml - mr) / max(L_max, 1)
    sy = (ch - mt - mb) / max(H_tot, 1)
    s  = min(sx, sy, 2.4)

    L_px   = inp.L_b * s
    Lb_px  = L_bot * s
    Lrt_px = L_rib_top * s
    Lrb_px = L_rib_bot * s
    T_px   = max(T * s, 5)
    rh_px  = max(rh * s, 0)
    tb_px  = max(tb * s, 5) if tb > 0 else 0
    bp_px  = max(T * s, 5)

    x0  = ml + pw           # ベースPL 左端
    xbp = x0 + bp_px        # ベースPL 右端 = フランジ起点
    yt  = mt                 # 天板上端
    ytb = yt + T_px          # 天板下端 = リブ上端
    yrb = ytb + rh_px        # リブ下端 = 下版上端
    ybb = yrb + tb_px        # 下版下端

    # 橋脚
    cv.create_rectangle(x0-pw, yt-10, x0, ybb+10,
                        fill="#c8c8c8", outline="#777", width=1.5)
    cv.create_text(x0-pw/2, (yt+ybb)/2, text="橋脚\n躯体",
                   font=("Arial", 7), fill="#555")

    # ベースプレート
    _plate(cv, x0, yt, xbp, ybb, fill=STEEL_TOP)

    # 天板（上フランジ）
    _plate(cv, xbp, yt, xbp+L_px, ytb, fill=STEEL_TOP)
    cv.create_text((xbp + xbp+L_px)/2, (yt+ytb)/2,
                   text=f"天板 t={T:.0f}", font=("Arial", 7), fill=STEEL_LINE)

    # 下版（下フランジ）
    if tb > 0:
        _plate(cv, xbp, yrb, xbp+Lb_px, ybb, fill=STEEL_BOT)
        cv.create_text((xbp + xbp+Lb_px)/2, (yrb+ybb)/2,
                       text=f"下版 t={tb:.0f}", font=("Arial", 7), fill=STEEL_LINE)

    # リブ（台形4角形：スカラップなし）
    if inp.has_rib and rh_px > 0:
        n = max(1, inp.n_rib)
        rib_pts = [
            (xbp,          ytb),   # TL: 壁側・天板下端
            (xbp + Lrt_px, ytb),   # TR: 上ちり先端
            (xbp + Lrb_px, yrb),   # BR: 下ちり先端
            (xbp,          yrb),   # BL: 壁側・下版上端
        ]
        _poly(cv, rib_pts, fill=STEEL_RIB, outline="#aa6600", lw=1.5)
        label_x = xbp + min(Lrt_px, Lrb_px) * 0.35
        cv.create_text(label_x, (ytb+yrb)/2,
                       text=f"リブ {n}枚\nt={inp.t_rib:.0f}mm",
                       font=("Arial", 7), fill="#5a3000")
        if L_px - Lrt_px > 3:
            _dim_h(cv, xbp+Lrt_px, xbp+L_px, ytb-14,
                   f"上ちり={inp.chiri_top:.0f}mm")
        if Lb_px - Lrb_px > 3:
            _dim_h(cv, xbp+Lrb_px, xbp+Lb_px, yrb+12,
                   f"下ちり={inp.chiri_bot:.0f}mm")

    # アンカー（水平破線）ピッチ基準で配置
    rows = max(inp.anchor_rows, 1)
    total_v = inp.anchor_pitch_v * (rows - 1)
    ay0 = (yt + ybb) / 2 - total_v * s / 2
    for i in range(rows):
        ay = ay0 + i * inp.anchor_pitch_v * s
        cv.create_line(x0-pw+4, ay, xbp, ay,
                       fill="#993300", width=1.2, dash=(5, 3))
    cv.create_text(x0-pw+2, (yt+ybb)/2,
                   text=f"アンカー\nφ{inp.d_anchor:.0f}\n{inp.anchor_cols}×{inp.anchor_rows}",
                   font=("Arial", 7), fill="#993300", anchor="w")

    # 荷重矢印
    V      = inp.W / max(inp.N, 1)
    H_load = inp.Kh * V
    lx = xbp + L_px * 0.5
    # 鉛直力（下向き）
    cv.create_line(lx, yt-36, lx, yt, fill="#c0392b", width=2.5, arrow=tk.LAST)
    cv.create_text(lx+3, yt-38, text=f"V={V:.1f}kN", anchor="sw",
                   font=("Arial", 8, "bold"), fill="#c0392b")
    # 水平力（横向き→ 先端方向）
    hy = yt + T_px + rh_px * 0.5
    cv.create_line(xbp-36, hy, xbp, hy, fill="#2471a3", width=2.5, arrow=tk.LAST)
    cv.create_text(xbp-38, hy-2, text=f"H={H_load:.1f}kN", anchor="se",
                   font=("Arial", 8, "bold"), fill="#2471a3")

    # 寸法
    dv_x = xbp + max(L_px, Lb_px) + 16
    _dim_h(cv, xbp, xbp+L_px, ybb+22, f"L_b={inp.L_b:.0f}mm")
    if tb > 0 and abs(Lb_px - L_px) > 2:
        _dim_h(cv, xbp, xbp+Lb_px, ybb+38, f"L_bot={L_bot:.0f}mm")
    _dim_v(cv, dv_x, yt,  ytb, f"t={T:.0f}")
    if rh_px > 0:
        _dim_v(cv, dv_x, ytb, yrb, f"h={rh:.0f}")
    if tb > 0:
        _dim_v(cv, dv_x, yrb, ybb, f"t={tb:.0f}")

    _title(cv, cw, "【側面図】")


# ===========================================================================
# 正面図
# ===========================================================================

def draw_front(cv, inp: BracketInput):
    """
    正面図（橋脚壁面に正対した図）
    ベースプレートを正面に。天板・下版が手前（奥行き）に突出。
    リブは n 枚がベースPL面上に表示。アンカー⊕。
    """
    cv.delete("all")
    cw, ch = cv.winfo_width(), cv.winfo_height()
    if cw < 20 or ch < 20: return

    rh   = inp.h_rib if inp.has_rib else 0
    tb   = inp.t_bot
    T    = inp.t_pl
    H    = T + rh + tb

    ml, mr, mt, mb = 14, 72, 52, 42
    sx = (cw - ml - mr) / max(inp.b_pl + 20, 1)
    sy = (ch - mt - mb) * 0.75 / max(H, 1)
    s  = min(sx, sy, 2.4)

    B_px  = inp.b_pl * s
    T_px  = max(T * s, 5)
    rh_px = max(rh * s, 0)
    tb_px = max(tb * s, 5) if tb > 0 else 0
    rt_px = max(inp.t_rib * s, 3) if inp.has_rib else 0
    H_px  = T_px + rh_px + tb_px

    cx    = ml + B_px/2
    oy    = mt
    rib_y0 = oy + T_px
    bot_y  = rib_y0 + rh_px
    bp_bot = bot_y + tb_px
    left, right = cx - B_px/2, cx + B_px/2

    # ベースプレート（ベース）
    _plate(cv, left, oy, right, bp_bot, fill=STEEL_TOP)

    # 天板帯（ベースPL上端から T_px 幅のバンド）
    _plate(cv, left, oy, right, oy + T_px, fill=STEEL_TOP, outline=STEEL_LINE)
    cv.create_text(cx, oy + T_px/2,
                   text=f"天板 t={T:.0f}", font=("Arial", 7), fill=STEEL_LINE)

    # 下版帯（ベースPL下端から tb_px 幅のバンド）
    if tb > 0:
        _plate(cv, left, bot_y, right, bp_bot, fill=STEEL_BOT, outline=STEEL_LINE)
        cv.create_text(cx, (bot_y + bp_bot)/2,
                       text=f"下版 t={tb:.0f}", font=("Arial", 7), fill=STEEL_LINE)

    # リブ（n 枚）：天板帯の下端から下版帯の上端まで
    if inp.has_rib and rh_px > 0:
        n = max(1, inp.n_rib)
        # 両端リブの外面をプレート端に合わせ、内側を等間隔で配置
        p_px = (B_px - rt_px) / max(n - 1, 1) if n > 1 else 0
        x0_rib = left   # 左端リブ外面 = プレート左端
        rxs = []
        for i in range(n):
            rx = x0_rib + p_px * i
            cv.create_rectangle(rx, rib_y0, rx + rt_px, bot_y,
                                 fill=STEEL_RIB, outline="#aa6600", width=1.4)
            rxs.append(rx + rt_px / 2)
        if n >= 2:
            p_mm = (inp.b_pl - inp.t_rib) / max(n - 1, 1)
            _dim_h(cv, rxs[0], rxs[1], bp_bot + 14, f"p={p_mm:.0f}mm")
        _dim_v(cv, right + 14, rib_y0, bot_y, f"h={rh:.0f}mm")

    # ベースPL全体ラベル
    cv.create_text(cx, oy + H_px*0.5,
                   text=f"ベースPL\nb={inp.b_pl:.0f}×H={H:.0f}",
                   font=("Arial", 7), fill=STEEL_LINE)

    # アンカー⊕ ピッチ基準で配置
    rows_a = max(inp.anchor_rows, 1)
    cols_a = max(inp.anchor_cols, 1)
    anc_r  = max(min(inp.d_anchor * s * 0.28, 10), 4)
    total_h_a = inp.anchor_pitch_h * (cols_a - 1) * s
    total_v_a = inp.anchor_pitch_v * (rows_a - 1) * s
    ax0 = cx - total_h_a / 2
    ay0 = oy + H_px / 2 - total_v_a / 2
    for ri in range(rows_a):
        for ci in range(cols_a):
            _anchor_cross(cv,
                          ax0 + ci * inp.anchor_pitch_h * s,
                          ay0 + ri * inp.anchor_pitch_v * s, anc_r)
    cv.create_text(right+18, oy+H_px/2,
                   text=f"⊕φ{inp.d_anchor:.0f}\n{cols_a}×{rows_a}本",
                   font=("Arial", 7), fill="#993300", anchor="w")

    # 荷重矢印
    V      = inp.W / max(inp.N, 1)
    H_load = inp.Kh * V
    # 鉛直力（下向き）
    cv.create_line(cx, oy-36, cx, oy, fill="#c0392b", width=2.5, arrow=tk.LAST)
    cv.create_text(cx+3, oy-38, text=f"V={V:.1f}kN", anchor="sw",
                   font=("Arial", 8, "bold"), fill="#c0392b")
    # 水平力（横向き→）
    hy = oy + T_px + rh_px * 0.5
    cv.create_line(left-36, hy, left, hy, fill="#2471a3", width=2.5, arrow=tk.LAST)
    cv.create_text(left-38, hy-2, text=f"H={H_load:.1f}kN", anchor="se",
                   font=("Arial", 8, "bold"), fill="#2471a3")

    _dim_h(cv, left, right, bp_bot+22, f"b={inp.b_pl:.0f}mm")
    _dim_v(cv, right+(52 if inp.has_rib else 22), oy, bp_bot, f"H={H:.0f}mm")
    _title(cv, cw, "【正面図】")


# ===========================================================================
# 平面図
# ===========================================================================

def draw_plan(cv, inp: BracketInput):
    """
    平面図（上から見た図）
    壁側を上端、先端を下方向に描く。
    リブは天板直下で溶接（天板・下版に接する）→ 隠れ線(破線)で表示。
    リブは各 X 位置に t_rib 幅 × L_rib_top 長の矩形（ベースPLから先端方向）。
    """
    cv.delete("all")
    cw, ch = cv.winfo_width(), cv.winfo_height()
    if cw < 20 or ch < 20: return

    L_bot, L_rib_top, L_rib_bot = _rib_geom(inp)
    L_max = max(inp.L_b, L_bot)

    ml, mr, mt, mb = 14, 68, 36, 50
    sx = (cw - ml - mr) / max(inp.b_pl, 1)
    sy = (ch - mt - mb) / max(L_max + inp.t_pl, 1)
    s  = min(sx, sy, 2.2)

    B_px   = inp.b_pl * s
    L_px   = inp.L_b  * s
    Lb_px  = L_bot    * s
    bp_px  = max(inp.t_pl * s, 5)
    rt_px  = max((inp.t_rib if inp.has_rib else inp.t_pl) * s, 3)
    Lrt_px = L_rib_top * s
    Lrb_px = L_rib_bot * s

    cx    = ml + B_px/2
    oy    = mt
    left, right = cx - B_px/2, cx + B_px/2
    y_fl  = oy + bp_px       # フランジ起点（ベースPL下端）

    # 橋脚壁
    cv.create_rectangle(left-8, oy-10, right+8, oy,
                        fill="#c8c8c8", outline="#777", width=1.5)
    cv.create_text(cx, oy-5, text="橋脚壁面",
                   font=("Arial", 7), fill="#555")

    # ベースプレート（断面）
    _plate(cv, left, oy, right, y_fl, fill=STEEL_TOP)
    cv.create_text(cx, oy+bp_px/2,
                   text="ベースPL", font=("Arial", 7), fill=STEEL_LINE)

    # 天板（上から見た矩形）
    _plate(cv, left, y_fl, right, y_fl+L_px,
           fill="#9bbcd8", outline=STEEL_LINE)
    cv.create_text(cx, y_fl+L_px/2,
                   text=f"天板\n{inp.b_pl:.0f}×{inp.L_b:.0f}mm",
                   font=("Arial", 8), fill=STEEL_LINE)

    # 下版（天板の下 = 同フットプリント、破線で範囲表示）
    if inp.t_bot > 0:
        cv.create_rectangle(left, y_fl, right, y_fl+Lb_px,
                             fill="", outline="#5577aa",
                             width=1.2, dash=(6, 3))
        if abs(Lb_px - L_px) > 4:
            cv.create_text(right+4, y_fl+Lb_px,
                           text=f"下版端\nL={L_bot:.0f}mm",
                           font=("Arial", 6), fill="#5577aa", anchor="w")

    # リブ（天板下に溶接。隠れ線として描画。幅方向のピッチで n 本）
    if inp.has_rib:
        n = max(1, inp.n_rib)
        p_px = (B_px - rt_px) / max(n - 1, 1) if n > 1 else 0
        x0_rib = left
        for i in range(n):
            rx = x0_rib + p_px * i
            # リブは天板下に溶接（ベースPLから Lrt_px まで）
            cv.create_rectangle(rx, y_fl, rx+rt_px, y_fl+Lrt_px,
                                 fill="#f0d090", outline="#cc8800",
                                 width=1.2, dash=(5, 3))
        # 上ちり線（天板先端からリブ上端まで）
        cv.create_line(left, y_fl+Lrt_px, right, y_fl+Lrt_px,
                       fill="#aa6600", dash=(4,3), width=1)
        cv.create_text(right+4, y_fl+Lrt_px,
                       text=f"上ちり={inp.chiri_top:.0f}mm",
                       font=("Arial", 6), fill="#aa6600", anchor="w")
        # 下ちり線
        if inp.t_bot > 0:
            cv.create_line(left, y_fl+Lrb_px, right, y_fl+Lrb_px,
                           fill="#557799", dash=(4,3), width=1)
            cv.create_text(right+4, y_fl+Lrb_px,
                           text=f"下ちり={inp.chiri_bot:.0f}mm",
                           font=("Arial", 6), fill="#557799", anchor="w")

    # 寸法
    _dim_h(cv, left, right, y_fl+L_px+28, f"b={inp.b_pl:.0f}mm")
    _dim_v(cv, right+32, y_fl, y_fl+L_px, f"L_b={inp.L_b:.0f}mm")

    _title(cv, cw, "【平面図】")


# ===========================================================================
# 3D アイソメ図
# ===========================================================================

def draw_3d(cv, inp: BracketInput):
    """
    3D アイソメ図
    座標系：
      X = ブラケット幅方向（0 → B = b_pl）  → 右下
      Y = 鉛直（0 = 下版下端、上向き）       → 上
      Z = 突出方向（0 = 壁面、大 = 先端）    → 左下
    リブ：台形断面（上端 Lr_top, 下端 Lr_bot で定義）
    """
    cv.delete("all")
    cw, ch = cv.winfo_width(), cv.winfo_height()
    if cw < 20 or ch < 20: return

    rh    = inp.h_rib if inp.has_rib else 0
    tb    = inp.t_bot
    T     = inp.t_pl
    H     = T + rh + tb
    B     = inp.b_pl
    L     = inp.L_b
    bp    = T                 # ベースPL厚
    L_bot, Lr_top, Lr_bot = _rib_geom(inp)

    ang    = _math.radians(30)
    cos30  = _math.cos(ang)
    sin30  = _math.sin(ang)
    Z_max  = bp + max(L, L_bot)   # 最大奥行き [mm]

    # アイソメ投影の全体寸法 [mm]
    proj_w_mm = (B + Z_max) * cos30
    proj_h_mm = H + (B + Z_max) * sin30

    pad = 48
    s = min((cw - pad) / max(proj_w_mm, 1),
            (ch - pad) / max(proj_h_mm, 1),
            1.8)

    # 原点 (X=0,Y=0,Z=0) = 左下前端 → iso(0,0,0) = (ox, oy)
    # 左端 iso(0,0,Z_max): ox - Z_max*cos30*s, oy + Z_max*sin30*s
    # 右端 iso(B,0,0):     ox + B*cos30*s,     oy + B*sin30*s
    # 上端 iso(0,H,0):     ox,                 oy - H*s
    # 描画の上端は oy - H*s, 下端は oy + (B+Z_max)*sin30*s
    # 描画の左端は ox - Z_max*cos30*s
    # 上マージン=pad/2, 左マージン=pad/2 + Z_max*cos30*s
    ox = pad/2 + Z_max * cos30 * s
    oy = pad/2 + H * s

    def iso(X, Y, Z):
        return (ox + (X - Z)*_math.cos(ang)*s,
                oy - Y*s + (X + Z)*_math.sin(ang)*s)

    def f4(p0,p1,p2,p3, fill, ol=STEEL_LINE):
        _poly(cv,[iso(*p0),iso(*p1),iso(*p2),iso(*p3)],fill,ol)

    def f3(p0,p1,p2, fill, ol=STEEL_LINE):
        _poly(cv,[iso(*p0),iso(*p1),iso(*p2)],fill,ol)

    # Painter's algorithm: 奥から順に描画
    # Y座標系: Y=0=下版下端, Y=tb=下版上端, Y=tb+rh=天板下端, Y=H=天板上端

    # ① ベースプレート（壁面 Z=0）
    f4((0,0,0),(B,0,0),(B,H,0),(0,H,0),  "#7bafd4")          # 正面
    f4((0,H,0),(B,H,0),(B,H,bp),(0,H,bp),"#9bbcd8")          # 上端面
    f4((B,0,0),(B,H,0),(B,H,bp),(B,0,bp),"#5a8ab0")          # 右面
    f4((0,0,0),(0,H,0),(0,H,bp),(0,0,bp),"#5a8ab0")          # 左面

    # アンカー⊕（Z=0面）ピッチ基準
    ra = max(inp.anchor_rows, 1)
    ca = max(inp.anchor_cols, 1)
    ax0_3d = (B - inp.anchor_pitch_h * (ca - 1)) / 2
    ay0_3d = (H - inp.anchor_pitch_v * (ra - 1)) / 2
    for ri in range(ra):
        for ci in range(ca):
            ax = ax0_3d + ci * inp.anchor_pitch_h
            ay = ay0_3d + ri * inp.anchor_pitch_v
            px2, py2 = iso(ax, ay, 0)
            cv.create_oval(px2-4,py2-4,px2+4,py2+4, fill="white",outline="#993300",width=1.2)
            cv.create_line(px2-4,py2,px2+4,py2, fill="#993300",width=1)
            cv.create_line(px2,py2-4,px2,py2+4, fill="#993300",width=1)

    # ② 下版（Z=bp..bp+L_bot）
    if tb > 0:
        f4((0,0,bp),(B,0,bp),(B,0,bp+L_bot),(0,0,bp+L_bot),    "#6080aa")  # 下面
        f4((0,0,bp+L_bot),(B,0,bp+L_bot),(B,tb,bp+L_bot),(0,tb,bp+L_bot),"#7bafd4") # 先端面
        f4((B,0,bp),(B,tb,bp),(B,tb,bp+L_bot),(B,0,bp+L_bot),  "#5a7090")  # 右面
        f4((0,tb,bp),(B,tb,bp),(B,tb,bp+L_bot),(0,tb,bp+L_bot),"#aec6e8")  # 上面

    # ③ 天板（Z=bp..bp+L）
    top_y0 = (tb + rh) if (inp.has_rib and rh > 0) else (H - T)
    top_y1 = H
    f4((0,top_y0,bp),(B,top_y0,bp),(B,top_y0,bp+L),(0,top_y0,bp+L),"#6080aa")  # 下面
    f4((0,top_y0,bp+L),(B,top_y0,bp+L),(B,top_y1,bp+L),(0,top_y1,bp+L),"#7bafd4") # 先端面
    f4((0,top_y1,bp),(B,top_y1,bp),(B,top_y1,bp+L),(0,top_y1,bp+L),"#aec6e8")  # 上面
    f4((B,top_y0,bp),(B,top_y1,bp),(B,top_y1,bp+L),(B,top_y0,bp+L),"#5a7090") # 右面

    # ④ リブ陰線（ソリッド面の後に描いて点線を最前面に）
    def _dashed_line(p0, p1, color="#cc8800"):
        x1, y1 = iso(*p0)
        x2, y2 = iso(*p1)
        cv.create_line(x1, y1, x2, y2, fill=color, width=1.4, dash=(5, 3))

    if inp.has_rib and rh > 0:
        n    = max(1, inp.n_rib)
        rt   = inp.t_rib
        p_mm = (B - rt) / max(n - 1, 1) if n > 1 else 0
        x0   = 0.0
        ry0  = tb
        ry1  = tb + rh
        for i in range(n):
            rx = x0 + p_mm * i
            if rx < 0 or rx + rt > B: continue
            # 各リブの頂点
            TL  = (rx,    ry1, bp)           # 壁側上左
            TR  = (rx+rt, ry1, bp)           # 壁側上右
            BL  = (rx,    ry0, bp)           # 壁側下左
            BR  = (rx+rt, ry0, bp)           # 壁側下右
            TL2 = (rx,    ry1, bp+Lr_top)    # 先端上左
            TR2 = (rx+rt, ry1, bp+Lr_top)    # 先端上右
            BL2 = (rx,    ry0, bp+Lr_bot)    # 先端下左
            BR2 = (rx+rt, ry0, bp+Lr_bot)    # 先端下右
            # 壁側面（台形）の4辺
            _dashed_line(BL, TL); _dashed_line(TL, TR)
            _dashed_line(TR, BR); _dashed_line(BR, BL)
            # 先端面（台形）の4辺
            _dashed_line(BL2, TL2); _dashed_line(TL2, TR2)
            _dashed_line(TR2, BR2); _dashed_line(BR2, BL2)
            # 上辺の奥行き線（天板下面に沿う）
            _dashed_line(TL, TL2); _dashed_line(TR, TR2)
            # 下辺の奥行き線（下版上面に沿う）
            _dashed_line(BL, BL2); _dashed_line(BR, BR2)

    # ⑤ 荷重矢印
    V      = inp.W / max(inp.N, 1)
    H_load = inp.Kh * V
    # 鉛直力（アイソメ上方から下向き）
    ax2, ay2 = iso(B/2, H, bp + L*0.5)
    cv.create_line(ax2, ay2-40, ax2, ay2, fill="#c0392b", width=2.5, arrow=tk.LAST)
    cv.create_text(ax2+3, ay2-42, text=f"V={V:.1f}kN", anchor="sw",
                   font=("Arial", 8, "bold"), fill="#c0392b")
    # 水平力（Z方向＝突出方向 →）
    hx1, hy1 = iso(B/2, H/2, 0)
    hx2, hy2 = iso(B/2, H/2, bp*0.8)
    cv.create_line(hx1, hy1, hx2, hy2, fill="#2471a3", width=2.5, arrow=tk.LAST)
    cv.create_text(hx1-3, hy1-2, text=f"H={H_load:.1f}kN", anchor="se",
                   font=("Arial", 8, "bold"), fill="#2471a3")

    _title(cv, cw, "【3D アイソメ図】")


# ===========================================================================
# メインウィンドウ
# ===========================================================================
# 計算書 HTML 生成
# ===========================================================================

def _capture_canvas_b64(canvas) -> str:
    """Canvas を PNG キャプチャして base64 文字列を返す"""
    try:
        from PIL import ImageGrab
        import io, base64
        canvas.update_idletasks()
        canvas.update()
        x = canvas.winfo_rootx()
        y = canvas.winfo_rooty()
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def _build_html(inp: BracketInput, res, anc: dict, allow,
                img_side="", img_front="", img_3d="", img_plan="") -> str:
    import datetime
    now = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")
    V   = inp.W / max(inp.N, 1)
    H   = inp.Kh * V

    def row(label, val, allow_val, jdg, margin=""):
        color = "#d4edda" if jdg in ("OK","OK(無応力)") else "#f8d7da"
        badge = f'<span style="color:{"green" if jdg.startswith("OK") else "red"};font-weight:bold">{jdg}</span>'
        return (f'<tr style="background:{color}">'
                f'<td>{label}</td><td style="text-align:right">{val}</td>'
                f'<td style="text-align:right">{allow_val}</td>'
                f'<td style="text-align:right">{margin}</td>'
                f'<td style="text-align:center">{badge}</td></tr>')

    def th(label):
        return (f'<tr style="background:#2255aa;color:white">'
                f'<th colspan="5" style="padding:6px 8px;text-align:left">{label}</th></tr>')

    def ms(m):
        return "∞" if m == float("inf") else f"{m:.3f}"

    comb_val = 1.0 / res.margins["anchor_comb"] if res.margins["anchor_comb"] != float("inf") else 0.0
    all_ok   = all(v in ("OK","OK(無応力)") for v in res.judgements.values())
    banner_color = "#28a745" if all_ok else "#dc3545"
    banner_text  = "総合判定：OK　― 全項目 許容値以内" if all_ok else \
                   f"総合判定：NG　― NG項目: {', '.join(k for k,v in res.judgements.items() if v=='NG')}"

    html = f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<title>ブラケット構造計算書</title>
<style>
  body{{font-family:"Meiryo","Yu Gothic",sans-serif;font-size:11pt;margin:20mm 15mm;color:#222}}
  h1{{font-size:14pt;text-align:center;border-bottom:2px solid #2255aa;padding-bottom:6px}}
  h2{{font-size:11pt;background:#2255aa;color:white;padding:4px 8px;margin-top:18px}}
  h3{{font-size:10pt;margin:12px 0 4px;color:#2255aa}}
  table{{width:100%;border-collapse:collapse;margin-bottom:10px;font-size:10pt}}
  th,td{{border:1px solid #bbb;padding:4px 8px}}
  th{{background:#eef2ff;text-align:center}}
  .banner{{background:{banner_color};color:white;font-size:13pt;font-weight:bold;
           text-align:center;padding:10px;border-radius:4px;margin-bottom:16px}}
  .info-table td{{border:none;padding:2px 12px 2px 0}}
  @media print{{
    .no-print{{display:none}}
    body{{margin:10mm}}
  }}
</style>
</head><body>
<div class="no-print" style="margin-bottom:12px">
  <button onclick="window.print()" style="padding:8px 24px;font-size:11pt;
    background:#2255aa;color:white;border:none;border-radius:4px;cursor:pointer">
    🖨️ 印刷／PDF保存
  </button>
</div>

<h1>沓座拡幅型 落橋防止装置ブラケット 構造計算書</h1>
<p style="text-align:right;color:#666;font-size:9pt">
  道路橋示方書（鋼橋編・コンクリート橋編）準拠　／　出力日時：{now}</p>

<div class="banner">{banner_text}</div>

<h2>1. 設計条件</h2>
<table class="info-table"><tbody>
<tr><td><b>荷重条件</b></td>
    <td>上部工自重 W = {inp.W:.0f} kN　／　設計水平震度 Kh = {inp.Kh}　／　ブラケット基数 N = {inp.N}</td></tr>
<tr><td><b>材質</b></td><td>{inp.material}　／　{inp.anchor_type}アンカー　／　{'地震時割増（×1.5）適用' if inp.seismic_case else '常時'}</td></tr>
<tr><td><b>天板</b></td><td>t = {inp.t_pl:.0f} mm　b = {inp.b_pl:.0f} mm　L = {inp.L_b:.0f} mm</td></tr>
<tr><td><b>下版</b></td><td>t = {inp.t_bot:.0f} mm　L = {inp.L_b_bot:.0f} mm</td></tr>
<tr><td><b>リブ</b></td><td>t = {inp.t_rib:.0f} mm　h = {inp.h_rib:.0f} mm　{inp.n_rib} 枚　上ちり = {inp.chiri_top:.0f} mm　下ちり = {inp.chiri_bot:.0f} mm</td></tr>
<tr><td><b>アンカー</b></td><td>φ{inp.d_anchor:.0f} mm　{inp.anchor_cols}（横）× {inp.anchor_rows}（縦）本　横ピッチ = {inp.anchor_pitch_h:.0f} mm　縦ピッチ = {inp.anchor_pitch_v:.0f} mm</td></tr>
<tr><td><b>コンクリート</b></td><td>f'c = {inp.f_c:.0f} N/mm²　縁辺距離 c_edge = {inp.c_edge:.0f} mm</td></tr>
</tbody></table>

<h2>2. 荷重計算</h2>
<table class="info-table"><tbody>
<tr><td>鉛直分担力</td><td>V = W / N = {inp.W:.0f} / {inp.N} = <b>{V:.1f} kN</b></td></tr>
<tr><td>水平力</td><td>H = Kh × V = {inp.Kh} × {V:.1f} = <b>{H:.1f} kN</b></td></tr>
<tr><td>根部曲げモーメント</td><td>M = H × L_b = {H:.1f} × {inp.L_b:.0f} = <b>{res.M:.1f} kN·mm</b></td></tr>
</tbody></table>

<h2>3. ブラケット根部断面算定</h2>
<table>
<tr><th>項目</th><th>実応力度 [N/mm²]</th><th>許容応力度 [N/mm²]</th><th>余裕率</th><th>判定</th></tr>
{row("曲げ応力度 σ_b", f"{res.sigma_b:.2f}", f"{allow.sigma_b:.2f}", res.judgements["sigma_b"], ms(res.margins["sigma_b"]))}
{row("せん断応力度 τ", f"{res.tau:.2f}", f"{allow.tau:.2f}", res.judgements["tau"], ms(res.margins["tau"]))}
{row("合成応力度 σ_v = √(σ_b²+3τ²)", f"{res.sigma_v:.2f}", f"{allow.sigma_v:.2f}", res.judgements["sigma_v"], ms(res.margins["sigma_v"]))}
</table>
<p style="font-size:9pt;color:#555">
断面係数 Z = {res.Z_pl:.1f} mm³　／　せん断有効断面積 A_w = {res.A_w:.1f} mm²</p>

<h2>4. アンカー部検討</h2>
<table>
<tr><th>項目</th><th>実値</th><th>許容／基準値</th><th>余裕率</th><th>判定</th></tr>
{row("引張応力度 σ_t [N/mm²]", f"{res.sigma_anchor_t:.2f}", f"{allow.anchor_tension:.2f}", res.judgements["anchor_tension"], ms(res.margins["anchor_tension"]))}
{row("せん断応力度 τ_v [N/mm²]", f"{res.tau_anchor_v:.2f}", f"{allow.anchor_shear:.2f}", res.judgements["anchor_shear"], ms(res.margins["anchor_shear"]))}
{row("組み合わせ比率（楕円相関）", f"{comb_val:.3f}", "≤ 1.000", res.judgements["anchor_comb"], ms(res.margins["anchor_comb"]))}
{row("破壊コーン 引張合力 [kN]", f"{anc['T_total']:.2f}", f"{res.concrete_cone_load:.2f}", res.judgements["cone"], ms(res.margins["cone"]))}
{row("必要埋込長 h_ef [mm]", f"{anc['h_ef_req']:.1f}（必要）", f"{anc['h_ef']:.0f}（採用 / 10d={anc['h_ef_std']:.0f}）", res.judgements["h_ef"], ms(res.margins["h_ef"]))}
{row("縁辺距離 c_edge [mm]", f"{inp.c_edge:.0f}", f"≥ {anc['c_min_required']:.0f}（= 6d）", res.judgements["edge"], ms(res.margins["edge"]))}
</table>
<p style="font-size:9pt;color:#555">
アンカー有効断面積 A_bolt = {anc['A_bolt']:.1f} mm²　（ねじ有効断面積率 75%）<br>
引張アンカー本数 n_t = {anc['n_tension']} 本　／　引張合力 T = M / e = {res.M:.1f} / {inp.e_anchor:.1f} = {anc['T_total']:.3f} kN<br>
引張圧縮間距離 e = {inp.e_anchor:.1f} mm　（縦ピッチ × (段数-1)）
</p>

"""
    # 図面セクション（画像がある場合のみ追加）
    views = [
        ("側面図",   img_side),
        ("正面図",   img_front),
        ("3D アイソメ図", img_3d),
        ("平面図",   img_plan),
    ]
    has_img = any(v for _, v in views)
    if has_img:
        html += """
<div style="page-break-before:always"></div>
<h2>5. ブラケット形状図</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px">
"""
        for title_v, b64 in views:
            if b64:
                html += (f'<div style="border:1px solid #bbb;border-radius:4px;padding:6px">'
                         f'<p style="text-align:center;font-weight:bold;margin:0 0 4px;'
                         f'color:#2255aa">{title_v}</p>'
                         f'<img src="data:image/png;base64,{b64}" '
                         f'style="width:100%;height:auto"></div>\n')
        html += "</div>\n"

    html += """
<p style="font-size:8pt;color:#999;margin-top:30px;border-top:1px solid #ccc;padding-top:6px">
本計算書は道路橋示方書（鋼橋編・コンクリート橋編）に基づく概略計算です。
設計に使用する場合は担当技術者による確認が必要です。</p>
</body></html>"""
    return html


# ===========================================================================
# 計算書プレビューウィンドウ
# ===========================================================================

class ReportWindow(tk.Toplevel):

    def __init__(self, parent, inp, res, anc, allow, images=None):
        super().__init__(parent)
        self.title("構造計算書プレビュー")
        self.geometry("820x700")
        self.resizable(True, True)
        self._inp, self._res, self._anc, self._allow = inp, res, anc, allow
        imgs = (images or []) + [""] * 4
        self._html = _build_html(inp, res, anc, allow,
                                 img_side=imgs[0], img_front=imgs[1],
                                 img_3d=imgs[2],   img_plan=imgs[3])
        self._build()

    def _build(self):
        # ── ツールバー ──
        bar = tk.Frame(self, bg="#2255aa")
        bar.pack(fill=tk.X)
        tk.Button(bar, text="🖨️  印刷 / PDF保存（ブラウザで開く）",
                  command=self._print,
                  font=("Arial", 10, "bold"), bg="#2255aa", fg="white",
                  activebackground="#1a3d80", relief="flat",
                  padx=12, pady=5).pack(side=tk.LEFT, padx=6, pady=4)
        tk.Button(bar, text="💾  HTMLファイルを保存",
                  command=self._save_html,
                  font=("Arial", 9), bg="#17a2b8", fg="white",
                  activebackground="#117a8b", relief="flat",
                  padx=10, pady=5).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(bar, text="✕ 閉じる",
                  command=self.destroy,
                  font=("Arial", 9), bg="#555", fg="white",
                  relief="flat", padx=10, pady=5).pack(side=tk.RIGHT, padx=6, pady=4)

        # ── テキストプレビュー（簡易） ──
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self._build_preview(frm)

    def _build_preview(self, parent):
        """計算書を構造化して表示"""
        import datetime
        inp, res, anc, allow = self._inp, self._res, self._anc, self._allow
        V = inp.W / max(inp.N, 1)
        H = inp.Kh * V

        canvas = tk.Canvas(parent, bg="white")
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inner = ttk.Frame(canvas)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        def title(text):
            tk.Label(inner, text=text, font=("Arial", 13, "bold"),
                     bg="#2255aa", fg="white", anchor="w",
                     padx=10, pady=5).pack(fill=tk.X, pady=(10, 2))

        def section(text):
            tk.Label(inner, text=text, font=("Arial", 10, "bold"),
                     bg="#dde8ff", fg="#2255aa", anchor="w",
                     padx=8, pady=3).pack(fill=tk.X, pady=(6, 1))

        def kv(label, value, unit=""):
            f = tk.Frame(inner, bg="white")
            f.pack(fill=tk.X, padx=12, pady=1)
            tk.Label(f, text=label, width=28, anchor="w",
                     font=("Arial", 9), bg="white").pack(side=tk.LEFT)
            tk.Label(f, text=f"{value}  {unit}", anchor="w",
                     font=("Arial", 9, "bold"), bg="white").pack(side=tk.LEFT)

        def result_table(headers, rows_data):
            f = ttk.Frame(inner)
            f.pack(fill=tk.X, padx=12, pady=3)
            col_widths = [26, 14, 14, 8, 6]
            for ci, (h, w) in enumerate(zip(headers, col_widths)):
                tk.Label(f, text=h, width=w, anchor="center",
                         font=("Arial", 8, "bold"),
                         bg="#eef2ff", relief="ridge").grid(
                    row=0, column=ci, sticky="nsew", padx=1, pady=1)
            for ri, (lbl, actual, allowable, jdg, margin) in enumerate(rows_data, 1):
                bg = "#d4edda" if jdg.startswith("OK") else "#f8d7da"
                vals = [lbl, actual, allowable, margin, jdg]
                for ci, (v, w) in enumerate(zip(vals, col_widths)):
                    fg = "green" if jdg.startswith("OK") else "red" if ci == 4 else "black"
                    tk.Label(f, text=v, width=w, anchor="center" if ci > 0 else "w",
                             font=("Arial", 8, "bold" if ci == 4 else "normal"),
                             bg=bg, fg=fg, relief="ridge").grid(
                        row=ri, column=ci, sticky="nsew", padx=1, pady=1)

        def ms(m):
            return "∞" if m == float("inf") else f"{m:.3f}"

        all_ok = all(v in ("OK","OK(無応力)") for v in res.judgements.values())
        banner_bg = "#28a745" if all_ok else "#dc3545"
        banner_text = "総合判定：OK　― 全項目 許容値以内" if all_ok else \
                      f"総合判定：NG　― NG項目: {', '.join(k for k,v in res.judgements.items() if v=='NG')}"
        tk.Label(inner, text=banner_text, font=("Arial", 11, "bold"),
                 bg=banner_bg, fg="white", pady=8).pack(fill=tk.X, pady=(4, 2))

        title("  沓座拡幅型 落橋防止装置ブラケット 構造計算書")
        now = __import__("datetime").datetime.now().strftime("%Y年%m月%d日 %H:%M")
        tk.Label(inner, text=f"道路橋示方書（鋼橋編・コンクリート橋編）準拠　出力：{now}",
                 font=("Arial", 8), bg="white", fg="#666").pack(anchor="e", padx=10)

        section("1. 設計条件")
        kv("上部工自重 W", f"{inp.W:.0f}", "kN")
        kv("設計水平震度 Kh", f"{inp.Kh}")
        kv("ブラケット基数 N", f"{inp.N}", "基")
        kv("材質", inp.material)
        kv("天板 t × b × L", f"{inp.t_pl:.0f} × {inp.b_pl:.0f} × {inp.L_b:.0f}", "mm")
        kv("下版 t × L", f"{inp.t_bot:.0f} × {inp.L_b_bot:.0f}", "mm")
        kv("リブ t × h × 枚数", f"{inp.t_rib:.0f} × {inp.h_rib:.0f} × {inp.n_rib}", "mm/枚")
        kv("アンカー φ × 配置", f"φ{inp.d_anchor:.0f}  {inp.anchor_cols}×{inp.anchor_rows}本", "")
        kv("横ピッチ / 縦ピッチ", f"{inp.anchor_pitch_h:.0f} / {inp.anchor_pitch_v:.0f}", "mm")
        kv("縁辺距離 c_edge", f"{inp.c_edge:.0f}", "mm")
        kv("コンクリート強度 f'c", f"{inp.f_c:.0f}", "N/mm²")

        section("2. 荷重計算")
        kv("鉛直分担力 V = W/N", f"{V:.1f}", "kN")
        kv("水平力 H = Kh × V", f"{H:.1f}", "kN")
        kv("根部曲げモーメント M = H×L_b", f"{res.M:.1f}", "kN·mm")

        section("3. ブラケット根部断面算定")
        kv("断面係数 Z", f"{res.Z_pl:.1f}", "mm³")
        kv("せん断有効断面積 A_w", f"{res.A_w:.1f}", "mm²")
        result_table(
            ["項目", "実応力度", "許容応力度", "余裕率", "判定"],
            [
                ("曲げ σ_b [N/mm²]",    f"{res.sigma_b:.2f}", f"{allow.sigma_b:.2f}", res.judgements["sigma_b"], ms(res.margins["sigma_b"])),
                ("せん断 τ [N/mm²]",    f"{res.tau:.2f}",     f"{allow.tau:.2f}",     res.judgements["tau"],     ms(res.margins["tau"])),
                ("合成 σ_v [N/mm²]",    f"{res.sigma_v:.2f}", f"{allow.sigma_v:.2f}", res.judgements["sigma_v"], ms(res.margins["sigma_v"])),
            ])

        section("4. アンカー部検討")
        kv("アンカー有効断面積 A_bolt", f"{anc['A_bolt']:.1f}", "mm²")
        kv("引張圧縮間距離 e_anchor", f"{inp.e_anchor:.1f}", "mm")
        result_table(
            ["項目", "実値", "許容／基準値", "余裕率", "判定"],
            [
                ("引張応力度 σ_t [N/mm²]",  f"{res.sigma_anchor_t:.2f}", f"{allow.anchor_tension:.2f}", res.judgements["anchor_tension"], ms(res.margins["anchor_tension"])),
                ("せん断応力度 τ_v [N/mm²]", f"{res.tau_anchor_v:.2f}",   f"{allow.anchor_shear:.2f}",   res.judgements["anchor_shear"],   ms(res.margins["anchor_shear"])),
                ("組み合わせ比率",
                    f"{1/res.margins['anchor_comb']:.3f}" if res.margins['anchor_comb'] != float('inf') else "0.000",
                    "≤ 1.000", res.judgements["anchor_comb"], ms(res.margins["anchor_comb"])),
                ("破壊コーン [kN]",          f"{anc['T_total']:.2f}",      f"{res.concrete_cone_load:.2f}", res.judgements["cone"], ms(res.margins["cone"])),
                ("必要埋込長 h_ef [mm]",     f"{anc['h_ef_req']:.1f}",     f"{anc['h_ef']:.0f}（採用）",   res.judgements["h_ef"], ms(res.margins["h_ef"])),
                ("縁辺距離 c_edge [mm]",     f"{inp.c_edge:.0f}",          f"≥{anc['c_min_required']:.0f}", res.judgements["edge"], ms(res.margins["edge"])),
            ])

    def _print(self):
        import tempfile, os, webbrowser
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html",
                                         delete=False, encoding="utf-8") as f:
            f.write(self._html)
            path = f.name
        webbrowser.open(f"file:///{path.replace(os.sep, '/')}")

    def _save_html(self):
        import datetime
        from tkinter import filedialog
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTMLファイル", "*.html"), ("全ファイル", "*.*")],
            initialfile=f"ブラケット計算書_{ts}.html",
            title="計算書HTMLを保存",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._html)
        messagebox.showinfo("保存完了", f"保存しました。\n{path}")


# ===========================================================================

class BracketApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("沓座拡幅型 落橋防止装置ブラケット 構造計算")
        self.state("zoomed")
        self.minsize(1200, 720)
        self._build_ui()
        self.after(300, self._refresh)

    # -----------------------------------------------------------------------
    def _build_ui(self):
        # 水平2分割：左（入力）＋右（図面＋結果）
        pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 左パネル
        frm_left = ttk.Frame(pane, width=272)
        frm_left.pack_propagate(False)
        pane.add(frm_left, weight=0)

        # 右パネル：上（4面図）＋下（結果＋ログ）
        frm_right = ttk.Frame(pane)
        pane.add(frm_right, weight=1)

        # ── 4面図（2×2グリッド）────────────────────────
        frm_views = ttk.Frame(frm_right)
        frm_views.pack(fill=tk.BOTH, expand=True)
        frm_views.rowconfigure(0, weight=1)
        frm_views.rowconfigure(1, weight=1)
        frm_views.columnconfigure(0, weight=1)
        frm_views.columnconfigure(1, weight=1)

        specs = [
            ("側面図",   "_cv_side",  0, 0),
            ("正面図",   "_cv_front", 0, 1),
            ("3D",       "_cv_3d",    1, 0),
            ("平面図",   "_cv_plan",  1, 1),
        ]
        for title, attr, row, col in specs:
            lf = ttk.LabelFrame(frm_views, text=title)
            lf.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
            cv = tk.Canvas(lf, bg="#f8f9fa", highlightthickness=0)
            cv.pack(fill=tk.BOTH, expand=True)
            setattr(self, attr, cv)
            cv.bind("<Configure>", lambda e: self.after(60, self._refresh))

        # ── 下段：結果テーブル＋ログ────────────────────
        pane_bot = ttk.PanedWindow(frm_right, orient=tk.HORIZONTAL)
        pane_bot.pack(fill=tk.BOTH, expand=False, pady=(3, 0))

        frm_tbl = ttk.LabelFrame(pane_bot, text="計算結果")
        pane_bot.add(frm_tbl, weight=3)
        self._build_table(frm_tbl)

        frm_log = ttk.LabelFrame(pane_bot, text="計算詳細ログ")
        pane_bot.add(frm_log, weight=2)
        self.log_box = scrolledtext.ScrolledText(
            frm_log, font=("Courier New", 8), height=7, state="disabled")
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # ── 左：ボタン（固定）＋判定ラベル───────────────
        self.lbl_overall = tk.Label(frm_left, text="　",
                                    font=("Arial", 10, "bold"),
                                    relief="ridge", pady=5, wraplength=250)
        self.lbl_overall.pack(side=tk.BOTTOM, fill=tk.X, padx=4, pady=(0, 4))

        frm_btn = tk.Frame(frm_left, bg="#2255aa", pady=3)
        frm_btn.pack(side=tk.BOTTOM, fill=tk.X, padx=4, pady=(0, 2))
        tk.Button(frm_btn, text="▶  計算実行", command=self._run,
                  font=("Arial", 11, "bold"), bg="#2255aa", fg="white",
                  activebackground="#1a3d80", relief="flat",
                  padx=8, pady=5).pack(side=tk.LEFT, expand=True,
                                       fill=tk.X, padx=(4, 2))
        tk.Button(frm_btn, text="📄 計算書出力", command=self._export,
                  font=("Arial", 9, "bold"), bg="#17a2b8", fg="white",
                  activebackground="#117a8b", relief="flat",
                  padx=6, pady=5).pack(side=tk.LEFT, expand=True,
                                       fill=tk.X, padx=(2, 2))
        tk.Button(frm_btn, text="クリア", command=self._clear,
                  font=("Arial", 9), bg="#777", fg="white",
                  activebackground="#444", relief="flat",
                  padx=6, pady=5).pack(side=tk.LEFT, padx=(0, 4))

        # ── 左：入力フォーム──────────────────────────
        self._build_inputs(frm_left)

    # -----------------------------------------------------------------------
    def _build_table(self, parent):
        cols = ("項目", "実応力度", "許容応力度", "余裕率", "判定")
        self.tree = ttk.Treeview(parent, columns=cols,
                                  show="headings", height=6)
        for col, w in zip(cols, [210, 110, 110, 75, 55]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")
        self.tree.tag_configure("ok",  background="#d4edda")
        self.tree.tag_configure("ng",  background="#f8d7da")
        self.tree.tag_configure("hdr", background="#dee2e6",
                                font=("Arial", 8, "bold"))
        sc = ttk.Scrollbar(parent, orient="vertical",
                           command=self.tree.yview)
        self.tree.configure(yscrollcommand=sc.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                       padx=2, pady=2)
        sc.pack(side=tk.RIGHT, fill=tk.Y)

    # -----------------------------------------------------------------------
    def _build_inputs(self, parent):
        self.vars: dict[str, tk.Variable] = {}

        cv_s = tk.Canvas(parent, highlightthickness=0)
        sb   = ttk.Scrollbar(parent, orient="vertical", command=cv_s.yview)
        cv_s.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        cv_s.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inner = ttk.Frame(cv_s)
        wid   = cv_s.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: cv_s.configure(scrollregion=cv_s.bbox("all")))
        cv_s.bind("<Configure>",
                  lambda e: cv_s.itemconfig(wid, width=e.width))
        cv_s.bind("<MouseWheel>",
                  lambda e: cv_s.yview_scroll(-1*(e.delta//120), "units"))

        def row(label, key, default, unit="", w=9):
            nonlocal r
            tk.Label(inner, text=label, anchor="w",
                     font=("Arial", 8)).grid(
                row=r, column=0, sticky="w", padx=(6,2), pady=1)
            var = tk.StringVar(value=str(default))
            ttk.Entry(inner, textvariable=var, width=w,
                      font=("Arial", 8)).grid(
                row=r, column=1, padx=2, pady=1, sticky="w")
            if unit:
                tk.Label(inner, text=unit, anchor="w",
                         font=("Arial", 7), fg="#666").grid(
                    row=r, column=2, sticky="w", padx=1)
            var.trace_add("write", lambda *_: self.after(80, self._refresh))
            self.vars[key] = var
            r += 1

        def combo(label, key, values, default):
            nonlocal r
            tk.Label(inner, text=label, anchor="w",
                     font=("Arial", 8)).grid(
                row=r, column=0, sticky="w", padx=(6,2), pady=1)
            var = tk.StringVar(value=default)
            ttk.Combobox(inner, textvariable=var, values=values,
                         width=8, state="readonly",
                         font=("Arial", 8)).grid(
                row=r, column=1, padx=2, pady=1, sticky="w")
            var.trace_add("write", lambda *_: self.after(80, self._refresh))
            self.vars[key] = var
            r += 1

        def chk(label, key, default):
            nonlocal r
            var = tk.BooleanVar(value=default)
            ttk.Checkbutton(inner, text=label, variable=var).grid(
                row=r, column=0, columnspan=3, sticky="w", padx=6, pady=1)
            var.trace_add("write", lambda *_: self.after(80, self._refresh))
            self.vars[key] = var
            r += 1

        def sec(text):
            nonlocal r
            ttk.Separator(inner, orient="horizontal").grid(
                row=r, column=0, columnspan=3, sticky="ew", pady=(5,2))
            r += 1
            tk.Label(inner, text=text,
                     font=("Arial", 9, "bold"), fg="#2255aa").grid(
                row=r, column=0, columnspan=3, sticky="w", padx=6)
            r += 1

        r = 0
        sec("① 荷重条件")
        row("上部工自重 W",      "W",   3500.0, "kN")
        row("設計水平震度 Kh",   "Kh",  0.40,   "-")
        row("ブラケット基数 N",  "N",   2,      "基")

        sec("② ブラケット形状")
        combo("材質", "material", ["SS400", "SM490"], "SM490")
        row("天板・BP厚 t_pl",   "t_pl",     22.0,  "mm")
        row("天板幅 b_pl",       "b_pl",     600.0, "mm")
        row("天板突出長 L_b",    "L_b",      500.0, "mm")
        chk("リブあり", "has_rib", True)
        row("リブ厚 t_rib",      "t_rib",    16.0,  "mm")
        row("リブ高さ h_rib",    "h_rib",    350.0, "mm")
        row("リブ枚数 n_rib",    "n_rib",    5,     "枚")
        row("下版厚 t_bot",      "t_bot",    16.0,  "mm")
        row("下版突出長 L_b_bot","L_b_bot",  300.0, "mm")
        row("上ちり chiri_top", "chiri_top", 30.0,  "mm")
        row("下ちり chiri_bot", "chiri_bot", 50.0,  "mm")

        sec("③ アンカー")
        combo("アンカー形式", "anchor_type", ["後施工", "埋込み"], "後施工")
        row("アンカー径 d",       "d_anchor",       30.0,  "mm")
        row("横本数（幅方向）",   "anchor_cols",    3,     "本")
        row("横ピッチ",           "anchor_pitch_h", 150.0, "mm")
        row("縦段数（高さ方向）", "anchor_rows",    2,     "段")
        row("縦ピッチ",           "anchor_pitch_v", 150.0, "mm")

        sec("④ コンクリート")
        row("縁辺距離 c_edge",   "c_edge", 150.0, "mm")
        row("基準強度 f'c",      "f_c",    24.0,  "N/mm²")
        chk("地震時割増（×1.5）", "seismic_case", True)

    # -----------------------------------------------------------------------
    def _get_inp(self) -> BracketInput | None:
        v = self.vars
        try:
            return BracketInput(
                W=float(v["W"].get()),
                Kh=float(v["Kh"].get()),
                N=max(1, int(float(v["N"].get()))),
                material=v["material"].get(),
                t_pl=max(0.1, float(v["t_pl"].get())),
                b_pl=max(0.1, float(v["b_pl"].get())),
                L_b=max(0.1, float(v["L_b"].get())),
                has_rib=bool(v["has_rib"].get()),
                t_rib=max(0.1, float(v["t_rib"].get())),
                h_rib=max(0.1, float(v["h_rib"].get())),
                t_bot=max(0.0, float(v["t_bot"].get())),
                L_b_bot=max(0.0, float(v["L_b_bot"].get())),
                chiri_top=max(0.0, float(v["chiri_top"].get())),
                chiri_bot=max(0.0, float(v["chiri_bot"].get())),
                anchor_type=v["anchor_type"].get(),
                d_anchor=max(0.1, float(v["d_anchor"].get())),
                anchor_cols=max(1, int(float(v["anchor_cols"].get()))),
                anchor_rows=max(1, int(float(v["anchor_rows"].get()))),
                anchor_pitch_h=max(1.0, float(v["anchor_pitch_h"].get())),
                anchor_pitch_v=max(1.0, float(v["anchor_pitch_v"].get())),
                n_rib=max(1, int(float(v["n_rib"].get()))),
                rib_pitch=0.0,
                c_edge=max(0.1, float(v["c_edge"].get())),
                f_c=max(0.1, float(v["f_c"].get())),
                seismic_case=bool(v["seismic_case"].get()),
            )
        except (ValueError, tk.TclError):
            return None

    # -----------------------------------------------------------------------
    def _refresh(self):
        inp = self._get_inp()
        if inp is None: return
        draw_side(self._cv_side,  inp)
        draw_front(self._cv_front, inp)
        draw_3d(self._cv_3d,    inp)
        draw_plan(self._cv_plan,  inp)

    # -----------------------------------------------------------------------
    def _run(self):
        inp = self._get_inp()
        if inp is None:
            messagebox.showerror("入力エラー", "数値を正しく入力してください。")
            return
        try:
            allow = get_allowable_stress(inp.material, inp.seismic_case, inp.f_c)
            V, H, M = calc_load(inp)
            br    = check_bracket(inp, H, M, allow)
            anc   = check_anchor(inp, H, M, allow)

            res = BracketResult(
                V=V, H=H, M=M,
                Z_pl=br["Z_pl"], A_w=br["A_w"],
                sigma_b=br["sigma_b"], tau=br["tau"], sigma_v=br["sigma_v"],
                T_anchor=anc["T_anchor"], V_anchor=anc["V_anchor"],
                sigma_anchor_t=anc["sigma_anchor_t"],
                tau_anchor_v=anc["tau_anchor_v"],
                concrete_cone_load=anc["N_cone_allow"],
                edge_check=anc["c_min_required"],
                allowable=allow,
            )

            for key, actual, allowable, label in [
                ("sigma_b", res.sigma_b, allow.sigma_b, "曲げ"),
                ("tau",     res.tau,     allow.tau,     "せん断"),
                ("sigma_v", res.sigma_v, allow.sigma_v, "合成"),
                ("anchor_tension", res.sigma_anchor_t, allow.anchor_tension, "アンカー引張"),
                ("anchor_shear",   res.tau_anchor_v,   allow.anchor_shear,   "アンカーせん断"),
            ]:
                res.judgements[key], res.margins[key] = judge(actual, allowable, label)

            comb = anc["comb_ratio"]
            res.judgements["anchor_comb"] = "OK" if comb <= 1.0 else "NG"
            res.margins["anchor_comb"]    = (1.0/comb) if comb > 0 else float("inf")
            res.judgements["cone"], res.margins["cone"] = judge(
                anc["T_total"], anc["N_cone_allow"], "破壊コーン")
            res.judgements["h_ef"] = "OK" if anc["h_ef_req"] <= anc["h_ef"] else "NG"
            res.margins["h_ef"]    = anc["h_ef"] / anc["h_ef_req"] if anc["h_ef_req"] > 0 else float("inf")
            res.judgements["edge"] = "OK" if anc["edge_ratio"] >= 1.0 else "NG"
            res.margins["edge"]    = anc["edge_ratio"]

            self._last_calc = (res, anc, allow)
            self._update_table(res, anc, allow, inp)
            self._update_log(inp, res, anc, allow)

        except (ValueError, ZeroDivisionError) as e:
            messagebox.showerror("計算エラー", str(e))

    # -----------------------------------------------------------------------
    def _update_table(self, res, anc, allow, inp):
        for item in self.tree.get_children():
            self.tree.delete(item)

        def add(label, actual_s, allow_s, key):
            jdg = res.judgements[key]
            tag = "ok" if jdg in ("OK","OK(無応力)") else "ng"
            self.tree.insert("", "end",
                             values=(label, actual_s, allow_s,
                                     ms(res.margins[key]),
                                     "OK" if tag=="ok" else "NG"),
                             tags=(tag,))

        self.tree.insert("", "end",
                         values=("─── ブラケット断面 ───","","","",""),
                         tags=("hdr",))
        add("曲げ応力度 σ_b [N/mm²]",
            f"{res.sigma_b:.2f}", f"{allow.sigma_b:.2f}", "sigma_b")
        add("せん断応力度 τ [N/mm²]",
            f"{res.tau:.2f}", f"{allow.tau:.2f}", "tau")
        add("合成応力度 σ_v [N/mm²]",
            f"{res.sigma_v:.2f}", f"{allow.sigma_v:.2f}", "sigma_v")

        self.tree.insert("", "end",
                         values=("─── アンカー ───","","","",""),
                         tags=("hdr",))
        add("アンカー引張応力度 [N/mm²]",
            f"{res.sigma_anchor_t:.2f}", f"{allow.anchor_tension:.2f}", "anchor_tension")
        add("アンカーせん断応力度 [N/mm²]",
            f"{res.tau_anchor_v:.2f}", f"{allow.anchor_shear:.2f}", "anchor_shear")
        comb_val = 1.0/res.margins["anchor_comb"] \
            if res.margins["anchor_comb"] != float("inf") else 0.0
        add("組み合わせ比率（楕円相関）",
            f"{comb_val:.3f}", "≤ 1.000", "anchor_comb")
        add("破壊コーン 引張合力 [kN]",
            f"{anc['T_total']:.2f}", f"{res.concrete_cone_load:.2f}", "cone")
        add("必要埋込長 h_ef [mm]",
            f"{anc['h_ef_req']:.1f}", f"採用:{anc['h_ef']:.0f}(10d={anc['h_ef_std']:.0f})", "h_ef")
        add("縁辺距離 c_edge [mm]",
            f"{inp.c_edge:.0f}", f"≥{anc['c_min_required']:.0f}", "edge")

        all_ok = all(v in ("OK","OK(無応力)") for v in res.judgements.values())
        if all_ok:
            self.lbl_overall.config(text="総合判定：OK  全項目 許容値以内",
                                    bg="#28a745", fg="white")
        else:
            ng = [k for k,v in res.judgements.items() if v=="NG"]
            self.lbl_overall.config(text=f"総合判定：NG\nNG項目: {', '.join(ng)}",
                                    bg="#dc3545", fg="white")

    # -----------------------------------------------------------------------
    def _update_log(self, inp, res, anc, allow):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", tk.END)
        lines = [
            "="*54,
            "  沓座拡幅型 落橋防止装置ブラケット 構造計算書",
            "="*54,
            f"  V = {inp.W}/{inp.N} = {res.V:.3f} kN（鉛直分担力）",
            f"  H = {inp.Kh}×{res.V:.3f} = {res.H:.3f} kN（水平力）",
            f"  M = {res.H:.3f}×{inp.L_b} = {res.M:.1f} kN·mm",
            "-"*54,
            f"  Z={res.Z_pl:.1f}mm³  Aw={res.A_w:.1f}mm²",
            f"  σ_b={res.sigma_b:.2f}  (許容:{allow.sigma_b:.2f}) N/mm²",
            f"  τ  ={res.tau:.2f}  (許容:{allow.tau:.2f}) N/mm²",
            f"  σ_v={res.sigma_v:.2f}  (許容:{allow.sigma_v:.2f}) N/mm²",
            "-"*54,
            f"  A_bolt={anc['A_bolt']:.1f}mm²",
            f"  T_total={anc['T_total']:.3f}kN  T/本={res.T_anchor:.3f}kN",
            f"  σ_t={res.sigma_anchor_t:.2f}  (許容:{allow.anchor_tension:.2f}) N/mm²",
            f"  τ_v={res.tau_anchor_v:.2f}  (許容:{allow.anchor_shear:.2f}) N/mm²",
            f"  必要埋込長 h_ef_req={anc['h_ef_req']:.1f}mm  標準10d={anc['h_ef_std']:.0f}mm  採用={anc['h_ef']:.0f}mm",
            f"  N_cone(採用h_ef)={res.concrete_cone_load:.2f}kN  作用={anc['T_total']:.2f}kN",
            f"  c_edge={inp.c_edge:.0f}mm (必要:{anc['c_min_required']:.0f}mm)",
            "="*54,
        ]
        self.log_box.insert(tk.END, "\n".join(lines))
        self.log_box.config(state="disabled")

    # -----------------------------------------------------------------------
    def _export(self):
        """計算書プレビューウィンドウを開く"""
        inp = self._get_inp()
        if inp is None:
            messagebox.showwarning("入力エラー", "入力値を確認してください。")
            return
        if not hasattr(self, "_last_calc"):
            messagebox.showwarning("出力エラー", "先に計算を実行してください。")
            return
        # ウィンドウを開く前にキャプチャ（開いた後は隠れる）
        self.lift()
        self.update()
        imgs = [_capture_canvas_b64(cv)
                for cv in [self._cv_side, self._cv_front,
                            self._cv_3d, self._cv_plan]]
        ReportWindow(self, inp, *self._last_calc, images=imgs)

    # -----------------------------------------------------------------------
    def _clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.lbl_overall.config(text="　", bg=self.cget("bg"), fg="black")
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", tk.END)
        self.log_box.config(state="disabled")


# ===========================================================================
if __name__ == "__main__":
    app = BracketApp()
    app.mainloop()
