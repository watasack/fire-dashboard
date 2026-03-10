import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import yaml
import copy
import plotly.express as px
import plotly.graph_objects as go
from src.simulator import simulate_future_assets, run_monte_carlo_simulation
from src.visualizer import create_fire_timeline_chart
from src.data_schema import get_column_names

# ページ設定
st.set_page_config(
    page_title="共働きFIREシミュレーター【フル版】",
    page_icon="💰",
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
        st.markdown("<h2 style='text-align: center;'>🔐 会員限定コンテンツ</h2>", unsafe_allow_html=True)
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
        st.error("😕 アクセスコードが正しくありません。")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- ヘッダー ---
st.markdown("<h1 style='text-align: center;'>💰 共働きFIREシミュレーター <span style='color:#6366f1'>【フル版】</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 2rem;'>〜 理想的な家族の未来を、データで具現化する 〜</p>", unsafe_allow_html=True)

# --- 設定ファイルの読み込み ---
with open("demo_config.yaml", "r", encoding="utf-8") as f:
    base_cfg = yaml.safe_load(f)

# --- レイアウト: サイドバー ---
with st.sidebar:
    st.header("👤 世帯の基本情報")
    income_h = st.number_input("🙎‍♂️ 夫の月収 (手取り/万円)", value=40, step=1, help="現在の平均的な手取り月収（ボーナス除外）")
    age_h = st.number_input("夫の現在の年齢", value=35, step=1)
    
    st.divider()
    income_w = st.number_input("🙎‍♀️ 妻の月収 (手取り/万円)", value=35, step=1, help="通常勤務時の手取り月収")
    age_w = st.number_input("妻の現在の年齢", value=35, step=1)
    
    st.header("🏠 キャッシュフロー")
    expense = st.number_input("基本の月間支出 (万円)", value=28, step=1, help="住居費・食費・娯楽費など全ての合計")
    assets = st.number_input("現在の金融資産 (万円)", value=2000, step=100, help="現金・株式・投資信託の合計")
    
    st.divider()
    st.caption("詳細な計算設定は note のマニュアルを参照してください。")

# --- メインコンテンツ: 育休・時短の設定 ---
st.subheader("🍼 ライフイベント・詳細設定")
tab_input, tab_advanced = st.tabs(["👶 育休・子供の設定", "⚙️ 詳細シミュレーション設定"])

with tab_input:
    child_birth = st.date_input(
        "第一子の誕生日（または予定日）",
        value=date.today() + relativedelta(months=6),
        help="この日付を基準に教育費や育休期間を算出します。"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 👩 妻のライフステージ")
        w_leave_pre = st.slider("産前休暇 (月数)", 0, 6, 2)
        w_leave_post = st.slider("産後育休 (月数)", 0, 24, 12)
        w_leave_inc = st.slider("育休中の月収 (万円)", 0, 50, 15, help="育児休業給付金の実効受取額")
        
        st.markdown("---")
        w_red_end_age = st.slider("時短勤務終了 (子供が何歳まで)", 0, 10, 3, help="時短勤務からフルタイムに戻る年齢")
        w_red_inc = st.slider("時短勤務中の月収 (万円)", 0, 60, 28)

    with col2:
        st.markdown("#### 👨 夫の育休")
        h_leave_post = st.slider("育休取得期間 (月数)", 0, 12, 1)
        h_leave_inc = st.slider("育休中の月収 (万円)", 0, 60, 30)
        st.caption("※給付金は「休業開始前賃金の67%（180日後50%）」の平均値を入力してください。")

with tab_advanced:
    st.info("💡 高度な設定（投資利回り、インフレ率、教育コース等）は `demo_config.yaml` の値に基づいています。")
    st.json({
        "期待利回り": f"{base_cfg['simulation']['standard']['annual_return_rate']*100}%",
        "インフレ率": f"{base_cfg['simulation']['standard']['inflation_rate']*100}%",
        "大学コース": "国立大学",
        "資産配分": "現金30% / 株式70%"
    })

st.markdown("---")

# --- 計算実行 ---
if st.button("🚀 プロフェッショナル・シミュレーションを開始", type="primary"):
    cfg = copy.deepcopy(base_cfg)
    current_date = datetime.today()
    birth_str = child_birth.strftime('%Y/%m/%d')
    cash = assets * 0.3 * 10000
    stocks = assets * 0.7 * 10000
    monthly_inc = (income_h + income_w) * 10000
    monthly_exp = expense * 10000
    
    # Config生成
    cfg['simulation'].update({
        'start_age': age_h,
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
        }]
    })
    cfg['education']['children'] = [{
        'name': 'お子さん', 'birthdate': birth_str, 'nursery': 'public', 'kindergarten': 'public',
        'elementary': 'public', 'junior_high': 'public', 'high': 'public', 'university': 'national'
    }]

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(progress):
        progress_bar.progress(progress)
        status_text.text(f"🔢 1,000通りの未来をシミュレーション中... {int(progress * 100)}%")

    with st.spinner("シミュレーションを実行中..."):
        # 1. 現行プランのシミュレーション
        df = simulate_future_assets(cash, stocks, None, monthly_inc, monthly_exp, cfg, "standard")
        df['year_offset'] = df['month'] / 12
        df['sakura_age'] = age_w + df['year_offset']
        
        # 2. 比較用（育休なし）
        cfg_no = copy.deepcopy(cfg)
        cfg_no['simulation'].update({'maternity_leave': [], 'sakura_reduced_hours': [], 'shuhei_parental_leave': []})
        df_no = simulate_future_assets(cash, stocks, None, monthly_inc, monthly_exp, cfg_no, "standard")
        df_no['year_offset'] = df_no['month'] / 12
        df_no['sakura_age'] = age_w + df_no['year_offset']
        
        # 3. モンテカルロシミュレーション
        fire_row = df[df['fire_achieved']].iloc[0] if df['fire_achieved'].any() else None
        mc_res = run_monte_carlo_simulation(
            cash, stocks, cfg, "standard", 1000, monthly_inc, monthly_exp, 
            progress_callback=update_progress,
            include_pre_fire=True
        ) if fire_row is not None else None

    progress_bar.empty()
    status_text.empty()

    # --- 結果表示 ---
    st.markdown("## 📊 シミュレーション解析結果")
    
    if fire_row is not None:
        fire_age = int(fire_row['sakura_age'])
        years_to_fire = fire_row['year_offset']
        assets_at_fire = fire_row['assets']
        
        # メトリクス表示
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("FIRE到達年齢", f"{fire_age}歳")
        with col_m2:
            st.metric("必要年数", f"{years_to_fire:.1f}年")
        with col_m3:
            st.metric("FIRE時資産", f"{assets_at_fire/10000:.0f}万円")
        with col_m4:
            if mc_res:
                st.metric("🔥 成功確率", f"{mc_res['success_rate']*100:.1f}%")

        # タブで詳細を整理
        tab_chart, tab_compare, tab_guide = st.tabs(["📈 未来の資産予測（確率分布）", "⚖️ 育休の経済的影響", "💡 資産を盤石にするガイド"])

        with tab_chart:
            st.markdown("#### 💹 1,000通りの未来シミュレーション")
            st.caption("蓄積期は確実な貯蓄計画を、FIRE後は市場のボラティリティ（変動）を考慮した確率的な推移を表示しています。")
            
            current_status = {
                'net_assets': assets * 10000,
                'cash_deposits': cash,
                'investment_trusts': stocks
            }
            fire_achievement = {
                'achieved': False,
                'achievement_date': fire_row['date'],
                'months_to_fire': int(fire_row['month'])
            }
            fire_target = {
                'recommended_target': assets_at_fire,
                'annual_expense': expense * 12 * 10000
            }
            simulations = {'standard': df}
            
            fig_timeline = create_fire_timeline_chart(
                current_status, fire_target, fire_achievement, simulations, cfg,
                monte_carlo_results=mc_res,
                show_baseline_after_fire=False,
                current_date=current_date
            )
            fig_timeline.update_layout(height=500)
            st.plotly_chart(fig_timeline, use_container_width=True)
            
            if mc_res:
                col_mc1, col_mc2 = st.columns([2, 1])
                with col_mc1:
                    st.markdown("##### 90歳時点の資産分布")
                    final_assets_list = [r['final_assets'] for r in mc_res['all_results']]
                    dist_fig = px.histogram(x=np.array(final_assets_list)/10000, nbins=50, color_discrete_sequence=['#10b981'])
                    dist_fig.add_vline(x=0, line_color="#ef4444", line_width=3)
                    dist_fig.update_layout(xaxis_title="最終資産 (万円)", yaxis_title="頻度", margin=dict(l=20, r=20, t=10, b=20), height=300)
                    st.plotly_chart(dist_fig, use_container_width=True)
                with col_mc2:
                    st.markdown("##### 📉 リスク解析結果")
                    st.write(f"**FIRE成功確率:** {mc_res['success_rate']*100:.1f}%")
                    st.write(f"**最悪ケース(下位5%):**  \n{mc_res['percentile_5']/10000:,.0f} 万円")
                    st.write(f"**標準的なケース(中央値):**  \n{mc_res['median_final_assets']/10000:,.0f} 万円")
                    st.info("💡 中央値は『平均的な市場環境』を維持できた場合の予測です。最悪ケースでも資産が残るプランが理想的です。")

        with tab_compare:
            st.subheader("育休・時短の経済的インパクト")
            fire_row_no = df_no[df_no['fire_achieved']].iloc[0] if df_no['fire_achieved'].any() else None
            if fire_row_no is not None:
                age_no = int(fire_row_no['sakura_age'])
                diff = fire_age - age_no
                st.info(f"育休・時短プランにより、FIRE到達はフル稼働時より **{diff}年** 変化します。")
                comp_data = {
                    "項目": ["到達年齢", "FIRE時資産", "90歳時点(MC中央値)"],
                    "フル稼働（育休なし）": [f"{age_no}歳", f"{fire_row_no['assets']/10000:.0f}万", "-"],
                    "現行プラン（育休あり）": [f"{fire_age}歳", f"{assets_at_fire/10000:.0f}万", f"{mc_res['median_final_assets']/10000:.0f}万" if mc_res else "-"],
                }
                st.table(pd.DataFrame(comp_data).set_index("項目"))
                st.success("育休は単なる休止ではなく、家族の土台を作る重要な期間です。数年の差であれば、人生全体の幸福度は現行プランの方が高いかもしれません。")

        with tab_guide:
            st.markdown("### 🧠 専門家によるシミュレーション解釈ガイド")
            with st.expander("📊 なぜ『一本の線』ではなく『範囲』で考えるのか？", expanded=True):
                st.write("""
                将来の資産推移を一本の線で予測することは、天気予報で「明日の12時00分に雨が0.5mm降る」と断定するようなものです。
                実際には、市場は常に変動します。このシミュレーターでは、**1,000通りの異なる未来（好景気、不景気、数年続く暴落など）**を計算し、
                そのうちの何%で資産が底を突かずに済むか（成功確率）を算出しています。
                """)
            with st.expander("🌋 暴落や暴騰はどのように考慮されていますか？"):
                st.write("""
                このシミュレーターは、単純なランダム計算ではなく、以下の高度な金融工学モデルを採用しています：
                1. **平均回帰性 (Mean Reversion)**: 暴騰が続いた後は調整が入りやすく、過度な暴落の後には本来の価値へ回復しやすい性質を再現。
                2. **ボラティリティ・クラスタリング (GARCHモデル)**: 「大きな変動の後は、大きな変動が続きやすい」という連鎖性を考慮。
                3. **非対称性**: 急激な暴落となだらかな上昇のスピード感の違いをモデル化。
                これにより、リーマンショックのような「数年に一度の事象」への耐性を検証できます。
                """)
            st.markdown("---")
            st.markdown("#### 💡 プランをより盤石にするための3つのアドバイス")
            if mc_res and mc_res['success_rate'] >= 0.95:
                st.success("**1. 完璧な準備状況です**  \n現在の貯蓄率と投資方針を維持できれば、ほぼ確実にFIREを維持できます。これ以上節約を強いるより、今を楽しむための支出に予算を割くことも検討してください。")
            elif mc_res and mc_res['success_rate'] >= 0.8:
                st.warning("**2. 『景気後退期』への備えを**  \n成功率は高いですが、最悪ケースでは目減りが発生します。FIRE達成時に生活費の2〜3年分を「現金」として確保（キャッシュクッション）しておくことで、暴落時に株式を売らずに済む仕組みを作りましょう。")
            else:
                st.error("**3. プランの修正が必要です**  \n成功確率が不十分です。FIRE年齢を1〜2年遅らせるか、時短勤務後の月収を数万円増やす、あるいは教育費の予算を調整することで、確率は劇的に改善します。")

    else:
        st.error("🚨 警告: 90歳までにFIREを達成できません。支出の見直し、または投資利回りの再確認を行ってください。")

st.divider()
st.caption("Produced by watasack/fire-dashboard. This simulator is for professional financial planning support.")

