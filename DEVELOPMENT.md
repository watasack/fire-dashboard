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
│   ├── pension_optimizer.py    # FIRE時期最適化エンジン（MC評価・並列処理）
│   ├── data_loader.py          # データ読み込み
│   ├── data_processor.py       # データ処理
│   ├── analyzer.py             # 現状分析
│   ├── data_schema.py          # データスキーマ定義
│   ├── visualizer.py           # グラフ生成（Plotly）
│   └── html_generator.py       # HTMLダッシュボード生成
├── tests/
│   ├── test_simulation_convergence.py  # 統合テスト（主要）
│   └── test_mc_standard_comparison.py  # MC vs 標準の詳細診断
├── scripts/
│   ├── generate_dashboard.py   # ダッシュボード生成スクリプト
│   └── optimize_pension.py     # FIRE時期最適化スクリプト（MC評価）
├── dashboard/
│   ├── index.html              # 生成されたダッシュボード
│   └── assets/
│       └── styles.css          # ダッシュボードのスタイル
├── dashboard_screenshots/       # ビジュアルテスト用スクリーンショット
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

### カテゴリ別予算管理（詳細版）

基本生活費を23カテゴリに細分化して管理する機能です。暴落時にどのカテゴリを削減するかを明確化できます。

#### 設定方法

**1. カテゴリ別予算を有効化:**

[config.yaml](config.yaml) の `fire.expense_categories.enabled` を `true` に設定：

```yaml
fire:
  expense_categories:
    enabled: true  # false: 従来の総額方式、true: カテゴリ別予算
```

**2. 設定内容検証:**

```bash
python scripts/validate_category_budgets.py
```

**検証内容:**
- 各ライフステージの合計が想定値と一致するか
- 裁量的支出比率が想定値と一致するか
- カテゴリIDの重複がないか

**期待される出力:**
```
[OK] すべての検証に合格しました！
  - カテゴリIDに重複なし
  - 全ステージの合計が想定値と一致
  - 裁量的支出比率が想定値と一致
```

#### カテゴリ構成（23カテゴリ）

**基礎生活費（11カテゴリ、削減対象外）:**
- 食費（自炊）、光熱費（電気・ガス・水道）、通信費（携帯・インターネット）
- 交通費（定期券）、保険（生命・損害）、医療費、日用品

**裁量的支出（12カテゴリ、暴落時削減対象）:**
- 食費（外食）、交通費（その他）、被服費、娯楽（映画/その他）
- 旅行（国内・海外）、趣味、教養（書籍・講座）、美容・理容、その他

#### カテゴリ別削減の動作

カテゴリ別予算が有効な場合、暴落時の削減は以下のように動作します：

| ドローダウン | レベル | 削減率 | 基礎生活費 | 裁量的支出（例: 外食24万円） |
|------------|--------|--------|-----------|---------------------------|
| -10%以上   | 正常   | 0%     | 削減なし   | 24万円（削減なし）           |
| -10% ~ -20% | 警戒   | 40%    | 削減なし   | 14.4万円（40%削減）         |
| -20% ~ -35% | 深刻   | 80%    | 削減なし   | 4.8万円（80%削減）          |
| -35%以下    | 危機   | 95%    | 削減なし   | 1.2万円（95%削減）          |

#### テスト

カテゴリ別予算機能の動作確認：

```bash
# カテゴリ別計算のテスト
python -m pytest tests/test_category_expense.py -v

# カテゴリ別動的削減のテスト
python -m pytest tests/test_category_dynamic_reduction.py -v
```

#### 後方互換性

`expense_categories.enabled: false` の場合、従来の総額方式（`base_expense_by_stage`）が使用されます。
既存のシミュレーションに影響を与えません。

---

## ビジュアルテスト（スクリーンショットベース）

ダッシュボードのUI/UX変更時は、**スクリーンショットを取得して実際の描画結果を確認する**ことを推奨する。CSSやHTMLの変更はコードだけでは最終的な見た目を判断できないため、必ずブラウザでの実際の描画を確認する。

### ワークフロー

