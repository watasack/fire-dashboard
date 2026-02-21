"""
可視化モジュール
Plotlyでインタラクティブグラフを生成
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
from dateutil.relativedelta import relativedelta
from src.data_schema import get_customdata_column_names

# 資産エリアチャート用の色定数
_COLOR_PRE_FIRE_CASH  = 'rgba(6, 182, 212, 0.4)'   # FIRE前 現金（シアン薄）
_COLOR_PRE_FIRE_STOCK = 'rgba(6, 182, 212, 0.7)'   # FIRE前 株式（シアン濃）
_COLOR_POST_FIRE_CASH  = 'rgba(16, 185, 129, 0.4)'  # FIRE後 現金（グリーン薄）
_COLOR_POST_FIRE_STOCK = 'rgba(16, 185, 129, 0.7)'  # FIRE後 株式（グリーン濃）


def _add_stacked_asset_traces(
    fig: go.Figure,
    df,
    group_key: str,
    cash_name: str,
    stock_name: str,
    cash_color: str,
    stock_color: str,
    customdata,
    cash_hover: str,
    stock_hover: str,
) -> None:
    """現金・株式の積み上げエリアトレースをfigに追加する（FIRE前/後/全期間で共通）。"""
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['cash'] / 10000,
        name=cash_name,
        legendgroup=group_key,
        stackgroup=group_key,
        line=dict(width=0),
        fillcolor=cash_color,
        customdata=customdata,
        hovertemplate=cash_hover,
        showlegend=True,
    ))
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['stocks'] / 10000,
        name=stock_name,
        legendgroup=group_key,
        stackgroup=group_key,
        line=dict(width=0),
        fillcolor=stock_color,
        customdata=customdata,
        hovertemplate=stock_hover,
        showlegend=True,
    ))


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


def _calculate_x_axis_range(
    simulations: Dict[str, pd.DataFrame],
    life_events: List[Dict]
) -> tuple:
    """
    X軸の表示範囲を計算（現在±6ヶ月マージン付き）。

    Args:
        simulations: シナリオ別シミュレーション結果
        life_events: ライフイベントリスト

    Returns:
        (x_min, x_max) のタプル
    """
    current_date = datetime.now()

    # 左端のラベルが見切れないように、少し前から表示開始
    x_min = current_date - relativedelta(months=6)  # 6ヶ月前から表示
    x_max = current_date

    # シミュレーションデータから最大日付を取得
    if len(simulations) > 0:
        first_scenario = list(simulations.values())[0]
        x_max = max(x_max, first_scenario['date'].max())

    # ライフイベントから最大日付を取得
    if len(life_events) > 0:
        last_event_date = life_events[-1]['date']
        x_max = max(x_max, last_event_date)

    # 右端のラベルが見切れないように、少し後まで表示
    x_max = x_max + relativedelta(months=6)  # 6ヶ月後まで表示

    return x_min, x_max


def _add_reference_markers(
    fig: go.Figure,
    current_status: Dict[str, Any],
    fire_target: Dict[str, Any],
    fire_achievement: Dict[str, Any],
    simulations: Dict[str, pd.DataFrame]
) -> None:
    """
    基準線・マーカー（現在位置、FIRE縦線、破綻ライン）を fig に追加する。

    Args:
        fig: Plotly図オブジェクト
        current_status: 現状分析結果
        fire_target: FIRE目標額情報
        fire_achievement: FIRE達成予想情報
        simulations: シナリオ別シミュレーション結果
    """
    # FIRE目標額（targetは後で使用するため計算のみ）
    target = fire_target['recommended_target'] / 10000

    # 現在位置のマーカー
    current_assets = current_status['net_assets'] / 10000
    now = pd.Timestamp.now()
    fig.add_trace(go.Scatter(
        x=[now],
        y=[current_assets],
        name='現在',
        mode='markers+text',
        marker=dict(size=12, color='#0d9488', symbol='circle'),
        text=['現在'],
        textposition='top center',
        textfont=dict(size=11, color='#0d9488', weight='bold'),
        hovertemplate=f'<b>現在</b><br>{current_assets:,.0f}万円<extra></extra>',
        showlegend=False
    ))

    # FIRE達成時期の縦線（細線・直線）
    achievement_date = None
    if fire_achievement and not fire_achievement.get('achieved'):
        achievement_date = fire_achievement['achievement_date']

    if achievement_date:
        y_max = max(
            simulations['standard']['assets'].max() / 10000 if 'standard' in simulations else 0,
            target
        ) * 1.1

        fig.add_trace(go.Scatter(
            x=[achievement_date, achievement_date],
            y=[0, y_max],
            name='FIRE達成時期',
            mode='lines',
            line={'color': '#f59e0b', 'width': 1},
            hovertemplate=f'<b>FIRE達成時期</b><br>{achievement_date.strftime("%Y年%m月")}<extra></extra>',
            showlegend=True
        ))

    # 安全マージン（500万円）- 細線・直線
    if len(simulations) > 0 and achievement_date:
        first_scenario = list(simulations.values())[0]
        x_start = first_scenario['date'].iloc[0]
        df_post = first_scenario[first_scenario['date'] >= achievement_date]
        x_end = df_post['date'].iloc[-1] if len(df_post) > 0 else achievement_date

        fig.add_trace(go.Scatter(
            x=[x_start, x_end],
            y=[500, 500],
            name='安全マージン',
            mode='lines',
            line={'color': '#dc2626', 'width': 1},
            hovertemplate='<b>安全マージン</b><br>¥500万<extra></extra>',
            showlegend=True
        ))


def _add_life_events_timeline(
    fig: go.Figure,
    life_events: List[Dict],
    simulations: Dict[str, pd.DataFrame]
) -> tuple:
    """
    ライフイベントタイムラインを fig に追加し、annotations/shapes を返す。

    Args:
        fig: Plotly図オブジェクト
        life_events: イベントリスト
        simulations: シナリオ別シミュレーション結果

    Returns:
        (annotations, shapes) のタプル
    """
    annotations = []
    shapes = []

    if len(life_events) == 0 or len(simulations) == 0:
        return annotations, shapes

    # Y軸の最小値を計算（タイムライン用のスペース確保）
    first_scenario = list(simulations.values())[0]
    y_max = first_scenario['assets'].max() / 10000
    y_timeline = -y_max * 0.15  # グラフの下部15%の位置

    # タイムライン軸（水平線）を追加（シミュレーション全体の期間）
    timeline_x0 = first_scenario['date'].iloc[0]
    timeline_x1 = first_scenario['date'].iloc[-1]

    # 時系列軸（水平線）
    shapes.append({
        'type': 'line',
        'xref': 'x',
        'yref': 'y',
        'x0': timeline_x0,
        'y0': y_timeline,
        'x1': timeline_x1,
        'y1': y_timeline,
        'line': {
            'color': '#94a3b8',
            'width': 2,
            'dash': 'solid'
        },
        'opacity': 0.6
    })

    # イベントの配置位置を計算（衝突回避アルゴリズム）
    event_positions = _calculate_event_positions(life_events)

    for i, event in enumerate(life_events):
        # イベントの日付と位置
        event_date = event['date']
        y_offset, x_offset_days = event_positions[i]

        # 横方向のオフセットを適用した表示位置
        display_date = event_date + pd.Timedelta(days=x_offset_days)

        # イベントから軸への縦線
        shapes.append({
            'type': 'line',
            'xref': 'x',
            'yref': 'y',
            'x0': event_date,
            'y0': y_timeline,
            'x1': event_date,
            'y1': y_timeline + y_offset,
            'line': {
                'color': event['color'],
                'width': 1.5,
                'dash': 'dot'
            },
            'opacity': 0.5
        })

        # タイムライン上のマーカー
        shapes.append({
            'type': 'circle',
            'xref': 'x',
            'yref': 'y',
            'x0': event_date - pd.Timedelta(days=15),
            'y0': y_timeline - 20,
            'x1': event_date + pd.Timedelta(days=15),
            'y1': y_timeline + 20,
            'fillcolor': event['color'],
            'line': {'color': event['color'], 'width': 2},
            'opacity': 0.9
        })

        # イベントラベル（横方向にもオフセット）
        annotation = {
            'x': display_date,  # 横方向にオフセットした位置
            'y': y_timeline + y_offset,
            'xref': 'x',
            'yref': 'y',
            'text': event['label'],
            'showarrow': True,
            'arrowhead': 2,
            'arrowsize': 1,
            'arrowwidth': 1.5,
            'arrowcolor': event['color'],
            'ax': 0,
            'ay': -30 if y_offset > 0 else 30,  # 上にあるイベントは矢印を上向きに
            'font': {'size': 12, 'color': event['color'], 'weight': 'bold'},
            'bgcolor': 'rgba(255, 255, 255, 0.9)',
            'bordercolor': event['color'],
            'borderwidth': 1,
            'borderpad': 3
        }

        # 左端のイベント（最初の1-2個）は左寄せにしてテキストが右側に表示されるようにする
        if i < 2:
            annotation['xanchor'] = 'left'
        # 右端のイベント（最後の1-2個）は右寄せにしてテキストが左側に表示されるようにする
        elif i >= len(life_events) - 2:
            annotation['xanchor'] = 'right'

        annotations.append(annotation)

    return annotations, shapes


def _calculate_event_positions(life_events: List[Dict]) -> List[tuple]:
    """
    ライフイベントの表示位置を計算（衝突回避アルゴリズム）。

    Args:
        life_events: イベントリスト（日付でソート済み）

    Returns:
        各イベントの (y_offset, x_offset_days) のリスト
    """
    event_positions = []
    min_gap_days = 365  # 1年以内のイベントは近いとみなす

    # 利用可能な垂直位置（上下に複数レベル）
    levels_up = [70, 110, 150]
    levels_down = [-70, -110, -150]

    # 横方向のオフセット（日数）
    x_offsets = [0, -45, 45, -90, 90]  # 中央、左、右、さらに左、さらに右

    for i, event in enumerate(life_events):
        event_date = event['date']

        # 前のイベントとの時間差をチェック
        if i == 0:
            # 最初のイベントは上に配置
            y_pos = levels_up[0]
            x_offset = x_offsets[0]
        else:
            prev_date = life_events[i-1]['date']
            days_diff = (event_date - prev_date).days

            if days_diff < min_gap_days:
                # 近いイベントは前のイベントと逆方向に配置
                prev_y_pos, prev_x_offset = event_positions[-1]
                if prev_y_pos > 0:
                    # 前が上なら下に
                    level_idx = 0
                    if i >= 2:
                        prev_prev_y_pos, _ = event_positions[-2]
                        if prev_prev_y_pos < 0:
                            # 前の前も下なら、より深いレベルを使用
                            level_idx = min(1, len(levels_down) - 1)
                    y_pos = levels_down[level_idx]
                else:
                    # 前が下なら上に
                    level_idx = 0
                    if i >= 2:
                        prev_prev_y_pos, _ = event_positions[-2]
                        if prev_prev_y_pos > 0:
                            # 前の前も上なら、より高いレベルを使用
                            level_idx = min(1, len(levels_up) - 1)
                    y_pos = levels_up[level_idx]

                # 横方向のオフセットも追加（非常に近い場合）
                if days_diff < 180:  # 半年以内
                    # 前回のx_offsetと異なる値を使用
                    x_offset_idx = (x_offsets.index(prev_x_offset) + 1) % len(x_offsets)
                    x_offset = x_offsets[x_offset_idx]
                else:
                    x_offset = x_offsets[0]
            else:
                # 離れているイベントは交互に配置
                if i % 2 == 0:
                    y_pos = levels_up[0]
                else:
                    y_pos = levels_down[0]
                x_offset = x_offsets[0]

        event_positions.append((y_pos, x_offset))

    return event_positions


def extract_life_events(config: Dict[str, Any], fire_achievement: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    ライフイベントを抽出

    Args:
        config: 設定辞書
        fire_achievement: FIRE達成情報

    Returns:
        イベントのリスト
    """
    events = []
    current_date = datetime.now()

    # 子供の進学イベント
    children = config.get('education', {}).get('children', [])
    # 子供ごとに異なる色を割り当て
    child_colors = [
        '#06b6d4',  # 第一子（颯）: シアン
        '#a855f7',  # 第二子（楓）: バイオレット
        '#ec4899',  # 第三子以降: ピンク
        '#f59e0b',  # 第四子以降: オレンジ
    ]

    for i, child in enumerate(children):
        birthdate_str = child.get('birthdate')
        if not birthdate_str:
            continue

        birthdate = datetime.strptime(birthdate_str, '%Y/%m/%d')
        child_name = child.get('name', f'子供{i+1}')  # 名前が設定されていればそれを使用
        child_color = child_colors[i] if i < len(child_colors) else child_colors[0]  # 子供ごとの色

        # 各進学イベント
        events_ages = [
            (3, '幼稚園入園'),
            (6, '小学校入学'),
            (12, '中学入学'),
            (15, '高校入学'),
            (18, '大学入学'),
            (22, '大学卒業'),
        ]

        for age, label in events_ages:
            event_date = birthdate + relativedelta(years=age)
            if event_date > current_date:  # 未来のイベントのみ
                events.append({
                    'date': event_date,
                    'label': f'{child_name} {label}',
                    'category': 'education',
                    'color': child_color  # 子供ごとに色を変える
                })

    # 住宅ローン完済
    mortgage_end_date_str = config.get('mortgage', {}).get('end_date')
    if mortgage_end_date_str:
        mortgage_end_date = datetime.strptime(mortgage_end_date_str, '%Y/%m/%d')
        if mortgage_end_date > current_date:
            events.append({
                'date': mortgage_end_date,
                'label': 'ローン完済',
                'category': 'mortgage',
                'color': '#f59e0b'  # 住宅関連はオレンジで統一
            })

    # 年金受給開始
    pension_people = config.get('pension', {}).get('people', [])
    pension_start_age = config.get('pension', {}).get('start_age', 65)
    for person in pension_people:
        birthdate_str = person.get('birthdate')
        name = person.get('name', '')
        if birthdate_str:
            birthdate = datetime.strptime(birthdate_str, '%Y/%m/%d')
            pension_date = birthdate + relativedelta(years=pension_start_age)
            if pension_date > current_date:
                events.append({
                    'date': pension_date,
                    'label': f'{name} 年金開始',
                    'category': 'pension',
                    'color': '#0891b2'
                })

    # メンテナンス費用（想定寿命までのイベントのみ）
    life_expectancy = config.get('simulation', {}).get('life_expectancy', 90)
    start_age = config.get('simulation', {}).get('start_age', 35)
    max_simulation_year = current_date.year + (life_expectancy - start_age)

    maintenance_items = config.get('house_maintenance', {}).get('items', [])
    for item in maintenance_items:
        first_year = item.get('first_year')
        frequency_years = item.get('frequency_years')
        name = item.get('name', '')

        if first_year and frequency_years:
            # シミュレーション期間内のメンテナンスイベントのみ
            for offset in range(0, 60, frequency_years):  # 最大60年分をチェック
                event_year = first_year + offset
                if event_year > max_simulation_year:
                    break  # 想定寿命を超えたら終了
                event_date = datetime(event_year, 1, 1)
                if event_date > current_date:
                    events.append({
                        'date': event_date,
                        'label': name,
                        'category': 'maintenance',
                        'color': '#f59e0b'  # 住宅関連はオレンジで統一
                    })

    # FIRE達成
    if fire_achievement and not fire_achievement.get('achieved'):
        fire_date = fire_achievement.get('achievement_date')
        if fire_date:
            events.append({
                'date': fire_date,
                'label': 'FIRE達成',
                'category': 'fire',
                'color': '#10b981'
            })

    # 日付でソート
    events.sort(key=lambda x: x['date'])

    return events

