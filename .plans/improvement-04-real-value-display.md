# 改善計画4: インフレ調整後の実質価値表示

## 目的
インフレを考慮した実質価値（購買力ベース）の表示を追加し、より正確な資産価値の把握を可能にする。

---

## 背景

現在のダッシュボードは**名目価値**（その時点での円貨ベースの金額）のみを表示しています。しかし、インフレ率が年2%の場合、30年後の1億円は現在の購買力では約5,500万円に相当します。

実質価値を表示することで:
- 「実際にどれだけのモノ・サービスが買えるか」が分かる
- インフレリスクを可視化できる
- より現実的な資産計画が立てられる

---

## 実装計画

### Step 4.1: 実質価値計算ロジックの追加

#### 実質価値の計算式

```python
実質価値 = 名目価値 ÷ (1 + インフレ率) ^ 経過年数
```

例: 2054年の1億円を2025年基準の実質価値に変換
```python
経過年数 = 2054 - 2025 = 29年
インフレ率 = 2% = 0.02
実質価値 = 100,000,000 ÷ (1.02 ^ 29) = 100,000,000 ÷ 1.756 = 56,946,909円
```

#### 実装

```python
# src/simulator.py に追加

def calculate_real_value(
    nominal_value: float,
    base_year: int,
    current_year: int,
    inflation_rate: float
) -> float:
    """
    名目価値を実質価値に変換

    Args:
        nominal_value: 名目価値（その時点での円貨金額）
        base_year: 基準年（この年の価値で表示）
        current_year: 対象年
        inflation_rate: 年率インフレ率（例: 0.02 = 2%）

    Returns:
        実質価値（base_year時点の購買力換算）
    """
    years_elapsed = current_year - base_year
    deflator = (1 + inflation_rate) ** years_elapsed
    return nominal_value / deflator


def add_real_value_columns(
    df: pd.DataFrame,
    base_year: int,
    inflation_rate: float
) -> pd.DataFrame:
    """
    シミュレーション結果に実質価値カラムを追加

    Args:
        df: シミュレーション結果（列: date, cash, stocks, assets, ...）
        base_year: 基準年
        inflation_rate: 年率インフレ率

    Returns:
        実質価値カラムを追加したDataFrame
        （列: ..., real_cash, real_stocks, real_assets）
    """
    df = df.copy()

    # 年を抽出
    df['year'] = df['date'].dt.year

    # 実質価値を計算
    df['real_cash'] = df.apply(
        lambda row: calculate_real_value(
            row['cash'], base_year, row['year'], inflation_rate
        ),
        axis=1
    )
    df['real_stocks'] = df.apply(
        lambda row: calculate_real_value(
            row['stocks'], base_year, row['year'], inflation_rate
        ),
        axis=1
    )
    df['real_assets'] = df['real_cash'] + df['real_stocks']

    return df
```

### Step 4.2: config.yaml に設定追加

```yaml
# 可視化設定
visualization:
  font_family: "'Segoe UI', -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Meiryo', sans-serif"

  # 実質価値表示設定
  show_real_value: true      # インフレ調整後の実質価値を表示
  real_value_base_year: 2025 # 基準年（この年の価値で表示）
```

### Step 4.3: シミュレーション結果に実質価値を追加

```python
# src/simulator.py の simulate_future_assets() 内

def simulate_future_assets(...) -> pd.DataFrame:
    """将来の資産推移をシミュレーション"""

    # ... 既存のシミュレーション処理 ...

    df = pd.DataFrame(results)

    # 実質価値カラムを追加
    show_real_value = config.get('visualization', {}).get('show_real_value', False)
    if show_real_value:
        base_year = config.get('visualization', {}).get('real_value_base_year', 2025)
        inflation_rate = params['inflation_rate']
        df = add_real_value_columns(df, base_year, inflation_rate)

    return df
```

### Step 4.4: 実質価値グラフの追加（visualizer.py）

#### 新しいグラフ関数を作成

```python
# src/visualizer.py に追加

def create_real_value_comparison_chart(
    simulations: Dict[str, pd.DataFrame],
    config: Dict[str, Any]
) -> go.Figure:
    """
    名目価値 vs 実質価値の比較チャート

    Args:
        simulations: シナリオ別シミュレーション結果
        config: 設定辞書

    Returns:
        Plotlyグラフオブジェクト
    """
    fig = go.Figure()

    if 'standard' not in simulations:
        return fig

    df = simulations['standard'].copy()

    # 名目価値（積み上げエリア）
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['cash'] / 10000,
        name='現金（名目）',
        mode='lines',
        line={'width': 0},
        stackgroup='nominal',
        fillcolor='rgba(6, 182, 212, 0.3)',  # シアン（薄め）
        hovertemplate='<b>名目</b><br>%{x|%Y年%m月}<br>現金: ¥%{y:,.0f}万<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['stocks'] / 10000,
        name='株式（名目）',
        mode='lines',
        line={'width': 0},
        stackgroup='nominal',
        fillcolor='rgba(14, 165, 233, 0.3)',  # ブルー（薄め）
        hovertemplate='<b>名目</b><br>%{x|%Y年%m月}<br>株式: ¥%{y:,.0f}万<extra></extra>'
    ))

    # 実質価値（積み上げエリア）
    if 'real_cash' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['real_cash'] / 10000,
            name='現金（実質）',
            mode='lines',
            line={'width': 0},
            stackgroup='real',
            fillcolor='rgba(34, 197, 94, 0.5)',  # グリーン
            hovertemplate='<b>実質</b><br>%{x|%Y年%m月}<br>現金: ¥%{y:,.0f}万<extra></extra>'
        ))

        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['real_stocks'] / 10000,
            name='株式（実質）',
            mode='lines',
            line={'width': 0},
            stackgroup='real',
            fillcolor='rgba(22, 163, 74, 0.5)',  # ダークグリーン
            hovertemplate='<b>実質</b><br>%{x|%Y年%m月}<br>株式: ¥%{y:,.0f}万<extra></extra>'
        ))

    # レイアウト
    base_year = config.get('visualization', {}).get('real_value_base_year', 2025)
    layout = get_common_layout(config, f'名目価値 vs 実質価値（{base_year}年基準）')
    layout.update({
        'yaxis': {'title': '万円', 'tickformat': ',.0f'},
        'hovermode': 'x unified',
        'showlegend': True,
        'height': 400
    })

    fig.update_layout(layout)
    return fig
```

