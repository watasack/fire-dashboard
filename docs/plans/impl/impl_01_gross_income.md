# 詳細実装計画: ① 年収（税引き前）入力への移行

最終更新: 2026-03-14（コード読み取り後に改訂）

---

## 概要

**※ステータス: 実装済み**
`full_app.py` および `src/tax_utils.py` における税引き前年収の入力および手取りへの変換ロジック、`avg_monthly_salary`を用いた年金計算の反映については**既に実装済み**です。
したがって、本項目の `full_app.py` 向けの実装タスクは完了しています。
また、`demo_app.py` のアップデートについては、すべての機能の `full_app.py` 向け実装が完了した後に全体でまとめて対応することになったため、現時点では着手しません。

---
（以下、過去の計画メモとして残す）
現在のツールは **手取り月収** を入力として使うが、競合はすべて **年収（税引き前）** を入力として自動で手取りを計算している。
「年収500万と言われたときにすぐ入力できる」のが競合優位。これが Phase 1 の最優先タスク。

他のすべての機能（④FIRE後税金など）がこの変更の上に乗るため、**最初に実装しなければならない。**

---

## 【設計原則】収入値のデータフローを終端まで追跡すること

収入に関わる入力変更では、**その値が参照されるすべての計算**を洗い出してから計画を書く。
「おそらく影響しないだろう」という推測で計画を止めてはならない。

---

## 現状のデータフロー（コード読み取り済み）

### フロー1: キャッシュフロー計算

```
UI: income_h（手取り月収・万円）
  → _build_simulation_config: cfg["simulation"]["husband_income"] = income_h * 10000
  → simulator.py _calculate_monthly_income: husband_income_base として月次収入計算に使用
  → 毎月の労働収入、育休給付金比率、時短勤務比率の計算に使用
```

→ **手取り月収を渡すのが正しい**。変換後の `income_h` をそのまま使う。

### フロー2: 年金計算（厚生年金）← 計画書初版で見落とした

```
UI: income_h（手取り月収・万円）← 現状ここで止まっていた
  → _build_simulation_config: cfg["pension"]["people"][0]["avg_monthly_salary"] を更新 【未実装】
    ↑ この値は demo_config.yaml の固定値 50万円/月 が使われ続ける

  → simulator.py _calculate_person_pension:
      avg_monthly_salary = person.get("avg_monthly_salary", 0)
      employees_pension = avg_monthly_salary * work_months * 乗率
```

**発見された問題:**
1. `avg_monthly_salary`（標準報酬月額）は `husband_income`（手取り月収）とは**完全に別フィールド**
2. `demo_config.yaml` に `avg_monthly_salary: 500000` が固定値で書かれており、UIの収入入力が**まったく反映されていない**
3. `demo_config.yaml` には `past_pension_base_annual: 150000`、`past_contribution_months: 160` という実績値も書かれており、フル版UIでは根拠不明の値が年金計算に混入する

→ **税引き前月収（= gross_annual / 12）を `avg_monthly_salary` に設定する必要がある**。
  加えて `past_pension_base_annual` / `past_contribution_months` を 0 にリセットする。

### フロー3: 昇給計算

```
husband_income × (1 + income_growth_rate)^years → 将来の月収推計
```

→ `income_h`（手取り月収）に昇給率を掛ける形。これは手取りに対して掛けることになるが、
  「手取りも給与と同比率で上昇する」近似として許容できる。変更不要。

### フロー4: 時短勤務の収入比率

```python
income_ratio = (cd["h_ri"] * 10000) / (income_h * 10000)  # 時短月収 / 通常月収
```

→ 比率計算のため `income_h` が `float` でも問題なし。ただし `income_h == 0` のガードが必要（既存コードで対処済み）。

### フロー5: _leave_inputs の default_income 引数

```python
ri = st.number_input("時短月収(万)", 0, 60, default_income, step=1, ...)
```

→ `step=1` は整数型。`income_h` が `float` （例: 38.7）のまま渡すと Streamlit でエラー。
  `int(income_h)` に変換して渡す必要がある。

---

## 変更方針

### ユーザーに見せるUI

| 変更前 | 変更後 |
|--------|--------|
| 月収（手取り）万円 | 年収（税引き前）万円 |
| デフォルト: 35 万円/月 | デフォルト: 600 万円/年（夫）/ 550万円（妻） |

年収入力の直下に「手取り目安: 約XX万円/月」を `st.caption()` で表示する。

### 変換ロジック（税金計算）

年収 → 手取り月収の変換は **簡易推計式** を使う（正確な税制計算は ④ で行う）。
`src/tax_utils.py`（新規ファイル）に実装する。