def _add_monte_carlo_ranges(
    fig: go.Figure,
    df_post: pd.DataFrame,
    monte_carlo_results: Dict[str, Any],
    achievement_date
) -> None:
    """
    モンテカルロシミュレーションの1σ、2σ範囲をグラフに追加

    Args:
        fig: Plotlyグラフオブジェクト
        df_post: FIRE達成後のデータ
        monte_carlo_results: モンテカルロシミュレーション結果
        achievement_date: FIRE達成日
    """
    import numpy as np
    from dateutil.relativedelta import relativedelta

    # パーセンタイルデータを取得（対数正規分布は非対称なのでパーセンタイルを使用）
    monthly_p50 = monte_carlo_results['monthly_p50']     # 中央値
    monthly_p025 = monte_carlo_results['monthly_p025']   # 2σ下限相当（2.5パーセンタイル）
    monthly_p16 = monte_carlo_results['monthly_p16']     # 1σ下限相当（16パーセンタイル）
    monthly_p84 = monte_carlo_results['monthly_p84']     # 1σ上限相当（84パーセンタイル）
    monthly_p975 = monte_carlo_results['monthly_p975']   # 2σ上限相当（97.5パーセンタイル）

    # FIRE達成後の日付配列を作成
    dates_post = pd.date_range(
        start=achievement_date,
        periods=len(monthly_p50),
        freq='MS'  # Month Start
    )

    # 万円単位に変換
    p50_man = monthly_p50 / 10000
    p025_man = monthly_p025 / 10000
    p16_man = monthly_p16 / 10000
    p84_man = monthly_p84 / 10000
    p975_man = monthly_p975 / 10000

    # 範囲を設定（パーセンタイルを直接使用）
    upper_2sigma = p975_man  # 97.5パーセンタイル
    lower_2sigma = p025_man  # 2.5パーセンタイル
    upper_1sigma = p84_man   # 84パーセンタイル
    lower_1sigma = p16_man   # 16パーセンタイル

    # 2σ範囲（薄いオレンジ）
    fig.add_trace(go.Scatter(
        x=dates_post,
        y=upper_2sigma,
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=dates_post,
        y=lower_2sigma,
        mode='lines',
        fill='tonexty',
        fillcolor='rgba(251, 146, 60, 0.1)',  # オレンジ、10%透明度
        line=dict(width=0),
        name='2σ範囲（95%）',
        hovertemplate='<b>2σ範囲</b><br>%{x|%Y年%m月}<br>%{y:,.0f}万円<extra></extra>'
    ))

    # 1σ範囲（濃いオレンジ）
    fig.add_trace(go.Scatter(
        x=dates_post,
        y=upper_1sigma,
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=dates_post,
        y=lower_1sigma,
        mode='lines',
        fill='tonexty',
        fillcolor='rgba(251, 146, 60, 0.2)',  # オレンジ、20%透明度
        line=dict(width=0),
        name='1σ範囲（68%）',
        hovertemplate='<b>1σ範囲</b><br>%{x|%Y年%m月}<br>%{y:,.0f}万円<extra></extra>'
    ))

    # 中央値線（オレンジの点線）
    fig.add_trace(go.Scatter(
        x=dates_post,
        y=p50_man,
        mode='lines',
        line=dict(color='rgb(251, 146, 60)', width=2, dash='dot'),  # オレンジ、点線
        name='中央値（MC）',
        hovertemplate='<b>中央値</b><br>%{x|%Y年%m月}<br>%{y:,.0f}万円<extra></extra>'
    ))




