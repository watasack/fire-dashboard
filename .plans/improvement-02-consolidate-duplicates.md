# 改善計画2: 重複コードの統合

## 目的
`simulate_future_assets()`, `simulate_post_fire_assets()`, `simulate_with_withdrawal()` の3関数に存在する類似の月次ループロジックを共通化し、DRY原則を適用する。

---

## 現状分析

### 重複している処理

3つのシミュレーション関数で以下の処理が重複:

1. **年変わり処理** (年が変わったらNISA枠リセット)
2. **収入計算** (`_calculate_monthly_income()` 呼び出し)
3. **支出計算** (`_calculate_monthly_expenses()` 呼び出し)
4. **現金管理** (収入加算、支出引出、不足時の株式売却)
5. **株式リターン計算** (月次リターンの適用)
6. **自動投資** (余剰現金の投資)
7. **結果記録** (月次データの保存)

### 違いがある処理

- `simulate_future_assets()`: **FIREチェック**を実行
- `simulate_post_fire_assets()`: **破綻チェック**を実行、社会保険料計算
- `simulate_with_withdrawal()`: **定額引出**処理

---

## 設計方針

### アプローチ1: コールバック方式（推奨）

共通の月次シミュレーションエンジンを作成し、関数固有の処理をコールバックで注入する。

```python
class SimulationCallbacks:
    """シミュレーション固有の処理を定義するコールバック"""

    def on_month_start(self, state: SimulationState) -> None:
        """月初処理（オプション）"""
        pass

    def on_month_end(self, state: SimulationState) -> Optional[Dict]:
        """月末処理（オプション）、返り値があれば記録に追加"""
        pass

    def should_terminate(self, state: SimulationState) -> bool:
        """シミュレーション終了判定"""
        return False
```

### アプローチ2: 継承方式

基底クラスで共通処理を定義し、派生クラスで固有処理をオーバーライド。

---

## 実装計画

### Step 2.1: SimulationState クラスの定義

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class SimulationState:
    """シミュレーションの状態を保持するクラス"""
    # 時間
    month_index: int
    current_date: datetime
    year_offset: float

    # 資産
    cash: float
    stocks: float
    nisa_balance: float
    stocks_cost_basis: float
    nisa_cost_basis: float

    # NISA
    nisa_annual_invested: float

    # 譲渡益
    capital_gains_this_year: float
    prev_year_capital_gains: float

    # FIRE関連
    fire_achieved: bool = False
    fire_achievement_month: Optional[int] = None

    # その他
    config: dict = None
    params: dict = None  # シナリオパラメータ
```

### Step 2.2: 共通月次処理エンジンの実装

```python
def _run_monthly_simulation(
    initial_state: SimulationState,
    total_months: int,
    callbacks: Optional['SimulationCallbacks'] = None
) -> List[Dict[str, Any]]:
    """
    共通の月次シミュレーションエンジン

    Args:
        initial_state: 初期状態
        total_months: シミュレーション月数
        callbacks: シミュレーション固有の処理

    Returns:
        月次結果のリスト
    """
    state = initial_state
    results = []

    for month_index in range(total_months):
        # 月初コールバック
        if callbacks and callbacks.on_month_start:
            callbacks.on_month_start(state)

        # 共通処理
        state = _process_common_monthly_cycle(state)

        # 月末コールバック
        extra_data = {}
        if callbacks and callbacks.on_month_end:
            extra_data = callbacks.on_month_end(state) or {}

        # 結果記録
        monthly_result = _build_monthly_result(state, extra_data)
        results.append(monthly_result)

        # 終了判定
        if callbacks and callbacks.should_terminate(state):
            break

    return results
```

### Step 2.3: 共通月次処理の実装

```python
def _process_common_monthly_cycle(state: SimulationState) -> SimulationState:
    """
    全シミュレーションで共通の月次処理

    Returns:
        更新後の状態
    """
    # 年変わり処理
    state = _advance_year(state)

    # 収入計算
    income = _calculate_monthly_income(
        state.year_offset,
        state.current_date,
        state.fire_achieved,
        state.config
    )

    # 支出計算
    expense = _calculate_monthly_expenses(
        state.year_offset,
        state.current_date,
        state.fire_achieved,
        state.prev_year_capital_gains,
        state.config,
        state.params
    )

    # 収入を現金に加算
    state.cash += income

    # 支出を現金から引出（不足時は株式売却）
    if state.cash >= expense:
        state.cash -= expense
    else:
        shortage = expense - state.cash
        state.cash = 0
        state = _sell_stocks_to_cover_shortage(state, shortage)

    # 株式リターンを適用
    monthly_return_rate = _get_monthly_return_rate(state.params['annual_return_rate'])
    state.stocks *= (1 + monthly_return_rate)
    state.nisa_balance *= (1 + monthly_return_rate)

    return state
