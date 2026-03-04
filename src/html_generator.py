"""
HTML生成モジュール
Plotlyグラフを統合してダッシュボードHTMLを生成
"""

import plotly.graph_objects as go
from typing import Dict, Any, List
from datetime import datetime
import json
import numpy as np
from src.data_schema import CUSTOMDATA_COLUMNS, DISPLAY_NAMES, INCOME_COLUMNS, EXPENSE_COLUMNS


def _format_man_yen(value: float) -> str:
    """円を万円表示にフォーマット"""
    return f"¥{value / 10000:,.0f}万"


def _build_kpi_detail_evidence(
    monte_carlo: Dict[str, Any],
    fire_target: Dict[str, Any],
    config: Dict[str, Any],
) -> str:
    """成功確率KPIの根拠テキストを生成（MC試行回数ベース）"""
    if not monte_carlo or 'success_rate' not in monte_carlo:
        return ''
    mc_cfg = config['simulation']['monte_carlo']
    iterations = mc_cfg['iterations']
    success_count = int(monte_carlo['success_rate'] * iterations)
    return f'{iterations:,}回中{success_count:,}回成功'



def _build_assumptions_html(config: Dict[str, Any], monte_carlo: Dict[str, Any]) -> str:
    """前提条件パネルのHTMLを生成（折りたたみ式）"""
    sim = config['simulation']
    std = sim['standard']
    mc_cfg = sim['monte_carlo']
    pension_cfg = config['pension']
    fire_cfg = config['fire']
    post_fire_cash = config['post_fire_cash_strategy']

    return_rate = std['annual_return_rate']
    inflation = std['inflation_rate']
    income_growth = std['income_growth_rate']
    return_std = mc_cfg['return_std_dev']
    mc_iters = mc_cfg['iterations']
    life_exp = sim['life_expectancy']
    start_age = sim['start_age']

    shuhei_income = sim['shuhei_income']
    sakura_income = sim['sakura_income']
    shuhei_post = sim['shuhei_post_fire_income']
    sakura_post = sim['sakura_post_fire_income']

    safety_margin = post_fire_cash['safety_margin']
    target_cash_reserve = post_fire_cash['target_cash_reserve']
    crash_threshold = post_fire_cash['market_crash_threshold']

    der = fire_cfg['dynamic_expense_reduction']
    der_enabled = der['enabled']
    der_rates = der['reduction_rates']

    summary_badge = f"年率{return_rate*100:.1f}% / σ{return_std*100:.1f}% / MC {mc_iters:,}回"

    rows = f'''
        <tr class="group-header"><td colspan="2">市場パラメータ</td></tr>
        <tr><td>年率リターン（期待値）</td><td>{return_rate*100:.1f}%</td></tr>
        <tr><td>リターン標準偏差</td><td>{return_std*100:.1f}%</td></tr>
        <tr><td>インフレ率</td><td>{inflation*100:.1f}%</td></tr>
        <tr><td>収入成長率</td><td>{income_growth*100:.1f}%</td></tr>
        <tr class="group-header"><td colspan="2">シミュレーション設定</td></tr>
        <tr><td>想定寿命</td><td>{life_exp}歳</td></tr>
        <tr><td>MCシミュレーション回数</td><td>{mc_iters:,}回</td></tr>
        <tr class="group-header"><td colspan="2">収入設定</td></tr>
        <tr><td>修平 手取り月額</td><td>¥{shuhei_income/10000:.1f}万</td></tr>
        <tr><td>桜 手取り月額</td><td>¥{sakura_income/10000:.1f}万</td></tr>
        <tr><td>FIRE後 修平 副収入</td><td>¥{shuhei_post/10000:.1f}万/月</td></tr>
        <tr><td>FIRE後 桜 事業収入</td><td>¥{sakura_post/10000:.1f}万/月</td></tr>
        <tr class="group-header"><td colspan="2">リスク管理</td></tr>
        <tr><td>安全マージン</td><td>{_format_man_yen(safety_margin)}（シミュレーション打ち切り・最適化制約）</td></tr>
        <tr><td>現金確保目標</td><td>{_format_man_yen(target_cash_reserve)}（FIRE後の現金管理目標）</td></tr>
        <tr><td>暴落判定閾値</td><td>{crash_threshold*100:.0f}%</td></tr>'''

    if der_enabled:
        l1 = der_rates['level_1_warning']
        l2 = der_rates['level_2_concern']
        l3 = der_rates['level_3_crisis']
        rows += f'''
        <tr class="group-header"><td colspan="2">動的支出削減</td></tr>
        <tr><td>警戒レベル</td><td>裁量支出{l1*100:.0f}%削減</td></tr>
        <tr><td>懸念レベル</td><td>裁量支出{l2*100:.0f}%削減</td></tr>
        <tr><td>危機レベル</td><td>裁量支出{l3*100:.0f}%削減</td></tr>'''

    return f'''
    <details class="info-detail">
      <summary class="info-summary">
        <span class="title-accent title-accent--slate"></span>
        シミュレーション前提条件
        <span class="summary-badge">{summary_badge}</span>
      </summary>
      <div class="info-detail-body">
        <table class="assumptions-table">
          <tbody>{rows}
          </tbody>
        </table>
      </div>
    </details>'''