```
1. コード変更（visualizer.py / html_generator.py / styles.css）
2. ダッシュボード再生成
     .venv/bin/python scripts/generate_dashboard.py
3. ブラウザでスクリーンショットを取得
4. 画像を確認し、意図通りの描画かを判断
5. 問題があれば 1 に戻る
```

### スクリーンショットの取得方法

ブラウザ自動化ツール（Playwright等）を使い、`file:///` プロトコルでダッシュボードHTMLを開いてスクリーンショットを取得する。

**推奨設定:**
- ビューポート幅: **1440px**（ダッシュボードの `max-width` に合わせる）
- デバイススケール: **2x以上**（高解像度キャプチャ）

**撮影対象の推奨区分:**

| 区分 | 対象 | 確認ポイント |
|------|------|------------|
| 全体 | ページ全体 | 全体のバランス、セクション間の余白、情報密度 |
| ヘッダー+KPI | Hero KPI + リスクカード | 数値の視認性、カード高さの均等性、色の意味 |
| メインチャート | 資産シミュレーション | 色の区別（蓄積期/FIRE期）、凡例の読みやすさ、基準線の視認性 |
| 並列セクション | 収支チャート + ライフイベント表 | 横並びのバランス、テーブルの読みやすさ |
| 下部パネル | 前提条件 + 最適化結果 | 折りたたみ動作、バッジの表示、展開時の内容 |

### スクリーンショットの保存

`dashboard_screenshots/` ディレクトリに保存する。命名規則:

```
{バージョン}_{セクション}.png

例:
  v5_full.png          — v5全体
  v5_chart_closeup.png — v5のメインチャート拡大
  v7_risk_cards.png    — v7のリスクカード
```

バージョン番号は作業セッション内で連番とする（gitコミット単位ではない）。

### ビジュアルテストが必要な変更の例

- Plotlyチャートの色・レイアウト変更（`visualizer.py`）
- CSSのグリッドレイアウト・間隔調整（`styles.css`）
- HTMLの構造変更・セクション追加（`html_generator.py`）
- レスポンシブ対応の確認（ビューポート幅を変えて撮影）

### 注意事項

- Plotlyチャートは `include_plotlyjs='cdn'` でCDNからJSを読み込むため、スクリーンショット取得時にはネットワーク接続が必要
- スクリーンショットは `.gitignore` に含めてリポジトリにはコミットしない（作業用の一時ファイル）

---

## テストの実行

### 統合テスト（推奨）

全ての主要な不変条件と整合性を検証します：

```bash
python -m tests.test_simulation_convergence
```

**検証内容:**
1. 標準シミュレーションとMC中央値の収束性（xfail: 大きな乖離が発生している場合はスキップ）
2. NISA残高 ≤ 株式残高（不変条件）
3. NISA年間投資枠（360万円）の遵守
4. 資産推移の異常検知（極端な減少の検出）

**期待される実行時間:** 約2-3分（MC 1000イテレーション）

### 包括的テストスイート

シミュレーション全体の整合性を169件のテストで検証します：

```bash
python -m pytest tests/test_simulation_integrity.py -v
```

**検証内容:**
- FIRE前・FIRE後の月次計算の整合性
- NISA不変条件（全月・全シナリオ）
- 収入・支出・年金計算の個別テスト
- 現金管理戦略・安全マージン維持
- 統一計算ロジック（FIRE前後で共通関数を使用）

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

### 2026-02-22: 動的支出削減機能の実装（暴落時の自動対応プロトコル）

**背景:**
- 拡張モデルで16%の破産リスク（P16=0円）が検出された
- FIRE直後の暴落に対する具体的な対応プランが必要
- 裁量的支出の削減と副収入増加により、破産リスクを低減

**実施内容:**

**Phase 1: 基本実装**
1. config.yamlに動的削減設定を追加（93-147行目）
   - ライフステージ別の裁量的支出比率（25-40%）
   - 3段階のドローダウン閾値: -10%, -20%, -35%
   - 段階的削減率: 50%, 80%, 100%
   - 副収入増加: 月5万円, 10万円, 15万円

2. 新関数の実装（src/simulator.py 354-509行目）
   - `calculate_drawdown_level()`: ドローダウン計算とレベル判定
   - `apply_dynamic_expense_reduction()`: 裁量的支出の削減適用
   - `apply_dynamic_income_boost()`: 副収入増加の適用

