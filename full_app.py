import streamlit as st
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import yaml
import copy
import numpy as np
from src.simulator import run_mc_fixed_fire
from src.visualizer import create_fire_timeline_chart
from src.utils import fmt_oku
from src.tax_utils import gross_to_net_monthly
from src.analytics import calc_depletion_age, get_bankrupt_depletion_ages

# =============================================================================
# 定数
# =============================================================================
_DEFAULT_GROSS_H         = 600   # 夫の年収デフォルト（税引き前・万円）
_DEFAULT_GROSS_W         = 550   # 妻の年収デフォルト（税引き前・万円）
_DEFAULT_AGE             = 35    # 年齢デフォルト（歳）
_MIN_AGE                 = 20    # 年齢入力下限
_MAX_AGE                 = 70    # 年齢入力上限
_DEFAULT_EXPENSE         = 28    # 月間支出デフォルト（万円）
_DEFAULT_ASSETS          = 2000  # 金融資産デフォルト（万円）
_DEFAULT_LEAVE_MONTHS    = 12    # 育休デフォルト（月）
_DEFAULT_LEAVE_INCOME    = 20    # 育休月収デフォルト（万円）
_DEFAULT_PRENATAL_MONTHS = 2     # 産前休業デフォルト（月）
_CASH_RATIO              = 0.3   # 現金比率（初期資産配分）
_STOCKS_RATIO            = 0.7   # 株式比率（初期資産配分）
_MC_ITERATIONS           = 1000  # MCシミュレーション試行回数
_DEFAULT_RENT            = 15    # 家賃デフォルト（万円）
_DEFAULT_MORTGAGE        = 10    # 住宅ローンデフォルト（万円/月）

_EMP_OPTIONS_H = ["会社員", "個人事業主", "専業主夫"]
_EMP_OPTIONS_W = ["会社員", "個人事業主", "専業主婦"]
_EMP_HELP = (
    "会社員：年金が手厚く、収入も毎年少しずつ上がる想定で計算します。\n"
    "個人事業主：国民年金のみ。収入は一定として計算します。\n"
    "専業主夫/主婦：収入なし。年金は国民年金のみ。"
)
_LEAVE_HELP  = "育休中にもらえる給付金の月額。目安は給与の50〜67%程度です。"
_TANTAN_HELP = "この子が何歳になったら時短勤務を終えるか。0なら時短なし。"
_ORDINALS      = ["第1子", "第2子", "第3子", "第4子"]
_DEFAULT_BIRTHS = [6, 30, 54, 78]  # 子ごとの誕生予定日オフセット（月）

# =============================================================================
# ページ設定・CSS
# =============================================================================
st.set_page_config(
    page_title="共働きFIREシミュレーター【フル版】",
    page_icon="📋",
    layout="wide",
)


def inject_custom_css():
    st.markdown("""
        <style>
        /* メイン背景とフォント */
        .main {
            background-color: #f8f9fa;
        }
        h1, h2, h3 {
            color: #1e3a8a;
            font-weight: 700;
        }
        /* メトリクスの装飾 */
        [data-testid="stMetricValue"] {
            font-size: 2.2rem !important;
            color: #1e40af !important;
        }
        /* カード風のコンテナ */
        .stExpander, .stTabs {
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            padding: 10px;
            border: none !important;
        }
        /* ボタンの強調 */
        .stButton>button {
            width: 100%;
            border-radius: 8px;
            height: 3em;
            background-color: #1e40af !important;
            font-weight: 600;
        }
        /* インフォメーションボックス */
        .stAlert {
            border-radius: 10px;
        }
        </style>
    """, unsafe_allow_html=True)


inject_custom_css()

# =============================================================================
# アクセスコード認証
# =============================================================================
def check_password() -> bool:
    """Returns `True` if the user had the correct password."""
    def password_entered():
        valid_codes = st.secrets.get("access_codes", [])
        if st.session_state["password"] in valid_codes:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>会員限定コンテンツ</h2>", unsafe_allow_html=True)
        st.text_input(
            "アクセスコードを入力してください", type="password", on_change=password_entered, key="password"
        )
        st.info("このページは有料フル版です。note記事の有料部分にアクセスコードが記載されています。")
        st.markdown("[▶ 無料デモはこちら](https://m2sbgpwr7ogazgwrxsqqsg.streamlit.app/)")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "アクセスコードを入力してください", type="password", on_change=password_entered, key="password"
        )
        st.error("アクセスコードが正しくありません。")
        return False
    return True


