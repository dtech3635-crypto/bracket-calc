"""
沓座拡幅型 落橋防止装置ブラケット 構造計算スクリプト
道路橋示方書（鋼橋編・コンクリート橋編）準拠
Python 3.10+
"""

from __future__ import annotations
import math
import sys
from dataclasses import dataclass, field
from typing import Literal

# ===========================================================================
# データクラス
# ===========================================================================

@dataclass
class BracketInput:
    """ユーザー入力パラメータ"""
    W: float                          # 上部工自重 [kN]
    Kh: float                         # 設計水平震度 [-]
    N: int                            # ブラケット基数
    material: Literal["SS400", "SM490"]  # 材質
    t_pl: float                       # プレート厚 [mm]
    L_b: float                        # 突出長さ（根元〜荷重点） [mm]
    b_pl: float                       # プレート幅（根元断面幅） [mm]
    has_rib: bool                     # リブの有無
    t_rib: float                      # リブ厚（has_rib=Trueのとき有効） [mm]
    h_rib: float                      # リブ高さ（has_rib=Trueのとき有効） [mm]
    t_bot: float                      # 下版厚 [mm]
    anchor_type: Literal["後施工", "埋込み"]  # アンカー形式
    d_anchor: float                   # アンカー径 [mm]
    anchor_cols: int = 3              # 横方向（幅方向）本数
    anchor_rows: int = 2              # 縦方向（高さ方向）段数
    anchor_pitch_h: float = 150.0    # 横ピッチ [mm]
    anchor_pitch_v: float = 150.0    # 縦ピッチ [mm]

    @property
    def n_anchor(self) -> int:
        return self.anchor_cols * self.anchor_rows

    @property
    def e_anchor(self) -> float:
        """引張側〜圧縮側アンカー群重心距離 [mm]"""
        return self.anchor_pitch_v * (self.anchor_rows - 1) if self.anchor_rows > 1 else self.anchor_pitch_v
    n_rib: int = 2                    # リブ枚数（has_rib=Trueのとき有効）
    rib_pitch: float = 0.0            # リブピッチ [mm]（0=等間隔自動）
    c_edge: float = 150.0             # コンクリート縁辺距離（アンカー芯〜コンクリート端） [mm]
    f_c: float = 24.0                 # コンクリート設計基準強度 [N/mm²]
    chiri_top: float = 30.0          # 上ちり：天板先端〜リブ上端の距離 [mm]
    chiri_bot: float = 50.0          # 下ちり：下版先端〜リブ下端の距離 [mm]
    L_b_bot: float   = 300.0         # 下版突出長さ [mm]（0=天板と同じ L_b）
    seismic_case: bool = True         # 地震時割増の適用


@dataclass
class AllowableStress:
    """許容応力度 [N/mm²]"""
    sigma_b: float    # 曲げ圧縮（引張）
    tau: float        # せん断
    sigma_v: float    # 合成応力（Von Mises 基準）
    sigma_weld: float # 溶接部（隅肉）
    anchor_tension: float   # アンカー引張
    anchor_shear: float     # アンカーせん断
    concrete_bearing: float # コンクリート支圧


@dataclass
class BracketResult:
    """計算結果"""
    V: float = 0.0           # 1基あたり鉛直分担力 [kN]
    H: float = 0.0           # 作用水平力 [kN]
    M: float = 0.0           # 根部曲げモーメント [kN·mm]
    Z_pl: float = 0.0        # 根部断面係数 [mm³]
    A_w: float = 0.0         # せん断有効断面積 [mm²]
    sigma_b: float = 0.0     # 曲げ応力度 [N/mm²]
    tau: float = 0.0         # せん断応力度 [N/mm²]
    sigma_v: float = 0.0     # 合成応力度 [N/mm²]
    T_anchor: float = 0.0    # アンカー1本あたり引張力 [kN]
    V_anchor: float = 0.0    # アンカー1本あたりせん断力 [kN]
    sigma_anchor_t: float = 0.0  # アンカー引張応力度 [N/mm²]
    tau_anchor_v: float = 0.0    # アンカーせん断応力度 [N/mm²]
    concrete_cone_load: float = 0.0  # コンクリート破壊コーン耐力 [kN]
    edge_check: float = 0.0      # 縁辺破壊チェック比率
    allowable: AllowableStress | None = None
    judgements: dict[str, str] = field(default_factory=dict)
    margins: dict[str, float] = field(default_factory=dict)