```python
def gross_to_net_monthly(gross_annual_man: float, employment_type: str) -> float:
    """税引き前年収（万円）→ 手取り月収（万円）の簡易変換"""
    # 会社員: 社会保険料(14.8%) + 給与所得控除 + 基礎控除 + 所得税・住民税
    # 個人事業主: 国民健康保険・国民年金 + 青色申告控除 + 所得税・住民税
    # 専業主夫/婦: 0
```

### _build_simulation_config の変更

引数に `gross_h: int`, `gross_w: int`（税引き前年収・万円）を追加する。

**変更内容（2箇所）:**

1. **キャッシュフロー計算用**: `income_h * 10000` を `husband_income` に設定（変更なし）
2. **年金計算用**: `gross_h * 10000 / 12` を `avg_monthly_salary` に設定（**新規追加**）
3. **過去実績リセット**: `past_pension_base_annual = 0`, `past_contribution_months = 0`（**新規追加**）

```python
def _build_simulation_config(
    base_cfg, *,
    age_h, age_w, type_h, type_w,
    income_h, income_w,          # 手取り月収（万円）: キャッシュフロー計算用
    gross_h, gross_w,            # 税引き前年収（万円）: 年金計算用 ← 新規追加
    monthly_exp, ...
) -> dict:
    # キャッシュフロー: 手取り月収をそのまま使用
    cfg["simulation"]["husband_income"] = income_h * 10000
    cfg["simulation"]["wife_income"]    = income_w * 10000

    # 年金: 標準報酬月額 = 税引き前月収 = 税引き前年収 / 12
    gross_monthly_h = gross_h * 10000 / 12
    gross_monthly_w = gross_w * 10000 / 12

    for i, (type_, gross_monthly) in enumerate([(type_h, gross_monthly_h), (type_w, gross_monthly_w)]):
        if i < len(cfg["pension"]["people"]):
            p = cfg["pension"]["people"][i]
            # UI非入力の過去実績をリセット（demo_config.yaml の固定値を排除）
            p["past_pension_base_annual"]  = 0
            p["past_contribution_months"] = 0
            if type_ == "会社員":
                p["avg_monthly_salary"] = gross_monthly
```

---

## 実装ステップ

### Step 1: `src/tax_utils.py` を新規作成

`gross_to_net_monthly()` と補助関数 `_kyuyo_shotoku_kojo()`, `_shotoku_zei()` を実装。

### Step 2: `tests/test_tax_utils.py` を新規作成

年収400万・600万・800万・1000万の会社員と個人事業主でテスト。

### Step 3: `full_app.py` — UI変更

- `_DEFAULT_INCOME = 35` → `_DEFAULT_GROSS_H = 600`, `_DEFAULT_GROSS_W = 550`
- 収入入力を年収（税引き前）に変更
- 変換後の手取りを `st.caption()` で表示
- `_leave_inputs` へは `int(income_h)` で渡す（float → int 変換）

### Step 4: `full_app.py` — `_build_simulation_config` に `gross_h`, `gross_w` 引数を追加

- 年金の `avg_monthly_salary` を `gross_h * 10000 / 12` で設定
- `past_pension_base_annual` と `past_contribution_months` を 0 にリセット

### Step 5: `full_app.py` — `_build_simulation_config` の呼び出し箇所に `gross_h=gross_h, gross_w=gross_w` を追加

---

## テスト方針

```bash
python tests/test_tax_utils.py                   # 変換関数の単体テスト（18件）
python tests/test_simulation_convergence.py      # 回帰テスト
```

**test_tax_utils.py 確認ケース:**

| 年収 | 雇用形態 | 期待手取り月収（目安） |
|------|---------|---------------------|
| 400万 | 会社員 | 約27万円/月 |
| 600万 | 会社員 | 約38〜40万円/月 |
| 800万 | 会社員 | 約50〜52万円/月 |
| 600万 | 個人事業主 | 約37〜40万円/月 |

**年金計算の影響確認（手動）:**

シミュレーション実行後、年金受給額が年収に連動して変化することを確認する。
例: 年収600万（標準報酬月額 50万）→ 会社員30年勤続の厚生年金 ≈ 年100万円程度

---

## 依存関係・注意事項

- **他の全機能の前提条件**: ④⑤⑥ はこの実装の完了後に実施する
- **標準報酬月額の近似**: `gross_annual / 12` を標準報酬月額として使用する。実際の標準報酬月額は等級制（32段階）で決まるが、フル版UIでは連続値の近似で十分
- **昇給による標準報酬月額の変化**: 現在の実装は `avg_monthly_salary` を固定値として使う。将来的には昇給に応じて年金受給額も増やすのが正確だが、複雑度が上がるため現状は初期年収固定で計算する
- **個人事業主の年金**: `type_ == "個人事業主"` の場合は `avg_monthly_salary` を設定しない（年金タイプが `national` になるため使われない）
- **`_leave_inputs` の型**: `default_income` は `int` で渡すこと（`step=1` の `st.number_input` との型整合性）
