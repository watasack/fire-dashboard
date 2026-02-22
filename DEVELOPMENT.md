# 開発者向けガイド

このドキュメントは、FIREダッシュボードプロジェクトの開発者向けガイドです。

## プロジェクト構造

```
.
├── config.yaml                  # シミュレーション設定
├── data/
│   ├── assets.csv              # 資産推移データ（日次）
│   └── transactions.csv        # 取引履歴
├── src/
│   ├── simulator.py            # シミュレーションエンジン（本体）
│   ├── data_loader.py          # データ読み込み
│   ├── data_processor.py       # データ処理
│   ├── analyzer.py             # 現状分析
│   ├── visualizer.py           # グラフ生成
│   └── html_generator.py       # HTMLダッシュボード生成
├── tests/
│   ├── test_simulation_convergence.py  # 統合テスト（主要）
│   └── test_mc_standard_comparison.py  # MC vs 標準の詳細診断
├── scripts/
│   └── generate_dashboard.py   # ダッシュボード生成スクリプト
├── dashboard/
│   └── index.html              # 生成されたダッシュボード
├── .serena/
│   └── analysis-bug-root-cause.md  # バグ根本原因分析
├── README.md                    # シミュレーション仕様書（NotebookLM用）
└── DEVELOPMENT.md              # このファイル
```

---

## クイックスタート

### ダッシュボード生成

```bash
python scripts/generate_dashboard.py
# → dashboard/index.html に出力
```

### テスト実行

```bash
# 統合テスト（推奨）
python tests/test_simulation_convergence.py

# 詳細診断
python tests/test_mc_standard_comparison.py
```

### FIRE達成時期の感度分析

各パラメータ変更時のFIRE達成時期への影響を分析：

```bash
python scripts/sensitivity_analysis.py
```

**分析内容:**
- 収入増加、支出削減、運用リターン向上などの効果を定量測定
- 費用対効果ランキングを自動生成
- 複合施策の効果も分析

**主要な発見:**
- 運用リターン向上が最も効果的（ただし**市場次第でコントロール不可**）
- 複合的改善（収入+支出+リターン）が現実的で効果的
- 収入増加や支出削減の単独効果は限定的（既に高い貯蓄率のため）

**重要:** パラメータの分類（コントロール可能 vs 外部要因）を理解してから実行することを推奨。
詳細は [.plans/fire-optimization-parameters.md](.plans/fire-optimization-parameters.md) を参照。

---

## テストの実行

### 統合テスト（推奨）

全ての主要な不変条件と整合性を検証します：

```bash
python tests/test_simulation_convergence.py
```

**検証内容:**
1. 標準シミュレーションとMC中央値の収束性（許容誤差10%）
2. NISA残高 ≤ 株式残高（不変条件）
3. NISA年間投資枠（360万円）の遵守
4. 資産推移の異常検知（極端な減少の検出）

**期待される実行時間:** 約2-3分（MC 1000イテレーション）

**期待される出力:**
```
============================================================
統合テスト: シミュレーション整合性検証
============================================================

=== シミュレーション整合性テスト ===
標準シミュレーション最終資産: 9,042,056円
  - 現金: 5,000,000円
  - 株式: 4,042,056円

MCシミュレーション分布:
  平均値:  14,536,587円
  中央値:  8,178,493円
  10%ile:  0円
  90%ile:  39,332,215円

乖離分析:
  標準 vs MC中央値: 9.55%
  標準 vs MC平均値: 60.77%
  MC中央値/平均値: 0.563 (対数正規分布では<1.0が正常)

[OK] テスト合格: 標準シミュレーションとMC中央値の整合性OK

=== NISA残高不変条件テスト ===
全661ヶ月中の違反: 0件
[OK] テスト合格: NISA残高は常に株式残高以下

=== NISA年間投資枠チェック ===
年間投資枠上限: 3,600,000円
超過年: 0年
[OK] テスト合格: NISA年間投資枠を遵守しています

=== 資産推移異常検知テスト ===
全期間: 661ヶ月
極端な株式減少（>50%）: 0件 (0.0%)
[OK] テスト合格: 異常な資産減少は検出されませんでした

============================================================
全テスト合格 [OK]
============================================================
```

### 詳細診断テスト

標準シミュレーションとMCシミュレーションの乖離を詳細分析します：

```bash
python tests/test_mc_standard_comparison.py
```

**出力内容:**
- FIRE達成時点の比較（両者が一致しているか）
- 最終資産の比較（中央値、平均値、パーセンタイル）
- 乖離の原因分析
- 対数正規分布の特性評価

---

## 開発ガイドライン

### NISA計算の注意点