```

### Step 2.4: 各シミュレーション関数のコールバック定義

#### `simulate_future_assets()` のコールバック

```python
class FutureSimulationCallbacks(SimulationCallbacks):
    """将来シミュレーション用のコールバック"""

    def on_month_end(self, state: SimulationState) -> Dict:
        # FIREチェック
        if not state.fire_achieved and state.month_index > 0:
            if can_retire_now(state.cash, state.stocks, ...):
                state.fire_achieved = True
                state.fire_achievement_month = state.month_index
                print(f"FIRE達成! at month {state.month_index}")

        return {'fire_achieved': state.fire_achieved}

    def on_month_start(self, state: SimulationState) -> None:
        # FIRE前の自動投資
        if not state.fire_achieved:
            state = _auto_invest_surplus(state)
```

#### `simulate_post_fire_assets()` のコールバック

```python
class PostFireSimulationCallbacks(SimulationCallbacks):
    """FIRE後シミュレーション用のコールバック"""

    def should_terminate(self, state: SimulationState) -> bool:
        # 破綻チェック
        total_assets = state.cash + state.stocks
        if total_assets < _BANKRUPTCY_THRESHOLD:
            return True  # シミュレーション終了
        return False
```

#### `simulate_with_withdrawal()` のコールバック

```python
class WithdrawalSimulationCallbacks(SimulationCallbacks):
    """定額引出シミュレーション用のコールバック"""

    def __init__(self, monthly_withdrawal: float):
        self.monthly_withdrawal = monthly_withdrawal

    def on_month_start(self, state: SimulationState) -> None:
        # 定額引出
        if state.cash >= self.monthly_withdrawal:
            state.cash -= self.monthly_withdrawal
        else:
            shortage = self.monthly_withdrawal - state.cash
            state.cash = 0
            state = _sell_stocks_to_cover_shortage(state, shortage)
```

### Step 2.5: 各シミュレーション関数のリファクタリング

```python
def simulate_future_assets(...) -> pd.DataFrame:
    """将来シミュレーション（リファクタリング後: 約30行）"""

    # 初期状態作成
    state = SimulationState(
        month_index=0,
        current_date=start_date,
        cash=current_cash,
        stocks=current_stocks,
        ...
        config=config,
        params=_get_scenario_parameters(config, scenario)
    )

    # コールバック作成
    callbacks = FutureSimulationCallbacks()

    # シミュレーション実行
    results = _run_monthly_simulation(state, total_months, callbacks)

    # DataFrame化
    return pd.DataFrame(results)
```

---

## 検証方法

```bash
python scripts/generate_dashboard.py
```

**確認項目**:
- FIRE達成日が 2030-09 で変化しないこと
- 全てのグラフが正常に表示されること
- 破綻判定が正しく動作すること

---

## 実装順序

1. Step 2.1: SimulationState クラス定義
2. Step 2.2: 共通月次処理エンジン実装
3. Step 2.3: 共通月次処理実装
4. 検証（既存の関数を変更せず、新しい関数のみテスト）
5. Step 2.4: コールバック定義
6. Step 2.5: 既存関数のリファクタリング
7. 検証・コミット

---

## 期待される効果

- **重複コード削減**: 月次処理ロジックが1箇所に集約
- **バグ修正の効率化**: 共通ロジックのバグは1箇所を修正するだけで全体に反映
- **新しいシミュレーションの追加が容易**: コールバッククラスを作成するだけ
- **コード量削減**: 約200行削減見込み

---

## 前提条件

**改善計画1（simulator.py のリファクタリング）が完了していること**

---

## 関連ファイル

- `src/simulator.py`

---

## 所要時間見積もり

- Step 2.1-2.3: 2-3時間
- Step 2.4-2.5: 2-3時間
- 合計: 4-6時間
