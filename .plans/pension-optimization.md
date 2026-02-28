# 実装計画: 年金受給開始年齢の最適化

## 概要

### 現状の問題点

`_determine_optimal_pension_start_age()` は資産比率の固定閾値で4段階の受給開始年齢を決定している（62, 65, 68, 70歳）。

- 実際に選択可能な62〜75歳の14通りのうち4通りしか使っていない
- 修平と桜を同じ閾値で判定しており、独立最適化できていない
- 一時点の資産比率のみで判断し、その後の資産推移への影響を考慮していない
- FIRE達成時期との連動が考慮されていない（FIRE時期で厚生年金の加入月数が変わる）

### 実装目標

FIRE達成時期と年金受給開始年齢を同時に最適化する。

**定式化（案A: 制約付き最小化）:**

$$
\underset{m^* \in \mathcal{M},\; a_{\text{修平}},\, a_{\text{桜}} \in \mathcal{A}}{\text{minimize}} \quad m^*
$$

$$
\text{subject to} \quad f(m^*, a_{\text{修平}}, a_{\text{桜}}) \geq 0.95
$$

- $m^*$: FIRE達成月
- $a_p$: 受給者 $p$ の年金受給開始年齢（$\in \{62, 63, \ldots, 75\}$）
- $f$: モンテカルロシミュレーションによるFIRE成功率
- $0.95$: 許容最低成功率

**解法**: 2段階最適化（確定的シミュレーションで候補絞り込み → MCで精密評価）

---

## 設計

### アーキテクチャ

```
scripts/optimize_pension.py          # 実行スクリプト（エントリポイント）
src/pension_optimizer.py             # 最適化ロジック（新規モジュール）
src/simulator.py                     # 既存（変更は最小限、年金開始年齢の外部注入を可能にする）
```

### 処理フロー

```
Phase 1: FIRE前シミュレーション（1回）
  simulate_future_assets() を FIRE判定なし で実行
  → 各月の状態（cash, stocks, nisa, cost_basis）を全記録

Phase 2: 確定的スクリーニング（高速、約3分）
  候補FIRE月 × 年金開始年齢 196通り = 全候補を列挙
  各候補に対して simulate_post_fire_assets()（確定的リターン）を実行
  → 最終資産 > 0 の候補のみ残し、最終資産上位 K=30 件を選出

Phase 3: MC精密評価（上位候補のみ、約15分）
  上位 K 件に対して MC シミュレーション（各500回）を実行
  → 成功率 ≥ 95% の候補のうち FIRE月が最小のものが最適解

Phase 4: 結果出力
  最適解の表示
  パレート参考情報（FIRE月 vs 成功率のトレードオフ）を表示
```

### Phase 1: FIRE前シミュレーション（FIRE判定なし）

既存の `simulate_future_assets()` は FIRE判定（`can_retire_now()`）を含むため、
FIRE判定なしで全期間の月次状態を記録する関数が必要。

**方針**: 既存の `simulate_future_assets()` を変更するのではなく、
新モジュール `pension_optimizer.py` 内で FIRE前（労働期間中）の月次状態記録に特化した
ラッパー関数を作成する。

```python
def simulate_pre_fire_trajectory(
    current_cash: float,
    current_stocks: float,
    config: Dict[str, Any],
    scenario: str,
    monthly_income: float,
    monthly_expense: float
) -> pd.DataFrame:
    """
    FIRE判定を行わず、全期間の月次状態を記録する。
    既存の simulate_future_assets() を fire判定無効で実行し、
    各月の (cash, stocks, nisa_balance, nisa_cost_basis, stocks_cost_basis) を返す。
    """
```

**実装方法**: `simulate_future_assets()` を呼び出し、結果DataFrameから
各月の状態を抽出する。FIRE判定は行わず、全月のデータを取得する。

ただし、既存の `simulate_future_assets()` は FIRE達成後に `can_retire_now()` を
呼ばなくなるだけでシミュレーション自体は続行する。
問題は FIRE達成後にモードが変わる（労働収入がなくなる等）こと。

**代替案**: `simulate_future_assets()` に `disable_fire_check=True` オプションを追加する。
これにより、FIRE判定をスキップして「ずっと働き続ける」シミュレーションを実行できる。
各月の完全な状態が得られるので、任意の月をFIRE候補として評価できる。