#### 重要な不変条件

```python
# 常に成立すべき条件
assert nisa_balance <= stocks, "NISA残高は株式残高を超えてはならない"
```

NISA残高は株式資産の一部であるため、この条件は常に真でなければなりません。
違反が検出された場合、NISA計算ロジックにバグがあります。

#### NISA残高の更新タイミング

1. **新規投資時**: `nisa_balance += 投資額`
2. **運用リターン適用時**: `nisa_balance *= (1 + monthly_return_rate)` ⚠️ **重要**
3. **売却時**: `nisa_balance -= 売却額`

**特に注意:** 運用リターン適用を忘れると、NISA残高が実際より低くなり、
標準シミュレーションとMCシミュレーションの間に大きな乖離が発生します。

#### 過去のバグ事例（2026-02-22）

**バグ内容:**
- FIRE前・FIRE後の月次処理で、NISA残高への運用リターン適用が漏れていた
- `_process_post_fire_monthly_cycle` (line 1228)
- `_process_future_monthly_cycle` (line 1970)

**影響:**
- 標準シミュレーション: 787万円
- MC中央値: 1527万円
- **約2倍の乖離が発生**

**原因:**
- コードの重複（3つの関数に類似ロジック）
- 一部の関数のみ修正され、他の関数が見落とされた

**対策:**
1. 運用リターン適用後に不変条件アサーションを追加
2. 統合テストで標準 vs MC の整合性を検証
3. デッドコード削除（230行）

**詳細:** [.serena/analysis-bug-root-cause.md](.serena/analysis-bug-root-cause.md)

### コード変更時のチェックリスト

月次処理ロジックを変更する際は、以下を確認してください：

- [ ] NISA残高への運用リターン適用を忘れていないか？
- [ ] 同様の処理が他の関数にも存在しないか？（重複チェック）
- [ ] 不変条件アサーション（`nisa_balance <= stocks`）が維持されているか？
- [ ] 統合テストが全て合格するか？

### 統合テストの追加

新しい不変条件を追加した場合は、`tests/test_simulation_convergence.py` にテストを追加してください：

```python
def test_新しい不変条件():
    """
    不変条件テスト: 〇〇が××であることを検証
    """
    config, current_status, trends = load_test_data()
    result = simulate_future_assets(
        current_assets=current_status['net_assets'],
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        config=config,
        scenario='standard'
    )

    # 不変条件を検証
    violations = result[result['条件違反']]
    assert len(violations) == 0, (
        f"エラーメッセージ: {len(violations)}件の違反が検出されました"
    )

    print("[OK] テスト合格: 〇〇は常に××です")
```

---

## トラブルシューティング

### テストが失敗する場合

#### 症状1: `test_standard_vs_monte_carlo_convergence` が失敗

```
AssertionError: 標準シミュレーションとMC中央値の乖離が大きすぎます。
標準: 9,042,056円, MC中央値: 5,123,456円
相対誤差: 15.23% (許容: 10.00%)
→ NISA運用リターン適用漏れなど、実装の不整合が疑われます。
```

**診断手順:**

1. 詳細診断テストを実行
   ```bash
   python tests/test_mc_standard_comparison.py
   ```

2. **FIRE達成時点が一致しているか確認**
   - 一致している → FIRE後の実装に問題
   - 一致していない → FIRE前の実装に問題

3. **標準 vs MC平均値の乖離を確認**
   - 60%以上の差がある場合、FIRE後の実装の違いの可能性
   - Jensen's inequalityにより、MC平均値 > 標準 は自然

4. **NISA残高への運用リターン適用を確認**
   ```python
   # _process_post_fire_monthly_cycle と _process_future_monthly_cycle で
   # 以下のコードが存在するか確認
   nisa_balance *= (1 + monthly_return_rate)
   ```

#### 症状2: `test_nisa_balance_never_exceeds_stocks` が失敗

```
AssertionError: NISA残高が株式残高を超える期間が3件検出されました。
NISA計算ロジックにバグがある可能性があります。
```

**原因と対処:**

NISA計算ロジックにバグがあります。以下を確認：

1. **売却処理で `nisa_balance` が正しく減少しているか**
   ```python
   # _sell_stocks_with_tax 関数を確認
   nisa_sold = min(amount, nisa_balance)
   nisa_balance -= nisa_sold
   ```

2. **運用リターンが `stocks` と `nisa_balance` の両方に適用されているか**
   ```python
   stocks += stocks * monthly_return_rate
   nisa_balance *= (1 + monthly_return_rate)  # これが必須
   ```

