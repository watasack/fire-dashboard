# 詳細実装計画: ④ FIRE後の税金計算

最終更新: 2026-03-14

---

## 概要

FIRE後は給与収入がなくなり、代わりに「株の売却益」「配当収入」が主な収入源になる。
この切り替わり時に以下の税負担増が発生する：

1. **国民健康保険料の急増**（前年給与収入を基準に算定 → FIREの翌年が最高額）
2. **国民年金保険料の発生**（会社員は厚生年金に含まれていたが、退職後は国民年金を別途支払う）
3. **配当・株売却益への課税**（20.315%）

これらを無視すると「FIRE直後の出費が思ったより大きい」という落とし穴が生じる。

---

## 現状の実装

### simulator.py — FIRE後の支出計算 (`_compute_post_fire_monthly_expenses`, lines 2177-2228)

```python
def _compute_post_fire_monthly_expenses(cfg, age_h, age_w, month_idx):
    # 生活費 + 住宅費 + 教育費 のみ
    # 健康保険料・年金保険料・投資課税はなし
    return total_expense
```

### 年金計算

FIRE後の年金受給（65歳以降）は既存ロジックで計算済み。
ただし年金受給前（退職〜65歳）の国民年金保険料支払いは未実装。

---

## 変更方針

### フェーズ分けしたFIRE後税金

FIRE後の税金を以下の3フェーズで計算する：

```
フェーズA: FIRE後1年目（国保スパイク）
  前年の給与収入をベースに国保算定 → 年収600万なら国保保険料が年60〜80万円
  現役時代と同じ保険料のまま1年間続く

フェーズB: FIRE後2年目以降〜65歳（国保通常）
  資産売却額（生活費分）をベースに国保算定 → 大幅に下がる
  + 国民年金保険料（約2万円/月、2026年水準）

フェーズC: 65歳以降（年金受給開始）
  年金収入から介護保険料・後期高齢者医療保険料が天引き（既存計算で概算）
```

### 実装する計算（簡易推計）

```python
# src/tax_utils.py に追加

def calc_post_fire_monthly_costs(
    pre_fire_annual_income: float,  # 退職前年収（円）
    living_expenses: float,          # 年間生活費（円）
    year_since_fire: int,            # FIRE後何年目か（1始まり）
    age_h: float,
) -> dict:
    """
    FIRE後の追加税負担（月額）を返す。
    returns: {"kokuho": float, "nenkin": float, "total": float}  # 月額（円）
    """
    if year_since_fire == 1:
        # 国保スパイク: 前年給与収入を基準に算定
        kokuho_annual = _calc_kokuho_annual(pre_fire_annual_income)
    else:
        # 2年目以降: 資産売却額（≒生活費）を収入として算定
        # 資産売却益の概算: 生活費の60%を特定口座から引き出し（20%課税前提）
        estimated_income = living_expenses * 0.6
        kokuho_annual = _calc_kokuho_annual(estimated_income)

    # 国民年金保険料（60歳未満の場合のみ）
    nenkin_monthly = 16980 if age_h < 60 else 0  # 2026年の第1号被保険者保険料

    return {
        "kokuho": kokuho_annual / 12,
        "nenkin": nenkin_monthly,
        "total":  kokuho_annual / 12 + nenkin_monthly,
    }

def _calc_kokuho_annual(income: float) -> float:
    """
    国民健康保険料の簡易計算（単身世帯・東京都平均ベース）。
    実際は自治体ごとに異なるが、平均的な水準で推計。
    """
    # 医療分 + 後期高齢者支援分 + 介護分（40〜65歳）
    # 所得割: (income - 430000) * 0.074  # 医療分
    income_deducted = max(0, income - 430_000)
    iryou   = income_deducted * 0.074 + 43_000  # 均等割含む
    kouki   = income_deducted * 0.025 + 15_000
    kaigo   = income_deducted * 0.017 + 10_000  # 40〜64歳のみ
    # 上限: 医療106万 + 後期支援24万 + 介護17万
    total = min(iryou, 1_060_000) + min(kouki, 240_000) + min(kaigo, 170_000)
    return total
```

