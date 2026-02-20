# 改善計画1: simulator.py の大規模関数リファクタリング

## 目的
`simulate_future_assets()` (265行)、`simulate_post_fire_assets()` (183行)、`simulate_with_withdrawal()` (122行) を論理的なセクションに分割し、可読性と保守性を向上させる。

---

## 対象関数の分析

### 1. `simulate_future_assets()` (L1251-1515, 265行)

**処理の流れ**:
1. 初期化処理 (L1278-1310): パラメータ検証、初期状態設定
2. シナリオパラメータ取得 (L1312-1317): 年率リターン、収入成長率など
3. 月次ループ本体 (L1319-1490):
   - 年変わり処理
   - 収入計算
   - 支出計算
   - 資産運用
   - FIREチェック（`can_retire_now()`呼び出し）
4. 結果の整形 (L1492-1515): DataFrameへの変換

**抽出する関数**:
- `_initialize_future_simulation()` (初期化処理)
- `_get_scenario_parameters()` (シナリオパラメータ取得)
- `_process_future_monthly_cycle()` (月次ループ本体)
- `_finalize_simulation_results()` (結果整形)

### 2. `simulate_post_fire_assets()` (L924-1106, 183行)

**処理の流れ**:
1. 初期化処理 (L940-1000): パラメータ、初期状態
2. 月次ループ本体 (L1002-1090):
   - 年変わり処理
   - 収入・支出計算
   - 資産運用
   - 破綻チェック
3. 結果返却 (L1092-1106)

**抽出する関数**:
- `_initialize_post_fire_simulation()` (初期化処理)
- `_process_post_fire_monthly_cycle()` (月次ループ本体)
- `_check_bankruptcy()` (破綻チェック)

### 3. `simulate_with_withdrawal()` (L1516-1637, 122行)

**処理の流れ**:
1. 初期化処理 (L1532-1555)
2. 月次ループ (L1557-1625)
3. 結果整形 (L1627-1637)

**抽出する関数**:
- `_initialize_withdrawal_simulation()` (初期化処理)
- `_process_withdrawal_monthly_cycle()` (月次ループ本体)

---

## 実装計画

### Phase 1: `simulate_future_assets()` のリファクタリング

#### Step 1.1: 初期化処理の抽出

```python
def _initialize_future_simulation(
    current_cash: float,
    current_stocks: float,
    current_assets: float,
    config: Dict[str, Any]
) -> Tuple[float, float, float, float, float, float]:
    """
    将来シミュレーションの初期状態を設定

    Returns:
        (cash, stocks, nisa_balance, stocks_cost_basis, nisa_cost_basis, nisa_annual_invested)
    """
```

**対象コード**: L1278-1310 (約33行)

#### Step 1.2: シナリオパラメータ取得の抽出

```python
def _get_scenario_parameters(
    config: Dict[str, Any],
    scenario: str
) -> Dict[str, float]:
    """
    シナリオ別のパラメータを取得

    Returns:
        {
            'annual_return_rate': float,
            'income_growth_rate': float,
            'expense_growth_rate': float,
            'inflation_rate': float
        }
    """
```

**対象コード**: L1312-1317 (約6行)

#### Step 1.3: 月次処理本体の抽出

```python
def _process_future_monthly_cycle(
    month_index: int,
    cash: float,
    stocks: float,
    nisa_balance: float,
    stocks_cost_basis: float,
    nisa_cost_basis: float,
    nisa_annual_invested: float,
    capital_gains_this_year: float,
    prev_year_capital_gains: float,
    config: Dict[str, Any],
    params: Dict[str, float],
    current_date: datetime,
    fire_achieved: bool,
    fire_achievement_month: Optional[int]
) -> Tuple[float, float, float, float, float, float, float, float, bool, Optional[int], Dict[str, Any]]:
    """
    1ヶ月分の処理を実行

    Returns:
        更新後の全状態変数のタプル
    """
```

**対象コード**: L1319-1490の内側ループ本体（約170行）

#### Step 1.4: 結果整形の抽出

```python
def _finalize_simulation_results(
    results: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> pd.DataFrame:
    """
    シミュレーション結果をDataFrameに変換
    """
```

**対象コード**: L1492-1515 (約24行)

#### Step 1.5: メイン関数の整理

```python
def simulate_future_assets(
    current_cash: float = None,
    current_stocks: float = None,
    current_assets: float = None,
    monthly_income: float = 0,
    monthly_expense: float = 0,
    config: Dict[str, Any] = None,
    scenario: str = 'standard'
) -> pd.DataFrame:
    """将来の資産推移をシミュレーション（リファクタリング後: 約50行）"""

    # 1. 初期化
    cash, stocks, nisa_balance, stocks_cost_basis, nisa_cost_basis, nisa_annual_invested = \
        _initialize_future_simulation(current_cash, current_stocks, current_assets, config)

    # 2. パラメータ取得
    params = _get_scenario_parameters(config, scenario)

    # 3. 月次ループ
    results = []
    fire_achieved = False
    fire_achievement_month = None

    for month_index in range(total_months):
        # 月次処理を実行
        cash, stocks, ..., fire_achieved, fire_achievement_month, monthly_result = \
            _process_future_monthly_cycle(
                month_index, cash, stocks, ..., config, params, ...
            )
        results.append(monthly_result)

    # 4. 結果整形
    return _finalize_simulation_results(results, config)
```

**削減見込み**: 265行 → 約50行 (81%削減)

---

### Phase 2: `simulate_post_fire_assets()` のリファクタリング

同様のパターンで3つのヘルパー関数を抽出し、メイン関数を約50行に削減。

**削減見込み**: 183行 → 約50行 (73%削減)

---

### Phase 3: `simulate_with_withdrawal()` のリファクタリング

同様のパターンで2つのヘルパー関数を抽出し、メイン関数を約40行に削減。

**削減見込み**: 122行 → 約40行 (67%削減)

---

## 検証方法

各Phase完了後に以下を確認:

```bash
python scripts/generate_dashboard.py
```

**確認項目**:
- FIRE達成日が 2030-09 で変化しないこと
- dashboard/index.html が正常に生成されること
- グラフ表示が正常であること

---

## 実装順序

1. Phase 1 (simulate_future_assets): Step 1.1 → 1.2 → 1.3 → 1.4 → 1.5
2. 検証・コミット
3. Phase 2 (simulate_post_fire_assets): 同様の手順
4. 検証・コミット
5. Phase 3 (simulate_with_withdrawal): 同様の手順
6. 検証・コミット

---

## 期待される効果

- **可読性**: 各関数が単一責任を持つため理解しやすい
- **保守性**: バグ修正時に影響範囲が明確
- **テスタビリティ**: 小さな関数単位でテストを書ける
- **コード量削減**: 約570行 → 約140行 (75%削減)

---

## 関連ファイル

- `src/simulator.py`

---

## 所要時間見積もり

- Phase 1: 2-3時間
- Phase 2: 1-2時間
- Phase 3: 1時間
- 合計: 4-6時間