# ===========================================================================
# 許容応力度の設定
# （道路橋示方書 鋼橋編 表-4.1, コンクリート橋編 準拠）
# ===========================================================================

def get_allowable_stress(material: str, seismic: bool, f_c: float) -> AllowableStress:
    """
    許容応力度を返す
    References:
      鋼橋編 4.2節 表-4.1（許容応力度）
      地震時割増係数: 鋼橋編 4.2.3 → 通常時の1.5倍（せん断は√3倍）
    """
    # ---------- 鋼材 ----------
    if material == "SS400":
        # 板厚 ≤ 40mm を想定
        sigma_b_normal = 140.0    # N/mm²（曲げ引張・圧縮）
        tau_normal = sigma_b_normal / math.sqrt(3)
    elif material == "SM490":
        sigma_b_normal = 180.0
        tau_normal = sigma_b_normal / math.sqrt(3)
    else:
        raise ValueError(f"未定義の材質: {material}。SS400 または SM490 を指定してください。")

    # 地震時割増（道示 鋼橋編 4.2.3）: 1.5倍
    factor = 1.5 if seismic else 1.0
    sigma_b = sigma_b_normal * factor
    tau = tau_normal * factor
    sigma_v = sigma_b  # Von Mises 基準で同値
    sigma_weld = sigma_b * 0.9  # 隅肉溶接は90%

    # ---------- アンカー（高強度アンカーボルト JIS B 1220 M16〜M36 相当） ----------
    # 後施工アンカーは道示 コンクリート橋編 11章、埋込みは鋼橋編付録
    # 引張 = 0.6×Fy（Fy=400 N/mm²相当）、せん断 = 引張/√3
    Fy_anchor = 400.0  # N/mm²（A307相当最低値）
    anchor_tension_normal = 0.6 * Fy_anchor
    anchor_shear_normal = anchor_tension_normal / math.sqrt(3)
    anchor_tension = anchor_tension_normal * factor
    anchor_shear = anchor_shear_normal * factor

    # ---------- コンクリート支圧 ----------
    # 道示 コンクリート橋編 7.4節 支圧応力度 → 0.3×f'c（簡易）
    concrete_bearing = 0.3 * f_c * factor

    return AllowableStress(
        sigma_b=sigma_b,
        tau=tau,
        sigma_v=sigma_v,
        sigma_weld=sigma_weld,
        anchor_tension=anchor_tension,
        anchor_shear=anchor_shear,
        concrete_bearing=concrete_bearing,
    )


# ===========================================================================
# 荷重計算
# ===========================================================================

def calc_load(inp: BracketInput) -> tuple[float, float, float]:
    """
    作用荷重を計算する

    V = W / N          [kN]  1基あたり鉛直分担力
    H = Kh × V        [kN]  水平力（落橋防止装置に作用）
    M = H × L_b        [kN·mm]

    Reference: 道路橋示方書 耐震設計編 5.4節（落橋防止システム）
    """
    if inp.N <= 0:
        raise ValueError("ブラケット基数 N は1以上の整数を指定してください。")
    if inp.Kh <= 0.0 or inp.Kh > 2.0:
        raise ValueError(f"設計水平震度 Kh={inp.Kh} が異常値です。0 < Kh ≤ 2.0 の範囲で指定してください。")
    if inp.W <= 0.0:
        raise ValueError("上部工自重 W は正の値を指定してください。")

    V = inp.W / inp.N           # 1基あたり鉛直分担力 [kN]
    H = inp.Kh * V              # 水平力 [kN]
    M = H * inp.L_b             # 根部曲げモーメント [kN·mm]
    return V, H, M


# ===========================================================================
# ブラケット断面算定
# ===========================================================================