def _build_optimization_html(config: Dict[str, Any]) -> str:
    """最適化結果サマリーパネルのHTMLを生成（折りたたみ式、デフォルト展開）"""
    fire_cfg = config['fire']
    pension_cfg = config['pension']
    cash_strategy = config['post_fire_cash_strategy']

    optimal_month = fire_cfg.get('optimal_fire_month')
    extra_budget = fire_cfg.get('optimal_extra_monthly_budget') or 0
    safety_margin = cash_strategy['safety_margin']
    safety_margin_man = safety_margin / 10000

    pension_deferral = config['pension_deferral']
    base_age = pension_cfg['start_age']
    deferral_rate_pct = pension_deferral['deferral_increase_rate'] * 100
    early_rate_pct = pension_deferral['early_decrease_rate'] * 100

    people = pension_cfg['people']
    pension_rows = ''
    for p in people:
        name = p['name']
        override = p.get('override_start_age')
        ptype = p['pension_type']
        type_label = '厚生年金+国民年金' if ptype == 'employee' else '国民年金'
        if override:
            diff = override - base_age
            if diff > 0:
                adj_pct = diff * deferral_rate_pct
                adj_label = f'+{adj_pct:.1f}%増額'
            elif diff < 0:
                adj_pct = abs(diff) * early_rate_pct
                adj_label = f'-{adj_pct:.1f}%減額'
            else:
                adj_label = '増減なし'
            pension_rows += f'''
        <tr>
          <td>{name}（{type_label}）</td>
          <td>{override}歳開始（{adj_label}）</td>
        </tr>'''

    if optimal_month is not None:
        years = optimal_month // 12
        months = optimal_month % 12
        fire_text = f'{years}年{months}ヶ月後'
    else:
        fire_text = '未設定'

    summary_badge = f"FIRE {fire_text} / 安全マージン{safety_margin_man:.0f}万円"

    return f'''
    <details class="info-detail" open>
      <summary class="info-summary">
        <span class="title-accent title-accent--amber"></span>
        最適化結果
        <span class="summary-badge">{summary_badge}</span>
      </summary>
      <div class="info-detail-body">
        <table class="assumptions-table">
          <tbody>
            <tr><td>最適FIRE時期</td><td>{fire_text}</td></tr>
            <tr><td>安全マージン</td><td>¥{safety_margin_man:.0f}万（ベースライン最終資産 ≥ この額）</td></tr>
            <tr><td>FIRE後追加予算</td><td>¥{extra_budget/10000:.1f}万/月</td></tr>
            <tr class="sep"><td colspan="2"></td></tr>{pension_rows}
          </tbody>
        </table>
        <div class="optimization-note">
          最適化により、ベースライン最終資産が安全マージン（{safety_margin_man:.0f}万円）以上を
          維持しながら最も早いFIRE時期と最適な年金受給開始年齢の組み合わせを探索しています。
        </div>
      </div>
    </details>'''


