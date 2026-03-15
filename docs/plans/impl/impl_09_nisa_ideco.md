# 詳細実装計画: ⑨ NISA/iDeCo対応

最終更新: 2026-03-15

---

## 概要

**※ステータス: 実装済み**
`full_app.py` のサイドバー「NISA / iDeCo の内訳を入力（任意）」エクスパンダー（L458-495）として実装済み。
NISA残高・年間積立額は `_build_simulation_config()` 経由で `nisa_balance` / `nisa_annual` として simulator に渡される。
iDeCo残高・月額は情報表示と節税目安の提示に留まり（60歳制約の注意書きあり）、シミュレーション本体への組み込みはPhase 4以降。

---

（以下、過去の計画メモとして残す）

競合（ふくわら式）のみが対応している差別化機能。NISA/iDeCoは日本の資産形成で非常に重要だが、
現在のツールは「金融資産合計」として一括入力するだけで非課税メリットを計算していない。

**実装する機能:**
1. **NISA残高・毎年の積立額** を分離して入力
2. **NISA口座内のリターンへの非課税メリット** を計算（課税口座と20.315%の差）
3. **iDeCoの制約（60歳まで引き出し不可）** を入力ガイドで明示

---

## 現状の問題

### full_app.py — 資産入力

```python
cash_input   = st.number_input("現金・預金（万円）", ...)
stocks_input = st.number_input("株式・投資信託（万円）", ...)
```

`stocks_input` に NISA・iDeCo・課税口座がすべて混在している。

### 不変条件（コード内で保証されている）

```
nisa_balance <= stocks  # 常に成立必須
```

この不変条件は `config.yaml` と `simulator.py` で強制されている。
現状は NISA を stocks の内数として管理している。

### config.yaml

```yaml
simulation:
  nisa_balance: ...  # stocks の内数として管理
```

### 税制上のメリット

| 口座種別 | 運用益課税 | 備考 |
|---------|-----------|------|
| 課税口座（特定口座） | 20.315% | 毎年の運用益に課税 |
| NISA | 0% | 非課税（成長投資枠: 1,200万円上限） |
| iDeCo | 0%（運用時）| 受取時に課税あり。60歳まで引出し不可 |

---

## 変更方針

### UI: 資産内訳の入力を詳細化

```python
# full_app.py — 資産入力セクション

st.subheader("現在の金融資産")

col1, col2 = st.columns(2)
with col1:
    cash_input = st.number_input("現金・預金（万円）", value=200, min_value=0, step=10)
with col2:
    total_stocks = st.number_input(
        "株式・投資信託 合計（万円）", value=1800, min_value=0, step=10
    )

# NISA の内数を展開
with st.expander("📋 内訳を入力（NISAなど）", expanded=False):
    nisa_balance = st.number_input(
        "うち NISA 残高（万円）",
        value=min(400, total_stocks),
        min_value=0, max_value=total_stocks,
        help="NISA口座（つみたて・成長投資枠）の合計残高。株式・投資信託合計の内数。"
    )
    nisa_annual = st.number_input(
        "NISA 年間積立額（万円）",
        value=36, min_value=0, max_value=360, step=6,
        help="毎年いくらNISA枠で積み立てるか。上限は成長投資枠+つみたて枠で360万円/年。"
    )
    ideco_balance = st.number_input(
        "iDeCo 残高（万円）",
        value=0, min_value=0,
        help="iDeCoは60歳まで引き出せません。FIRE時期が60歳未満の場合は、"
             "この金額をFIRE後の資産として使えないことに注意してください。"
    )
    ideco_monthly = st.number_input(
        "iDeCo 月額掛金（万円）",
        value=0, min_value=0, max_value=7,  # 会社員の上限: 月2.3万円
        help="会社員は月2.3万円（年27.6万円）が上限。"
    )

    if ideco_balance > 0 and fire_age_h < 60:
        st.warning(
            f"⚠️ FIRE予定年齢（{fire_age_h:.0f}歳）がiDeCo受給開始（60歳）より前です。"
            f"iDeCo残高{ideco_balance}万円はFIRE後すぐには使えません。"
            f"保守的に試算したい場合はiDeCo残高を0として入力してください。"
        )

# バリデーション: NISA は stocks の内数
if nisa_balance > total_stocks:
    st.error("NISA残高が株式・投資信託合計を超えています。")
    nisa_balance = total_stocks
```

### 非課税メリットの計算

#### 簡易実装（Phase 2 向け）

毎年の運用益に対する節税額を計算し、リターンに上乗せする形で簡易モデル化する。

```python
# src/tax_utils.py に追加

def nisa_tax_benefit_per_month(nisa_balance: float, annual_return: float) -> float:
    """
    NISA 非課税メリットの月次等価額。

    課税口座なら税引後リターン = annual_return * (1 - 0.20315)
    NISA は  annual_return をそのまま享受
    差分: annual_return * 0.20315 が節税額

    Parameters:
        nisa_balance: NISA残高（円）
        annual_return: 年次リターン率（例: 0.05）

    Returns:
        月次節税額相当（円）
    """
    annual_benefit = nisa_balance * annual_return * 0.20315
    return annual_benefit / 12
```