def check_bracket(inp: BracketInput, H: float, M: float,
                  allow: AllowableStress) -> dict:
    """
    ブラケット根部の断面算定

    断面係数: Z = b × t² / 6  （矩形断面）
    リブあり: 等価断面係数を加算（簡易：リブの断面係数を加算）
    せん断有効断面積: A_w = b × t（プレート全断面）

    曲げ応力度:  σ_b = M×10³ / Z    [N/mm²]  （M: kN·mm → N·mm = ×1000）
    せん断応力度: τ  = H×10³ / A_w   [N/mm²]
    合成応力度:  σ_v = √(σ_b² + 3τ²) [N/mm²]  （Von Mises）

    Reference: 道路橋示方書 鋼橋編 4.2節
    """
    t = inp.t_pl
    b = inp.b_pl

    if t <= 0 or b <= 0:
        raise ValueError("プレート厚・幅は正の値を指定してください。")

    # 根部断面係数（矩形プレート）
    Z_pl = b * t ** 2 / 6.0  # mm³

    # 下版の断面係数を加算（I形断面の簡易計算）
    # 天板・下版をフランジ、リブをウェブとしてI形断面の慣性モーメントから算定
    if inp.t_bot > 0 and inp.has_rib:
        if inp.t_rib <= 0 or inp.h_rib <= 0:
            raise ValueError("リブ厚・高さは正の値を指定してください（has_rib=True）。")
        n_rib = max(1, inp.n_rib)
        H_tot = inp.t_pl + inp.h_rib + inp.t_bot   # 全断面高さ
        yg = H_tot / 2.0                            # 中立軸（対称断面）
        # 天板フランジ
        I_top = (inp.b_pl * inp.t_pl**3 / 12.0 +
                 inp.b_pl * inp.t_pl * (yg - inp.t_pl/2)**2)
        # 下版フランジ
        I_bot = (inp.b_pl * inp.t_bot**3 / 12.0 +
                 inp.b_pl * inp.t_bot * (yg - inp.h_rib - inp.t_bot/2)**2)
        # ウェブ（リブ）
        I_web = n_rib * inp.t_rib * inp.h_rib**3 / 12.0
        I_tot = I_top + I_bot + I_web
        Z_pl  = I_tot / yg  # 上端基準
    elif inp.has_rib:
        if inp.t_rib <= 0 or inp.h_rib <= 0:
            raise ValueError("リブ厚・高さは正の値を指定してください（has_rib=True）。")
        n_rib = max(1, inp.n_rib)
        Z_rib = inp.t_rib * inp.h_rib ** 2 / 6.0 * n_rib
        Z_pl += Z_rib

    # せん断有効断面積
    A_w = b * t  # mm²（矩形断面：全断面）

    # 応力度計算（単位変換: kN·mm → N·mm = ×1000, kN → N = ×1000）
    M_Nmm = M * 1e3   # N·mm
    H_N = H * 1e3     # N

    if Z_pl == 0:
        raise ZeroDivisionError("断面係数 Z がゼロです。形状パラメータを確認してください。")
    if A_w == 0:
        raise ZeroDivisionError("せん断有効断面積 A_w がゼロです。")

    sigma_b = M_Nmm / Z_pl
    tau = H_N / A_w
    sigma_v = math.sqrt(sigma_b ** 2 + 3.0 * tau ** 2)

    return {
        "Z_pl": Z_pl,
        "A_w": A_w,
        "sigma_b": sigma_b,
        "tau": tau,
        "sigma_v": sigma_v,
    }


# ===========================================================================
# アンカー検討
# ===========================================================================