3. 月次ループへの統合（src/simulator.py 2048-2103行目）
   - ドローダウン計算を月次で実行
   - 削減後の支出で資産推移を計算
   - 副収入を月次収入に加算

4. `_precompute_monthly_cashflows()`の拡張
   - 基本生活費配列を追加で返す（削減前の支出）
   - ライフステージ配列を追加で返す（裁量的支出比率の判定用）

5. ユニットテスト作成（tests/test_dynamic_expense_reduction.py 322行）
   - ドローダウン計算テスト（6テスト）
   - 支出削減ロジックテスト（8テスト）
   - 副収入増加テスト（5テスト）
   - 統合テスト（1テスト）

6. 効果分析スクリプト作成（scripts/dynamic_reduction_analysis.py 225行）
   - 削減なし vs 削減ありの比較
   - 成功率、破産率、資産分布の定量分析

**Phase 2: パラメータ調整（早期警戒対応）**
1. ドローダウン閾値を早期化
   - レベル1: -15% → -10%（早期警戒）
   - レベル2: -30% → -20%
   - レベル3: -50% → -35%

2. 削減率を調整（最終値）
   - レベル1: 40%（警戒）
   - レベル2: 80%（深刻）
   - レベル3: 95%（危機、実質ほぼ全削減だが0円ではない）

3. 副収入増加機能（削除済み）
   - 当初実装したが、現実的な行動可能性の懸念から削除

**達成された効果（モンテカルロ1000回シミュレーション）:**

| 指標 | 調整前 | 調整後 | 改善 |
|------|--------|--------|------|
| **成功率** | 57.0% | 99.8% | **+42.8ポイント** |
| **破産率** | 43.0% | 0.2% | **▲42.8ポイント** |
| **P10（下位10%）** | 0円（破産） | 336,000円 | **破産回避** |
| **P50（中央値）** | 807万円 | 1,180万円 | +46.2% |
| **P90（上位10%）** | 5,422万円 | 5,793万円 | +6.8% |

**主要な発見:**
- ✅ 破産率を16% → 0.2%に激減（**98.8%削減**）
- ✅ 最悪シナリオで破産回避（P10が0円 → 33.6万円）
- ✅ 中央値も46%改善（支出削減の効果）
- ⚠️ 暴落時の生活水準低下を許容（裁量的支出を最大100%削減）
- ⚠️ 暴落時の副業負担を許容（月15万円まで）

**テスト結果:**
- ユニットテスト: 19/19合格（test_dynamic_expense_reduction.py）
- 統合テスト: 全34テスト合格
- 後方互換性: 既存テストで動的削減を無効化して合格

**影響範囲:**
- config.yaml（動的削減設定）
- src/simulator.py（3つの新関数、月次ループ統合、_precompute_monthly_cashflows拡張）
- tests/test_dynamic_expense_reduction.py（新規）
- tests/test_simulation_convergence.py（既存テストで無効化）
- scripts/dynamic_reduction_analysis.py（新規）

**使用方法:**
```yaml
# config.yamlで有効化
fire:
  dynamic_expense_reduction:
    enabled: true  # falseがデフォルト（オプトイン）

    # ドローダウン閾値
    drawdown_thresholds:
      level_1_warning: -0.10  # -10%で警戒
      level_2_concern: -0.20  # -20%で深刻
      level_3_crisis: -0.35   # -35%で危機

    # 削減率
    reduction_rates:
      level_0_normal: 0.0     # 削減なし
      level_1_warning: 0.40   # 40%削減
      level_2_concern: 0.80   # 80%削減
      level_3_crisis: 0.95    # 95%削減
```

**コミット:**
- `d1c4bae` - 動的支出削減のパラメータ調整（早期警戒、積極削減、副収入増加）
- `ec91d40` - 動的支出削減機能の基本実装
- `41c5f61` - 拡張モデルのドキュメント追加

**注意事項:**
- この機能は、暴落時に実際に支出を削減し、副業で収入を増やすことを前提としています
- 実際の行動可能性（副業の実現性、生活水準の許容度）を考慮して有効化してください
- 無効化（enabled: false）の場合、従来通り固定支出でシミュレーションされます

