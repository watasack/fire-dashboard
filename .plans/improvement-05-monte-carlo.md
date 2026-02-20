# 改善計画5: モンテカルロシミュレーション

## 目的
確率的シミュレーション（モンテカルロ法）を導入し、FIRE成功確率を計算する。

---

## 背景

現在のシミュレーションは決定論的（リターン率が固定）ですが、実際の市場は変動します。モンテカルロシミュレーションでは:
- 毎月のリターンをランダムに変動させる（正規分布に従う）
- 1000回以上シミュレーションを実行
- 「90歳まで資産が持つ」確率を計算

例: 成功確率85% → 1000回中850回は成功、150回は破綻

---

## 実装計画

### Step 5.1: ランダムリターン生成

```python
import numpy as np

def generate_random_returns(
    annual_return_mean: float,
    annual_return_std: float,
    total_months: int,
    random_seed: Optional[int] = None
) -> np.ndarray:
    """
    月次リターンをランダム生成（正規分布）

    Args:
        annual_return_mean: 年率リターン平均（例: 0.05 = 5%）
        annual_return_std: 年率リターン標準偏差（例: 0.15 = 15%）
        total_months: シミュレーション月数
        random_seed: 乱数シード（再現性のため）

    Returns:
        月次リターン率の配列（長さ: total_months）
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    # 年率 → 月率に変換
    monthly_return_mean = (1 + annual_return_mean) ** (1/12) - 1
    monthly_return_std = annual_return_std / np.sqrt(12)

    # 正規分布からサンプリング
    returns = np.random.normal(
        loc=monthly_return_mean,
        scale=monthly_return_std,
        size=total_months
    )

    return returns
```

### Step 5.2: モンテカルロシミュレーション実行

```python
def run_monte_carlo_simulation(
    current_cash: float,
    current_stocks: float,
    config: Dict[str, Any],
    scenario: str = 'standard',
    iterations: int = 1000
) -> Dict[str, Any]:
    """
    モンテカルロシミュレーションを実行

    Args:
        current_cash: 現在の現金
        current_stocks: 現在の株式
        config: 設定辞書
        scenario: シナリオ名
        iterations: シミュレーション回数

    Returns:
        {
            'success_rate': 成功確率（0-1）,
            'median_final_assets': 最終資産の中央値,
            'percentile_10': 下位10%の最終資産,
            'percentile_90': 上位10%の最終資産,
            'all_results': 全イテレーションの結果リスト
        }
    """
    results = []
    params = config['simulation'][scenario]

    for i in range(iterations):
        # ランダムリターンを生成
        random_returns = generate_random_returns(
            params['annual_return_rate'],
            config['simulation']['monte_carlo']['return_std_dev'],
            600,  # 50年 = 600ヶ月
            random_seed=i  # 再現性のため
        )

        # シミュレーション実行（リターンを外部から注入）
        df = simulate_with_random_returns(
            current_cash, current_stocks, config, random_returns
        )

        # 最終資産を記録
        final_assets = df['assets'].iloc[-1]
        success = final_assets >= _BANKRUPTCY_THRESHOLD

        results.append({
            'final_assets': final_assets,
            'success': success
        })

    # 成功確率を計算
    success_count = sum(1 for r in results if r['success'])
    success_rate = success_count / iterations

    # 統計情報を計算
    final_assets_list = [r['final_assets'] for r in results]
    return {
        'success_rate': success_rate,
        'median_final_assets': np.median(final_assets_list),
        'percentile_10': np.percentile(final_assets_list, 10),
        'percentile_90': np.percentile(final_assets_list, 90),
        'all_results': results
    }
```

### Step 5.3: config.yaml に設定追加

```yaml
simulation:
  # モンテカルロシミュレーション設定
  monte_carlo:
    enabled: true
    iterations: 1000              # シミュレーション回数
    return_std_dev: 0.15          # 年率リターンの標準偏差（15%）
    show_distribution: true       # 結果分布を表示
```

### Step 5.4: 成功確率グラフの作成

```python
def create_monte_carlo_distribution_chart(
    mc_results: Dict[str, Any],
    config: Dict[str, Any]
) -> go.Figure:
    """
    モンテカルロシミュレーション結果の分布グラフ

    Args:
        mc_results: run_monte_carlo_simulation() の結果

    Returns:
        ヒストグラム + 成功確率表示
    """
    fig = go.Figure()

    final_assets = [r['final_assets'] / 10000 for r in mc_results['all_results']]

    # ヒストグラム
    fig.add_trace(go.Histogram(
        x=final_assets,
        nbinsx=50,
        name='最終資産分布',
        marker={'color': 'rgba(34, 197, 94, 0.7)'}
    ))

    # 成功確率をアノテーション
    success_rate = mc_results['success_rate']
    fig.add_annotation(
        text=f'<b>FIRE成功確率: {success_rate*100:.1f}%</b>',
        x=0.5, y=0.95,
        xref='paper', yref='paper',
        showarrow=False,
        font={'size': 18, 'color': '#10b981'},
        bgcolor='rgba(255, 255, 255, 0.9)'
    )

    layout = get_common_layout(config, 'FIRE成功確率（モンテカルロ）')
    layout.update({
        'xaxis': {'title': '最終資産（万円）'},
        'yaxis': {'title': '頻度'},
        'height': 400
    })

    fig.update_layout(layout)
    return fig
```

---

## 検証方法

```bash
python scripts/generate_dashboard.py
```

- 成功確率が表示されること（例: 85%）
- 分布グラフが正規分布に近い形になること
- イテレーション数を増やすと成功確率が安定すること

---

## 実装順序

1. Step 5.1: ランダムリターン生成
2. Step 5.2: モンテカルロシミュレーション実行
3. Step 5.3: config.yaml 設定
4. Step 5.4: グラフ作成
5. ダッシュボードへの統合
6. 検証・コミット

---

## 期待される効果

- **リスクの定量化**: 成功確率で意思決定できる
- **安全マージンの設定**: 成功確率90%以上を目指すなど
- **市場変動の影響を評価**: ボラティリティが高いとどうなるか

---

## 前提条件

改善計画1（simulator.py リファクタリング）が完了していること

---

## 関連ファイル

- `src/simulator.py`
- `src/visualizer.py`
- `config.yaml`

---

## 所要時間見積もり

5-8時間（計算時間の最適化含む）