def check_anchor(inp: BracketInput, H: float, M: float,
                 allow: AllowableStress) -> dict:
    """
    アンカー部の検討

    【引張力（モーメントによる引抜き）】
    引張側アンカー本数 n_t = n_anchor / anchor_rows（上段本数）
    T_total = M / e_anchor           [kN]    （レバーアーム = e_anchor）
    T_anchor = T_total / n_t         [kN/本]
    σ_t = T_anchor×10³ / A_bolt     [N/mm²]

    【せん断力】
    V_total = H                      [kN]
    V_anchor = V_total / n_anchor    [kN/本]
    τ_v = V_anchor×10³ / A_bolt     [N/mm²]

    【引張・せん断組み合わせ（道示 コンクリート橋編 11章）】
    (σ_t / σ_t_all)^2 + (τ_v / τ_v_all)^2 ≤ 1.0

    【コンクリート破壊コーン耐力（後施工アンカー）】
    N_cone = 0.5 × f'c^0.5 × π × h_ef²  [N]  （道示 コンクリート橋編 11章 式11.3.1）
    h_ef: 有効埋込み深さ ≈ 10×d_anchor（簡易）

    【縁辺破壊チェック】
    c_edge ≥ 6×d_anchor を目安（道示 コンクリート橋編 11.3.2）

    Reference: 道路橋示方書 コンクリート橋編 11章（アンカーボルト）
    """
    if inp.anchor_cols < 1:
        raise ValueError("アンカー横本数 anchor_cols は1以上を指定してください。")
    if inp.anchor_rows < 1:
        raise ValueError("アンカー縦段数 anchor_rows は1以上を指定してください。")
    if inp.anchor_pitch_h <= 0 or inp.anchor_pitch_v <= 0:
        raise ValueError("アンカーピッチは正の値を指定してください。")

    # アンカー有効断面積（ねじ部）
    # JIS B 1220 実績換算：A_bolt ≈ 0.75 × π/4 × d²（ねじ有効断面積率75%）
    d = inp.d_anchor
    A_bolt = 0.75 * math.pi / 4.0 * d ** 2  # mm²

    # 引張側アンカー本数（上段 = 横方向本数）
    n_tension = inp.anchor_cols
    if n_tension == 0:
        raise ValueError("アンカー横本数がゼロです。anchor_cols を見直してください。")

    # 引張合力・1本あたり引張力
    T_total = M / inp.e_anchor          # kN（M[kN·mm] / e[mm]）
    T_anchor = T_total / n_tension      # kN/本
    sigma_anchor_t = T_anchor * 1e3 / A_bolt  # N/mm²

    # せん断力
    V_anchor = H / inp.n_anchor         # kN/本
    tau_anchor_v = V_anchor * 1e3 / A_bolt  # N/mm²

    # 引張・せん断の組み合わせ比率（楕円相関式）
    comb_ratio = (sigma_anchor_t / allow.anchor_tension) ** 2 + \
                 (tau_anchor_v / allow.anchor_shear) ** 2

    # ── 必要埋込長（逆算）────────────────────────────────────────
    # N_cone = 0.5 × √f'c × π × h_ef²  [N]  ≥ T_total [kN]
    # h_ef_req = √( T_total×10³ / (0.5×√f'c×π) )
    seismic_factor = 1.5 if inp.seismic_case else 1.0
    T_req_N = T_total * 1e3 / seismic_factor   # 割増なしの必要耐力 [N]
    denom = 0.5 * math.sqrt(inp.f_c) * math.pi
    h_ef_req = math.sqrt(T_req_N / denom) if denom > 0 else 0.0  # mm（必要埋込長）
    # 10d との比較（道示 後施工アンカー標準埋込深さ = 10d）
    h_ef_std = 10.0 * d
    h_ef_use = max(h_ef_req, h_ef_std)   # 採用埋込長（必要値と標準値の大きい方）

    # 採用埋込長での耐力確認
    N_cone_N    = 0.5 * math.sqrt(inp.f_c) * math.pi * h_ef_use ** 2  # N
    N_cone_kN   = N_cone_N / 1e3
    N_cone_allow = N_cone_kN * seismic_factor

    # 縁辺破壊チェック（c_edge ≥ 6d，道示 コンクリート橋編 11.3.2）
    c_min_required = 6.0 * d
    edge_ratio = inp.c_edge / c_min_required

    return {
        "A_bolt":          A_bolt,
        "n_tension":       n_tension,
        "T_total":         T_total,
        "T_anchor":        T_anchor,
        "V_anchor":        V_anchor,
        "sigma_anchor_t":  sigma_anchor_t,
        "tau_anchor_v":    tau_anchor_v,
        "comb_ratio":      comb_ratio,
        "h_ef_req":        h_ef_req,        # 必要埋込長 [mm]
        "h_ef_std":        h_ef_std,        # 標準埋込長 10d [mm]
        "h_ef":            h_ef_use,        # 採用埋込長 [mm]
        "N_cone_allow":    N_cone_allow,
        "T_total_for_cone": T_total,
        "edge_ratio":      edge_ratio,
        "c_min_required":  c_min_required,
    }


# ===========================================================================
# 判定・余裕率
# ===========================================================================

def judge(actual: float, allowable: float, label: str) -> tuple[str, float]:
    """
    余裕率 = allowable / actual を計算し OK/NG を返す
    """
    if actual <= 0.0:
        return "OK(無応力)", float("inf")
    if allowable <= 0.0:
        raise ValueError(f"{label}: 許容値がゼロです。")
    margin = allowable / actual
    result = "OK" if margin >= 1.0 else "NG"
    return result, margin