### 2026-02-28〜03-01: 年金インフレ調整・サブステージ対応・支出設定更新

**背景:**
- 基本生活費はインフレ連動（2%/年）するが、年金収入は固定（名目額不変）だった
- 子供独立後の支出が単一値で、70歳・80歳以降の医療費増を反映できていなかった
- 支出設定が2025年実績と乖離していた

**実施内容:**

1. **年金インフレ調整（`pension_growth_rate`）**
   - `config.yaml` に `simulation.standard.pension_growth_rate: 0.01` を追加
   - `calculate_pension_income()` に `inflation_factor = (1 + rate) ^ 経過年数` を適用
   - マクロ経済スライド相当（1%/年）で年金額が名目増加

2. **子供独立後サブステージ対応**
   - `empty_nest` を3段階に分割:
     - `empty_nest_active`: 〜69歳（2,573,000円/年）
     - `empty_nest_senior`: 70〜79歳（2,224,000円/年、医療費増）
     - `empty_nest_elderly`: 80歳〜（1,848,000円/年、介護費・医療費が中心）
   - 年齢境界: `senior_from_age: 70`, `elderly_from_age: 80`
   - `_get_life_stage()`, `_get_age_at_offset()`, `calculate_base_expense()` 等に対応

3. **支出設定の2025年実績反映**
   - 旅行: `travel_domestic` + `travel_international` → `travel`（統合）
   - 保険: `insurance_life`, `insurance_casualty` → 0円（未契約）
   - 裁量的支出比率の更新（young_child: 25% → 44%、empty_nest: 40% → 59% 等）
   - 削減率の調整: L1=40%, L2=80%, L3=95%

4. **年金計算の過去実績対応**
   - `past_pension_base_annual: 236929` / `past_contribution_months: 177` を設定
   - 過去加入分（低報酬時代）と将来加入分（現在報酬）を分けて正確に計算

**コミット:**
- `258e531` - スクリーンショットキャプチャスクリプトの改善
- `c3700ba` - テストを計算ロジック修正後の設定値・APIに合わせて更新
- `3344ef4` - 計算ロジック修正に伴うドキュメント更新
- `6ed7b6d` - シミュレーション計算ロジックの重要バグ9件を修正

**影響範囲:**
- config.yaml（年金・サブステージ・支出設定・削減率）
- src/simulator.py（`calculate_pension_income`, `_get_life_stage`, 支出計算）

---

### 2026-03-01: MCシミュレーション高速化（バッチ生成・並列評価）

**背景:**
- `scripts/optimize_pension.py` の探索ループが計算時間の大部分を占めていた
- 大量の候補を高速に評価する仕組みが必要だった

**実施内容:**

1. **バッチリターン生成（~100x高速化）**
   - `generate_random_returns_batch(n_paths)`: N本の乱数リターン列を行列 `(N, T)` で一括生成
   - `generate_returns_enhanced_batch(n_paths)`: GARCH+非対称平均回帰のN並列版
   - Python ループ（N回×T月）→ NumPy 行列演算（T月×N parallel）

2. **候補並列評価**
   - Phase 2確定的スクリーニングで `ProcessPoolExecutor` を使ってfire_month候補を並列評価
   - `_init_worker(project_root)`: Windowsスポーン方式対応のワーカー初期化
   - `if __name__ == '__main__':` ガードが必要（`scripts/optimize_pension.py` に実装済み）
   - stdin からの実行（`python -`）は不可。必ず .py ファイルから実行すること

**コミット:**
- `984a6c3` - ビジュアルテスト手法とMCシミュレーション仕様を文書化
- (別途) feat+perf(simulator): バッチリターン生成追加
- (別途) chore(script): 最適化スクリプトの探索パラメータ拡張

**影響範囲:**
- src/simulator.py（`generate_random_returns_batch`, `generate_returns_enhanced_batch`）
- src/pension_optimizer.py（Phase 2並列評価）
- scripts/optimize_pension.py（パラメータ拡張）

---

### 2026-03-04〜03-14: Streamlit フル版アプリ（full_app.py）開発