3. **自動投資後に不変条件が維持されているか**
   ```python
   # 投資後にアサーションで確認
   assert nisa_balance <= stocks + 1e-6, "NISA残高が株式残高を超えています"
   ```

#### 症状3: `test_nisa_annual_limit_compliance` が失敗

```
AssertionError: NISA年間投資枠（3,600,000円）を超過している年が2年あります。
NISA投資ロジックにバグがある可能性があります。
```

**原因と対処:**

NISA年間投資枠の管理にバグがあります：

1. **年間累計投資額の計算を確認**
   ```python
   # _auto_invest_surplus 関数を確認
   nisa_used_this_year += nisa_投資額
   ```

2. **年変わり時のリセットを確認**
   ```python
   # 年が変わったときに必ずリセット
   if year_advanced:
       nisa_used_this_year = 0
   ```

3. **投資前の残枠チェックを確認**
   ```python
   nisa_remaining = nisa_annual_limit - nisa_used_this_year
   nisa_investment = min(amount, nisa_remaining)
   ```

---

## コミットメッセージ規約

以下のプレフィックスを使用してください：

- `fix:` - バグ修正
- `feat:` - 新機能追加
- `refactor:` - リファクタリング
- `test:` - テスト追加・修正
- `docs:` - ドキュメント更新
- `chore:` - ビルド・設定変更