# ===========================================================================
# レポート出力
# ===========================================================================

def print_report(inp: BracketInput, res: BracketResult) -> None:
    sep = "=" * 70
    sub = "-" * 70

    print(sep)
    print("  沓座拡幅型 落橋防止装置ブラケット 構造計算書")
    print("  道路橋示方書（鋼橋編・コンクリート橋編）準拠")
    print(sep)

    print("\n【1. 入力パラメータ】")
    print(sub)
    print(f"  上部工自重                W        = {inp.W:>10.2f}  kN")
    print(f"  設計水平震度              Kh       = {inp.Kh:>10.3f}  -")
    print(f"  ブラケット基数            N        = {inp.N:>10d}  基")
    print(f"  材質                                 {inp.material}")
    print(f"  プレート厚                t_pl     = {inp.t_pl:>10.1f}  mm")
    print(f"  プレート幅（根元）        b_pl     = {inp.b_pl:>10.1f}  mm")
    print(f"  突出長さ                  L_b      = {inp.L_b:>10.1f}  mm")
    print(f"  リブ有無                             {'あり' if inp.has_rib else 'なし'}")
    if inp.has_rib:
        print(f"  リブ厚                    t_rib    = {inp.t_rib:>10.1f}  mm")
        print(f"  リブ高さ                  h_rib    = {inp.h_rib:>10.1f}  mm")
    print(f"  アンカー形式                         {inp.anchor_type}アンカー")
    print(f"  アンカー径                d_anchor = {inp.d_anchor:>10.1f}  mm")
    print(f"  横方向本数×ピッチ        {inp.anchor_cols}本 × {inp.anchor_pitch_h:.0f}mm")
    print(f"  縦方向段数×ピッチ        {inp.anchor_rows}段 × {inp.anchor_pitch_v:.0f}mm")
    print(f"  合計本数                  n_anchor = {inp.n_anchor:>10d}  本")
    print(f"  引張圧縮間距離            e_anchor = {inp.e_anchor:>10.1f}  mm")
    print(f"  コンクリート縁辺距離      c_edge   = {inp.c_edge:>10.1f}  mm")
    print(f"  コンクリート基準強度      f'c      = {inp.f_c:>10.1f}  N/mm²")
    print(f"  地震時割増                           {'適用 (×1.5)' if inp.seismic_case else '不適用'}")

    allow = res.allowable
    print("\n【2. 許容応力度】")
    print(sub)
    print(f"  曲げ応力度（鋼材）        σ_all    = {allow.sigma_b:>10.2f}  N/mm²")
    print(f"  せん断応力度（鋼材）      τ_all    = {allow.tau:>10.2f}  N/mm²")
    print(f"  合成応力度（鋼材）        σ_v_all  = {allow.sigma_v:>10.2f}  N/mm²")
    print(f"  溶接部（隅肉）            σ_w_all  = {allow.sigma_weld:>10.2f}  N/mm²")
    print(f"  アンカー引張              σ_t_all  = {allow.anchor_tension:>10.2f}  N/mm²")
    print(f"  アンカーせん断            τ_v_all  = {allow.anchor_shear:>10.2f}  N/mm²")
    print(f"  コンクリート支圧          f_b_all  = {allow.concrete_bearing:>10.2f}  N/mm²")

    print("\n【3. 荷重計算】")
    print(sub)
    print(f"  鉛直分担力  V = W / N")
    print(f"            V = {inp.W} / {inp.N} = {res.V:.3f}  kN")
    print(f"  水平力      H = Kh × V")
    print(f"            H = {inp.Kh} × {res.V:.3f} = {res.H:.3f}  kN")
    print(f"  根部曲げ M = H × L_b")
    print(f"            M = {res.H:.3f} × {inp.L_b} = {res.M:.1f}  kN·mm")

    print("\n【4. ブラケット根部断面算定】")
    print(sub)
    print(f"  断面係数          Z   = b×t²/6 {'+ リブ' if inp.has_rib else ''}")
    print(f"                    Z   = {res.Z_pl:.1f}  mm³")
    print(f"  せん断有効断面積  A_w = b×t = {res.A_w:.1f}  mm²")
    print()
    print(f"  曲げ応力度  σ_b = M / Z")
    print(f"            σ_b = {res.M*1e3:.1f} N·mm / {res.Z_pl:.1f} mm³")
    print(f"                = {res.sigma_b:.2f}  N/mm²    許容: {allow.sigma_b:.2f}  N/mm²")
    j, m = res.judgements.get("sigma_b", "?"), res.margins.get("sigma_b", 0.0)
    print(f"            → 余裕率 {m:.3f}  [{j}]")

    print()
    print(f"  せん断応力度  τ = H / A_w")
    print(f"            τ = {res.H*1e3:.1f} N / {res.A_w:.1f} mm²")
    print(f"              = {res.tau:.2f}  N/mm²    許容: {allow.tau:.2f}  N/mm²")
    j, m = res.judgements.get("tau", "?"), res.margins.get("tau", 0.0)
    print(f"            → 余裕率 {m:.3f}  [{j}]")

    print()
    print(f"  合成応力度  σ_v = √(σ_b² + 3τ²)  ← Von Mises")
    print(f"            σ_v = √({res.sigma_b:.2f}² + 3×{res.tau:.2f}²)")
    print(f"                = {res.sigma_v:.2f}  N/mm²    許容: {allow.sigma_v:.2f}  N/mm²")
    j, m = res.judgements.get("sigma_v", "?"), res.margins.get("sigma_v", 0.0)
    print(f"            → 余裕率 {m:.3f}  [{j}]")

    print("\n【5. アンカー部検討】")
    print(sub)
    A_bolt_disp = res.T_anchor * 1e3 / res.sigma_anchor_t if res.sigma_anchor_t > 0 else 0.0
    print(f"  アンカー有効断面積  A_bolt = 0.75×π/4×d²")
    print(f"                    A_bolt = {A_bolt_disp:.1f}  mm²")
    print()
    T_total_disp = res.T_anchor * inp.anchor_cols
    print(f"  引張合力  T_total = M / e_anchor")
    print(f"          T_total = {res.M:.1f} / {inp.e_anchor:.1f} = {T_total_disp:.3f}  kN")
    print(f"  引張/本  T       = {res.T_anchor:.3f}  kN")
    print(f"  引張応力度 σ_t   = {res.sigma_anchor_t:.2f}  N/mm²    許容: {allow.anchor_tension:.2f}  N/mm²")
    j, m = res.judgements.get("anchor_tension", "?"), res.margins.get("anchor_tension", 0.0)
    print(f"            → 余裕率 {m:.3f}  [{j}]")

    print()
    print(f"  せん断/本  V     = {res.V_anchor:.3f}  kN")
    print(f"  せん断応力度 τ_v = {res.tau_anchor_v:.2f}  N/mm²    許容: {allow.anchor_shear:.2f}  N/mm²")
    j, m = res.judgements.get("anchor_shear", "?"), res.margins.get("anchor_shear", 0.0)
    print(f"            → 余裕率 {m:.3f}  [{j}]")

    print()
    comb_val = 1.0 / res.margins.get("anchor_comb", float("inf")) if res.margins.get("anchor_comb", float("inf")) != float("inf") else 0.0
    j_comb = res.judgements.get("anchor_comb", "?")
    print(f"  引張・せん断組み合わせ（楕円相関式）")
    print(f"  (σ_t/σ_t_all)² + (τ_v/τ_v_all)² = {comb_val:.3f}  ≤ 1.0  [{j_comb}]")

    print()
    h_ef_disp = 10.0 * inp.d_anchor
    print(f"  コンクリート破壊コーン耐力（引張，h_ef=10d={h_ef_disp:.0f}mm 仮定）")
    print(f"  N_cone = 0.5×√f'c×π×h_ef²")
    print(f"         = 0.5×√{inp.f_c}×π×{h_ef_disp:.0f}² × 1.5（地震時）")
    print(f"         = {res.concrete_cone_load:.2f}  kN    作用: {T_total_disp:.3f}  kN")
    j, m = res.judgements.get("cone", "?"), res.margins.get("cone", 0.0)
    print(f"            → 余裕率 {m:.3f}  [{j}]")

    print()
    j_edge = res.judgements.get("edge", "?")
    print(f"  縁辺破壊チェック（c_edge ≥ 6d = {res.edge_check:.0f} mm）")
    print(f"  c_edge = {inp.c_edge:.0f} mm  [{j_edge}]")

    print()
    print(sep)
    all_ok = all(v in ("OK", "OK(無応力)") for v in res.judgements.values())
    overall = "【OK】全項目 許容値以内" if all_ok else "【NG】一部項目が許容値を超過"
    print(f"  総合判定: {overall}")
    print(sep)

    if not all_ok:
        print("\n  ※NG項目一覧:")
        for key, jdg in res.judgements.items():
            if jdg == "NG":
                print(f"    - {key}: 余裕率 {res.margins[key]:.3f}")