→ **代替案を採用**。`simulate_future_assets()` に最小限の変更を加える。

### Phase 2: 確定的スクリーニング

```python
def run_deterministic_screening(
    pre_fire_df: pd.DataFrame,
    config: Dict[str, Any],
    scenario: str,
    fire_month_candidates: List[int],
    pension_age_range: range = range(62, 76)
) -> pd.DataFrame:
    """
    全候補 (fire_month, a_shuhei, a_sakura) を確定的シミュレーションで評価。

    Args:
        pre_fire_df: Phase 1 の結果（各月の状態）
        config: 設定辞書
        scenario: シナリオ名
        fire_month_candidates: 評価するFIRE候補月のリスト
        pension_age_range: 年金開始年齢の範囲（デフォルト: 62-75）

    Returns:
        columns: [fire_month, age_shuhei, age_sakura, final_assets, feasible]
    """
```

**FIRE候補月の選定**:

- `can_retire_now()` 相当の判定で「そもそもFIREが成立しうる月」を絞り込む
- 現実的な範囲: 現在のルールベースFIRE月 ± 36ヶ月（3年前後）
- 12ヶ月刻みで粗く探索 → 有望な範囲で6ヶ月刻みに細分化

**年金開始年齢の config への注入**:

`simulate_post_fire_assets()` および `_simulate_post_fire_with_random_returns()` は
内部で `calculate_pension_income()` → `_determine_optimal_pension_start_age()` を呼ぶ。
年金開始年齢を外部から指定するために、config を一時的にオーバーライドする。

```python
def _make_config_with_pension_ages(
    config: Dict[str, Any],
    age_shuhei: int,
    age_sakura: int
) -> Dict[str, Any]:
    """
    年金開始年齢を固定した config のコピーを作成。
    pension_deferral を無効化し、pension.start_age を直接設定する代わりに、
    各人の fixed_start_age を設定する。
    """
```

**実装方法**: `calculate_pension_income()` に `override_start_ages` パラメータを追加する。
指定された場合、`_determine_optimal_pension_start_age()` をスキップして固定年齢を使用する。

### Phase 3: MC精密評価

```python
def run_mc_evaluation(
    top_candidates: pd.DataFrame,
    pre_fire_df: pd.DataFrame,
    config: Dict[str, Any],
    scenario: str,
    iterations: int = 500
) -> pd.DataFrame:
    """
    上位候補に対してモンテカルロシミュレーションを実行。

    Args:
        top_candidates: Phase 2 で選出された上位候補
        pre_fire_df: Phase 1 の結果
        config: 設定辞書
        scenario: シナリオ名
        iterations: MC イテレーション数

    Returns:
        columns: [fire_month, age_shuhei, age_sakura,
                  success_rate, p10_assets, median_assets, mean_assets]
    """
```

既存の `_simulate_post_fire_with_random_returns()` を再利用する。
`_precompute_monthly_cashflows()` は各候補ごとに年金開始年齢が異なるため、
候補ごとに再計算が必要。

**MC反復数の設計**:

- スクリーニング用（Phase 3 初回）: 500回（信頼区間 ±2%程度）
- 最終確認用（最適解の近傍）: 1000回（信頼区間 ±1.5%程度）

### Phase 4: 結果出力

```python
def format_optimization_result(
    optimal: Dict[str, Any],
    all_evaluated: pd.DataFrame,
    baseline: Dict[str, Any]
) -> str:
    """
    最適化結果を整形して出力。

    出力内容:
    - 最適解 (m*, a_修平*, a_桜*) とその成功率・資産統計
    - 現在のルールベースとの比較（FIRE月の差分、成功率の差分）
    - パレート参考情報（FIRE月 vs 成功率のテーブル）
    """
```

---

## 既存コードへの変更

### 変更1: `simulate_future_assets()` に `disable_fire_check` オプション追加

**ファイル**: `src/simulator.py`

```python
def simulate_future_assets(
    current_cash: float = None,
    current_stocks: float = None,
    current_assets: float = None,
    monthly_income: float = 0,
    monthly_expense: float = 0,
    config: Dict[str, Any] = None,
    scenario: str = 'standard',
    disable_fire_check: bool = False  # 新規追加
) -> pd.DataFrame:
```