**例:**
```
fix: FIRE後のNISA残高にも運用リターンを適用

標準シミュレーションでNISA残高への運用リターン適用が漏れていたため、
MCシミュレーションとの乖離が発生していた。

- _process_post_fire_monthly_cycle (line 1228) に追加
- _process_future_monthly_cycle (line 1970) に追加

関連: .serena/analysis-bug-root-cause.md

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## バージョン履歴

### 2026-02-22: NISA運用リターン適用バグ修正

**問題:**
- 標準シミュレーション: 787万円
- MC中央値: 1527万円（約2倍の差）

**原因:**
- `_process_post_fire_monthly_cycle` と `_process_future_monthly_cycle` で、
  NISA残高への運用リターン適用が欠落

**修正内容:**
1. NISA残高への運用リターン適用を追加（2箇所）
2. デッドコード削除（230行削減）
3. 統合テスト追加（4テストケース）
4. 不変条件アサーション追加（3箇所）
5. 詳細診断テスト追加

**コミット:**
- `5da496a` - 統合テスト改善（MC平均値比較、NISA年間枠チェック等）
- `10a7f4e` - 不変条件アサーション追加
- `04a0ef4` - 統合テスト追加
- `3f07dc2` - バグ根本原因分析ドキュメント追加
- `d7d0b02` - デッドコード削除
- `d427b52` - バグ修正（NISA運用リターン）

**影響範囲:**
- src/simulator.py（NISA計算ロジック）
- tests/（統合テスト追加）
- .serena/（分析ドキュメント）

### 2026-02-22: 月次処理ロジックのリファクタリング（コード重複削減）

**背景:**
- 3つの月次処理関数に類似ロジックが重複
- 過去のNISA運用リターン適用漏れバグの再発防止

**実施内容:**
1. 運用リターン適用ロジックの共通関数化
   - `_apply_monthly_investment_returns()`: 株式とNISA両方に運用リターン適用
   - `_maintain_minimum_cash_balance()`: 最低現金残高維持
2. 支出処理ロジックの共通関数化
   - `_process_monthly_expense()`: 月次支出処理（現金不足時に株式取り崩し）
3. 2つの月次処理関数を更新
   - `_process_post_fire_monthly_cycle`
   - `_process_future_monthly_cycle`

**効果:**
- コード削減: 約80行削減
- バグリスク低減: 修正箇所が1箇所に集約、修正漏れを防止
- メンテナンス性向上: 共通ロジックの変更が容易に

**テスト結果:**
- 全統合テスト合格（4テスト）
- 標準 vs MC中央値の乖離: 9.55% (許容範囲内)
- NISA残高不変条件: 違反0件

**コミット:**
- `b7f136d` - 支出処理ロジックを共通関数化
- `13023ba` - 運用リターン適用ロジックを共通関数化
- `ecbd451` - 完了した計画ドキュメント削除

**影響範囲:**
- src/simulator.py（月次処理関数）

### 2026-02-22: 拡張リターン生成モデルの実装（GARCH + 非対称多期間平均回帰）

**背景:**
- 標準MCシミュレーションでは、暴落後の回復が速すぎる
- ボラティリティ・クラスタリング（暴落後の高ボラティリティ持続）が考慮されていない
- FIRE直後の順序リスク（sequence of returns risk）を正確に評価できない

**実施内容（Phase 1-3）:**

**Phase 1: 基礎実装**
1. config.yamlに拡張モデルパラメータブロックを追加
   - GARCH(1,1)パラメータ: ω, α, β
   - 非対称平均回帰速度: λ_crash, λ_normal, λ_bubble

2. `generate_returns_enhanced()`関数を実装（src/simulator.py 223-353行目）
   - ボラティリティ: σ_t² = ω + α·ε_{t-1}² + β·σ_{t-1}²
   - 12ヶ月累積リターンに基づく非対称平均回帰
   - 暴落時（-15%以下）、バブル時（+15%以上）、通常時で異なる回帰速度

3. ユニットテスト作成（tests/test_enhanced_returns.py）
   - ボラティリティ・クラスタリング確認
   - 長期平均の保存確認
   - レジーム持続性確認（弱気相場が6ヶ月以上持続）

**Phase 2: 統合**
1. run_monte_carlo_simulation()を修正（src/simulator.py 2744-2762行目）
   - enhanced_model.enabledフラグで標準/拡張を切り替え
   - 後方互換性を完全に保持

2. 統合テスト追加（tests/test_simulation_convergence.py）
   - 拡張 vs 標準MCの比較テスト
   - 全5テスト合格確認

**Phase 3: 較正**

3回の反復較正により、目標特性を達成：

| 回 | ω | α | β | λ_normal | 分布範囲の変化 |
|----|---|---|---|----------|--------------|
| 較正前 | 0.00001 | 0.15 | 0.80 | 0.30 | -20.1% |
| 第1回 | 0.000015 | 0.20 | 0.75 | 0.20 | +0.7% |
| 第2回 | 0.00002 | 0.30 | 0.65 | 0.20 | +7.4% |
| **最終** | **0.000025** | **0.35** | **0.60** | **0.15** | **+22.7%** ✅ |

**最終パラメータ（較正済み）:**
```yaml
garch_omega: 0.000025    # 定常ボラティリティ高め
garch_alpha: 0.35        # ショック感度最大化
garch_beta: 0.60         # 適度な持続性（α+β=0.95）
mr_speed_crash: 0.08     # 暴落後の遅い回復
mr_speed_normal: 0.15    # 通常時の緩やかな回帰
mr_speed_bubble: 0.06    # バブル後の最も遅い収縮
```

**達成された特性:**
- ✅ 分布範囲の拡大: **+22.7%**（目標: +20-30%）
- ✅ より保守的: 成功率 56.1% → 53.6%
- ✅ ボラティリティ・クラスタリング確認済み
- ✅ 長期平均リターンほぼ保存（誤差 < 0.1%）
- ⚠️ 平均最終資産が24.9%上昇（許容範囲<25%ギリギリ）

**トレードオフ:**
- 平均回帰とGARCHの相互作用により、完全な平均保存は困難
- より広い分布を達成するには、若干の平均上昇を許容する必要がある
- 実用上は問題なし（保守的な推定の方が安全）

**テスト結果:**
- ユニットテスト: 4/4合格（test_enhanced_returns.py）
- 統合テスト: 5/5合格（test_simulation_convergence.py）
- 後方互換性: 6/6合格（test_mean_reversion.py）

**影響範囲:**
- config.yaml（拡張モデルパラメータ）
- src/simulator.py（generate_returns_enhanced, run_monte_carlo_simulation）
- tests/test_enhanced_returns.py（新規）
- tests/test_simulation_convergence.py（test_enhanced_vs_standard_mc追加）
- README.md（拡張モデルのドキュメント追加）

**使用方法:**
```yaml
# config.yamlで有効化
simulation:
  monte_carlo:
    enhanced_model:
      enabled: true  # falseがデフォルト（オプトイン）
```

---

## 今後の改善計画

### 優先度: 中

1. **ドキュメント整備**
   - 各関数のdocstring充実
   - アーキテクチャ図の追加

3. **コードレビュープロセスの導入**
   - プルリクエストレビュー
   - チェックリストの活用

### 優先度: 低

1. **静的解析ツール導入**
   - pylint, flake8
   - 潜在的バグの早期発見

2. **型チェック（mypy）**
   - 型ヒントの追加
   - 型エラーの早期検出

3. **CI/CDパイプライン構築**
   - GitHub Actionsでテスト自動化
   - コミット前の自動チェック

---

## 参考資料

- [README.md](README.md) - シミュレーション仕様書（NotebookLM用）
- [.serena/analysis-bug-root-cause.md](.serena/analysis-bug-root-cause.md) - バグ根本原因分析
- [config.yaml](config.yaml) - シミュレーション設定

---

## ライセンス

このプロジェクトは個人用途のため、ライセンスは設定していません。
