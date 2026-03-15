# 詳細実装計画: ③ 教育方針の3択

最終更新: 2026-03-15

---

## 概要

**※ステータス: 実装済み**
`full_app.py` の子ども設定で `standard`（公立小中高＋国立大）/ `moderate`（高校のみ私立）/ `private_heavy`（私立中高＋私立大）の3択セレクトボックスが実装済み。

---

（以下、過去の計画メモとして残す）

現在は「公立小中高 + 国立大学」の固定コストのみ。競合（ふくわら式など）は私立・公立を選択できる。
教育費はFIREを大きく左右する（子1人で1,000〜2,000万円の差）ため、ユーザーが選択できるようにする。

---

## 現状の実装

### config.yaml — 教育費定義

```yaml
education:
  costs:
    elementary:  {public: 320000,  private: 1600000}  # 年額
    junior_high: {public: 490000,  private: 1400000}
    high:        {public: 460000,  private: 1000000}
    university:  {national: 540000, private_arts: 900000, private_science: 1200000}
  periods:
    elementary:  {start_age: 6,  end_age: 12}
    junior_high: {start_age: 12, end_age: 15}
    high:        {start_age: 15, end_age: 18}
    university:  {start_age: 18, end_age: 22}
```

### simulator.py — `calculate_education_expense` (lines 664-729)

```python
def calculate_education_expense(cfg, child_birth_month, current_month_idx):
    """子どもの年齢に応じた教育費を返す（円/月）"""
    # 各学校段階の年齢で costs["public"] or costs["national"] を使用
    # 現状: 全段階で public / national 固定
```

### full_app.py — 子ども入力 (lines 375-402)

```python
edu_children = []
for i in range(num_children):
    birth = st.date_input(f"子{i+1}の誕生日", ...)
    edu_children.append({"birth": birth})
```

現状は誕生日のみ。教育方針の選択はない。

---

## 変更方針

### 教育方針の3択定義

| 選択肢 | 内容 | 追加費用目安（子1人）|
|--------|------|---------------------|
| **標準**（デフォルト） | 公立小中高 + 国立大学 | 〜800万円 |
| **やや手厚め** | 公立小中 + 私立高 + 国立大学 | 〜1,100万円 |
| **私立重視** | 公立小 + 私立中高 + 私立文系大学 | 〜1,800万円 |

※金額は在学年数分の合算概算

### UI: 教育方針を子どもごとに選択

```python
# full_app.py — 子ども入力セクション
for i in range(num_children):
    cols = st.columns([2, 2])
    with cols[0]:
        birth = st.date_input(f"子{i+1}の誕生日", ...)
    with cols[1]:
        policy = st.selectbox(
            f"子{i+1}の教育方針",
            options=["標準（公立中心）", "やや手厚め（高校のみ私立）", "私立重視"],
            index=0,
            help="公立小中高+国立大 / 公立小中+私立高+国立大 / 公立小+私立中高+私立文系大"
        )
    edu_children.append({"birth": birth, "policy": policy})
```

### config.yaml — 方針マッピング追加

```yaml
education:
  policies:
    standard:
      elementary:  public
      junior_high: public
      high:        public
      university:  national
    moderate:
      elementary:  public
      junior_high: public
      high:        private
      university:  national
    private_heavy:
      elementary:  public
      junior_high: private
      high:        private
      university:  private_arts
  costs:
    # 既存のまま
```

### simulator.py — `calculate_education_expense` 修正

```python
def calculate_education_expense(cfg, child_info, current_month_idx):
    """
    child_info = {"birth": date, "policy": "standard" | "moderate" | "private_heavy"}
    """
    policy_key = child_info.get("policy", "standard")
    policy = cfg["education"]["policies"][policy_key]

    # 学校段階ごとに policy から公立/私立を取得して費用を決定
    for stage, period in cfg["education"]["periods"].items():
        if period["start_age"] <= child_age < period["end_age"]:
            school_type = policy[stage]  # e.g., "public", "private", "national"
            annual_cost = cfg["education"]["costs"][stage][school_type]
            return annual_cost / 12  # 月割り
    return 0
```

### _build_simulation_config — edu_children のフォーマット変更

```python
# 変更前
edu_children = [{"birth": date}]

# 変更後
edu_children = [{"birth": date, "policy": policy_str}]
```

`_build_simulation_config` → `cfg["education"]["children"]` に policy を含むリストとして格納。

---

## 方針選択肢の費用比較（参考）

| 段階 | 標準 | やや手厚め | 私立重視 |
|------|------|-----------|---------|
| 小学6年 | 192万 | 192万 | 192万 |
| 中学3年 | 147万 | 147万 | 420万 |
| 高校3年 | 138万 | 300万 | 300万 |
| 大学4年 | 216万 | 216万 | 360万 |
| **合計** | **693万** | **855万** | **1,272万** |

---

## 実装ステップ

### Step 1: config.yaml — policies セクション追加

既存の costs はそのまま残し、policies マッピングを新規追加。

### Step 2: simulator.py — `calculate_education_expense` 修正

`child_info` に `policy` キーが含まれることを前提に、費用を動的に決定。
後方互換: `policy` がない場合は `"standard"` にフォールバック。

### Step 3: full_app.py — UI追加

子ども入力セクションに `selectbox` を追加。
`edu_children` リストに `"policy"` を含める。

### Step 4: 結果表示に教育費サマリーを追加（任意）

```python
# 子1: 標準 → 約693万円（6歳〜22歳）
# 子2: 私立重視 → 約1,272万円（6歳〜22歳）
```

---

## テスト方針

```bash
python tests/test_simulation_convergence.py
```

**手動確認ケース:**

| 設定 | 期待動作 |
|------|---------|
| 子1人・標準 | 現状と同じ結果（後方互換） |
| 子1人・私立重視 | 教育費期間中の支出が増加 |
| 子2人・異なる方針 | 子ごとの費用が正しく加算される |

---

## 依存関係・注意事項

- **① との依存なし**: 独立して実装可能
- **② との依存なし**: 独立して実装可能
- **子どもなしの場合**: `edu_children` が空リストの場合は変更なし
- **大学の私立区分**: `private_arts`（文系）と `private_science`（理系）があるが、UIでは単純化して「私立」として扱い、内部では `private_arts` を使用する。理系対応は後の改善で行う
- **計算タイミング**: 教育費は月次で計算され、MC全パスに自動反映される
