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
    font_family = "'Inter', " + config['visualization']['font_family']
    return {
        'title': {
            'text': '',
        },
        'font': {
            'family': font_family,
            'size': 12,
            'color': '#334155'
        },
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
        'hovermode': 'x unified',
        'hoverlabel': {
            'bgcolor': '#164e63',
            'font': {'size': 12, 'family': font_family, 'color': '#ecfeff'},
            'bordercolor': '#0e7490'
        },
        'margin': {'l': 56, 'r': 24, 't': 24, 'b': 48},
        'legend': {
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'right',
            'x': 1,
            'bgcolor': 'rgba(255, 255, 255, 0)',
            'borderwidth': 0,
            'font': {'size': 12, 'color': '#475569'}
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
    fig = go.Figure()

    # 純資産（メイン）
    fig.add_trace(go.Scatter(
        x=asset_df['date'],
        y=asset_df['net_assets'],
        name='純資産',
        line=dict(color='#0d9488', width=2.5, shape='spline'),
        mode='lines',
        fill='tozeroy',
        fillcolor='rgba(13, 148, 136, 0.06)'
    ))

    # 総資産
    fig.add_trace(go.Scatter(
        x=asset_df['date'],
        y=asset_df['total_assets'],
        name='総資産',
        line=dict(color='#06b6d4', width=2, shape='spline'),
        mode='lines'
    ))

    # 債務
    fig.add_trace(go.Scatter(
        x=asset_df['date'],
        y=asset_df['debt'],
        name='債務',
        line=dict(color='#e11d48', width=1.5, dash='dot', shape='spline'),
        mode='lines'
    ))

    # レイアウト
    layout = get_common_layout(config, '')
    layout.update({
        'xaxis': {
            'title': '',
            'showgrid': False,
            'zeroline': False,
            'rangeselector': {
                'buttons': [
                    {'count': 1, 'label': "1M", 'step': "month", 'stepmode': "backward"},
                    {'count': 3, 'label': "3M", 'step': "month", 'stepmode': "backward"},
                    {'count': 6, 'label': "6M", 'step': "month", 'stepmode': "backward"},
                    {'count': 1, 'label': "1Y", 'step': "year", 'stepmode': "backward"},
                    {'step': "all", 'label': "All"}
                ],
                'bgcolor': '#e0f2fe',
                'activecolor': '#06b6d4',
                'font': {'size': 11, 'color': '#334155'},
                'borderwidth': 0,
                'y': 1.08
            },
            'rangeslider': {'visible': True, 'bgcolor': '#f8fafc', 'thickness': 0.06}
        },
        'yaxis': {
            'title': '',
            'showgrid': True,
            'gridcolor': '#e0f2fe',
            'gridwidth': 1,
            'tickformat': ',.0f',
            'zeroline': False,
            'side': 'right'
        },
        'height': 480
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
        title={'text': "達成率", 'font': {'size': 14, 'weight': 'bold', 'color': '#475569'}},
        number={'suffix': "%", 'font': {'size': 36, 'weight': 'bold', 'color': '#164e63'}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': '#bae6fd', 'dtick': 25},
            'bar': {'color': '#06b6d4', 'thickness': 0.75},
            'bgcolor': "#e0f2fe",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 25], 'color': '#ffe4e6'},
                {'range': [25, 50], 'color': '#fef3c7'},
                {'range': [50, 75], 'color': '#cffafe'},
                {'range': [75, 100], 'color': '#ccfbf1'}
            ],
            'threshold': {
                'line': {'color': "#0d9488", 'width': 3},
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
            'color': ['#06b6d4', '#e0f2fe'],
            'line': {'width': 0},
            'cornerradius': 6
        },
        text=[f'{current_assets/10000:,.0f}万円', f'{shortfall/10000:,.0f}万円'],
        textposition='outside',
        textfont={'size': 12, 'weight': 'bold', 'color': '#334155'},
        hovertemplate='<b>%{x}</b><br>%{y:,.0f}円<extra></extra>'
    ), row=1, col=2)

    font_family = "'Inter', " + config['visualization']['font_family']
    # レイアウト
    fig.update_layout(
        title='',
        height=440,
        showlegend=False,
        font={'family': font_family, 'size': 12, 'color': '#334155'},
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        margin={'l': 32, 'r': 32, 't': 48, 'b': 48}
    )

    # 棒グラフの軸設定
    fig.update_xaxes(showgrid=False, row=1, col=2)
    fig.update_yaxes(
        showgrid=True,
        gridcolor='#e0f2fe',
        tickformat=',.0f',
        title='',
        zeroline=False,
        row=1, col=2
    )

    # 目標額の注釈
    fig.add_annotation(
        text=f"目標: <b>{target_assets/10000:,.0f}万円</b>",
        xref="paper", yref="paper",
        x=0.75, y=1.08,
        showarrow=False,
        font={'size': 12, 'color': '#0891b2', 'weight': 'bold'},
        bgcolor='rgba(6, 182, 212, 0.08)',
        bordercolor='rgba(6, 182, 212, 0.2)',
        borderwidth=1,
        borderpad=6
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

    # Refined color palette - cyan-centric
    colors_palette = ['#06b6d4', '#0d9488', '#d97706', '#e11d48', '#8b5cf6', '#0891b2', '#14b8a6', '#f59e0b']

    # ドーナツチャート
    fig = go.Figure(data=[go.Pie(
        labels=categories,
        values=amounts,
        hole=0.55,
        marker={
            'colors': colors_palette[:len(categories)],
            'line': {'color': '#ffffff', 'width': 2}
        },
        textinfo='label+percent',
        textposition='outside',
        textfont={'size': 11, 'weight': 'bold', 'color': '#334155'},
        hovertemplate='<b>%{label}</b><br>金額: %{value:,.0f}円<br>割合: %{percent}<extra></extra>',
        pull=[0.03 if i == 0 else 0 for i in range(len(categories))]
    )])

    # 中央にテキスト追加
    total_expense = expense_breakdown['total_expense']
    fig.add_annotation(
        text=f"<b>{total_expense/10000:,.1f}万円</b><br><span style='font-size:11px;color:#7c9aaf'>総支出</span>",
        x=0.5, y=0.5,
        font={'size': 15, 'color': '#164e63', 'weight': 'bold'},
        showarrow=False,
        align='center'
    )

    # レイアウト
    layout = get_common_layout(config, '')
    layout.update({
        'height': 440,
        'showlegend': True,
        'legend': {
            'orientation': 'v',
            'yanchor': 'middle',
            'y': 0.5,
            'xanchor': 'left',
            'x': 1.02,
            'bgcolor': 'rgba(0, 0, 0, 0)',
            'borderwidth': 0,
            'font': {'size': 12, 'color': '#334155'}
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
            'name': '楽観 (7%)',
            'color': '#0d9488',
            'fill': 'rgba(13, 148, 136, 0.06)'
        },
        'standard': {
            'name': '標準 (5%)',
            'color': '#06b6d4',
            'fill': 'rgba(6, 182, 212, 0.08)'
        },
        'pessimistic': {
            'name': '悲観 (3%)',
            'color': '#e11d48',
            'fill': 'rgba(225, 29, 72, 0.04)'
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
                line={'width': 2.5 if scenario == 'standard' else 1.5, 'color': cfg['color'], 'shape': 'spline'},
                fill='tonexty' if scenario != 'pessimistic' else 'tozeroy',
                fillcolor=cfg['fill'],
                hovertemplate='<b>%{fullData.name}</b><br>%{x|%Y年%m月}<br>%{y:,.0f}円<extra></extra>'
            ))

    # FIRE目標額の横線
    target = fire_target['recommended_target']
    if len(simulations) > 0:
        first_scenario = list(simulations.values())[0]
        fig.add_trace(go.Scatter(
            x=[first_scenario['date'].iloc[0], first_scenario['date'].iloc[-1]],
            y=[target, target],
            name='FIRE目標',
            mode='lines',
            line={'color': '#f59e0b', 'width': 2, 'dash': 'dash'},
            hovertemplate=f'<b>FIRE目標</b><br>{target:,.0f}円<extra></extra>'
        ))

    # レイアウト
    layout = get_common_layout(config, '')
    layout.update({
        'xaxis': {
            'title': '',
            'showgrid': False,
            'zeroline': False
        },
        'yaxis': {
            'title': '',
            'showgrid': True,
            'gridcolor': '#e0f2fe',
            'tickformat': ',.0f',
            'zeroline': False,
            'side': 'right'
        },
        'height': 480
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
    fig = go.Figure()

    # 収入
    fig.add_trace(go.Bar(
        x=cashflow_df['month'],
        y=cashflow_df['income'],
        name='収入',
        marker={'color': '#0d9488', 'line': {'width': 0}, 'cornerradius': 4}
    ))

    # 支出（負の値として表示）
    fig.add_trace(go.Bar(
        x=cashflow_df['month'],
        y=-cashflow_df['expense'],
        name='支出',
        marker={'color': '#e11d48', 'line': {'width': 0}, 'cornerradius': 4}
    ))

    # 純収支（折れ線）
    fig.add_trace(go.Scatter(
        x=cashflow_df['month'],
        y=cashflow_df['net_cashflow'],
        name='純収支',
        mode='lines+markers',
        line={'color': '#06b6d4', 'width': 2.5, 'shape': 'spline'},
        marker={'size': 6},
        yaxis='y2'
    ))

    # レイアウト
    layout = get_common_layout(config, '')
    layout.update({
        'xaxis': {'title': '', 'showgrid': False},
        'yaxis': {'title': '', 'showgrid': True, 'gridcolor': '#e0f2fe', 'zeroline': False},
        'yaxis2': {
            'title': '',
            'overlaying': 'y',
            'side': 'right',
            'showgrid': False,
            'zeroline': False
        },
        'barmode': 'relative',
        'height': 440
    })

    fig.update_layout(layout)

    return fig
