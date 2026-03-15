# 詳細実装計画: ⑤ 最悪ケース枯渇年齢の表示

最終更新: 2026-03-15

---

## 概要

**※ステータス: 実装済み**
`full_app.py` の破産シナリオ分析セクション（L818-854）で `calc_depletion_age`（下位5%・25%枯渇年齢）と `get_bankrupt_depletion_ages`（枯渇年齢ヒストグラム）が実装済み。
`src/analytics.py` に算出ロジックあり。

---

（以下、過去の計画メモとして残す）

現在の結果表示は「FIRE成功確率XX%」のみで、「失敗したらいつ資産がなくなるか」が見えない。
競合（63400r）は「資産が枯渇する年齢の分布」を明示している。

**追加する表示:**
- 「最悪ケース（下位5%）: ○○歳で資産が枯渇」
- 「中央値: 90歳時点で残高XX百万円」

これにより「万が一失敗しても70代まで持つならリスク許容できる」という判断ができる。

---

## 現状の実装

### `run_mc_fixed_fire` の返り値

```python
{
    'all_results': list,          # 90歳時点の最終資産リスト（1,000要素）
    'median_final_assets': float, # 中央値
    'percentile_5': float,        # 下位5%（= percentile_5 < 0 なら破産）
    'success_rate': float,        # 90歳まで資産がプラスの割合
    ...
}
```

### full_app.py — 結果表示

現状はメトリクスカード4枚（FIRE年齢、FIRE時資産、成功確率、何か）を表示。
`all_results` の中身はヒストグラム描画には使っていない（可能性がある）。

---

## 変更方針

### 「破産シナリオ分析」セクションを追加

```python
# full_app.py — 結果表示セクション

all_results = mc_res["all_results"]  # 90歳時点資産のリスト（円）
bankrupt_results = [r for r in all_results if r <= 0]

if bankrupt_results:
    st.subheader("万が一失敗した場合のリスク分析")
    col1, col2, col3 = st.columns(3)

    with col1:
        worst_age = calc_depletion_age(mc_res, percentile=0.05)
        st.metric("最悪ケース枯渇年齢（下位5%）", f"{worst_age:.0f}歳")

    with col2:
        p25_age = calc_depletion_age(mc_res, percentile=0.25)
        st.metric("枯渇年齢（下位25%）", f"{p25_age:.0f}歳")

    with col3:
        bankrupt_rate = len(bankrupt_results) / len(all_results) * 100
        st.metric("破産シナリオ数", f"{bankrupt_rate:.1f}%（{len(bankrupt_results)}通り）")
```

### `calc_depletion_age` 関数の実装

**問題**: `all_results` は「90歳時点の最終資産」のリストであり、「何歳で枯渇したか」の情報は含まれていない。

**解決策 A（簡易推計）**: 90歳時点の資産が `-X万円` であれば、線形補間で「何歳で0になるか」を推計。

```python
def calc_depletion_age(mc_res: dict, percentile: float) -> float:
    """
    MCパスのうち percentile 分位のパスが何歳で資産枯渇するかを推計。

    手法: all_paths（全パスの資産推移）から percentile に該当するパスを取得し、
         資産が0になる月を線形補間で推定。
    """
    all_paths = mc_res.get("all_paths")  # shape: (iterations, months)
    if all_paths is None:
        # all_paths がない場合は簡易推計（90歳時点資産から外挿）
        return _estimate_depletion_from_final(mc_res, percentile)

    # 各パスの枯渇月を特定
    depletion_months = []
    for path in all_paths:
        zero_crossings = np.where(path <= 0)[0]
        if len(zero_crossings) > 0:
            depletion_months.append(zero_crossings[0])
        else:
            depletion_months.append(len(path))  # 枯渇しなかった場合はシミュレーション終端

    # percentile 分位の枯渇月
    depletion_month = np.percentile(depletion_months, percentile * 100)

    # 月 → 年齢変換
    birth_year_h = mc_res["fire_date"].year - mc_res["fire_age_h"]
    start_age_h  = mc_res.get("start_age_h", 35)  # シミュレーション開始時の夫年齢
    depletion_age = start_age_h + depletion_month / 12
    return depletion_age
```

**解決策 B（推奨）**: `run_mc_fixed_fire` が `all_paths`（全パスの月次資産推移）を返すよう修正する。

```python
# simulator.py の run_mc_fixed_fire に追加
return {
    ...existing keys...,
    "all_paths": np.array(all_monthly_assets),  # shape: (iterations, total_months)
}
```

`all_paths` は (1000 × 660) = 約66万要素の float 配列。
メモリ使用量: 660,000 × 8 bytes ≈ 5MB（問題なし）。

---

## 実装ステップ

### Step 1: `simulator.py` — `run_mc_fixed_fire` に `all_paths` を追加

現在の返り値に `all_paths: np.ndarray` を追加。

```python
# run_mc_fixed_fire 内
all_monthly_assets = []  # 各パスの月次資産リスト
for i in range(iterations):
    path = simulate_single_mc_path(...)
    all_monthly_assets.append(path)
    all_results.append(path[-1])  # 90歳時点（既存）

return {
    ...existing...,
    "all_paths": np.array(all_monthly_assets),  # 新規追加
}
```

### Step 2: `src/analytics.py`（新規または既存）— `calc_depletion_age` 実装

全パスの枯渇月を計算し、パーセンタイルで集計する関数。

### Step 3: `full_app.py` — 枯渇年齢の表示セクション追加

### Step 4: ヒストグラム表示（任意）

破産したパスの「枯渇年齢分布」をヒストグラムで表示する：

```python
import plotly.express as px

depletion_ages = [...]  # 破産パスの枯渇年齢リスト
fig = px.histogram(
    x=depletion_ages,
    nbins=20,
    title="資産枯渇年齢の分布（破産シナリオのみ）",
    labels={"x": "枯渇年齢（歳）"}
)
st.plotly_chart(fig)
```

---

## テスト方針

```bash
python tests/test_simulation_convergence.py
```

**手動確認:**

| 成功確率 | 期待動作 |
|---------|---------|
| 100% | 破産シナリオセクションは非表示 |
| 80% | 下位5%の枯渇年齢が表示される |
| 50% | 枯渇年齢がFIRE後比較的早い時期を示す |

---

## 依存関係・注意事項

- **`all_paths` のメモリ**: 5MBは問題ないが、`all_paths` をセッション間でキャッシュしない（`@st.cache_data` の対象外にする）
- **`run_mc_fixed_fire` の返り値拡張**: `full_app.py` がすでに使っているキーは変更しない。`all_paths` を追加するだけ
- **パフォーマンス**: `all_paths` の生成は各パスのシミュレーション結果を保持するだけなので、追加コストは最小限
- **表示の条件分岐**: 成功確率100%（破産なし）の場合は枯渇年齢セクションを非表示にする
- **「90歳まで」の制限**: 現在のシミュレーションは90歳で終了するため、「90歳を超えて持つかどうか」は計算できない。この制限を注記に入れる
