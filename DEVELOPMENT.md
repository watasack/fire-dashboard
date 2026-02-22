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