def create_fire_timeline_chart(
    current_status: Dict[str, Any],
    fire_target: Dict[str, Any],
    fire_achievement: Dict[str, Any],
    simulations: Dict[str, Any],
    config: Dict[str, Any],
    monte_carlo_results: Dict[str, Any] = None
) -> go.Figure:
    """
    FIRE達成までの道のりと達成後の持続性を統合したチャートを作成

    FIRE達成前後で色を変えて視覚的に分かりやすく表示
    - FIRE前（労働期間）: シアン系
    - FIRE後（リタイア期間）: グリーン系
    - モンテカルロ範囲（FIRE後のみ）: 1σ、2σの範囲を半透明で表示

    Args:
        current_status: 現状分析結果
        fire_target: FIRE目標額情報
        fire_achievement: FIRE達成予想情報
        simulations: シナリオ別シミュレーション結果
        config: 設定辞書
        monte_carlo_results: モンテカルロシミュレーション結果（オプション）

    Returns:
        Plotlyグラフオブジェクト
    """
    fig = go.Figure()

    # FIRE達成日を取得
    achievement_date = None
    if fire_achievement and not fire_achievement.get('achieved'):
        achievement_date = fire_achievement['achievement_date']

    # 標準シナリオ
    if 'standard' in simulations:
        df = simulations['standard'].copy()

        if achievement_date:
            # FIRE達成前（労働期間）- シアン系の積み上げエリア
            df_pre = df[df['date'] <= achievement_date].copy()
            if len(df_pre) > 0:
                customdata_pre = df_pre[get_customdata_column_names()].values
                _add_stacked_asset_traces(
                    fig, df_pre, 'pre',
                    '現金（FIRE前）', '株式（FIRE前）',
                    _COLOR_PRE_FIRE_CASH, _COLOR_PRE_FIRE_STOCK,
                    customdata_pre,
                    '<b>FIRE前</b><br><b>%{x|%Y年%m月}</b><br>現金: <b>¥%{y:,.0f}万</b><extra></extra>',
                    '<b>FIRE前</b><br><b>%{x|%Y年%m月}</b><br>株式: <b>¥%{y:,.0f}万</b><extra></extra>',
                )

            # FIRE達成後（リタイア期間）- グリーン系の積み上げエリア
            df_post = df[df['date'] >= achievement_date].copy()  # 90歳まで全期間
            if len(df_post) > 0:
                customdata_post = df_post[get_customdata_column_names()].values
                _add_stacked_asset_traces(
                    fig, df_post, 'post',
                    '現金（FIRE後）', '株式（FIRE後）',
                    _COLOR_POST_FIRE_CASH, _COLOR_POST_FIRE_STOCK,
                    customdata_post,
                    '<b>FIRE後</b><br><b>%{x|%Y年%m月}</b><br>現金: <b>¥%{y:,.0f}万</b><extra></extra>',
                    '<b>FIRE後</b><br><b>%{x|%Y年%m月}</b><br>株式: <b>¥%{y:,.0f}万</b><extra></extra>',
                )

                # モンテカルロの1σ、2σ範囲を追加（FIRE後のみ）
                if monte_carlo_results and 'monthly_p50' in monte_carlo_results:
                    _add_monte_carlo_ranges(
                        fig, df_post, monte_carlo_results, achievement_date
                    )
        else:
            # すでに達成済みの場合は全てグリーン系の積み上げエリア
            df_all = df.head(480).copy()
            customdata_all = df_all[get_customdata_column_names()].values
            _add_stacked_asset_traces(
                fig, df_all, 'all',
                '現金', '株式',
                _COLOR_POST_FIRE_CASH, _COLOR_POST_FIRE_STOCK,
                customdata_all,
                '<b>現金</b><br>%{x|%Y年%m月}<br>¥%{y:,.0f}万円<extra></extra>',
                '<b>株式</b><br>%{x|%Y年%m月}<br>¥%{y:,.0f}万円<extra></extra>',
            )

    # 基準線・マーカー追加（現在位置、FIRE縦線、破綻ライン）
    _add_reference_markers(fig, current_status, fire_target, fire_achievement, simulations)

    # ライフイベントタイムライン追加
    life_events = extract_life_events(config, fire_achievement)
    annotations, shapes = _add_life_events_timeline(fig, life_events, simulations)

    # X軸範囲計算
    x_min, x_max = _calculate_x_axis_range(simulations, life_events)

    # Y軸範囲計算（ベースシミュレーションを基準に）
    y_max = None
    if 'standard' in simulations:
        df = simulations['standard']
        # DataFrameの'assets'は円単位なので、万円に変換
        max_assets_yen = df['assets'].max()
        max_assets_man = max_assets_yen / 10000  # 万円に変換
        y_max = max_assets_man * 1.2

    # レイアウト
    layout = get_common_layout(config, '')
    yaxis_config = {
        'title': '万円',
        'showgrid': True,
        'gridcolor': '#e0f2fe',
        'tickformat': ',.0f',
        'zeroline': False,
        'side': 'right'
    }
    # Y軸の上限を設定（モンテカルロの2σ範囲でベースシミュレーションが隠れないように）
    if y_max is not None:
        yaxis_config['range'] = [0, y_max]

    layout.update({
        'xaxis': {
            'title': '',
            'showgrid': False,
            'zeroline': False,
            'range': [x_min, x_max]  # X軸の範囲を明示的に指定
        },
        'yaxis': yaxis_config,
        'height': 500,  # タイムライン用に高さを増やす
        'showlegend': True,
        'legend': {
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'right',
            'x': 1,
            'bgcolor': 'rgba(255, 255, 255, 0)',
            'borderwidth': 0,
            'font': {'size': 12, 'color': '#475569'}
        },
        'hovermode': 'closest',
        'margin': {'l': 20, 'r': 56, 't': 40, 'b': 80},  # 下部マージンを増やす
        'annotations': annotations,
        'shapes': shapes
    })

    fig.update_layout(layout)

    return fig