if not check_password():
    st.stop()

# =============================================================================
# 純粋関数（UIなし・テスト可能）
# =============================================================================
def _build_children_config(children_ui: list, income_h: int, income_w: int) -> tuple:
    """子どもUI入力から simulator に渡す5つの config リストを構築する。

    Returns:
        (edu_children, maternity, w_reduced, h_parental, h_reduced)
    """
    edu_children, maternity, w_reduced, h_parental, h_reduced = [], [], [], [], []
    for cd in children_ui:
        n  = cd["name"]
        bs = cd["birth"].strftime('%Y/%m/%d')
        edu_children.append({
            'name': n, 'birthdate': bs, 'nursery': 'public', 'kindergarten': 'public',
            'elementary': 'public', 'junior_high': 'public', 'high': 'public', 'university': 'national',
            'policy': cd.get('policy', 'standard'),
        })
        maternity.append({
            'child': n, 'months_before': cd["w_lp"], 'months_after': cd["w_la"],
            'monthly_income': cd["w_li"] * 10000,
        })
        if cd["w_re"] * 12 > cd["w_la"]:
            w_reduced.append({
                'child': n, 'start_months_after': cd["w_la"], 'end_months_after': cd["w_re"] * 12,
                'income_ratio': (cd["w_ri"] * 10000) / (income_w * 10000) if income_w > 0 else 0,
            })
        h_parental.append({
            'child': n, 'months_after': cd["h_la"],
            'monthly_income': cd["h_li"] * 10000,
            'monthly_income_after_180days': cd["h_li"] * 10000,
        })
        if cd["h_re"] * 12 > cd["h_la"]:
            h_reduced.append({
                'child': n, 'start_months_after': cd["h_la"], 'end_months_after': cd["h_re"] * 12,
                'income_ratio': (cd["h_ri"] * 10000) / (income_h * 10000) if income_h > 0 else 0,
            })
    return edu_children, maternity, w_reduced, h_parental, h_reduced


