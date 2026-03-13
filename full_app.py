import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import yaml
import copy
import plotly.express as px
import plotly.graph_objects as go
from src.simulator import simulate_future_assets, run_monte_carlo_simulation, run_mc_fixed_fire
from src.visualizer import create_fire_timeline_chart
from src.data_schema import get_column_names

def fmt_oku(yen: float) -> str:
    """円単位の値を億/万円で表記する"""
    man = yen / 10000
    if man >= 10000:
        return f"{man/10000:.1f}億円"
    return f"{man:,.0f}万円"


# ページ設定
st.set_page_config(
    page_title="共働きFIREシミュレーター【フル版】",
    page_icon="📋",
    layout="wide",
)

# --- カスタムCSSの適用 ---
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

# --- Step 1: アクセスコード認証 ---
def check_password():
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
    else:
        return True

if not check_password():
    st.stop()

# --- ヘッダー ---
st.markdown("<h1 style='text-align: center;'>共働きFIREシミュレーター <span style='color:#6366f1'>【フル版】</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 2rem;'>〜 理想的な家族の未来を、データで具現化する 〜</p>", unsafe_allow_html=True)

# --- 設定ファイルの読み込み ---
with open("demo_config.yaml", "r", encoding="utf-8") as f:
    base_cfg = yaml.safe_load(f)

# --- レイアウト: サイドバー ---
with st.sidebar:
    st.header("世帯の基本情報")
    income_h = st.number_input("夫の月収 (手取り/万円)", value=40, min_value=1, step=1, help="現在の手取り月収（ボーナス除外）。")
    age_h = st.number_input("夫の現在の年齢", value=35, min_value=20, max_value=70, step=1)
    type_h = st.selectbox("夫の雇用形態", ["会社員", "個人事業主"], index=0,
        help="会社員：厚生年金+国民年金・収入は毎年2%成長。個人事業主：国民年金のみ・収入は固定。")

    st.divider()
    income_w = st.number_input("妻の月収 (手取り/万円)", value=35, min_value=1, step=1, help="通常勤務時の手取り月収。育休・時短期間以外は一定として計算します。")
    age_w = st.number_input("妻の現在の年齢", value=35, min_value=20, max_value=70, step=1)
    type_w = st.selectbox("妻の雇用形態", ["個人事業主", "会社員"], index=0,
        help="会社員：厚生年金+国民年金。個人事業主：国民年金のみ。")

    st.header("キャッシュフロー")
    expense = st.number_input("基本の月間支出 (万円)", value=28, min_value=5, step=1, help="住居費・食費・娯楽費など全ての合計（住宅ローンは別途10万円/月を加算して計算）")
    assets = st.number_input("現在の金融資産 (万円)", value=2000, min_value=0, step=100, help="現金・株式・投資信託の合計。うち30%を現金、70%を株式として計算します。NISAの既存残高は0円として扱います。")

    st.divider()
    st.caption("詳細な計算設定は note のマニュアルを参照してください。")

# --- メインコンテンツ: 育休・時短の設定 ---
st.subheader("ライフイベント・詳細設定")
tab_input, tab_advanced = st.tabs(["育休・子供の設定", "⚙️ 詳細シミュレーション設定"])