def _build_life_events_table(
    life_events: List[Dict],
    simulations: Dict,
    config: Dict[str, Any],
) -> str:
    """ライフイベント財務インパクト表のHTMLを生成"""
    if not life_events:
        return ''

    pension_people = config['pension']['people']
    children = config['education']['children']
    start_age = config['simulation']['start_age']

    birthdates = {}
    for p in pension_people:
        birthdates[p['name']] = p['birthdate']
    for c in children:
        birthdates[c['name']] = c['birthdate']

    # 年次の収支変化をシミュレーションデータから抽出
    df = simulations.get('standard')
    annual_data = {}
    if df is not None:
        df_copy = df.copy()
        df_copy['year'] = df_copy['date'].dt.year
        for year, grp in df_copy.groupby('year'):
            total_income = grp['income'].sum()
            total_expense = grp['expense'].sum()
            annual_data[year] = {'income': total_income, 'expense': total_expense}

    rows = ''
    for event in life_events:
        event_date = event['date']
        label = event['label']
        color = event['color']
        year = event_date.year

        # 年齢計算
        ages = []
        for p in pension_people:
            bd = p['birthdate']
            if bd:
                birth_year = int(bd.split('/')[0])
                age = year - birth_year
                ages.append(f"{p['name']}{age}歳")

        age_str = ' / '.join(ages) if ages else ''

        # 前年比の収支変化（色分け用にHTMLタグ付き）
        impact_html = ''
        if year in annual_data and (year - 1) in annual_data:
            prev = annual_data[year - 1]
            curr = annual_data[year]
            income_delta = (curr['income'] - prev['income']) / 10000
            expense_delta = (curr['expense'] - prev['expense']) / 10000
            parts = []
            if abs(income_delta) > 5:
                sign = '+' if income_delta > 0 else ''
                css = 'impact-positive' if income_delta > 0 else 'impact-negative'
                parts.append(f'<span class="{css}">収入{sign}{income_delta:.0f}万</span>')
            if abs(expense_delta) > 5:
                sign = '+' if expense_delta > 0 else ''
                css = 'impact-negative' if expense_delta > 0 else 'impact-positive'
                parts.append(f'<span class="{css}">支出{sign}{expense_delta:.0f}万</span>')
            impact_html = '&ensp;'.join(parts) if parts else '<span class="impact-neutral">―</span>'
        else:
            impact_html = '<span class="impact-neutral">―</span>'

        rows += f'''
          <tr>
            <td>{event_date.strftime('%Y/%m')}</td>
            <td><span class="event-dot" style="background:{color}"></span>{label}</td>
            <td class="age-cell">{age_str}</td>
            <td class="impact-cell">{impact_html}</td>
          </tr>'''

    return f'''
    <section class="life-events-section">
      <h3 class="panel-title"><span class="title-accent title-accent--purple"></span>ライフイベントと財務インパクト</h3>
      <div class="life-events-table-wrap">
        <table class="life-events-table">
          <thead>
            <tr>
              <th>年月</th>
              <th>イベント</th>
              <th>年齢</th>
              <th>年間収支変化（前年比）</th>
            </tr>
          </thead>
          <tbody>{rows}
          </tbody>
        </table>
      </div>
    </section>'''