def _build_simulation_config(
    base_cfg: dict, *,
    age_h: int, age_w: int, type_h: str, type_w: str,
    income_h: float, income_w: float, gross_h: int, gross_w: int, monthly_exp: int,
    housing_type: str, rent: int, mortgage_payment: int, mortgage_end_date,
    edu_children: list, maternity: list, w_reduced: list,
    h_parental: list, h_reduced: list,
    husband_post_fire_income: int = 0,
    wife_post_fire_income: int = 0,
    husband_side_fire_until: int = 65,
    wife_side_fire_until: int = 65,
) -> dict:
    """ユーザー入力を base_cfg に適用して simulator 用の完全な config を返す。

    Args:
        income_h: 夫の手取り月収（万円）- キャッシュフロー計算に使用
        income_w: 妻の手取り月収（万円）- キャッシュフロー計算に使用
        gross_h:  夫の税引き前年収（万円）- 厚生年金の標準報酬月額計算に使用
        gross_w:  妻の税引き前年収（万円）- 厚生年金の標準報酬月額計算に使用
        husband_post_fire_income: 夫のFIRE後副収入（万円/月）
        wife_post_fire_income:    妻のFIRE後副収入（万円/月）
        husband_side_fire_until:  夫の副収入終了年齢（歳）
        wife_side_fire_until:     妻の副収入終了年齢（歳）
    """
    cfg = copy.deepcopy(base_cfg)
    current_year = datetime.today().year
    base_growth_rate = cfg['simulation']['standard']['income_growth_rate']

    cfg['fire']['expense_categories']['enabled'] = False
    cfg['fire']['manual_annual_expense'] = monthly_exp * 12

    if housing_type == '賃貸':
        cfg['mortgage']['enabled'] = False
        cfg['house_maintenance']['enabled'] = False
        cfg['simulation']['monthly_rent'] = rent * 10000
    else:
        cfg['simulation']['monthly_rent'] = 0
        cfg['mortgage']['monthly_payment'] = mortgage_payment * 10000
        cfg['mortgage']['end_date'] = f'{mortgage_end_date}/12/31'

    cfg['simulation'].update({
        'start_age': age_h,
        'start_age_w': age_w,
        'husband_income': income_h * 10000,
        'wife_income': income_w * 10000,
        'maternity_leave': maternity,
        'wife_reduced_hours': w_reduced,
        'husband_parental_leave': h_parental,
        'husband_reduced_hours': h_reduced,
        'husband_post_fire_income': husband_post_fire_income * 10000,
        'wife_post_fire_income': wife_post_fire_income * 10000,
        'husband_side_fire_until': husband_side_fire_until,
        'wife_side_fire_until': wife_side_fire_until,
    })
    cfg['education']['children'] = edu_children

    # 標準報酬月額（税引き前月収）= 年収 / 12 — 厚生年金の受給額計算に使用
    gross_monthly_h = gross_h * 10000 / 12
    gross_monthly_w = gross_w * 10000 / 12

    if len(cfg['pension']['people']) >= 1:
        cfg['pension']['people'][0]['birthdate'] = f'{current_year - age_h}/07/01'
        cfg['pension']['people'][0]['pension_type'] = 'employee' if type_h == '会社員' else 'national'
        # 過去の年金実績はUI非入力のため0にリセット（avg_monthly_salary×全加入期間で計算）
        cfg['pension']['people'][0]['past_pension_base_annual'] = 0
        cfg['pension']['people'][0]['past_contribution_months'] = 0
        if type_h == '会社員':
            cfg['pension']['people'][0]['avg_monthly_salary'] = gross_monthly_h
    if len(cfg['pension']['people']) >= 2:
        cfg['pension']['people'][1]['birthdate'] = f'{current_year - age_w}/07/01'
        cfg['pension']['people'][1]['pension_type'] = 'employee' if type_w == '会社員' else 'national'
        cfg['pension']['people'][1]['past_pension_base_annual'] = 0
        cfg['pension']['people'][1]['past_contribution_months'] = 0
        if type_w == '会社員':
            cfg['pension']['people'][1]['avg_monthly_salary'] = gross_monthly_w

    cfg['simulation']['husband_income_growth_rate'] = base_growth_rate if type_h == '会社員' else 0.0
    cfg['simulation']['wife_income_growth_rate']    = base_growth_rate if type_w == '会社員' else 0.0
    if type_h == '専業主夫':
        cfg['simulation']['husband_income'] = 0
    if type_w == '専業主婦':
        cfg['simulation']['wife_income'] = 0

    return cfg