`disable_fire_check=True` の場合、`can_retire_now()` の呼び出しをスキップし、
全期間を「FIRE未達成（労働継続）」として実行する。
`nisa_cost_basis` 列も結果DataFrameに含める（現在は含まれていない可能性を確認する）。

**影響範囲**: 既存の呼び出し箇所はデフォルト値 `False` で動作が変わらない。

### 変更2: `calculate_pension_income()` に年金開始年齢オーバーライド追加

**ファイル**: `src/simulator.py`

```python
def calculate_pension_income(
    year_offset: float,
    config: Dict[str, Any],
    fire_achieved: bool = False,
    fire_year_offset: float = None,
    current_assets: float = None,
    fire_target_assets: float = None,
    override_start_ages: Dict[str, int] = None  # 新規追加
) -> float:
```

`override_start_ages` が指定された場合（例: `{'修平': 70, '桜': 65}`）、
`_determine_optimal_pension_start_age()` を呼ばず、各人に対して指定された年齢を使用する。

**影響範囲**: 既存の呼び出し箇所はデフォルト値 `None` で動作が変わらない。

### 変更3: `_simulate_post_fire_with_random_returns()` への年金開始年齢伝搬

**ファイル**: `src/simulator.py`

`_precompute_monthly_cashflows()` が年金収入を事前計算しているため、
この関数にも `override_start_ages` を伝搬する必要がある。

```python
def _precompute_monthly_cashflows(
    years_offset: float,
    total_months: int,
    config: Dict[str, Any],
    post_fire_income: float,
    override_start_ages: Dict[str, int] = None  # 新規追加
) -> Tuple[...]:
```

### 変更4: `simulate_post_fire_assets()` への年金開始年齢伝搬

**ファイル**: `src/simulator.py`

```python
def simulate_post_fire_assets(
    current_cash: float,
    current_stocks: float,
    years_offset: float,
    config: Dict[str, Any],
    scenario: str = 'standard',
    nisa_balance: float = 0,
    nisa_cost_basis: float = 0,
    stocks_cost_basis: float = None,
    override_start_ages: Dict[str, int] = None  # 新規追加
) -> float:
```

---

## 新規コード

### `src/pension_optimizer.py`

```python
"""
年金受給開始年齢の最適化モジュール

FIRE達成時期と年金受給開始年齢を同時に最適化する。

定式化:
    minimize   m*  (FIRE達成月)
    subject to f(m*, a_修平, a_桜) >= 0.95  (MC成功率)
    where      a_修平, a_桜 ∈ {62, 63, ..., 75}

解法:
    Phase 1: FIRE前シミュレーション（FIRE判定なし、全月の状態記録）
    Phase 2: 確定的スクリーニング（全候補を高速評価、上位K件を選出）
    Phase 3: MC精密評価（上位候補のみ、成功率≥95%で最小FIRE月を選択）
"""
```

主要な関数:

1. `optimize_pension_start_ages()` — メインエントリポイント
2. `_simulate_pre_fire_trajectory()` — Phase 1
3. `_run_deterministic_screening()` — Phase 2
4. `_run_mc_evaluation()` — Phase 3
5. `_make_config_with_pension_ages()` — config オーバーライド
6. `_find_optimal_solution()` — 成功率≥95%でFIRE月最小の解を選出
7. `_format_result()` — 結果整形

### `scripts/optimize_pension.py`

```python
"""
年金受給開始年齢の最適化スクリプト

使用方法:
    python scripts/optimize_pension.py

出力:
    - 最適解 (FIRE月, 修平の受給開始年齢, 桜の受給開始年齢)
    - 現在のルールベースとの比較
    - FIRE月 vs 成功率のトレードオフ表
"""
```

---

## 実装ステップ

### Step 1: 既存コードの変更（simulator.py）

1. `simulate_future_assets()` に `disable_fire_check` パラメータ追加
2. `calculate_pension_income()` に `override_start_ages` パラメータ追加
3. `_precompute_monthly_cashflows()` に `override_start_ages` パラメータ追加
4. `simulate_post_fire_assets()` に `override_start_ages` パラメータ追加
5. `_simulate_post_fire_with_random_returns()` に `override_start_ages` パラメータ追加
6. 結果DataFrameに `nisa_cost_basis` 列が含まれることを確認