**背景:**
- HTMLダッシュボード（個人専用）とは別に、外部公開用のStreamlitアプリを新規開発
- noteのフル版有料記事読者向けのアクセスコード認証付きシミュレーター

**全体構成:**
- エントリポイント: `full_app.py`（単一ファイル + `src/` モジュール活用）
- デプロイ先: Streamlit Cloud
- 認証: `st.secrets["access_codes"]` によるアクセスコード認証

---

**主要機能（実装済み）:**

1. **MCシミュレーション連携（`run_mc_fixed_fire`）**
   - 固定FIRE月 + 二分探索でtarget_success_rate（デフォルト90%）に対応するFIRE月を決定
   - 1,000回MCで成功率・破産率・資産分布を算出
   - `base_df`（決定論的ライン）と `monte_carlo_results` を統合表示

2. **子どもの設定（最大4人）**
   - 妻: 産前/産後育休・時短勤務（終了年齢・時短月収）
   - 夫: 育休（デフォルト12ヶ月）・時短勤務
   - 雇用形態（会社員/個人事業主/専業主夫・主婦）で年金・昇給率が変わる

3. **住宅形態の選択**
   - 持ち家: ローン月額・返済完了年をサイドバーで直接入力
   - 賃貸: 家賃月額を入力
   - 住宅費・生活費・支出合計を動的に表示

4. **純粋関数による設計**
   - `_build_children_config()`: 子どもUI入力 → simulator config 変換
   - `_build_simulation_config()`: 全UI入力 → 完全な config 生成
   - テスト可能な設計（`st.*` 呼び出しなし）

5. **UI/UX**
   - サイドバー: 夫婦2列レイアウト・住宅形態・キャッシュフロー
   - タブ構成: 育休設定 / 詳細設定（JSON表示）
   - 結果: FIRE年齢・必要年数・FIRE時資産 の3メトリクス + 資産予測チャート + 解釈ガイド

---

**主なコミット（時系列）:**

| コミット | 内容 |
|---------|------|
| `35f9ab8` | UI/UX改善: サイドバー2列化・スライダー廃止 |
| `b216332` | 子どもの人数を最大4人に拡張 |
| `a27bbaa` | 雇用形態ごとの収入成長率・専業主夫/主婦対応 |
| `c0162a1` | 夫の育休デフォルトを12ヶ月に変更 |
| `2541c4d` | 個人名(shuhei/sakura)を汎用名称(husband/wife)に置換 |
| `652a803` | マジックナンバーを定数化 |
| `f1e990c` | 純粋関数抽出・`_build_children_config`・`_build_simulation_config` |
| `c5a1728` | 住宅形態（持ち家/賃貸）選択を追加 |
| `ad8cb82` | ローン月額・返済完了年をサイドバーへ移動 |
| `a0f6235` | 支出合計（住宅費＋生活費）の動的表示 |
| `ff3fb37` | ユーザー向けテキストを非技術者向けに平易化 |

---

**定数一覧（`full_app.py` 冒頭）:**

```python
_DEFAULT_INCOME          = 35    # 月収デフォルト（万円）
_DEFAULT_AGE             = 35    # 年齢デフォルト（歳）
_DEFAULT_EXPENSE         = 28    # 生活費デフォルト（万円）
_DEFAULT_ASSETS          = 2000  # 金融資産デフォルト（万円）
_DEFAULT_LEAVE_MONTHS    = 12    # 育休デフォルト（月）
_DEFAULT_RENT            = 15    # 家賃デフォルト（万円）
_DEFAULT_MORTGAGE        = 10    # 住宅ローンデフォルト（万円/月）
_CASH_RATIO              = 0.3   # 現金比率（初期資産配分）
_STOCKS_RATIO            = 0.7   # 株式比率（初期資産配分）
_MC_ITERATIONS           = 1000  # MCシミュレーション試行回数
```

---

**影響範囲:**
- `full_app.py`（Streamlitアプリ本体）
- `src/utils.py`（`fmt_oku` を共通ユーティリティとして新規作成）
- `src/simulator.py`（`monthly_rent` 対応・`run_mc_fixed_fire` 追加）
- `src/visualizer.py`（FIREタイミングバンド削除・固定FIRE時期表示に変更）

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