# =============================================================================
# UI 部品
# =============================================================================
def _leave_inputs(label: str, prefix: str, ci: int, disabled: bool,
                  default_leave: int, default_income: int, maternity: bool = False) -> dict:
    """育休・時短の入力コンテナを描画し、値の dict を返す。

    Args:
        label:          コンテナ見出し（例: "夫の育休・時短"）
        prefix:         widget key のプレフィックス（"h" or "w"）
        ci:             子どものインデックス
        disabled:       専業主夫/主婦のとき True
        default_leave:  育休(月) or 産後(月) のデフォルト値
        default_income: 時短月収のデフォルト値
        maternity:      True のとき産前/産後行を追加（妻用）

    Returns:
        {"la", "li", "re", "ri"} ＋ maternity=True のとき "lp" も含む
    """
    with st.container(border=True):
        st.caption(label)
        _a, _b = st.columns(2)
        if maternity:
            with _a:
                lp = st.number_input("産前(月)", 0, 6, _DEFAULT_PRENATAL_MONTHS, step=1,
                    key=f"{prefix}_lp_{ci}", disabled=disabled)
            with _b:
                la = st.number_input("産後(月)", 0, 24, default_leave, step=1,
                    key=f"{prefix}_la_{ci}", disabled=disabled)
            _a, _b = st.columns(2)
            with _a:
                li = st.number_input("育休月収(万)", 0, 50, _DEFAULT_LEAVE_INCOME, step=1,
                    key=f"{prefix}_li_{ci}", disabled=disabled, help=_LEAVE_HELP)
            with _b:
                re = st.number_input("時短終了(歳)", 0, 10, 0, step=1,
                    key=f"{prefix}_re_{ci}", disabled=disabled, help=_TANTAN_HELP)
            ri = st.number_input("時短月収(万)", 0, 60, default_income, step=1,
                key=f"{prefix}_ri_{ci}", disabled=(disabled or re == 0))
        else:
            lp = None
            with _a:
                la = st.number_input("育休(月)", 0, 12, default_leave, step=1,
                    key=f"{prefix}_la_{ci}", disabled=disabled)
            with _b:
                li = st.number_input("育休月収(万)", 0, 60, _DEFAULT_LEAVE_INCOME, step=1,
                    key=f"{prefix}_li_{ci}", disabled=disabled, help=_LEAVE_HELP)
            _a, _b = st.columns(2)
            with _a:
                re = st.number_input("時短終了(歳)", 0, 10, 0, step=1,
                    key=f"{prefix}_re_{ci}", disabled=disabled, help=_TANTAN_HELP)
            with _b:
                ri = st.number_input("時短月収(万)", 0, 60, default_income, step=1,
                    key=f"{prefix}_ri_{ci}", disabled=(disabled or re == 0))

        if re > 0 and re * 12 <= la:
            st.warning(f"⚠️ 時短終了({re}歳)が育休終了({la}ヶ月後)より早い")

        result = {"la": la, "li": li, "re": re, "ri": ri}
        if lp is not None:
            result["lp"] = lp
        return result


def _render_guide_tab(target_rate: int) -> None:
    """シミュレーション解釈ガイドタブの静的コンテンツを描画する。"""
    st.markdown("### シミュレーション解釈ガイド")
    with st.expander("なぜ『一本の線』ではなく『範囲』で考えるのか？", expanded=True):
        st.write("""
        将来の資産推移を一本の線で予測することは、天気予報で「明日の12時00分に雨が0.5mm降る」と断定するようなものです。
        実際には、市場は常に変動します。このシミュレーターでは、**1,000通りの異なる未来（好景気、不景気、数年続く暴落など）**を計算し、
        各シナリオでFIREが実現できるタイミングの分布を算出しています。
        """)
    with st.expander("暴落や暴騰はどのように考慮されていますか？"):
        st.write("""
        単純なランダム計算ではなく、実際の株式市場の動きに近い計算方法を使っています：
        1. **相場の揺り戻し**: 上がりすぎた後は下がりやすく、下がりすぎた後は戻りやすい動きを再現しています。
        2. **荒れ相場の連鎖**: 相場が大きく動く時期は続く傾向があるため、その連鎖も考慮しています。
        3. **下落の速さ**: 暴落は急激で、回復はゆっくりという非対称な動きも再現しています。
        これにより、リーマンショックのような「数年に一度の大暴落」にも耐えられるかを検証できます。
        """)
    st.markdown("---")
    st.markdown("#### 目標成功確率の見方")
    st.info(f"""
**{target_rate}%の意味**: リーマンショック規模の暴落を含む1,000通りの市場シナリオのうち、
**{target_rate}%のシナリオ**でこの時期にFIRE可能です。

残り{100 - target_rate}%のシナリオでは、市場環境によってFIREが数年先にずれる可能性があります。
目標確率を変えると、FIRE時期がどう変わるか「詳細シミュレーション設定」タブで確認できます。
""")


# =============================================================================
# ヘッダー・設定ファイル読み込み
# =============================================================================
st.markdown("<h1 style='text-align: center;'>共働きFIREシミュレーター <span style='color:#6366f1'>【フル版】</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 2rem;'>〜 理想的な家族の未来を、データで具現化する 〜</p>", unsafe_allow_html=True)

with open("demo_config.yaml", "r", encoding="utf-8") as f:
    base_cfg = yaml.safe_load(f)