def create_monte_carlo_distribution_chart(
    mc_results: Dict[str, Any],
    config: Dict[str, Any]
) -> go.Figure:
    """
    モンテカルロシミュレーション結果の分布グラフ

    Args:
        mc_results: run_monte_carlo_simulation() の結果
        config: 設定辞書

    Returns:
        ヒストグラム + 成功確率表示のFigure
    """
    fig = go.Figure()

    # 最終資産を万円単位に変換
    final_assets = [r['final_assets'] / 10000 for r in mc_results['all_results']]

    # ヒストグラム
    fig.add_trace(go.Histogram(
        x=final_assets,
        nbinsx=50,
        name='最終資産分布',
        marker={'color': 'rgba(34, 197, 94, 0.7)'},
        hovertemplate='最終資産: %{x:.0f}万円<br>頻度: %{y}<extra></extra>'
    ))

    # 成功確率をアノテーション
    success_rate = mc_results['success_rate']
    median_assets = mc_results['median_final_assets'] / 10000
    percentile_10 = mc_results['percentile_10'] / 10000
    percentile_90 = mc_results['percentile_90'] / 10000

    annotations = [
        # 成功確率（メイン）
        dict(
            text=f'<b>FIRE成功確率: {success_rate*100:.1f}%</b>',
            x=0.5, y=0.95,
            xref='paper', yref='paper',
            showarrow=False,
            font={'size': 20, 'color': '#10b981' if success_rate >= 0.9 else '#f59e0b'},
            bgcolor='rgba(255, 255, 255, 0.95)',
            bordercolor='#10b981' if success_rate >= 0.9 else '#f59e0b',
            borderwidth=2,
            borderpad=8
        ),
        # 統計情報
        dict(
            text=f'中央値: {median_assets:,.0f}万円<br>'
                 f'10%ile: {percentile_10:,.0f}万円<br>'
                 f'90%ile: {percentile_90:,.0f}万円',
            x=0.02, y=0.98,
            xref='paper', yref='paper',
            showarrow=False,
            font={'size': 12, 'color': '#475569'},
            bgcolor='rgba(255, 255, 255, 0.9)',
            align='left',
            xanchor='left',
            yanchor='top'
        )
    ]

    layout = get_common_layout(config, 'FIRE成功確率（モンテカルロシミュレーション）')
    layout.update({
        'xaxis': {
            'title': '最終資産（90歳時点・万円）',
            'gridcolor': '#e2e8f0'
        },
        'yaxis': {
            'title': '頻度',
            'gridcolor': '#e2e8f0'
        },
        'height': 450,
        'annotations': annotations,
        'showlegend': False
    })

    fig.update_layout(layout)

    return fig