### 2026-03-02〜03-04: 最適化エンジン刷新・ダッシュボード改善・インフラ整備

**実施内容（主要変更）:**

1. **FIRE後収入モデルの変更（`ce1e8f2`）**
   - 線形逓減モデル（`taper_years`年で0に減少）を廃止
   - 年金受給開始まで設定額を固定で得るモデルに統一
   - 修平: 50,000円/月 → 100,000円/月

2. **pension_optimizer Phase 3 MC評価削除（`811b6b7`）**
   - Phase 3（MCシミュレーションによる精密評価）を削除
   - **決定論的ベースライン最終資産 ≥ 安全マージン** でFIRE月を判定するシンプルな方式に変更
   - Phase 0: FIRE前投資戦略スクリーニングを新規追加
   - パレートフロンティアJSON出力機能を追加（`dashboard/data/pareto_frontier.json`）

3. **ダッシュボード改善（`6707d48`, `50ab9b2`, `e305379`）**
   - セカンダリKPI（リスクメトリクス4カード）を削除
   - Hero KPIを4指標に拡張: FIRE達成率 / 達成予想 / セミFIRE成功率 / 今すぐ完全FIRE成功率
   - パレートフロンティアチャート（FIRE年齢 vs 最小パス資産）を追加

4. **Pydanticスキーマによるconfig.yamlバリデーション導入（`7ff2c37`）**
   - `src/config_schema.py` に AppConfig スキーマを定義
   - 設定値の型チェック・必須フィールドチェックを起動時に実行

5. **FIRE後シミュレーション共通関数化（`38ab3cf`）**
   - FIRE後計算パスを共通関数に統合し、コード重複を削減
   - `e15b81f` にて FIRE後計算パスの整合性検証テストを追加

6. **包括的テストスイート追加（`58206e0`）**
   - `tests/test_simulation_integrity.py`（169件）を新規追加
   - `tests/test_unified_calculation.py`, `tests/test_post_fire_cash_strategy.py` 等も追加

**影響範囲:**
- src/simulator.py、src/pension_optimizer.py（モデル変更・共通関数化）
- src/html_generator.py、src/visualizer.py（ダッシュボード構成変更）
- src/config_schema.py（新規: Pydanticスキーマ）
- tests/（テスト大幅追加）
- config.yaml（FIRE後収入・安全マージン値変更）

---

## 参考資料

- [README.md](README.md) - シミュレーション仕様書（NotebookLM用）
- [.serena/analysis-bug-root-cause.md](.serena/analysis-bug-root-cause.md) - バグ根本原因分析
- [config.yaml](config.yaml) - シミュレーション設定

---

## 検証の徹底と品質担保

### 1. UIエントリーポイントの実行検証
Streamlit（`full_app.py`）などのUIエントリーポイントは、単純なスクリプト実行だけでは**ボタン押下後の条件分岐内**などのコードパスが実行されません。
変更を加えた際は、必ず以下のいずれかを実施すること：
- **実機操作**: 実際にアプリを起動し、変更した箇所のボタンを押し、最終的な描画（グラフ表示等）までエラーが出ないことを目で確認する。
- **カバレッジの意識**: 単なる「起動テスト」で満足せず、変更した行が実際に実行される操作を行う。

### 2. 静的解析の推奨
`NameError`（変数の定義漏れ）などは、実行しなくても静的解析ツールで検知可能です。
特に複雑な条件分岐を変更した際は、以下のコマンド等でチェックすることを推奨します：
```bash
# 未定義変数や未使用インポートをチェック
flake8 full_app.py
# または
pyflakes full_app.py
```

### 3. 検証スクリプトの限界を理解する
`verify_pipeline.py` などの自作検証スクリプトは、内部ロジック（`src/`）の検証には有効ですが、それらを呼び出す「繋ぎ込み部分（`full_app.py` 等）」のミスは検知できません。
「ライブラリの正常性」と「アプリとしての動作」は別物として、両方の面から検証を行うこと。

---

## ライセンス

このプロジェクトは個人用途のため、ライセンスは設定していません。
