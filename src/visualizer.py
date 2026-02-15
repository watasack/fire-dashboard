"""
可視化モジュール
Plotlyでインタラクティブグラフを生成
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
from dateutil.relativedelta import relativedelta


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


def create_fire_timeline_chart(
    current_status: Dict[str, Any],
    fire_target: Dict[str, Any],
    fire_achievement: Dict[str, Any],
    simulations: Dict[str, pd.DataFrame],
    config: Dict[str, Any]
) -> go.Figure:
    """
    FIRE達成までの道のりと達成後の持続性を統合したチャートを作成

    FIRE達成前後で色を変えて視覚的に分かりやすく表示
    - FIRE前（労働期間）: シアン系
    - FIRE後（リタイア期間）: グリーン系

    Args:
        current_status: 現状分析結果
        fire_target: FIRE目標額情報
        fire_achievement: FIRE達成予想情報
        simulations: シナリオ別シミュレーション結果
        config: 設定辞書

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
            # FIRE達成前（労働期間）- シアン
            df_pre = df[df['date'] <= achievement_date].copy()
            if len(df_pre) > 0:
                # クリックデータ用にカスタムデータを準備
                customdata_pre = df_pre[['labor_income', 'pension_income', 'base_expense', 'education_expense', 'mortgage_payment', 'maintenance_cost', 'workation_cost', 'investment_return']].values
                fig.add_trace(go.Scatter(
                    x=df_pre['date'],
                    y=df_pre['assets'] / 10000,
                    name='FIRE前',
                    legendgroup='資産',
                    line=dict(color='#06b6d4', width=2.5, shape='spline'),
                    fill='tozeroy',
                    fillcolor='rgba(6, 182, 212, 0.15)',
                    customdata=customdata_pre,
                    hovertemplate='<b>FIRE前</b><br><b>%{x|%Y年%m月}</b><br>資産: <b>¥%{y:,.0f}万</b><extra></extra>',
                    showlegend=True
                ))

            # FIRE達成後（リタイア期間）- グリーン
            df_post = df[df['date'] >= achievement_date].copy()  # 90歳まで全期間
            if len(df_post) > 0:
                # クリックデータ用にカスタムデータを準備
                customdata_post = df_post[['labor_income', 'pension_income', 'base_expense', 'education_expense', 'mortgage_payment', 'maintenance_cost', 'workation_cost', 'investment_return']].values
                fig.add_trace(go.Scatter(
                    x=df_post['date'],
                    y=df_post['assets'] / 10000,
                    name='FIRE後',
                    legendgroup='資産',
                    line=dict(color='#10b981', width=2.5, shape='spline'),
                    fill='tozeroy',
                    fillcolor='rgba(16, 185, 129, 0.15)',
                    customdata=customdata_post,
                    hovertemplate='<b>FIRE後</b><br><b>%{x|%Y年%m月}</b><br>資産: <b>¥%{y:,.0f}万</b><extra></extra>',
                    showlegend=True
                ))
        else:
            # すでに達成済みの場合は全てグリーン
            df_all = df.head(480).copy()
            customdata_all = df_all[['labor_income', 'pension_income', 'base_expense', 'education_expense', 'mortgage_payment', 'maintenance_cost', 'workation_cost', 'investment_return']].values
            fig.add_trace(go.Scatter(
                x=df_all['date'],
                y=df_all['assets'] / 10000,
                name='資産推移',
                line=dict(color='#10b981', width=2.5, shape='spline'),
                fill='tozeroy',
                fillcolor='rgba(16, 185, 129, 0.15)',
                customdata=customdata_all,
                hovertemplate='<b>資産推移</b><br>%{x|%Y年%m月}<br>%{y:,.0f}万円<extra></extra>'
            ))


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

    # 破綻ライン（500万円）- 細線・直線
    if len(simulations) > 0 and achievement_date:
        first_scenario = list(simulations.values())[0]
        x_start = first_scenario['date'].iloc[0]
        df_post = first_scenario[first_scenario['date'] >= achievement_date]
        x_end = df_post['date'].iloc[-1] if len(df_post) > 0 else achievement_date

        fig.add_trace(go.Scatter(
            x=[x_start, x_end],
            y=[500, 500],
            name='破綻ライン',
            mode='lines',
            line={'color': '#dc2626', 'width': 1},
            hovertemplate='<b>破綻ライン</b><br>¥500万<extra></extra>',
            showlegend=True
        ))

    # ライフイベントタイムラインを追加
    life_events = extract_life_events(config, fire_achievement)

    # イベントのアノテーションを追加
    annotations = []
    shapes = []

    if len(life_events) > 0 and len(simulations) > 0:
        # Y軸の最小値を計算（タイムライン用のスペース確保）
        first_scenario = list(simulations.values())[0]
        y_max = first_scenario['assets'].max() / 10000
        y_timeline = -y_max * 0.15  # グラフの下部15%の位置

        # タイムライン軸（水平線）を追加（シミュレーション全体の期間）
        if len(simulations) > 0:
            first_scenario = list(simulations.values())[0]
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

        # イベントの配置位置を計算（重ならないように、縦横にオフセット）
        event_positions = []  # (y_offset, x_offset_days) のタプルのリスト
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
                        # 連続する場合は異なるレベルを使用
                        level_idx = 0
                        # 前の前もチェック
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

    # X軸の範囲を計算（全体を統一）
    current_date = datetime.now()

    # 左端のラベルが見切れないように、少し前から表示開始
    from dateutil.relativedelta import relativedelta
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

    # レイアウト
    layout = get_common_layout(config, '')
    layout.update({
        'xaxis': {
            'title': '',
            'showgrid': False,
            'zeroline': False,
            'range': [x_min, x_max]  # X軸の範囲を明示的に指定
        },
        'yaxis': {
            'title': '万円',
            'showgrid': True,
            'gridcolor': '#e0f2fe',
            'tickformat': ',.0f',
            'zeroline': False,
            'side': 'right'
        },
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
