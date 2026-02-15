"""
HTML生成モジュール
Plotlyグラフを統合してダッシュボードHTMLを生成
"""

import plotly.graph_objects as go
from typing import Dict, Any, List
from datetime import datetime


def generate_dashboard_html(
    charts: Dict[str, go.Figure],
    summary_data: Dict[str, Any],
    action_items: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> None:
    """
    一画面完結型のダッシュボードHTMLを生成

    Args:
        charts: グラフオブジェクトの辞書
        summary_data: サマリーデータ
        action_items: アクションアイテムのリスト
        config: 設定辞書
    """
    current_status = summary_data['current_status']
    fire_target = summary_data['fire_target']
    fire_achievement = summary_data.get('fire_achievement')
    trends = summary_data['trends']
    expense_breakdown = summary_data['expense_breakdown']
    update_time = summary_data['update_time']

    # グラフをHTMLに変換
    fire_timeline_html = charts['fire_timeline'].to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})

    # FIRE達成情報の文字列生成
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

    # カテゴリー別支出比率をJSON化
    import json
    category_percentages = expense_breakdown.get('category_percentages', {})
    # TOP5のみを取得
    top_categories = sorted(category_percentages.items(), key=lambda x: x[1], reverse=True)[:5]
    category_data_json = json.dumps(dict(top_categories))

    # 家族情報をJSON化
    family_info = []

    # 親の情報
    pension_people = config.get('pension', {}).get('people', [])
    for person in pension_people:
        family_info.append({
            'name': person.get('name', ''),
            'birthdate': person.get('birthdate', ''),
            'role': 'parent'
        })

    # 子供の情報
    children = config.get('education', {}).get('children', [])
    for i, child in enumerate(children):
        child_name = child.get('name', f'子供{i+1}')  # 名前が設定されていればそれを使用
        family_info.append({
            'name': child_name,
            'birthdate': child.get('birthdate', ''),
            'role': 'child'
        })

    family_info_json = json.dumps(family_info, ensure_ascii=False)

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
    </header>

    <!-- メインKPI -->
    <section class="hero-kpi">
      <div class="kpi-primary">
        <div class="kpi-label">FIRE達成率</div>
        <div class="kpi-value kpi-value--large">{fire_target['progress_rate']:.1%}</div>
        <div class="kpi-detail">あと¥{fire_target['shortfall']/10000:,.0f}万円</div>
      </div>
      <div class="kpi-divider"></div>
      <div class="kpi-primary">
        <div class="kpi-label">達成予想</div>
        <div class="kpi-value kpi-value--large">{achievement_text}</div>
        <div class="kpi-detail">{achievement_detail}</div>
      </div>
    </section>

    <!-- メイングラフ（全幅） -->
    <section class="main-chart">
      <div class="chart-panel">
        <h2 class="chart-title">資産シミュレーション</h2>
        <div class="chart-content">
          {fire_timeline_html}
        </div>
        <!-- クリック詳細情報 -->
        <div id="click-details" style="display: none; margin-top: 20px; padding: 20px; background: #f0f9ff; border-radius: 8px; border-left: 4px solid #06b6d4; max-height: 600px; overflow-y: auto;">
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
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; min-height: 0;">

            <!-- 左側: ウォーターフォールグラフ -->
            <div>
              <div id="waterfall-chart" style="width: 100%; height: 350px;"></div>
            </div>

            <!-- 右側: 詳細テーブル -->
            <div>
              <table id="detail-table" style="width: 100%; border-collapse: collapse; font-size: 13px; background: white; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                <thead>
                  <tr style="background: #e0f2fe;">
                    <th style="padding: 10px 12px; text-align: left; font-weight: 600; color: #0c4a6e; border-bottom: 2px solid #bae6fd;">項目</th>
                    <th style="padding: 10px 12px; text-align: right; font-weight: 600; color: #0c4a6e; border-bottom: 2px solid #bae6fd;">金額</th>
                  </tr>
                </thead>
                <tbody id="detail-table-body">
                  <!-- JavaScriptで動的に生成 -->
                </tbody>
              </table>
            </div>

          </div>
        </div>
      </div>
    </section>

  </div>

  <!-- グラフクリックイベント処理 -->
  <script>
    // カテゴリー別支出比率（TOP5）
    const categoryPercentages = {category_data_json};

    // 家族情報
    const familyInfo = {family_info_json};

    // 年齢計算関数
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

    // Plotlyグラフの読み込み完了を待つ
    window.addEventListener('load', function() {{
      // 少し遅延させてPlotlyグラフが確実にレンダリングされるまで待つ
      setTimeout(function() {{
        const graphDiv = document.querySelector('.chart-content .plotly-graph-div');

        if (!graphDiv) {{
          console.error('グラフが見つかりません');
          return;
        }}

        console.log('グラフが見つかりました:', graphDiv);

        // Plotlyクリックイベントをリッスン
        graphDiv.on('plotly_click', function(data) {{
          console.log('クリックイベント:', data);

          const point = data.points[0];
          if (!point) return;

          // クリックされた点のデータを取得
          const date = new Date(point.x);
          const assets = point.y;
          const customdata = point.customdata;

          console.log('カスタムデータ:', customdata);

          // 詳細パネルを表示
          const detailsDiv = document.getElementById('click-details');
          detailsDiv.style.display = 'block';

          // 日付フォーマット
          const dateStr = date.getFullYear() + '年' +
                         (date.getMonth() + 1) + '月';

          // データを表示
          document.getElementById('detail-date').textContent = dateStr;
          document.getElementById('detail-assets').textContent =
            '¥' + assets.toFixed(1) + '万';

          if (customdata && customdata.length >= 7) {{
            // customdata: [labor_income, pension_income, base_expense, education_expense, mortgage_payment, maintenance_cost, investment_return]
            const laborIncome = customdata[0];
            const pensionIncome = customdata[1];
            const baseExpense = customdata[2];
            const educationExpense = customdata[3];
            const mortgagePayment = customdata[4];
            const maintenanceCost = customdata[5];
            const investmentReturn = customdata[6];

            const totalIncome = laborIncome + pensionIncome;
            const totalExpense = baseExpense + educationExpense + mortgagePayment + maintenanceCost;

            // 詳細テーブルを生成
            const tableBody = document.getElementById('detail-table-body');
            tableBody.innerHTML = '';

            // ヘルパー関数: テーブル行を追加
            function addRow(label, value, className = '') {{
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

              // スタイル設定
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

            // 家族情報セクション
            if (familyInfo.length > 0) {{
              addRow('家族構成', '', 'section-header');
              for (const person of familyInfo) {{
                const age = calculateAge(person.birthdate, date);
                const ageStr = age + '歳';
                addRow(person.name, ageStr, 'subcategory');
              }}
            }}

            // 収入セクション
            addRow('収入', '', 'section-header');
            if (laborIncome > 0) {{
              addRow('労働収入', '+¥' + (laborIncome / 10000).toFixed(1) + '万', 'income');
            }}
            if (pensionIncome > 0) {{
              addRow('年金収入', '+¥' + (pensionIncome / 10000).toFixed(1) + '万', 'income');
            }}
            addRow('収入合計', '¥' + (totalIncome / 10000).toFixed(1) + '万', 'subtotal bold');

            // 支出セクション
            addRow('支出', '', 'section-header');

            // 基本生活費をカテゴリ別に表示
            if (baseExpense > 0) {{
              const baseExpenseManEn = baseExpense / 10000;
              addRow('基本生活費', '-¥' + baseExpenseManEn.toFixed(1) + '万', 'expense');

              // カテゴリー別に表示（TOP5）
              const categories = Object.keys(categoryPercentages);
              if (categories.length > 0) {{
                for (const category of categories) {{
                  const percentage = categoryPercentages[category] / 100;
                  const categoryExpense = baseExpenseManEn * percentage;
                  if (categoryExpense > 0.1) {{
                    addRow('  - ' + category, '-¥' + categoryExpense.toFixed(1) + '万', 'subcategory');
                  }}
                }}
              }}
            }}

            if (educationExpense > 0) {{
              addRow('教育費', '-¥' + (educationExpense / 10000).toFixed(1) + '万', 'expense');
            }}
            if (mortgagePayment > 0) {{
              addRow('住宅ローン', '-¥' + (mortgagePayment / 10000).toFixed(1) + '万', 'expense');
            }}
            if (maintenanceCost > 0) {{
              addRow('メンテナンス費用', '-¥' + (maintenanceCost / 10000).toFixed(1) + '万', 'expense');
            }}
            addRow('支出合計', '-¥' + (totalExpense / 10000).toFixed(1) + '万', 'subtotal bold');

            // その他セクション
            addRow('その他', '', 'section-header');
            if (investmentReturn > 0) {{
              addRow('運用益', '+¥' + (investmentReturn / 10000).toFixed(1) + '万', 'income');
            }}

            // 純変動
            const netChange = (totalIncome - totalExpense + investmentReturn) / 10000;
            const netChangeStr = (netChange >= 0 ? '+' : '') + '¥' + netChange.toFixed(1) + '万';
            addRow('純変動', netChangeStr, 'total');

            // ウォーターフォールグラフを作成（細分化、0円項目を除外）

            // データ項目を定義（0でない項目のみ含める）
            const items = [];
            if (laborIncome !== 0) {{
              items.push({{
                label: '労働収入',
                value: laborIncome / 10000,
                measure: 'relative'
              }});
            }}
            if (pensionIncome !== 0) {{
              items.push({{
                label: '年金収入',
                value: pensionIncome / 10000,
                measure: 'relative'
              }});
            }}

            // 基本生活費をカテゴリー別に分割（TOP5）
            if (baseExpense !== 0) {{
              const baseExpenseManEn = baseExpense / 10000;
              const categories = Object.keys(categoryPercentages);

              if (categories.length > 0) {{
                // カテゴリー別に分割
                for (const category of categories) {{
                  const percentage = categoryPercentages[category] / 100;
                  const categoryExpense = baseExpenseManEn * percentage;
                  if (categoryExpense > 0.1) {{  // 0.1万円以上のみ表示
                    items.push({{
                      label: category,
                      value: -categoryExpense,
                      measure: 'relative'
                    }});
                  }}
                }}
              }} else {{
                // カテゴリーデータがない場合は基本生活費として表示
                items.push({{
                  label: '基本生活費',
                  value: -baseExpenseManEn,
                  measure: 'relative'
                }});
              }}
            }}

            if (educationExpense !== 0) {{
              items.push({{
                label: '教育費',
                value: -educationExpense / 10000,
                measure: 'relative'
              }});
            }}
            if (mortgagePayment !== 0) {{
              items.push({{
                label: '住宅ローン',
                value: -mortgagePayment / 10000,
                measure: 'relative'
              }});
            }}
            if (maintenanceCost !== 0) {{
              items.push({{
                label: 'メンテナンス',
                value: -maintenanceCost / 10000,
                measure: 'relative'
              }});
            }}
            if (investmentReturn !== 0) {{
              items.push({{
                label: '運用益',
                value: investmentReturn / 10000,
                measure: 'relative'
              }});
            }}

            // 純変動を最後に追加
            items.push({{
              label: '純変動',
              value: netChange,
              measure: 'total'
            }});

            const waterfallData = [{{
              type: 'waterfall',
              orientation: 'v',
              x: items.map(item => item.label),
              y: items.map(item => item.value),
              measure: items.map(item => item.measure),
              textposition: 'auto',
              text: items.map(item => {{
                const val = item.value;
                const prefix = val >= 0 ? '+' : '';
                return prefix + val.toFixed(1) + '万';
              }}),
              increasing: {{ marker: {{ color: '#10b981' }} }},
              decreasing: {{ marker: {{ color: '#ef4444' }} }},
              totals: {{ marker: {{ color: '#06b6d4' }} }},
              connector: {{
                line: {{ color: '#94a3b8', width: 1, dash: 'dot' }}
              }}
            }}];

            const waterfallLayout = {{
              showlegend: false,
              margin: {{ t: 40, b: 50, l: 50, r: 20 }},
              yaxis: {{
                title: '万円',
                tickformat: ',.0f',
                gridcolor: '#e0f2fe'
              }},
              xaxis: {{
                tickangle: 0
              }},
              plot_bgcolor: '#f0f9ff',
              paper_bgcolor: '#f0f9ff'
            }};

            Plotly.newPlot('waterfall-chart', waterfallData, waterfallLayout, {{ displayModeBar: false, responsive: true }});
          }} else {{
            // データがない場合
            const tableBody = document.getElementById('detail-table-body');
            tableBody.innerHTML = '<tr><td colspan="2" style="padding: 20px; text-align: center; color: #64748b;">データがありません</td></tr>';
          }}

          // 詳細パネルの内部スクロールを最上部にリセット
          detailsDiv.scrollTop = 0;
        }});
      }}, 500); // 500ms待機
    }});
  </script>
</body>
</html>
"""

    # ファイル出力
    output_path = config['output']['html_file']
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\nDashboard HTML generated: {output_path}")