# =============================================================================
# サイドバー入力
# =============================================================================
with st.sidebar:
    st.header("世帯の基本情報")
    _sh, _sw = st.columns(2)
    with _sh:
        st.markdown("**夫**")
        type_h = st.selectbox("雇用形態　", _EMP_OPTIONS_H, index=0, help=_EMP_HELP)
        _income_h_disabled = (type_h == "専業主夫")
        gross_h = st.number_input("年収（税引き前・万円）", value=0 if _income_h_disabled else _DEFAULT_GROSS_H,
            min_value=0, step=10, disabled=_income_h_disabled,
            help="源泉徴収票の「支払金額」を入力してください。手取りではなく税引き前の金額です。")
        income_h = gross_to_net_monthly(gross_h, type_h)
        if not _income_h_disabled:
            st.caption(f"手取り目安: 約{income_h:.0f}万円/月")
        age_h = st.number_input("年齢", value=_DEFAULT_AGE, min_value=_MIN_AGE, max_value=_MAX_AGE, step=1)
    with _sw:
        st.markdown("**妻**")
        type_w = st.selectbox("雇用形態", _EMP_OPTIONS_W, index=0, help=_EMP_HELP)
        _income_w_disabled = (type_w == "専業主婦")
        gross_w = st.number_input("年収（税引き前・万円） ", value=0 if _income_w_disabled else _DEFAULT_GROSS_W,
            min_value=0, step=10, disabled=_income_w_disabled,
            help="源泉徴収票の「支払金額」を入力してください。手取りではなく税引き前の金額です。")
        income_w = gross_to_net_monthly(gross_w, type_w)
        if not _income_w_disabled:
            st.caption(f"手取り目安: 約{income_w:.0f}万円/月")
        age_w = st.number_input("年齢 ", value=_DEFAULT_AGE, min_value=_MIN_AGE, max_value=_MAX_AGE, step=1)

    st.header("キャッシュフロー")
    housing_type = st.radio("住宅形態", ["持ち家", "賃貸"], horizontal=True)
    if housing_type == "賃貸":
        rent = st.number_input("家賃(万円)", value=_DEFAULT_RENT, min_value=0, step=1,
            help="毎月の家賃。シミュレーション期間中一定として計算します。")
        mortgage_payment = 0
        mortgage_end_date = None
        _expense_help = "食費・光熱費・通信費など住宅費を除く生活費の合計。"
    else:
        rent = 0
        _mc1, _mc2 = st.columns(2)
        with _mc1:
            mortgage_payment = st.number_input("ローン月額(万円)", value=_DEFAULT_MORTGAGE,
                min_value=0, step=1, help="毎月の住宅ローン返済額。")
        with _mc2:
            mortgage_end_date = st.number_input("返済完了(西暦)", value=2060,
                min_value=2025, max_value=2100, step=1, help="返済完了の年（12月末扱い）。")
        _expense_help = "食費・光熱費・通信費など住宅費を除く生活費の合計。"
    expense = st.number_input("生活費(万円)", value=_DEFAULT_EXPENSE, min_value=5, step=1,
        help=_expense_help)
    _housing_cost = rent if housing_type == "賃貸" else mortgage_payment
    _total_exp = expense + _housing_cost
    st.caption(f"支出合計:  \n{_housing_cost}万(住宅費) ＋ {expense}万(生活費) ＝ **{_total_exp}万円/月**")
    assets = st.number_input("金融資産(万円)", value=_DEFAULT_ASSETS, min_value=0, step=100,
        help="現金・株式・投資信託などを合計した金額を入力してください。")

    st.header("FIRE後の副収入（サイドFIRE）")
    st.write("完全リタイアではなく、パートや副業などで部分的に収入を得る場合に入力してください。")
    _sf_h, _sf_w = st.columns(2)
    with _sf_h:
        husband_post_fire_income = st.number_input(
            "夫の副収入（万円/月）",
            value=0, min_value=0, step=1,
            help="FIRE後に夫が得るパート・副業・フリーランスなどの月間労働収入。"
        )
        husband_side_fire_until = st.number_input(
            "夫の副収入 終了年齢（歳）",
            value=65, min_value=0, max_value=100, step=1,
            help="夫の副収入が何歳まで続くか。この年齢に達したら0として計算します。"
        )
    with _sf_w:
        wife_post_fire_income = st.number_input(
            "妻の副収入（万円/月）",
            value=0, min_value=0, step=1,
            help="FIRE後に妻が得るパート・副業・フリーランスなどの月間労働収入。"
        )
        wife_side_fire_until = st.number_input(
            "妻の副収入 終了年齢（歳）",
            value=65, min_value=0, max_value=100, step=1,
            help="妻の副収入が何歳まで続くか。この年齢に達したら0として計算します。"
        )

    st.divider()
    st.caption("詳細な計算設定は note のマニュアルを参照してください。")

