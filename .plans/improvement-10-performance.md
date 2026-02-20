# 改善計画10: パフォーマンス最適化

## 目的
シミュレーション実行時間を短縮し、ユーザー体験を向上させる。

---

## 現状分析

### ボトルネック特定

```bash
# プロファイリング実行
python -m cProfile -o profile.stats scripts/generate_dashboard.py

# 結果確認
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

**予想されるボトルネック**:
1. **毎月のFIREチェック**: `can_retire_now()` → `simulate_post_fire_assets()` 呼び出しが重い
2. **3シナリオの逐次実行**: 並列化できる
3. **重複計算**: 教育費・年金などを毎月再計算

---

## 実装計画

### Step 10.1: FIREチェックの最適化

#### 問題点
毎月 `can_retire_now()` を呼び出すと、内部で90歳までのシミュレーションを実行するため計算量が膨大。

#### 解決策1: チェック頻度の削減

```python
# 毎月チェック → 3ヶ月ごとにチェック
if not fire_achieved and month_index % 3 == 0:
    if can_retire_now(...):
        fire_achieved = True
```

#### 解決策2: 簡易FIREチェック

```python
def quick_fire_check(cash: float, stocks: float, annual_expense: float) -> bool:
    """
    簡易FIREチェック（4%ルール）

    総資産 >= 年間支出 × 25 なら FIRE 可能と判定
    """
    total_assets = cash + stocks
    return total_assets >= annual_expense * 25

# メインループ内
if not fire_achieved and quick_fire_check(cash, stocks, annual_expense):
    # 簡易チェックを通過した場合のみ、詳細チェック
    if can_retire_now(...):
        fire_achieved = True
```

#### 解決策3: 結果のキャッシング

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def can_retire_now_cached(
    cash: float,
    stocks: float,
    year_offset: float,
    # ... その他不変なパラメータ
) -> bool:
    """キャッシュ付きFIREチェック"""
    return can_retire_now(cash, stocks, ...)
```

### Step 10.2: 3シナリオの並列実行

```python
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

def simulate_scenario(scenario_name: str, config: Dict) -> Tuple[str, pd.DataFrame]:
    """1つのシナリオをシミュレート（並列実行用）"""
    df = simulate_future_assets(
        current_cash=...,
        current_stocks=...,
        config=config,
        scenario=scenario_name
    )
    return scenario_name, df

def run_all_scenarios_parallel(config: Dict) -> Dict[str, pd.DataFrame]:
    """3シナリオを並列実行"""
    scenarios = ['standard', 'optimistic', 'pessimistic']

    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(simulate_scenario, scenario, config)
            for scenario in scenarios
        ]

        results = {}
        for future in futures:
            scenario_name, df = future.result()
            results[scenario_name] = df

    return results
```

### Step 10.3: 教育費・年金の事前計算

```python
def precompute_education_expenses(
    total_months: int,
    config: Dict
) -> np.ndarray:
    """
    全月分の教育費を事前計算

    Returns:
        月次教育費の配列（長さ: total_months）
    """
    expenses = np.zeros(total_months)
    for month_index in range(total_months):
        year_offset = month_index / 12
        expenses[month_index] = calculate_education_expense(year_offset, config)
    return expenses

# メインループ内
education_expenses = precompute_education_expenses(total_months, config)

for month_index in range(total_months):
    # 事前計算済みの値を使用
    education_expense = education_expenses[month_index]
```

### Step 10.4: NumPyベクトル化

```python
# Before: ループで1ヶ月ずつ処理
for month_index in range(total_months):
    stocks *= (1 + monthly_return_rate)

# After: NumPy配列で一括処理
stocks_array = np.zeros(total_months)
stocks_array[0] = initial_stocks

for month_index in range(1, total_months):
    stocks_array[month_index] = stocks_array[month_index-1] * (1 + monthly_return_rate)
```

### Step 10.5: パフォーマンス計測

```python
import time

def measure_performance(func, *args, **kwargs):
    """実行時間を計測"""
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    print(f"{func.__name__}: {elapsed:.2f}秒")
    return result

# 使用例
simulations = measure_performance(run_all_scenarios_parallel, config)
```

---

## 検証方法

### Before/After の計測

```bash
# 最適化前
time python scripts/generate_dashboard.py
# → 実行時間: 45秒

# 最適化後
time python scripts/generate_dashboard.py
# → 実行時間: 15秒（目標: 3倍高速化）
```

### 正確性の確認

```bash
python scripts/generate_dashboard.py
# → FIRE達成日: 2030-09 で変化なし
```

---

## 実装順序

1. Step 10.1: FIREチェック最適化（最も効果が高い）
2. 検証（実行時間計測）
3. Step 10.2: 並列実行
4. 検証
5. Step 10.3: 事前計算
6. Step 10.4: ベクトル化（可能な箇所のみ）
7. Step 10.5: 最終パフォーマンス計測
8. コミット

---

## 期待される効果

- **実行時間短縮**: 45秒 → 15秒（目標: 3倍高速化）
- **ユーザー体験向上**: ダッシュボード生成が高速化
- **開発効率向上**: デバッグ・検証が速くなる

---

## 注意事項

- 最適化により複雑性が増す場合は見送る
- 正確性を損なう最適化は避ける
- 計測して効果が小さい場合は実装しない

---

## 前提条件

改善計画1-2が完了していると、最適化箇所が明確

---

## 関連ファイル

- `src/simulator.py`
- `scripts/generate_dashboard.py`

---

## 所要時間見積もり

4-6時間（計測・検証含む）