### simulator.py — `_compute_post_fire_monthly_expenses` 修正

```python
def _compute_post_fire_monthly_expenses(cfg, age_h, age_w, month_idx, fire_month):
    total_expense = ...  # 既存計算

    # FIRE後税金を追加
    pre_fire_income = cfg["simulation"].get("husband_gross_annual", 0) + \
                      cfg["simulation"].get("wife_gross_annual", 0)
    year_since_fire = (month_idx - fire_month) // 12 + 1
    living_exp_annual = total_expense * 12  # 概算

    if year_since_fire > 0:
        tax_costs = calc_post_fire_monthly_costs(
            pre_fire_annual_income=pre_fire_income,
            living_expenses=living_exp_annual,
            year_since_fire=year_since_fire,
            age_h=age_h,
        )
        total_expense += tax_costs["total"]

    return total_expense
```

**注意**: `_compute_post_fire_monthly_expenses` のシグネチャ変更が必要（`fire_month` 引数を追加）。
この関数の呼び出し元をすべて確認し、引数を渡すよう修正する。

---

## UI変更

### 結果表示 — FIRE後税金の内訳

```python
if not mc_res["impossible"]:
    fire_year_taxes = calc_post_fire_monthly_costs(
        pre_fire_annual_income=gross_h * 10000 + gross_w * 10000,
        living_expenses=monthly_exp * 12 * 10000,
        year_since_fire=1,
        age_h=age_h,
    )
    st.warning(
        f"⚠️ FIRE直後1年間: 国保保険料 {fire_year_taxes['kokuho']/10000:.1f}万円/月、"
        f"国民年金 {fire_year_taxes['nenkin']/10000:.1f}万円/月 が追加で発生します。"
        f"（前年の給与収入が基準のため）"
    )
```

---

## 実装ステップ

### Step 1: `src/tax_utils.py` に `calc_post_fire_monthly_costs` を追加

`_calc_kokuho_annual` も同ファイルに。

### Step 2: config.yaml — `pre_fire_income` の参照方法を確定

① 年収入力（`gross_annual`）が実装済みなら、そこから取得。
未実装の場合は `husband_income * 12` を代理値として使用。

### Step 3: simulator.py — `_compute_post_fire_monthly_expenses` に `fire_month` 引数を追加

呼び出し元（`simulate_future_assets`、`run_monte_carlo_simulation` 等）を確認して修正。

### Step 4: 全体テスト

```bash
python tests/test_simulation_convergence.py
```

国保スパイクにより FIRE 直後1年の支出が増えることを確認。

---

## テスト方針

**国保スパイクの数値確認:**

| 退職前年収 | FIRE後1年目国保（年額） | 2年目以降国保（年額） |
|-----------|----------------------|---------------------|
| 400万 | 約35万 | 約20万 |
| 600万 | 約55万 | 約28万 |
| 800万 | 約70万 | 約35万 |

（自治体平均値との比較で±20%以内なら許容範囲）

---

## 依存関係・注意事項

- **① 年収入力への依存**: `pre_fire_annual_income` として `gross_annual` が必要。① が未実装の場合は `husband_income * 12`（手取り月収の12倍）で代替するが、精度が低下する
- **MCシミュレーションの全パスへの影響**: `_compute_post_fire_monthly_expenses` はMCの全1,000パスで呼ばれるため、パフォーマンスへの影響を確認する。`calc_post_fire_monthly_costs` は純関数のため問題ないはず
- **配偶者の国保**: 扶養家族（専業主婦/夫）も同一世帯として国保加入。ただし保険料は世帯単位のため、単純に2倍にはならない。現実装では夫1人分として概算し、注記を付ける
- **自治体差**: 国保保険料は自治体ごとに大きく異なる（東京23区 vs 地方都市で30%以上の差も）。今回は平均値で実装し、「お住まいの自治体によって異なります」と注記する
- **投資収益への課税**: 配当・売却益の20.315%課税は、資産シミュレーションのリターン計算に折り込まれているとみなし（税引後リターンとして）、別途計上しない