### Step 4.5: ダッシュボードに実質価値グラフを追加

```python
# scripts/generate_dashboard.py の create_dashboard() 内

def create_dashboard(...):
    """ダッシュボードHTML生成"""

    # ... 既存のグラフ生成 ...

    # 実質価値グラフを追加
    show_real_value = config.get('visualization', {}).get('show_real_value', False)
    if show_real_value:
        real_value_chart = create_real_value_comparison_chart(simulations, config)
        sections.append({
            'title': f'📊 名目価値 vs 実質価値（購買力ベース）',
            'chart': real_value_chart,
            'description': (
                f'インフレを考慮した実質価値（{base_year}年基準の購買力）を表示しています。'
                '名目価値と実質価値の差がインフレによる購買力の低下を表します。'
            )
        })
```

### Step 4.6: FIRE達成額を実質価値で表示

```python
# src/html_generator.py に追加

def format_real_value_info(
    fire_achievement: Dict[str, Any],
    config: Dict[str, Any]
) -> str:
    """
    FIRE達成額の実質価値情報をHTML化

    Returns:
        HTML文字列
    """
    if not fire_achievement or fire_achievement.get('achieved'):
        return ''

    achievement_date = fire_achievement['achievement_date']
    nominal_assets = fire_achievement['assets_at_achievement']

    # 実質価値を計算
    base_year = config.get('visualization', {}).get('real_value_base_year', 2025)
    inflation_rate = config['simulation']['standard']['inflation_rate']
    achievement_year = achievement_date.year

    real_assets = calculate_real_value(
        nominal_assets, base_year, achievement_year, inflation_rate
    )

    html = f"""
    <div class="real-value-info">
        <p>FIRE達成時の資産</p>
        <ul>
            <li>名目: <strong>¥{nominal_assets:,.0f}</strong></li>
            <li>実質（{base_year}年基準）: <strong>¥{real_assets:,.0f}</strong></li>
            <li>差額: ¥{nominal_assets - real_assets:,.0f}
                <span class="info-tooltip">
                    (インフレによる購買力低下)
                </span>
            </li>
        </ul>
    </div>
    """
    return html
```

---

## 検証方法

### 1. 実質価値の計算確認

```python
# テストケース
assert calculate_real_value(100_000_000, 2025, 2054, 0.02) == 56_946_909  # ±1%の誤差許容
```

### 2. グラフ表示確認

```bash
python scripts/generate_dashboard.py
```

- 「名目価値 vs 実質価値」グラフが追加されていること
- 時間が経つにつれて名目価値と実質価値の差が開くこと
- FIRE達成時の実質価値が表示されていること

### 3. 設定の切り替え確認

```yaml
# config.yaml
show_real_value: false  # 無効化
```

→ グラフが表示されないこと

---

## 実装順序

1. Step 4.1: 実質価値計算ロジック追加
2. Step 4.2: config.yaml 設定追加
3. Step 4.3: シミュレーション結果に実質価値追加
4. 検証（データが正しく計算されているか確認）
5. Step 4.4: 実質価値グラフ作成
6. Step 4.5: ダッシュボードに追加
7. Step 4.6: FIRE達成額の実質価値表示
8. 検証・コミット

---

## 期待される効果

- **インフレリスクの可視化**: 購買力ベースで資産価値を把握
- **より現実的な計画**: 「実際に買えるもの」で考えられる
- **教育的効果**: インフレの影響を実感できる
- **意思決定の改善**: 実質ベースでFIRE可否を判断できる

---

## 前提条件

なし（独立して実施可能）

---

## 関連ファイル

- `src/simulator.py` (計算ロジック追加)
- `src/visualizer.py` (グラフ追加)
- `src/html_generator.py` (HTML生成)
- `scripts/generate_dashboard.py` (統合)
- `config.yaml` (設定追加)

---

## 所要時間見積もり

- Step 4.1-4.3: 1-2時間
- Step 4.4-4.6: 2-3時間
- 合計: 3-5時間
