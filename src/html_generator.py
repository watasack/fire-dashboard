"""
HTML生成モジュール
Plotlyグラフを統合してダッシュボードHTMLを生成
"""

import plotly.graph_objects as go
from typing import Dict, Any
from datetime import datetime


def generate_dashboard_html(
    charts: Dict[str, go.Figure],
    summary_data: Dict[str, Any],
    config: Dict[str, Any]
) -> None:
    """
    ダッシュボードHTMLを生成

    Args:
        charts: グラフオブジェクトの辞書
        summary_data: サマリーデータ
        config: 設定辞書
    """
    current_status = summary_data['current_status']
    fire_target = summary_data['fire_target']
    trends = summary_data['trends']
    update_time = summary_data['update_time']

    # グラフをHTMLに変換
    asset_timeline_html = charts['asset_timeline'].to_html(full_html=False, include_plotlyjs='cdn')
    fire_progress_html = charts['fire_progress'].to_html(full_html=False, include_plotlyjs=False)
    expense_breakdown_html = charts['expense_breakdown'].to_html(full_html=False, include_plotlyjs=False)
    future_simulation_html = charts['future_simulation'].to_html(full_html=False, include_plotlyjs=False)

    # HTMLテンプレート
    html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FIRE Dashboard</title>
    <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <div class="dashboard-wrapper">
    <header>
      <div class="header-inner">
        <div class="header-top">
          <div class="header-brand">
            <div class="header-logo">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
              </svg>
            </div>
            <div>
              <h1>{config['project']['name']}</h1>
              <p class="subtitle">{config['project']['description']}</p>
            </div>
          </div>
          <div class="header-meta">
            <p class="update-time"><span class="status-dot"></span> 最終更新: {update_time.strftime('%Y年%m月%d日 %H:%M')}</p>
          </div>
        </div>
        <div class="header-divider"></div>
      </div>
    </header>

    <section class="summary-cards">
      <div class="card card--assets">
        <div class="card-icon card-icon--assets">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
        </div>
        <h3>現在の純資産</h3>
        <p class="value">&yen;{current_status['net_assets']/10000:,.0f}万</p>
        <p class="subvalue">総資産: &yen;{current_status['total_assets']/10000:,.0f}万円</p>
      </div>

      <div class="card card--fire">
        <div class="card-icon card-icon--fire">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </div>
        <h3>FIRE達成率</h3>
        <p class="value">{fire_target['progress_rate']:.1%}</p>
        <p class="subvalue">目標: &yen;{fire_target['recommended_target']/10000:,.0f}万円</p>
      </div>

      <div class="card card--savings">
        <div class="card-icon card-icon--savings">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
        </div>
        <h3>貯蓄率</h3>
        <p class="value">{trends['savings_rate']:.1%}</p>
        <p class="subvalue">月次平均: &yen;{trends['monthly_avg_savings']/10000:,.1f}万円</p>
      </div>

      <div class="card card--expense">
        <div class="card-icon card-icon--expense">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
        </div>
        <h3>年間支出</h3>
        <p class="value">&yen;{trends['annual_expense']/10000:,.0f}万</p>
        <p class="subvalue">月次平均: &yen;{trends['monthly_avg_expense']/10000:,.1f}万円</p>
      </div>
    </section>

    <section class="dashboard-grid">
      <div class="chart-container">
        <div class="chart-header">
          <h2>資産推移</h2>
          <span class="chart-badge">時系列</span>
        </div>
        <div class="chart-body">
          {asset_timeline_html}
        </div>
      </div>

      <div class="chart-container">
        <div class="chart-header">
          <h2>FIRE達成進捗</h2>
          <span class="chart-badge">進捗</span>
        </div>
        <div class="chart-body">
          {fire_progress_html}
        </div>
      </div>

      <div class="chart-container">
        <div class="chart-header">
          <h2>カテゴリー別支出</h2>
          <span class="chart-badge">内訳</span>
        </div>
        <div class="chart-body">
          {expense_breakdown_html}
        </div>
      </div>

      <div class="chart-container">
        <div class="chart-header">
          <h2>将来資産シミュレーション</h2>
          <span class="chart-badge">予測</span>
        </div>
        <div class="chart-body">
          {future_simulation_html}
        </div>
      </div>
    </section>

    <footer>
      <div class="footer-links">
        <p>データソース: 資産推移月次.csv, 収入・支出詳細.csv</p>
        <span class="footer-divider"></span>
        <p>標準シナリオ {config['simulation']['standard']['annual_return_rate']:.1%} リターン / {config['simulation']['standard']['inflation_rate']:.1%} インフレ</p>
      </div>
    </footer>
  </div>
</body>
</html>
"""

    # ファイル出力
    output_path = config['output']['html_file']
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\nDashboard HTML generated: {output_path}")