# =============================================================================
# メインコンテンツ: ライフイベント・詳細設定
# =============================================================================
target_rate = 90

st.subheader("ライフイベント・詳細設定")
tab_input, tab_advanced = st.tabs(["育休・子供の設定", "詳細シミュレーション設定"])

with tab_input:
    _nc_col, _ = st.columns([1, 3])
    with _nc_col:
        num_children = st.number_input("子どもの人数", min_value=1, max_value=4, value=1, step=1)

    children_ui = []
    for _ci in range(num_children):
        with st.expander(_ORDINALS[_ci], expanded=(_ci == 0)):
            _bc1, _bc2 = st.columns([2, 2])
            with _bc1:
                _birth = st.date_input(
                    "誕生日（または予定日）",
                    value=date.today() + relativedelta(months=_DEFAULT_BIRTHS[_ci]),
                    key=f"birth_{_ci}",
                    help="この日付を基準に教育費・育休期間を算出します。",
                )
            with _bc2:
                _edu_policy = st.selectbox(
                    "教育方針",
                    options=["standard", "moderate", "private_heavy"],
                    format_func=lambda x: {
                        "standard": "標準（公立小中高＋国立大）",
                        "moderate": "やや手厚め（高校のみ私立）",
                        "private_heavy": "私立重視（私立中高＋私立文系大）",
                    }[x],
                    index=0,
                    key=f"edu_policy_{_ci}",
                    help="公立小中高+国立大: 〜693万 / 公立小中+私立高+国立大: 〜855万 / 公立小+私立中高+私立文系大: 〜1,272万（子1人あたり合計）",
                )
            col_h, col_w = st.columns(2)  # 夫LEFT・妻RIGHT
            with col_h:
                h = _leave_inputs("夫の育休・時短", "h", _ci, type_h == "専業主夫",
                    default_leave=_DEFAULT_LEAVE_MONTHS if _ci == 0 else 0, default_income=int(income_h))
            with col_w:
                w = _leave_inputs("妻の育休・時短", "w", _ci, type_w == "専業主婦",
                    default_leave=_DEFAULT_LEAVE_MONTHS, default_income=int(income_w), maternity=True)
            children_ui.append({
                "birth": _birth, "name": f"子{_ci+1}", "policy": _edu_policy,
                "w_lp": w.get("lp", 0), "w_la": w["la"], "w_li": w["li"], "w_re": w["re"], "w_ri": w["ri"],
                "h_la": h["la"], "h_li": h["li"], "h_re": h["re"], "h_ri": h["ri"],
            })

with tab_advanced:
    st.info("以下の前提条件は固定値です。変更が必要な場合はnoteのマニュアルをご参照ください。")
    _base_growth = base_cfg['simulation']['standard']['income_growth_rate'] * 100
    _h_growth = f"{_base_growth:.0f}%/年" if type_h == '会社員' else "なし（固定）"
    _w_growth = f"{_base_growth:.0f}%/年" if type_w == '会社員' else "なし（固定）"
    st.json({
        "FIRE維持の目標確率": f"{target_rate}%",
        "想定利回り（年率）": f"{base_cfg['simulation']['standard']['annual_return_rate']*100:.0f}%",
        "物価上昇率（年率）": f"{base_cfg['simulation']['standard']['inflation_rate']*100:.0f}%",
        "夫の昇給率（年率）": _h_growth,
        "妻の昇給率（年率）": _w_growth,
        "住宅": (
            f"賃貸 {rent}万円/月（一定）"
            if housing_type == '賃貸'
            else f"持ち家ローン {mortgage_payment}万円/月（{mortgage_end_date}年末まで）"
        ),
        "FIRE後副収入": (
            f"夫{husband_post_fire_income:.0f}万（{husband_side_fire_until}歳まで） + "
            f"妻{wife_post_fire_income:.0f}万（{wife_side_fire_until}歳まで） = "
            f"計{husband_post_fire_income + wife_post_fire_income:.0f}万円/月"
        ),
        "年金受給開始": f"夫{base_cfg['pension']['people'][0].get('override_start_age', 65)}歳 / 妻{base_cfg['pension']['people'][1].get('override_start_age', 65)}歳",
        "教育コース": "、".join(
            "{}: {}".format(
                f"子{i+1}",
                {"standard": "標準（公立中心）", "moderate": "やや手厚め（高校のみ私立）", "private_heavy": "私立重視"}.get(cd.get("policy", "standard"), "標準")
            )
            for i, cd in enumerate(children_ui)
        ) if children_ui else "公立小中高 + 国立大学",
        "資産の内訳（初期）": "現金30% / 株式70%（NISAの初期残高は0円）",
    })