#### MCシミュレーションへの組み込み

```python
# simulate_single_mc_path 内（概念）
# 各月のリターン計算時に NISA 節税メリットを加算

gross_return = assets * monthly_return
nisa_benefit = nisa_tax_benefit_per_month(nisa_balance_at_month, annual_return)
# nisa_benefit を gross_return に加算 or 支出から差し引く形で反映
```

#### NISA 残高の追跡

NISA 残高は毎月増加（年間積立 = `nisa_annual` を月割り）し、
NISA 残高が `total_stocks` を超えないよう管理する。

```python
# 毎月の NISA 残高更新
nisa_monthly_addition = nisa_annual * 10000 / 12
nisa_balance_at_month = min(
    nisa_balance_prev * (1 + monthly_return) + nisa_monthly_addition,
    assets_at_month,  # 総資産を超えない
    3600_0000,        # NISA 上限: 1,800万円（つみたて600万 + 成長投資枠1200万）
)
```

### iDeCo の扱い

**Phase 2 では完全な iDeCo 計算は行わない。** 以下の方針とする：

1. iDeCo 残高はユーザーが「60歳以前にFIREするなら含めない」ことを警告で促す
2. iDeCo 掛金（月額）は「税控除によって実質コストが減る」という簡易計算を表示する：
   ```
   iDeCo 掛金 2.3万円/月 → 所得税20%+住民税10% = 実質負担 1.84万円/月（節税0.46万円）
   ```
3. iDeCo 受給時の課税（退職所得控除）は対象外とし、注記に含める

---

## _build_simulation_config への変更

```python
def _build_simulation_config(
    ...,
    nisa_balance,       # NISA残高（万円）← 新規追加
    nisa_annual,        # NISA年間積立（万円）← 新規追加
    ideco_balance,      # iDeCo残高（万円）← 新規追加（参考情報）
    ...
) -> dict:
    cfg["simulation"]["nisa_balance"] = nisa_balance * 10000
    cfg["simulation"]["nisa_annual"]  = nisa_annual * 10000
    # iDeCo は警告表示のみで計算には含めない
```

### 不変条件の維持

```
nisa_balance <= stocks（= total_stocks - ideco）
```

UIでの入力バリデーションと config での自動調整で保証する：

```python
cfg["simulation"]["nisa_balance"] = min(
    cfg["simulation"]["nisa_balance"],
    cfg["simulation"]["stocks"]
)
```

---

## 実装ステップ

### Step 1: `full_app.py` — UI の拡張

`st.expander` 内に NISA/iDeCo 入力欄を追加。デフォルトは折りたたみ（任意入力）。

### Step 2: `_build_simulation_config` — 新規引数追加

`nisa_annual` を config に追加。

### Step 3: `src/tax_utils.py` — `nisa_tax_benefit_per_month` 実装

### Step 4: `simulator.py` — NISA 残高追跡とメリット計算

MCループ内で NISA 残高を更新し、非課税メリット分をリターンに反映。

### Step 5: 不変条件のテスト

```bash
python tests/test_simulation_convergence.py
```

`nisa_balance <= stocks` が常に成立することを確認。

---

## テスト方針

**NISA 非課税メリットの大きさ確認:**

| NISA 残高 | 年利5%の場合 | 課税口座との差（年） |
|----------|------------|-------------------|
| 500万円 | 25万円運用益 | 節税額: 約5万円/年 |
| 1,000万円 | 50万円運用益 | 節税額: 約10万円/年 |
| 1,800万円（上限） | 90万円運用益 | 節税額: 約18万円/年 |

NISA残高1,800万円で年間18万円の節税 → FIRE到達が数ヶ月早まる程度の効果。

---

## 依存関係・注意事項

- **不変条件 `nisa_balance <= stocks`**: コード全体で保証が必要。UIバリデーション + config 設定の両方で担保する
- **① 年収入力との関係**: iDeCo の所得控除効果は税引き前年収があれば正確に計算できる。① 実装後に精度向上が可能
- **NISA 上限の追跡**: 2024年以降の新 NISA は「つみたて投資枠 120万/年 + 成長投資枠 240万/年 = 360万/年、総上限 1,800万円」。毎年の積立額が上限に達したら新規積立を止める処理が必要
- **iDeCo の拠出上限**: 会社員（企業年金なし）: 月2.3万円、自営業: 月6.8万円。UIで雇用形態に応じて `max_value` を変える
- **NISA のリターン**: MC シミュレーションの各パスで NISA 残高のリターンも確率的に変動する。NISA 残高を別途追跡するか、総資産に対する比率で近似するかを選択する（後者の方が実装が容易）