# ===========================================================================
# メイン
# ===========================================================================

def main() -> None:
    # ---------------------------------------------------------
    # ★ ここでパラメータを設定（スクリプト直接実行時）
    # ---------------------------------------------------------
    inp = BracketInput(
        W=3500.0,           # 上部工自重 [kN]
        Kh=0.40,            # 設計水平震度
        N=2,                # ブラケット基数
        material="SM490",   # SS400 or SM490
        t_pl=22.0,          # プレート厚 [mm]
        b_pl=400.0,         # プレート幅（根元断面） [mm]
        L_b=350.0,          # 突出長さ [mm]
        has_rib=True,       # リブ有無
        t_rib=16.0,         # リブ厚 [mm]
        h_rib=200.0,        # リブ高さ [mm]
        anchor_type="後施工",
        d_anchor=30.0,
        anchor_cols=3,
        anchor_rows=2,
        anchor_pitch_h=150.0,
        anchor_pitch_v=150.0,
        c_edge=150.0,       # コンクリート縁辺距離 [mm]
        f_c=24.0,           # コンクリート基準強度 [N/mm²]
        seismic_case=True,  # 地震時割増 適用
    )

    try:
        # 1. 許容応力度
        allow = get_allowable_stress(inp.material, inp.seismic_case, inp.f_c)

        # 2. 荷重
        V, H, M = calc_load(inp)

        # 3. ブラケット断面
        br = check_bracket(inp, H, M, allow)

        # 4. アンカー
        anc = check_anchor(inp, H, M, allow)

        # 5. 結果オブジェクト組み立て
        res = BracketResult(
            V=V,
            H=H,
            M=M,
            Z_pl=br["Z_pl"],
            A_w=br["A_w"],
            sigma_b=br["sigma_b"],
            tau=br["tau"],
            sigma_v=br["sigma_v"],
            T_anchor=anc["T_anchor"],
            V_anchor=anc["V_anchor"],
            sigma_anchor_t=anc["sigma_anchor_t"],
            tau_anchor_v=anc["tau_anchor_v"],
            concrete_cone_load=anc["N_cone_allow"],
            edge_check=anc["c_min_required"],
            allowable=allow,
        )

        # 6. 判定・余裕率
        res.judgements["sigma_b"], res.margins["sigma_b"] = judge(
            res.sigma_b, allow.sigma_b, "曲げ応力度")
        res.judgements["tau"], res.margins["tau"] = judge(
            res.tau, allow.tau, "せん断応力度")
        res.judgements["sigma_v"], res.margins["sigma_v"] = judge(
            res.sigma_v, allow.sigma_v, "合成応力度")
        res.judgements["anchor_tension"], res.margins["anchor_tension"] = judge(
            res.sigma_anchor_t, allow.anchor_tension, "アンカー引張")
        res.judgements["anchor_shear"], res.margins["anchor_shear"] = judge(
            res.tau_anchor_v, allow.anchor_shear, "アンカーせん断")

        # 組み合わせ（楕円相関式）: 比率 ≤ 1.0
        comb = anc["comb_ratio"]
        comb_ok = "OK" if comb <= 1.0 else "NG"
        res.judgements["anchor_comb"] = comb_ok
        res.margins["anchor_comb"] = (1.0 / comb) if comb > 0 else float("inf")

        # 破壊コーン（引張合力 vs コーン耐力）
        T_total = anc["T_total"]
        res.judgements["cone"], res.margins["cone"] = judge(
            T_total, anc["N_cone_allow"], "破壊コーン")

        # 縁辺距離
        edge_ok = "OK" if anc["edge_ratio"] >= 1.0 else "NG"
        res.judgements["edge"] = edge_ok
        res.margins["edge"] = anc["edge_ratio"]

        # 7. 出力
        print_report(inp, res)

    except (ValueError, ZeroDivisionError) as e:
        print(f"\n[エラー] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