def generate_dashboard_html(
    charts: Dict[str, go.Figure],
    summary_data: Dict[str, Any],
    action_items: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> None:
    """一画面完結型のダッシュボードHTMLを生成"""
    current_status = summary_data['current_status']
    fire_target = summary_data['fire_target']
    fire_achievement = summary_data.get('fire_achievement')
    trends = summary_data['trends']
    expense_breakdown = summary_data['expense_breakdown']
    monte_carlo = summary_data.get('monte_carlo')
    life_events = summary_data.get('life_events', [])
    simulations = summary_data.get('simulations', {})
    update_time = summary_data['update_time']

    # グラフをHTMLに変換
    fire_timeline_html = charts['fire_timeline'].to_html(
        full_html=False, include_plotlyjs='cdn', config={'responsive': True}
    )
    income_expense_html = ''
    if 'income_expense_stream' in charts:
        income_expense_html = charts['income_expense_stream'].to_html(
            full_html=False, include_plotlyjs=False, config={'responsive': True}
        )

    pareto_frontier_html = ''
    if charts.get('pareto_frontier'):
        pareto_frontier_html = charts['pareto_frontier'].to_html(
            full_html=False, include_plotlyjs=False, config={'responsive': True}
        )

    # FIRE達成情報
    if fire_achievement:
        if fire_achievement.get('achieved'):
            achievement_text = '達成済み！'
            achievement_detail = 'おめでとうございます'
        else:
            achievement_date = fire_achievement['achievement_date']
            years = fire_achievement['years_to_fire']
            months = fire_achievement['remaining_months']
            achievement_text = f"{achievement_date.strftime('%Y年%m月')}"
            achievement_detail = f"あと{years}年{months}ヶ月"
    else:
        achievement_text = '計算中'
        achievement_detail = ''

    # 成功率の表示（感覚的表現を排除）
    if monte_carlo and 'success_rate' in monte_carlo:
        success_rate = monte_carlo['success_rate']
        success_text = f"{success_rate*100:.1f}%"
        success_detail = _build_kpi_detail_evidence(monte_carlo, fire_target, config)
    else:
        success_text = '―'
        success_detail = 'MC未実行'

    # 今すぐFIREした場合の成功率
    immediate_fire_mc = summary_data.get('immediate_fire_mc')
    if immediate_fire_mc and 'success_rate' in immediate_fire_mc:
        imm_rate = immediate_fire_mc['success_rate']
        immediate_fire_text = f"{imm_rate*100:.1f}%"
        immediate_fire_detail = _build_kpi_detail_evidence(immediate_fire_mc, fire_target, config)
    else:
        immediate_fire_text = '―'
        immediate_fire_detail = ''

    # FIRE後副収入の合計（セミFIRE前提の表示用）
    sim_cfg = config['simulation']
    post_fire_income_monthly = (
        sim_cfg['shuhei_post_fire_income']
        + sim_cfg['sakura_post_fire_income']
    )

    # 前提条件の短縮表示
    std_cfg = sim_cfg['standard']
    return_rate = std_cfg['annual_return_rate']
    inflation = std_cfg['inflation_rate']
    achievement_basis = f"年率{return_rate*100:.0f}%・インフレ{inflation*100:.0f}%前提"

    # 達成率の根拠
    progress = fire_target['progress_rate']
    target_yen = fire_target['recommended_target']
    current_yen = fire_target.get('current_net_assets', current_status['net_assets'])
    progress_detail = f"目標{_format_man_yen(target_yen)} / 現在{_format_man_yen(current_yen)}"

    # データスキーマ
    customdata_schema = {col: idx for idx, col in enumerate(CUSTOMDATA_COLUMNS)}
    customdata_schema_json = json.dumps(customdata_schema)
    display_names_json = json.dumps(DISPLAY_NAMES, ensure_ascii=False)
    income_columns_json = json.dumps(INCOME_COLUMNS)
    expense_columns_json = json.dumps(EXPENSE_COLUMNS)

    category_percentages = expense_breakdown.get('category_percentages', {})
    top_categories = sorted(category_percentages.items(), key=lambda x: x[1], reverse=True)[:5]
    category_data_json = json.dumps(dict(top_categories))

    # 家族情報
    family_info = []
    pension_people = config['pension']['people']
    for person in pension_people:
        family_info.append({
            'name': person['name'],
            'birthdate': person['birthdate'],
            'role': 'parent'
        })
    children = config['education']['children']
    for i, child in enumerate(children):
        child_name = child['name']
        family_info.append({
            'name': child_name,
            'birthdate': child['birthdate'],
            'role': 'child'
        })
    family_info_json = json.dumps(family_info, ensure_ascii=False)

    # セクション構築
    assumptions_html = _build_assumptions_html(config, monte_carlo)
    optimization_html = _build_optimization_html(config)
    life_events_table_html = _build_life_events_table(life_events, simulations, config)

    # HTMLテンプレート
    html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FIREダッシュボード</title>
    <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <div class="dashboard-container">
    <!-- ヘッダー -->
    <header class="dashboard-header">
      <div class="header-brand">
        <h1>FIREダッシュボード</h1>
      </div>
      <div class="header-update">
        <span class="status-dot"></span>
        <span>{update_time.strftime('%Y-%m-%d %H:%M')} 更新</span>
      </div>
    </header>

    <!-- メインKPI（根拠付き） -->
    <section class="hero-kpi">
      <div class="kpi-primary">
        <div class="kpi-label">FIRE達成率</div>
        <div class="kpi-value kpi-value--large">{progress:.1%}</div>
        <div class="progress-bar-wrap">
          <div class="progress-bar-fill" style="width: {min(progress * 100, 100):.1f}%"></div>
        </div>
        <div class="kpi-detail">{progress_detail}</div>
      </div>
      <div class="kpi-divider"></div>
      <div class="kpi-primary">
        <div class="kpi-label">達成予想</div>
        <div class="kpi-value kpi-value--large">{achievement_text}</div>
        <div class="kpi-detail kpi-detail--accent">{achievement_detail}</div>
        <div class="kpi-detail">{achievement_basis}</div>
      </div>
      <div class="kpi-divider"></div>
      <div class="kpi-primary">
        <div class="kpi-label">セミFIRE成功率<br><small style="font-weight:normal;color:var(--text-secondary)">(副収入{post_fire_income_monthly/10000:.0f}万円/月)</small></div>
        <div class="kpi-value kpi-value--large">{success_text}</div>
        <div class="kpi-detail">{success_detail}</div>
      </div>
      <div class="kpi-divider"></div>
      <div class="kpi-primary">
        <div class="kpi-label">今すぐ完全FIRE成功率<br><small style="font-weight:normal;color:var(--text-secondary)">(副収入なし)</small></div>
        <div class="kpi-value kpi-value--large">{immediate_fire_text}</div>
        <div class="kpi-detail">{immediate_fire_detail}</div>
      </div>
    </section>

    <!-- メイングラフ（資産シミュレーション） -->
    <section class="main-chart">
      <div class="chart-panel">
        <h2 class="chart-title"><span class="title-accent title-accent--teal"></span>資産シミュレーション</h2>
        <div class="chart-content">
          {fire_timeline_html}
        </div>
        <!-- クリック詳細情報 -->
        <div id="click-details" style="display: none; margin-top: 20px; padding: 20px; background: #f0f9ff; border-radius: 8px; border-left: 4px solid #06b6d4;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <h3 style="margin: 0; font-size: 15px; color: #0c4a6e; font-weight: 600;">
              <span id="detail-date"></span>の詳細
            </h3>
            <div style="text-align: right;">
              <div style="font-size: 11px; color: #64748b;">資産残高</div>
              <div id="detail-assets" style="font-size: 18px; font-weight: 700; color: #0891b2;"></div>
            </div>
          </div>

          <!-- 2カラムレイアウト -->
          <div style="display: grid; grid-template-columns: 1.6fr 1fr; gap: 20px; min-height: 0;">
            <div>
              <div id="waterfall-chart" style="width: 100%; height: 350px;"></div>
            </div>
            <div>
              <table id="detail-table" style="width: 100%; border-collapse: collapse; font-size: 13px; background: white; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                <thead>
                  <tr style="background: #e0f2fe;">
                    <th style="padding: 10px 12px; text-align: left; font-weight: 600; color: #0c4a6e; border-bottom: 2px solid #bae6fd;">項目</th>
                    <th style="padding: 10px 12px; text-align: right; font-weight: 600; color: #0c4a6e; border-bottom: 2px solid #bae6fd;">金額</th>
                  </tr>
                </thead>
                <tbody id="detail-table-body"></tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 収支 + ライフイベント（並列レイアウト） -->
    <section class="dual-content">
      <div class="chart-panel">
        <h2 class="chart-title"><span class="title-accent title-accent--blue"></span>年次収支内訳推移</h2>
        <div class="chart-content">
          {income_expense_html}
        </div>
      </div>
      {life_events_table_html}
    </section>

    <!-- パレートチャート + 前提条件・最適化結果 -->
    <section class="bottom-layout">
      {'<div class="chart-panel"><h2 class="chart-title"><span class="title-accent title-accent--teal"></span>FIRE年齢 vs ベースライン最終資産</h2>' + pareto_frontier_html + '</div>' if pareto_frontier_html else '<div></div>'}
      <div class="info-panels-stacked">
        {assumptions_html}
        {optimization_html}
      </div>
    </section>

  </div>

  <!-- グラフクリックイベント処理 -->
  <script>
    const CUSTOMDATA_SCHEMA = {customdata_schema_json};
    const DISPLAY_NAMES = {display_names_json};
    const INCOME_COLUMNS = {income_columns_json};
    const EXPENSE_COLUMNS = {expense_columns_json};
    const categoryPercentages = {category_data_json};
    const familyInfo = {family_info_json};

    function getCustomDataValue(customdata, columnName) {{
      const index = CUSTOMDATA_SCHEMA[columnName];
      return index !== undefined ? customdata[index] : 0;
    }}

    function calculateAge(birthdate, targetDate) {{
      const birth = new Date(birthdate);
      const target = new Date(targetDate);
      let age = target.getFullYear() - birth.getFullYear();
      const monthDiff = target.getMonth() - birth.getMonth();
      if (monthDiff < 0 || (monthDiff === 0 && target.getDate() < birth.getDate())) {{
        age--;
      }}
      return age;
    }}

    window.addEventListener('load', function() {{
      setTimeout(function() {{
        const graphDiv = document.querySelector('.main-chart:first-of-type .chart-content .plotly-graph-div');
        if (!graphDiv) return;

        graphDiv.on('plotly_click', function(data) {{
          const point = data.points[0];
          if (!point) return;
          const date = new Date(point.x);
          const assets = point.y;
          const customdata = point.customdata;

          const detailsDiv = document.getElementById('click-details');
          detailsDiv.style.display = 'block';

          const dateStr = date.getFullYear() + '年' + (date.getMonth() + 1) + '月';
          document.getElementById('detail-date').textContent = dateStr;
          document.getElementById('detail-assets').textContent = '¥' + assets.toFixed(1) + '万';

          if (customdata && customdata.length >= Object.keys(CUSTOMDATA_SCHEMA).length) {{
            const laborIncome = getCustomDataValue(customdata, 'labor_income');
            const shuheiIncome = getCustomDataValue(customdata, 'shuhei_income');
            const sakuraIncome = getCustomDataValue(customdata, 'sakura_income');
            const pensionIncome = getCustomDataValue(customdata, 'pension_income');
            const childAllowance = getCustomDataValue(customdata, 'child_allowance');
            const baseExpense = getCustomDataValue(customdata, 'base_expense');
            const educationExpense = getCustomDataValue(customdata, 'education_expense');
            const mortgagePayment = getCustomDataValue(customdata, 'mortgage_payment');
            const maintenanceCost = getCustomDataValue(customdata, 'maintenance_cost');
            const workationCost = getCustomDataValue(customdata, 'workation_cost');
            const pensionPremium = getCustomDataValue(customdata, 'pension_premium');
            const healthInsurancePremium = getCustomDataValue(customdata, 'health_insurance_premium');
            const investmentReturn = getCustomDataValue(customdata, 'investment_return');
            const cash = getCustomDataValue(customdata, 'cash');
            const stocks = getCustomDataValue(customdata, 'stocks');
            const autoInvested = getCustomDataValue(customdata, 'auto_invested');
            const capitalGainsTax = getCustomDataValue(customdata, 'capital_gains_tax');

            const totalIncome = laborIncome + pensionIncome + childAllowance;
            const totalExpense = baseExpense + educationExpense + mortgagePayment + maintenanceCost + workationCost + pensionPremium + healthInsurancePremium;

            const tableBody = document.getElementById('detail-table-body');
            tableBody.innerHTML = '';

            function addRow(label, value, className) {{
              className = className || '';
              const row = document.createElement('tr');
              row.className = className;
              const cellLabel = document.createElement('td');
              cellLabel.textContent = label;
              cellLabel.style.padding = '8px 12px';
              cellLabel.style.borderBottom = '1px solid #e0f2fe';
              const cellValue = document.createElement('td');
              cellValue.textContent = value;
              cellValue.style.padding = '8px 12px';
              cellValue.style.textAlign = 'right';
              cellValue.style.borderBottom = '1px solid #e0f2fe';
              cellValue.style.fontWeight = className.includes('bold') ? '600' : 'normal';
              if (className.includes('section-header')) {{
                cellLabel.style.background = '#cffafe';
                cellLabel.style.fontWeight = '600';
                cellLabel.style.color = '#0c4a6e';
                cellValue.style.background = '#cffafe';
                cellValue.style.fontWeight = '600';
                cellValue.style.color = '#0c4a6e';
              }} else if (className.includes('subtotal')) {{
                cellLabel.style.fontWeight = '600';
                cellLabel.style.color = '#334155';
                cellValue.style.fontWeight = '600';
                cellValue.style.color = '#334155';
              }} else if (className.includes('total')) {{
                cellLabel.style.background = '#e0f2fe';
                cellLabel.style.fontWeight = '700';
                cellLabel.style.color = '#0891b2';
                cellValue.style.background = '#e0f2fe';
                cellValue.style.fontWeight = '700';
                cellValue.style.color = '#0891b2';
              }} else if (className.includes('subcategory')) {{
                cellLabel.style.paddingLeft = '24px';
                cellLabel.style.fontSize = '12px';
                cellLabel.style.color = '#64748b';
                cellValue.style.fontSize = '12px';
                cellValue.style.color = '#64748b';
              }}
              row.appendChild(cellLabel);
              row.appendChild(cellValue);
              tableBody.appendChild(row);
            }}

            if (familyInfo.length > 0) {{
              addRow('家族構成', '', 'section-header');
              for (const person of familyInfo) {{
                const age = calculateAge(person.birthdate, date);
                addRow(person.name, age + '歳', 'subcategory');
              }}
            }}

            addRow('収入', '', 'section-header');
            if (laborIncome > 0) {{
              addRow('労働収入', '+¥' + (laborIncome / 10000).toFixed(1) + '万', 'income');
              if (shuheiIncome > 0) addRow('└ 修平', '+¥' + (shuheiIncome / 10000).toFixed(1) + '万', 'subcategory');
              if (sakuraIncome > 0) addRow('└ 桜', '+¥' + (sakuraIncome / 10000).toFixed(1) + '万', 'subcategory');
            }}
            if (pensionIncome > 0) addRow('年金収入', '+¥' + (pensionIncome / 10000).toFixed(1) + '万', 'income');
            if (childAllowance > 0) addRow('児童手当', '+¥' + (childAllowance / 10000).toFixed(1) + '万', 'income');
            addRow('収入合計', '¥' + (totalIncome / 10000).toFixed(1) + '万', 'subtotal bold');

            addRow('支出', '', 'section-header');
            if (baseExpense > 0) {{
              const baseExpenseManEn = baseExpense / 10000;
              addRow('基本生活費', '-¥' + baseExpenseManEn.toFixed(1) + '万', 'expense');
              const categories = Object.keys(categoryPercentages);
              if (categories.length > 0) {{
                for (const category of categories) {{
                  const percentage = categoryPercentages[category] / 100;
                  const categoryExpense = baseExpenseManEn * percentage;
                  if (categoryExpense > 0.1) addRow('  - ' + category, '-¥' + categoryExpense.toFixed(1) + '万', 'subcategory');
                }}
              }}
            }}
            if (educationExpense > 0) addRow('教育費', '-¥' + (educationExpense / 10000).toFixed(1) + '万', 'expense');
            if (mortgagePayment > 0) addRow('住宅ローン', '-¥' + (mortgagePayment / 10000).toFixed(1) + '万', 'expense');
            if (maintenanceCost > 0) addRow('メンテナンス費用', '-¥' + (maintenanceCost / 10000).toFixed(1) + '万', 'expense');
            if (workationCost > 0) addRow('ワーケーション', '-¥' + (workationCost / 10000).toFixed(1) + '万', 'expense');
            if (pensionPremium > 0) addRow('国民年金保険料', '-¥' + (pensionPremium / 10000).toFixed(1) + '万', 'expense');
            if (healthInsurancePremium > 0) addRow('国民健康保険料', '-¥' + (healthInsurancePremium / 10000).toFixed(1) + '万', 'expense');
            addRow('支出合計', '-¥' + (totalExpense / 10000).toFixed(1) + '万', 'subtotal bold');

            addRow('資産構成', '', 'section-header');
            if (cash >= 0) addRow('現金・預金', '¥' + (cash / 10000).toFixed(1) + '万', 'subcategory');
            if (stocks >= 0) addRow('投資信託', '¥' + (stocks / 10000).toFixed(1) + '万', 'subcategory');
            addRow('総資産', '¥' + ((cash + stocks) / 10000).toFixed(1) + '万', 'subtotal bold');

            addRow('その他', '', 'section-header');
            if (investmentReturn > 0) addRow('運用益', '+¥' + (investmentReturn / 10000).toFixed(1) + '万', 'income');
            if (autoInvested > 0) addRow('自動投資（NISA）', '-¥' + (autoInvested / 10000).toFixed(1) + '万', 'expense');
            if (capitalGainsTax > 0) addRow('譲渡益課税', '-¥' + (capitalGainsTax / 10000).toFixed(1) + '万', 'expense');

            const netChange = (totalIncome - totalExpense + investmentReturn - autoInvested - capitalGainsTax) / 10000;
            const netChangeStr = (netChange >= 0 ? '+' : '') + '¥' + netChange.toFixed(1) + '万';
            addRow('純変動', netChangeStr, 'total');

            // ウォーターフォールチャート
            const items = [];
            if (laborIncome !== 0) items.push({{ label: '労働収入', value: laborIncome / 10000, measure: 'relative' }});
            if (pensionIncome !== 0) items.push({{ label: '年金収入', value: pensionIncome / 10000, measure: 'relative' }});
            if (childAllowance !== 0) items.push({{ label: '児童手当', value: childAllowance / 10000, measure: 'relative' }});

            if (baseExpense !== 0) {{
              const baseExpenseManEn = baseExpense / 10000;
              const categories = Object.keys(categoryPercentages);
              if (categories.length > 0) {{
                for (const category of categories) {{
                  const percentage = categoryPercentages[category] / 100;
                  const categoryExpense = baseExpenseManEn * percentage;
                  if (categoryExpense > 0.1) items.push({{ label: category, value: -categoryExpense, measure: 'relative' }});
                }}
              }} else {{
                items.push({{ label: '基本生活費', value: -baseExpenseManEn, measure: 'relative' }});
              }}
            }}
            if (educationExpense !== 0) items.push({{ label: '教育費', value: -educationExpense / 10000, measure: 'relative' }});
            if (mortgagePayment !== 0) items.push({{ label: '住宅ローン', value: -mortgagePayment / 10000, measure: 'relative' }});
            if (maintenanceCost !== 0) items.push({{ label: 'メンテナンス', value: -maintenanceCost / 10000, measure: 'relative' }});
            if (workationCost !== 0) items.push({{ label: 'ワーケーション', value: -workationCost / 10000, measure: 'relative' }});
            if (pensionPremium !== 0) items.push({{ label: '国民年金', value: -pensionPremium / 10000, measure: 'relative' }});
            if (healthInsurancePremium !== 0) items.push({{ label: '国民健康保険', value: -healthInsurancePremium / 10000, measure: 'relative' }});
            if (investmentReturn !== 0) items.push({{ label: '運用益', value: investmentReturn / 10000, measure: 'relative' }});
            if (autoInvested !== 0) items.push({{ label: '自動投資', value: -autoInvested / 10000, measure: 'relative' }});
            if (capitalGainsTax !== 0) items.push({{ label: '譲渡益課税', value: -capitalGainsTax / 10000, measure: 'relative' }});
            items.push({{ label: '純変動', value: netChange, measure: 'total' }});

            const waterfallData = [{{
              type: 'waterfall', orientation: 'v',
              x: items.map(item => item.label), y: items.map(item => item.value),
              measure: items.map(item => item.measure),
              textposition: 'auto',
              text: items.map(item => {{ const val = item.value; return (val >= 0 ? '+' : '') + val.toFixed(1) + '万'; }}),
              increasing: {{ marker: {{ color: '#10b981' }} }},
              decreasing: {{ marker: {{ color: '#ef4444' }} }},
              totals: {{ marker: {{ color: '#06b6d4' }} }},
              connector: {{ line: {{ color: '#94a3b8', width: 1, dash: 'dot' }} }}
            }}];
            const waterfallLayout = {{
              showlegend: false,
              margin: {{ t: 40, b: 50, l: 50, r: 20 }},
              yaxis: {{ title: '万円', tickformat: ',.0f', gridcolor: '#e0f2fe' }},
              xaxis: {{ tickangle: 0 }},
              plot_bgcolor: '#f0f9ff', paper_bgcolor: '#f0f9ff'
            }};
            Plotly.newPlot('waterfall-chart', waterfallData, waterfallLayout, {{ displayModeBar: false, responsive: true }});
          }} else {{
            document.getElementById('detail-table-body').innerHTML = '<tr><td colspan="2" style="padding: 20px; text-align: center; color: #64748b;">データがありません</td></tr>';
          }}
          detailsDiv.scrollTop = 0;
        }});
      }}, 500);
    }});
  </script>
</body>
</html>
"""

    output_path = config['output']['html_file']
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\nDashboard HTML generated: {output_path}")
