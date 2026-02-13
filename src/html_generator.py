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
    <header>
        <h1>{config['project']['name']}</h1>
        <p class="subtitle">{config['project']['description']}</p>
        <p class="update-time">最終更新: {update_time.strftime('%Y年%m月%d日 %H:%M')}</p>
    </header>

    <section class="summary-cards">
        <div class="card">
            <h3>💰 現在の純資産</h3>
            <p class="value">¥{current_status['net_assets']/10000:,.0f}万</p>
            <p class="subvalue">総資産: ¥{current_status['total_assets']/10000:,.0f}万円</p>
        </div>

        <div class="card">
            <h3>🎯 FIRE達成率</h3>
            <p class="value">{fire_target['progress_rate']:.1%}</p>
            <p class="subvalue">目標: ¥{fire_target['recommended_target']/10000:,.0f}万円</p>
        </div>

        <div class="card">
            <h3>📊 貯蓄率</h3>
            <p class="value">{trends['savings_rate']:.1%}</p>
            <p class="subvalue">月次平均: ¥{trends['monthly_avg_savings']/10000:,.1f}万円</p>
        </div>

        <div class="card">
            <h3>💸 年間支出</h3>
            <p class="value">¥{trends['annual_expense']/10000:,.0f}万</p>
            <p class="subvalue">月次平均: ¥{trends['monthly_avg_expense']/10000:,.1f}万円</p>
        </div>
    </section>

    <section class="dashboard-grid">
        <div class="chart-container">
            {asset_timeline_html}
        </div>

        <div class="chart-container">
            {fire_progress_html}
        </div>

        <div class="chart-container">
            {expense_breakdown_html}
        </div>

        <div class="chart-container">
            {future_simulation_html}
        </div>
    </section>

    <footer>
        <p>データソース: 資産推移月次.csv, 収入・支出詳細.csv</p>
        <p>シミュレーション設定: 標準シナリオ {config['simulation']['standard']['annual_return_rate']:.1%} リターン, {config['simulation']['standard']['inflation_rate']:.1%} インフレ</p>
    </footer>
</body>
</html>
"""

    # ファイル出力
    output_path = config['output']['html_file']
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\nDashboard HTML generated: {output_path}")