with tab_input:
    child_birth = st.date_input(
        "第一子の誕生日（または予定日）",
        value=date.today() + relativedelta(months=6),
        help="この日付を基準に教育費や育休期間を算出します。"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 妻のライフステージ")
        w_leave_pre = st.slider("産前休暇 (月数)", 0, 6, 2, help="産前休暇中も「育休中の月収」を適用して計算します。")
        w_leave_post = st.slider("産後育休 (月数)", 0, 24, 12)
        w_leave_inc = st.slider("育休中の月収 (万円)", 0, 50, 15, help="産前休暇〜産後育休全期間の月収。育児休業給付金 = 通常給与の約67%（180日後50%）の平均値を入力してください。")
        
        st.markdown("---")
        w_red_end_age = st.slider("時短勤務終了 (子供が何歳まで)", 0, 10, 3, help="時短勤務からフルタイムに戻る年齢。育休終了後〜この年齢まで時短として計算します。")
        w_red_inc = st.slider("時短勤務中の月収 (万円)", 0, 60, 28)
        # 時短期間の整合チェック
        if w_red_end_age * 12 <= w_leave_post:
            st.warning(f"⚠️ 時短終了（子供{w_red_end_age}歳）が育休終了（{w_leave_post}ヶ月後）より早いため、時短勤務期間が0になります。")

    with col2:
        st.markdown("#### 夫の育休")
        h_leave_post = st.slider("育休取得期間 (月数)", 0, 12, 1)
        h_leave_inc = st.slider("育休中の月収 (万円)", 0, 60, 30)
        st.caption("※給付金は「休業開始前賃金の67%（180日後50%）」の平均値を入力してください。")

target_rate = 90

with tab_advanced:
    st.info("以下の前提条件は固定値です。変更には `demo_config.yaml` の編集が必要です（note マニュアル参照）。")
    _h_growth = f"{base_cfg['simulation']['standard']['income_growth_rate']*100:.0f}%/年" if type_h == '会社員' else "なし（固定）"
    st.json({
        "FIRE維持の目標確率": f"{target_rate}%",
        "期待利回り（年率）": f"{base_cfg['simulation']['standard']['annual_return_rate']*100:.0f}%",
        "インフレ率（年率）": f"{base_cfg['simulation']['standard']['inflation_rate']*100:.0f}%",
        "夫の昇給率（年率）": f"{_h_growth} ※妻は成長なし",
        "住宅ローン": f"{base_cfg['mortgage']['monthly_payment']//10000:.0f}万円/月（{base_cfg['mortgage']['end_date']}まで）",
        "FIRE後副収入": f"夫{base_cfg['simulation']['shuhei_post_fire_income']//10000:.0f}万 + 妻{base_cfg['simulation']['sakura_post_fire_income']//10000:.0f}万 = 計{(base_cfg['simulation']['shuhei_post_fire_income']+base_cfg['simulation']['sakura_post_fire_income'])//10000:.0f}万円/月",
        "年金受給開始": f"夫{base_cfg['pension']['people'][0].get('override_start_age', 65)}歳 / 妻{base_cfg['pension']['people'][1].get('override_start_age', 65)}歳",
        "教育コース": "公立小中高 + 国立大学",
        "資産配分（初期）": "現金30% / 株式70%（NISA初期残高は0円）",
    })

st.markdown("---")

# --- 計算実行 ---
if st.button("シミュレーションを開始", type="primary"):
    cfg = copy.deepcopy(base_cfg)
    current_date = datetime.today()
    birth_str = child_birth.strftime('%Y/%m/%d')
    cash = assets * 0.3 * 10000
    stocks = assets * 0.7 * 10000
    monthly_inc = (income_h + income_w) * 10000
    monthly_exp = expense * 10000
    
    # Config生成
    # --- 支出: カテゴリ別予算を無効化し、ユーザー入力を反映 ---
    cfg['fire']['expense_categories']['enabled'] = False
    cfg['fire']['manual_annual_expense'] = monthly_exp * 12  # 月次 → 年次に変換

    cfg['simulation'].update({
        'start_age': age_h,
        'shuhei_income': income_h * 10000,   # ユーザー入力で上書き（必須）
        'sakura_income': income_w * 10000,   # ユーザー入力で上書き（必須）
        'maternity_leave': [{
            'child': 'お子さん', 'months_before': w_leave_pre, 'months_after': w_leave_post,
            'monthly_income': w_leave_inc * 10000
        }],
        'sakura_reduced_hours': [{
            'child': 'お子さん', 'start_months_after': w_leave_post, 'end_months_after': w_red_end_age * 12,
            'income_ratio': (w_red_inc * 10000) / (income_w * 10000) if income_w > 0 else 0
        }],
        'shuhei_parental_leave': [{
            'child': 'お子さん', 'months_after': h_leave_post, 'monthly_income': h_leave_inc * 10000,
            'monthly_income_after_180days': h_leave_inc * 10000
        }],
        'shuhei_reduced_hours': [],  # UIで設定しないため空に（夫の時短は入力なし）
    })
    cfg['education']['children'] = [{
        'name': 'お子さん', 'birthdate': birth_str, 'nursery': 'public', 'kindergarten': 'public',
        'elementary': 'public', 'junior_high': 'public', 'high': 'public', 'university': 'national'
    }]
    # 年金のbirthdate をユーザーの年齢から逆算して更新
    birth_year_h = current_date.year - age_h
    birth_year_w = current_date.year - age_w
    if len(cfg['pension']['people']) >= 1:
        cfg['pension']['people'][0]['birthdate'] = f'{birth_year_h}/07/01'
        cfg['pension']['people'][0]['pension_type'] = 'employee' if type_h == '会社員' else 'national'
    if len(cfg['pension']['people']) >= 2:
        cfg['pension']['people'][1]['birthdate'] = f'{birth_year_w}/07/01'
        cfg['pension']['people'][1]['pension_type'] = 'employee' if type_w == '会社員' else 'national'
    # 夫が個人事業主の場合は収入成長率を0に（シミュレーターは夫のみ成長率を適用）
    if type_h == '個人事業主':
        for _sc in ['standard', 'pessimistic', 'optimistic']:
            if _sc in cfg['simulation']:
                cfg['simulation'][_sc]['income_growth_rate'] = 0.0

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(progress):
        progress_bar.progress(progress)
        status_text.text(f"1,000通りの未来をシミュレーション中... {int(progress * 100)}%")

    with st.spinner("シミュレーションを実行中..."):
        # 目標成功確率を達成するFIRE月を二分探索で決定し、固定FIRE月でMCシミュレーション
        mc_res = run_mc_fixed_fire(
            cash, stocks, cfg,
            target_success_rate=target_rate / 100.0,
            monthly_income=monthly_inc,
            monthly_expense=monthly_exp,
            scenario="standard",
            iterations=1000,
            progress_callback=update_progress,
        )

        df = mc_res['base_df']
        df['year_offset'] = df['month'] / 12
        df['sakura_age'] = age_w + df['year_offset']

    progress_bar.empty()
    status_text.empty()

    # --- 結果表示 ---
    st.markdown("## シミュレーション解析結果")

    if mc_res.get('impossible'):
        max_rate = int(mc_res['max_achievable_rate'] * 100)
        st.error(
            f"⚠️ 目標{target_rate}%は達成できません。\n\n"
            f"現在のパラメータで到達可能な最高成功確率は **{max_rate}%** です。\n"
            f"目標を{max_rate}%以下に変更するか、月間支出を減らすか、現在の金融資産を増やしてください。"
        )
    else:
        fire_month_val = mc_res['fire_month']          # 目標パーセンタイルのFIRE月
        fire_date_val  = mc_res['fire_date']
        fire_age_h_val = mc_res['fire_age_h']
        fire_age_w_val = mc_res['fire_age_w']

        # FIRE時資産（base_df の target_fire_month 行から取得）
        base_df_for_assets = mc_res['base_df']
        if fire_month_val < len(base_df_for_assets):
            assets_at_fire = base_df_for_assets.iloc[fire_month_val]['assets']
        else:
            assets_at_fire = base_df_for_assets.iloc[-1]['assets']

        years_to_fire = fire_month_val / 12.0

        # メトリクス表示
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
            st.metric("FIRE時資産（目標シナリオ）", fmt_oku(assets_at_fire))

        # タブで詳細を整理
        tab_chart, tab_guide = st.tabs(["資産予測（確率分布）", "シミュレーション解釈ガイド"])

        with tab_chart:
            st.markdown("#### 1,000通りの未来シミュレーション")
            st.caption(
                "全シナリオで現在から90歳まで通しでシミュレーションし、各パスで資産がFIREしきい値を超えた月を記録しています。"
                f" 目標{target_rate}%ラインのFIRE時期: {fire_date_val.strftime('%Y年%m月') if fire_date_val else '—'}"
            )

            # FIRE達成情報（チャート分割用）
            fire_row_for_chart = df[df['fire_achieved']].iloc[0] if df['fire_achieved'].any() else None
            if fire_row_for_chart is not None:
                current_status = {
                    'net_assets': assets * 10000,
                    'cash_deposits': cash,
                    'investment_trusts': stocks,
                }
                fire_achievement = {
                    'achieved': False,
                    'achievement_date': fire_row_for_chart['date'],
                    'months_to_fire': int(fire_row_for_chart['month']),
                }
                fire_target = {
                    'recommended_target': assets_at_fire,
                    'annual_expense': expense * 12 * 10000,
                }
                simulations = {'standard': df}

                fig_timeline = create_fire_timeline_chart(
                    current_status, fire_target, fire_achievement, simulations, cfg,
                    monte_carlo_results=mc_res,
                    show_baseline_after_fire=False,
                    current_date=current_date,
                )
                fig_timeline.update_layout(height=500)
                st.plotly_chart(fig_timeline, use_container_width=True)


        with tab_guide:
            st.markdown("### シミュレーション解釈ガイド")
            with st.expander("なぜ『一本の線』ではなく『範囲』で考えるのか？", expanded=True):
                st.write("""
                将来の資産推移を一本の線で予測することは、天気予報で「明日の12時00分に雨が0.5mm降る」と断定するようなものです。
                実際には、市場は常に変動します。このシミュレーターでは、**1,000通りの異なる未来（好景気、不景気、数年続く暴落など）**を計算し、
                各シナリオでFIREが実現できるタイミングの分布を算出しています。
                """)
            with st.expander("暴落や暴騰はどのように考慮されていますか？"):
                st.write("""
                このシミュレーターは、単純なランダム計算ではなく、以下の高度な金融工学モデルを採用しています：
                1. **平均回帰性 (Mean Reversion)**: 暴騰が続いた後は調整が入りやすく、過度な暴落の後には本来の価値へ回復しやすい性質を再現。
                2. **ボラティリティ・クラスタリング (GARCHモデル)**: 「大きな変動の後は、大きな変動が続きやすい」という連鎖性を考慮。
                3. **非対称性**: 急激な暴落となだらかな上昇のスピード感の違いをモデル化。
                これにより、リーマンショックのような「数年に一度の事象」への耐性を検証できます。
                """)
            st.markdown("---")
            st.markdown("#### 目標成功確率の見方")
            st.info(f"""
**{target_rate}%の意味**: リーマンショック規模の暴落を含む1,000通りの市場シナリオのうち、
**{target_rate}%のシナリオ**でこの時期にFIRE可能です。

残り{100 - target_rate}%のシナリオでは、市場環境によってFIREが数年先にずれる可能性があります。
目標確率を変えると、FIRE時期がどう変わるか「詳細シミュレーション設定」タブで確認できます。
""")

st.divider()
st.caption("Produced by watasack/fire-dashboard. This simulator is for professional financial planning support.")