### Step 2: 最適化モジュール新規作成（pension_optimizer.py）

1. Phase 1: `_simulate_pre_fire_trajectory()` 実装
2. Phase 2: `_run_deterministic_screening()` 実装
3. Phase 3: `_run_mc_evaluation()` 実装
4. メインエントリポイント `optimize_pension_start_ages()` 実装
5. 結果整形 `_format_result()` 実装

### Step 3: 実行スクリプト作成（optimize_pension.py）

1. config 読み込み、データ読み込み、最適化実行のスクリプト作成
2. 結果の標準出力への表示

### Step 4: 動作確認

1. 確定的スクリーニング（Phase 2）が妥当な候補を選出することを確認
2. MC評価（Phase 3）の成功率が既存の `run_monte_carlo_simulation()` と整合することを確認
3. 最適解が現在のルールベースと比較して改善（または同等）であることを確認

---

## 計算量の見積もり

### Phase 1: FIRE前シミュレーション

- 1回の `simulate_future_assets()` 実行: 約1秒
- 合計: **約1秒**

### Phase 2: 確定的スクリーニング

- FIRE候補月: 現在のFIRE月 ± 36ヶ月を12ヶ月刻み → 約7通り
- 年金開始年齢: 14 × 14 = 196通り
- 合計候補数: 7 × 196 = **1,372通り**
- 1回の `simulate_post_fire_assets()`: 約50ms
- 合計: **約70秒**

### Phase 3: MC精密評価

- 上位候補: 30件
- 1件あたりのMC（500イテレーション）: 約15秒
- 合計: **約7.5分**

### 総計: 約10分

---

## 出力例（想定）

```
============================================================
年金受給開始年齢の最適化
============================================================

Phase 1: FIRE前シミュレーション実行中...
  全600ヶ月の状態を記録 [OK]

Phase 2: 確定的スクリーニング（1,372通り）
  FIRE候補月: [48, 60, 72, 84, 96, 108, 120]
  年金開始年齢: 62-75歳 × 2人 = 196通り
  実行可能な候補: 892/1,372通り [OK]

Phase 3: MC精密評価（上位30候補、各500回）
  Progress: 10/30 完了...
  Progress: 20/30 完了...
  Progress: 30/30 完了... [OK]

============================================================
最適化結果
============================================================

  最適解:
    FIRE達成月:         月72（現在から6年後、41歳）
    修平の受給開始年齢:  70歳（+42.0%増額）
    桜の受給開始年齢:    65歳（増減なし）
    FIRE成功率:         96.2%
    P10最終資産:        1,230万円
    中央値最終資産:      4,820万円

  現在のルールベースとの比較:
    ルールベースFIRE月:  月78（6.5年後）
    ルールベース成功率:  99.8%
    ルールベース年金:    修平70歳 / 桜65歳
    → 最適化により FIRE時期を 6ヶ月前倒し（成功率95%制約内）

============================================================
パレート参考情報（FIRE月 vs 成功率）
============================================================

  FIRE月 | 最適年金(修/桜) | 成功率  | P10資産
  -------|----------------|---------|--------
  月60   | 72歳/65歳      | 87.4%   | -210万円  ← 制約不満足
  月66   | 71歳/65歳      | 93.0%   | 580万円   ← 制約不満足
  月72   | 70歳/65歳      | 96.2%   | 1,230万円 ← 最適解 ★
  月78   | 70歳/65歳      | 98.4%   | 2,100万円
  月84   | 68歳/65歳      | 99.2%   | 3,050万円
  月96   | 67歳/65歳      | 99.8%   | 4,200万円
```

---

## 将来の拡張

- **パラメータ最適化への発展**: 年金開始年齢以外のパラメータ（現金バッファ月数、暴落閾値等）も同時に最適化する基盤として活用可能
- **許容成功率の感度分析**: α=90%, 95%, 99% でそれぞれ最適解を計算し、許容リスクの影響を可視化
- **パレートフロンティアの可視化**: ダッシュボードにFIRE月 vs 成功率のインタラクティブグラフを追加
