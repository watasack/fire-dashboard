"""
可視化モジュール
Plotlyでインタラクティブグラフを生成
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Any


def get_common_layout(config: Dict[str, Any], title: str = "") -> dict:
    """
    共通のグラフレイアウト設定を取得

    Args:
        config: 設定辞書
        title: グラフタイトル

    Returns:
        レイアウト設定辞書
    """
    return {
        'title': {
            'text': title,
            'font': {'size': 20, 'weight': 'bold', 'color': '#1f2937'},
            'x': 0.5,
            'xanchor': 'center'
        },
        'font': {
            'family': config['visualization']['font_family'],
            'size': 13,
            'color': '#374151'
        },
        'plot_bgcolor': 'rgba(249, 250, 251, 0.5)',
        'paper_bgcolor': 'rgba(255, 255, 255, 0)',
        'hovermode': 'x unified',
        'hoverlabel': {
            'bgcolor': 'white',
            'font': {'size': 13, 'family': config['visualization']['font_family']},
            'bordercolor': '#e5e7eb'
        },
        'margin': {'l': 60, 'r': 40, 't': 80, 'b': 60},
        'legend': {
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'right',
            'x': 1,
            'bgcolor': 'rgba(255, 255, 255, 0.8)',
            'bordercolor': '#e5e7eb',
            'borderwidth': 1
        }
    }


def create_asset_timeline_chart(asset_df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
    """
    資産推移グラフを作成

    Args:
        asset_df: 資産推移データフレーム
        config: 設定辞書

    Returns:
        Plotlyグラフオブジェクト
    """
    colors = config['visualization']['color_scheme']

    fig = go.Figure()

    # 純資産（メイン）
    fig.add_trace(go.Scatter(
        x=asset_df['date'],
        y=asset_df['net_assets'],
        name='純資産',
        line=dict(color='#10b981', width=3),
        mode='lines',
        fill='tozeroy',
        fillcolor='rgba(16, 185, 129, 0.1)'
    ))

    # 総資産
    fig.add_trace(go.Scatter(
        x=asset_df['date'],
        y=asset_df['total_assets'],
        name='総資産',
        line=dict(color='#6366f1', width=2),
        mode='lines'
    ))

    # 債務
    fig.add_trace(go.Scatter(
        x=asset_df['date'],
        y=asset_df['debt'],
        name='債務',
        line=dict(color='#ef4444', width=2, dash='dot'),
        mode='lines'
    ))

    # レイアウト
    layout = get_common_layout(config, '資産推移')
    layout.update({
        'xaxis': {
            'title': {'text': '日付', 'font': {'size': 14, 'weight': 'bold'}},
            'showgrid': True,
            'gridcolor': '#e5e7eb',
            'gridwidth': 1,
            'rangeselector': {
                'buttons': [
                    {'count': 1, 'label': "1ヶ月", 'step': "month", 'stepmode': "backward"},
                    {'count': 3, 'label': "3ヶ月", 'step': "month", 'stepmode': "backward"},
                    {'count': 6, 'label': "6ヶ月", 'step': "month", 'stepmode': "backward"},
                    {'count': 1, 'label': "1年", 'step': "year", 'stepmode': "backward"},
                    {'step': "all", 'label': "全期間"}
                ],
                'bgcolor': 'rgba(255, 255, 255, 0.9)',
                'activecolor': '#6366f1',
                'font': {'size': 11}
            },
            'rangeslider': {'visible': True, 'bgcolor': 'rgba(249, 250, 251, 0.8)'}
        },
        'yaxis': {
            'title': {'text': '金額 (円)', 'font': {'size': 14, 'weight': 'bold'}},
            'showgrid': True,
            'gridcolor': '#e5e7eb',
            'gridwidth': 1,
            'tickformat': ',.0f'
        },
        'height': 550
    })

    fig.update_layout(layout)

    return fig


def create_fire_progress_chart(
    current_status: Dict[str, Any],
    fire_target: Dict[str, Any],
    config: Dict[str, Any]
) -> go.Figure:
    """
    FIRE達成進捗チャートを作成

    Args:
        current_status: 現状分析結果
        fire_target: FIRE目標額情報
        config: 設定辞書

    Returns:
        Plotlyグラフオブジェクト
    """
    # サブプロット作成（ゲージ + 棒グラフ）
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "indicator"}, {"type": "bar"}]],
        subplot_titles=("", ""),
        column_widths=[0.45, 0.55],
        horizontal_spacing=0.15
    )

    # ゲージチャート
    progress_rate = fire_target['progress_rate']
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=progress_rate * 100,
        title={'text': "FIRE達成率", 'font': {'size': 18, 'weight': 'bold', 'color': '#1f2937'}},
        number={'suffix': "%", 'font': {'size': 42, 'weight': 'bold', 'color': '#10b981'}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 2, 'tickcolor': '#d1d5db'},
            'bar': {'color': '#10b981', 'thickness': 0.8},
            'bgcolor': "rgba(249, 250, 251, 0.5)",
            'borderwidth': 2,
            'bordercolor': "#e5e7eb",
            'steps': [
                {'range': [0, 25], 'color': 'rgba(239, 68, 68, 0.15)'},
                {'range': [25, 50], 'color': 'rgba(251, 146, 60, 0.15)'},
                {'range': [50, 75], 'color': 'rgba(251, 191, 36, 0.15)'},
                {'range': [75, 100], 'color': 'rgba(16, 185, 129, 0.15)'}
            ],
            'threshold': {
                'line': {'color': "#10b981", 'width': 4},
                'thickness': 0.85,
                'value': 100
            }
        }
    ), row=1, col=1)

    # 棒グラフ（現在資産 vs 目標）
    current_assets = fire_target['current_net_assets']
    target_assets = fire_target['recommended_target']
    shortfall = fire_target['shortfall']

    fig.add_trace(go.Bar(
        x=['現在の資産', '不足額'],
        y=[current_assets, shortfall],
        marker={
            'color': ['#10b981', '#f59e0b'],
            'line': {'color': '#ffffff', 'width': 2}
        },
        text=[f'JPY{current_assets:,.0f}', f'JPY{shortfall:,.0f}'],
        textposition='outside',
        textfont={'size': 13, 'weight': 'bold', 'color': '#374151'},
        hovertemplate='<b>%{x}</b><br>JPY%{y:,.0f}<extra></extra>'
    ), row=1, col=2)

    # レイアウト
    fig.update_layout(
        title={
            'text': 'FIRE達成進捗',
            'font': {'size': 20, 'weight': 'bold', 'color': '#1f2937'},
            'x': 0.5,
            'xanchor': 'center'
        },
        height=500,
        showlegend=False,
        font={'family': config['visualization']['font_family'], 'size': 13},
        plot_bgcolor='rgba(249, 250, 251, 0.5)',
        paper_bgcolor='rgba(255, 255, 255, 0)',
        margin={'l': 40, 'r': 40, 't': 100, 'b': 60}
    )

    # 棒グラフの軸設定
    fig.update_xaxes(showgrid=False, row=1, col=2)
    fig.update_yaxes(
        showgrid=True,
        gridcolor='#e5e7eb',
        tickformat=',.0f',
        title={'text': '金額 (円)', 'font': {'size': 13}},
        row=1, col=2
    )

    # 目標額の注釈
    fig.add_annotation(
        text=f"🎯 目標: <b>JPY{target_assets:,.0f}</b>",
        xref="paper", yref="paper",
        x=0.75, y=1.12,
        showarrow=False,
        font={'size': 15, 'color': '#6366f1', 'weight': 'bold'},
        bgcolor='rgba(99, 102, 241, 0.1)',
        bordercolor='#6366f1',
        borderwidth=2,
        borderpad=8
    )

    return fig


def create_expense_breakdown_chart(
    expense_breakdown: Dict[str, Any],
    config: Dict[str, Any]
) -> go.Figure:
    """
    カテゴリー別支出分析チャートを作成

    Args:
        expense_breakdown: カテゴリー別支出情報
        config: 設定辞書

    Returns:
        Plotlyグラフオブジェクト
    """
    top_categories = expense_breakdown['top_categories']

    # データ準備
    categories = [cat['category'] for cat in top_categories]
    amounts = [cat['amount'] for cat in top_categories]

    # プロフェッショナルなカラーパレット
    colors_palette = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']

    # ドーナツチャート
    fig = go.Figure(data=[go.Pie(
        labels=categories,
        values=amounts,
        hole=0.45,
        marker={
            'colors': colors_palette[:len(categories)],
            'line': {'color': '#ffffff', 'width': 3}
        },
        textinfo='label+percent',
        textposition='outside',
        textfont={'size': 13, 'weight': 'bold'},
        hovertemplate='<b>%{label}</b><br>金額: JPY%{value:,.0f}<br>割合: %{percent}<extra></extra>',
        pull=[0.05 if i == 0 else 0 for i in range(len(categories))]  # 最大カテゴリーを少し引き出す
    )])

    # 中央にテキスト追加
    total_expense = expense_breakdown['total_expense']
    fig.add_annotation(
        text=f"<b>総支出</b><br>JPY{total_expense:,.0f}",
        x=0.5, y=0.5,
        font={'size': 16, 'color': '#1f2937', 'weight': 'bold'},
        showarrow=False,
        align='center'
    )

    # レイアウト
    layout = get_common_layout(config, 'カテゴリー別支出内訳 (Top 5)')
    layout.update({
        'height': 500,
        'showlegend': True,
        'legend': {
            'orientation': 'v',
            'yanchor': 'middle',
            'y': 0.5,
            'xanchor': 'left',
            'x': 1.05,
            'bgcolor': 'rgba(255, 255, 255, 0.9)',
            'bordercolor': '#e5e7eb',
            'borderwidth': 1,
            'font': {'size': 12}
        }
    })

    fig.update_layout(layout)

    return fig


def create_future_simulation_chart(
    simulations: Dict[str, pd.DataFrame],
    fire_target: Dict[str, Any],
    config: Dict[str, Any]
) -> go.Figure:
    """
    将来資産シミュレーションチャートを作成

    Args:
        simulations: シナリオ別シミュレーション結果
        fire_target: FIRE目標額情報
        config: 設定辞書

    Returns:
        Plotlyグラフオブジェクト
    """
    fig = go.Figure()

    # シナリオ設定（色と順序を改善）
    scenario_config = {
        'optimistic': {
            'name': '楽観シナリオ (7%)',
            'color': '#10b981',
            'fill': 'rgba(16, 185, 129, 0.15)'
        },
        'standard': {
            'name': '標準シナリオ (5%)',
            'color': '#6366f1',
            'fill': 'rgba(99, 102, 241, 0.2)'
        },
        'pessimistic': {
            'name': '悲観シナリオ (3%)',
            'color': '#ef4444',
            'fill': 'rgba(239, 68, 68, 0.15)'
        }
    }

    # 各シナリオの資産推移（逆順で追加してfillを正しく）
    for scenario in ['pessimistic', 'standard', 'optimistic']:
        if scenario in simulations:
            df = simulations[scenario]
            cfg = scenario_config[scenario]

            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['assets'],
                name=cfg['name'],
                mode='lines',
                line={'width': 3 if scenario == 'standard' else 2, 'color': cfg['color']},
                fill='tonexty' if scenario != 'pessimistic' else 'tozeroy',
                fillcolor=cfg['fill'],
                hovertemplate='<b>%{fullData.name}</b><br>日付: %{x|%Y年%m月}<br>資産: JPY%{y:,.0f}<extra></extra>'
            ))

    # FIRE目標額の横線
    target = fire_target['recommended_target']
    if len(simulations) > 0:
        first_scenario = list(simulations.values())[0]
        fig.add_trace(go.Scatter(
            x=[first_scenario['date'].iloc[0], first_scenario['date'].iloc[-1]],
            y=[target, target],
            name=f'🎯 FIRE目標額',
            mode='lines',
            line={'color': '#f59e0b', 'width': 3, 'dash': 'dash'},
            hovertemplate=f'<b>FIRE目標額</b><br>JPY{target:,.0f}<extra></extra>'
        ))

    # レイアウト
    layout = get_common_layout(config, '将来資産シミュレーション (50年)')
    layout.update({
        'xaxis': {
            'title': {'text': '年', 'font': {'size': 14, 'weight': 'bold'}},
            'showgrid': True,
            'gridcolor': '#e5e7eb'
        },
        'yaxis': {
            'title': {'text': '資産 (円)', 'font': {'size': 14, 'weight': 'bold'}},
            'showgrid': True,
            'gridcolor': '#e5e7eb',
            'tickformat': ',.0f'
        },
        'height': 550
    })

    fig.update_layout(layout)

    return fig


def create_monthly_cashflow_chart(
    cashflow_df: pd.DataFrame,
    config: Dict[str, Any]
) -> go.Figure:
    """
    月次収支推移チャートを作成（オプション）

    Args:
        cashflow_df: 月次収支データフレーム
        config: 設定辞書

    Returns:
        Plotlyグラフオブジェクト
    """
    colors = config['visualization']['color_scheme']

    fig = go.Figure()

    # 収入
    fig.add_trace(go.Bar(
        x=cashflow_df['month'],
        y=cashflow_df['income'],
        name='収入',
        marker={'color': '#10b981', 'line': {'color': '#ffffff', 'width': 2}}
    ))

    # 支出（負の値として表示）
    fig.add_trace(go.Bar(
        x=cashflow_df['month'],
        y=-cashflow_df['expense'],
        name='支出',
        marker={'color': '#ef4444', 'line': {'color': '#ffffff', 'width': 2}}
    ))

    # 純収支（折れ線）
    fig.add_trace(go.Scatter(
        x=cashflow_df['month'],
        y=cashflow_df['net_cashflow'],
        name='純収支',
        mode='lines+markers',
        line={'color': '#6366f1', 'width': 3},
        marker={'size': 8},
        yaxis='y2'
    ))

    # レイアウト
    layout = get_common_layout(config, '月次収支推移')
    layout.update({
        'xaxis': {'title': '月'},
        'yaxis': {'title': '収入・支出 (円)'},
        'yaxis2': {
            'title': '純収支 (円)',
            'overlaying': 'y',
            'side': 'right'
        },
        'barmode': 'relative',
        'height': 500
    })

    fig.update_layout(layout)

    return fig
