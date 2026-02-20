# 改善計画3: 型ヒントの完全化

## 目的
全ての関数に型ヒントを追加し、IDE補完の向上とバグの早期発見を実現する。

---

## 現状分析

### 型ヒント未完全な関数の洗い出し

```bash
# 型ヒントが不完全な関数を検出
grep -n "def " src/*.py | grep -v " -> " | wc -l
```

主な未完全箇所:
- 一部の内部ヘルパー関数
- 古いコードで型ヒントが省略されている関数
- 複雑な型（Dict, List, Tuple, Optional）が適切に記述されていない箇所

---

## 実装計画

### Step 3.1: 型エイリアスの定義

複雑な型を読みやすくするため、共通の型エイリアスを定義。

```python
# src/types.py (新規作成)
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import pandas as pd

# 設定関連
ConfigDict = Dict[str, Any]
ScenarioParams = Dict[str, float]

# シミュレーション結果
MonthlyResult = Dict[str, Union[float, datetime, bool]]
SimulationResults = pd.DataFrame

# 資産状態
AssetState = Tuple[float, float, float, float, float]  # (cash, stocks, nisa, cost_basis, nisa_cost_basis)

# FIRE関連
FIREStatus = Dict[str, Union[bool, Optional[datetime], float]]
```

### Step 3.2: simulator.py の型ヒント追加

#### 既存関数の型ヒント強化

```python
from src.types import ConfigDict, ScenarioParams, MonthlyResult, SimulationResults

def _get_monthly_return_rate(annual_return_rate: float) -> float:
    """OK - 既に完全"""

def _get_age_at_offset(birthdate_str: str, year_offset: float) -> float:
    """OK - 既に完全"""

def calculate_education_expense(
    year_offset: float,
    config: ConfigDict  # Dict[str, Any] → ConfigDict
) -> float:
    """型エイリアスを適用"""

def calculate_pension_income(
    year_offset: float,
    fire_achieved: bool,
    config: ConfigDict
) -> Tuple[float, float, float]:  # 戻り値の型を明示
    """
    年金収入を計算

    Returns:
        (monthly_pension_income, shuhei_pension, sakura_pension)
    """
```

#### 新しいヘルパー関数の型ヒント

```python
def _advance_year(
    state: 'SimulationState',  # 前方参照
    capital_gains_this_year: float,
    nisa_annual_invested: float
) -> Tuple[float, float]:
    """
    年変わり処理

    Returns:
        (prev_year_capital_gains, reset_nisa_annual_invested)
    """
```

#### 大規模関数の型ヒント

```python
def simulate_future_assets(
    current_cash: Optional[float] = None,
    current_stocks: Optional[float] = None,
    current_assets: Optional[float] = None,
    monthly_income: float = 0,
    monthly_expense: float = 0,
    config: Optional[ConfigDict] = None,
    scenario: str = 'standard'
) -> SimulationResults:
    """
    将来の資産推移をシミュレーション

    Args:
        current_cash: 現在の現金残高（優先）
        current_stocks: 現在の株式残高（優先）
        current_assets: 現在の純資産（後方互換性、未使用推奨）
        monthly_income: 月次収入
        monthly_expense: 月次支出
        config: 設定辞書
        scenario: シナリオ名 ('standard' | 'optimistic' | 'pessimistic')

    Returns:
        シミュレーション結果のDataFrame（列: date, cash, stocks, assets, ...）

    Raises:
        ValueError: config が None の場合
    """
```

### Step 3.3: visualizer.py の型ヒント追加

```python
from typing import Dict, List, Any, Tuple
import plotly.graph_objects as go
import pandas as pd

def create_fire_timeline_chart(
    current_status: Dict[str, Any],
    fire_target: Dict[str, Any],
    fire_achievement: Dict[str, Any],
    simulations: Dict[str, pd.DataFrame],
    config: Dict[str, Any]
) -> go.Figure:
    """OK - 既に完全"""

def _add_stacked_asset_traces(
    fig: go.Figure,  # 既に追加済み
    df: pd.DataFrame,
    period: str,
    cash_name: str,
    stock_name: str,
    cash_color: str,
    stock_color: str,
    customdata: Any,
    cash_hovertemplate: str,
    stock_hovertemplate: str
) -> None:
    """OK - 既に完全"""

def extract_life_events(
    config: Dict[str, Any],
    fire_achievement: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """OK - 既に完全"""
```

### Step 3.4: analyzer.py, data_loader.py, config.py の型ヒント追加

各ファイルの全関数に型ヒントを追加。

```python
# src/analyzer.py
def analyze_current_status(
    df: pd.DataFrame,
    config: ConfigDict
) -> Dict[str, Union[float, int, str]]:
    """現状分析"""

# src/data_loader.py
def load_asset_data(
    file_path: str,
    encoding: str = 'cp932'
) -> pd.DataFrame:
    """資産データ読み込み"""

# src/config.py
def load_config(
    config_path: str = 'config.yaml'
) -> ConfigDict:
    """設定ファイル読み込み"""
```

### Step 3.5: mypy による型チェック設定

```toml
# pyproject.toml (新規作成)
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
strict_equality = true

[[tool.mypy.overrides]]
module = [
    "plotly.*",
    "pandas.*",
    "yaml.*"
]
ignore_missing_imports = true
```

### Step 3.6: 型チェック実行

```bash
# mypy のインストール
pip install mypy

# 型チェック実行
mypy src/ scripts/

# エラーがあれば修正
```

---

## 検証方法

### 1. 型チェック

```bash
mypy src/ scripts/
# → No errors found
```

### 2. IDE補完の確認

VSCode等で関数を呼び出す際、引数の型情報がポップアップ表示されることを確認。

### 3. 動作確認

```bash
python scripts/generate_dashboard.py
# → FIRE達成日: 2030-09 で変化なし
```

---

## 実装順序

1. Step 3.1: 型エイリアス定義 (`src/types.py` 作成)
2. Step 3.2: simulator.py の型ヒント追加
3. Step 3.3: visualizer.py の型ヒント追加
4. Step 3.4: その他ファイルの型ヒント追加
5. Step 3.5: mypy 設定
6. Step 3.6: 型チェック実行・修正
7. 検証・コミット

---

## 期待される効果

- **IDE補完の向上**: 引数の型が明確になり、補完が効きやすくなる
- **バグの早期発見**: 型の不一致をコーディング時点で検出
- **ドキュメントとしての役割**: 関数の入出力が型情報から読み取れる
- **リファクタリングの安全性向上**: 型チェックで破壊的変更を検出

---

## 前提条件

なし（改善計画1-2と並行実施可能）

---

## 関連ファイル

- `src/types.py` (新規作成)
- `src/simulator.py`
- `src/visualizer.py`
- `src/analyzer.py`
- `src/data_loader.py`
- `src/config.py`
- `pyproject.toml` (新規作成)

---

## 所要時間見積もり

- Step 3.1: 30分
- Step 3.2-3.4: 2-3時間
- Step 3.5-3.6: 1-2時間
- 合計: 3.5-5.5時間