st.markdown("---")

# =============================================================================
# シミュレーション実行・結果表示
# =============================================================================
if st.button("シミュレーションを開始", type="primary"):
    cash      = assets * _CASH_RATIO   * 10000
    stocks    = assets * _STOCKS_RATIO * 10000
    monthly_inc = (income_h + income_w) * 10000
    monthly_exp = expense * 10000
    current_date = datetime.today()

    edu_children, maternity, w_reduced, h_parental, h_reduced = _build_children_config(
        children_ui, income_h, income_w
    )
    cfg = _build_simulation_config(
        base_cfg,
        age_h=age_h, age_w=age_w, type_h=type_h, type_w=type_w,
        income_h=income_h, income_w=income_w, gross_h=gross_h, gross_w=gross_w,
        monthly_exp=monthly_exp,
        housing_type=housing_type, rent=rent,
        mortgage_payment=mortgage_payment, mortgage_end_date=mortgage_end_date,
        edu_children=edu_children, maternity=maternity, w_reduced=w_reduced,
        h_parental=h_parental, h_reduced=h_reduced,
        husband_post_fire_income=husband_post_fire_income,
        wife_post_fire_income=wife_post_fire_income,
        husband_side_fire_until=husband_side_fire_until,
        wife_side_fire_until=wife_side_fire_until,
    )

    progress_bar = st.progress(0)
    status_text  = st.empty()

    def update_progress(progress):
        progress_bar.progress(progress)
        status_text.text(f"1,000通りの未来をシミュレーション中... {int(progress * 100)}%")

    with st.spinner("シミュレーションを実行中..."):
        mc_res = run_mc_fixed_fire(
            cash, stocks, cfg,
            target_success_rate=target_rate / 100.0,
            monthly_income=monthly_inc,
            monthly_expense=monthly_exp,
            scenario="standard",
            iterations=_MC_ITERATIONS,
            progress_callback=update_progress,
        )
        df = mc_res['base_df']
        df['year_offset'] = df['month'] / 12
        df['wife_age']    = age_w + df['year_offset']

    progress_bar.empty()
    status_text.empty()

    st.markdown("## シミュレーション結果")

    if husband_post_fire_income > 0 or wife_post_fire_income > 0:
        st.info(
            f"サイドFIRE設定: 夫 {husband_post_fire_income}万円/月（{husband_side_fire_until}歳まで）、"
            f"妻 {wife_post_fire_income}万円/月（{wife_side_fire_until}歳まで）\n"
            f"FIRE後実質支出 = 支出 − 労働収入 として計算しています。"
        )

    if mc_res.get('impossible'):
        max_rate = int(mc_res['max_achievable_rate'] * 100)
        st.error(
            f"⚠️ 目標{target_rate}%は達成できません。\n\n"
            f"現在の条件では最高でも **{max_rate}%** の確率でしかFIREできません。\n"
            f"生活費を減らすか、金融資産を増やすと改善できます。"
        )
    else:
        fire_month_val = mc_res['fire_month']
        fire_date_val  = mc_res['fire_date']
        fire_age_h_val = mc_res['fire_age_h']
        fire_age_w_val = mc_res['fire_age_w']

        base_df = mc_res['base_df']
        assets_at_fire = (
            base_df.iloc[fire_month_val]['assets']
            if fire_month_val < len(base_df)
            else base_df.iloc[-1]['assets']
        )
        years_to_fire = fire_month_val / 12.0

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            fire_age_label = (
                f"夫{fire_age_h_val:.0f}歳 / 妻{fire_age_w_val:.0f}歳"
                if fire_age_w_val and age_h != age_w else f"{fire_age_h_val:.0f}歳"
            )
            st.metric(f"目標{target_rate}%のFIRE年齢", fire_age_label)
        with col_m2:
            st.metric("必要年数", f"{years_to_fire:.1f}年")
        with col_m3:
            st.metric("FIRE達成時の資産額", fmt_oku(assets_at_fire))

        # ── 破産シナリオ分析 ──────────────────────────────────────────────
        all_paths = mc_res.get("all_paths")
        bankrupt_count = sum(1 for r in mc_res["all_results"] if not r["success"])
        if all_paths is not None and bankrupt_count > 0:
            st.subheader("万が一失敗した場合のリスク分析")
            st.caption(
                "シミュレーション終端（90歳）まで持たなかったシナリオのみを対象とした分析です。"
                "「下位5%」は1,000通りのうち最も悪い50通りの平均的な結果を示します。"
            )
            _col_b1, _col_b2, _col_b3 = st.columns(3)
            with _col_b1:
                _worst_age = calc_depletion_age(mc_res, 0.05, cfg)
                st.metric("最悪ケース枯渇年齢（下位5%）", f"{_worst_age:.0f}歳")
            with _col_b2:
                _p25_age = calc_depletion_age(mc_res, 0.25, cfg)
                st.metric("枯渇年齢（下位25%）", f"{_p25_age:.0f}歳")
            with _col_b3:
                _bankrupt_rate = bankrupt_count / len(mc_res["all_results"]) * 100
                st.metric("破産シナリオ数", f"{_bankrupt_rate:.1f}%（{bankrupt_count}通り）")

            # 枯渇年齢のヒストグラム（破産パスのみ）
            import plotly.express as px
            _depletion_ages = get_bankrupt_depletion_ages(mc_res, cfg)
            if _depletion_ages:
                _fig_hist = px.histogram(
                    x=_depletion_ages,
                    nbins=20,
                    title="資産枯渇年齢の分布（破産シナリオのみ）",
                    labels={"x": "枯渇年齢（夫・歳）", "count": "シナリオ数"},
                )
                _fig_hist.update_layout(
                    xaxis_title="枯渇年齢（夫・歳）",
                    yaxis_title="シナリオ数",
                    showlegend=False,
                    height=300,
                )
                st.plotly_chart(_fig_hist, use_container_width=True)

        tab_chart, tab_guide = st.tabs(["資産予測（確率分布）", "シミュレーション解釈ガイド"])

        with tab_chart:
            st.markdown("#### 1,000通りの未来シミュレーション")
            st.caption(
                f"1,000通りの未来シナリオで90歳まで計算した結果です。"
                f" 目標FIRE時期: {fire_date_val.strftime('%Y年%m月') if fire_date_val else '—'}"
            )
            fire_row = df[df['fire_achieved']].iloc[0] if df['fire_achieved'].any() else None
            if fire_row is not None:
                fig_timeline = create_fire_timeline_chart(
                    current_status={'net_assets': assets * 10000, 'cash_deposits': cash, 'investment_trusts': stocks},
                    fire_target={'recommended_target': assets_at_fire, 'annual_expense': expense * 12 * 10000},
                    fire_achievement={'achieved': False, 'achievement_date': fire_row['date'], 'months_to_fire': int(fire_row['month'])},
                    simulations={'standard': df},
                    config=cfg,
                    monte_carlo_results=mc_res,
                    show_baseline_after_fire=False,
                    current_date=current_date,
                )
                fig_timeline.update_layout(height=500)
                st.plotly_chart(fig_timeline, use_container_width=True)

        with tab_guide:
            _render_guide_tab(target_rate)
