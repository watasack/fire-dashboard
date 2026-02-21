# 次セッション: 月次処理ロジックの共通化リファクタリング

## 背景と目的

### 現在の問題
FIREダッシュボードのシミュレーターには、月次処理を行う3つの関数があり、類似したロジックが重複しています：

1. **`_process_future_monthly_cycle`** (line 1844-2061)
   - FIRE前の月次処理
   - 収入計算、支出処理、運用リターン、自動投資を含む

2. **`_process_post_fire_monthly_cycle`** (line 1126-1258)
   - FIRE後の月次処理
   - 収入計算、支出処理、運用リターンを含む

3. **`_process_withdrawal_monthly_cycle`** (line 2185-2307)
   - 退職シミュレーション用の月次処理
   - 支出処理、運用リターンを含む

### 過去のバグ事例
2026-02-22に発生したNISA運用リターン適用漏れバグは、このコード重複が原因でした：
- 一部の関数のみ修正され、他の関数が見落とされた
- 標準シミュレーションとMCシミュレーションに約2倍の乖離が発生
- 詳細: [.serena/analysis-bug-root-cause.md](.serena/analysis-bug-root-cause.md)

### リファクタリングの目的
1. **コード重複の削減**: 共通ロジックを一箇所に集約
2. **バグリスクの低減**: 修正漏れを防ぐ
3. **メンテナンス性向上**: 変更が容易になる
4. **テストの網羅性向上**: 共通関数のテストで全体をカバー

---

## 実施すべきタスク

### フェーズ1: 現状分析（必須）

1. **3つの関数の詳細読み込み**
   ```bash
   # 以下の関数を全て読み込んで理解する
   - _process_future_monthly_cycle (line 1844-2061)
   - _process_post_fire_monthly_cycle (line 1126-1258)
   - _process_withdrawal_monthly_cycle (line 2185-2307)
   ```

2. **共通処理の特定**
   - 収入計算ロジック
   - 支出処理ロジック
   - 運用リターン適用ロジック
   - 株式売却ロジック
   - 最低現金残高維持ロジック
   - 自動投資ロジック（FIRE前のみ）

3. **差分の明確化**
   - FIRE前特有の処理
   - FIRE後特有の処理
   - 退職シミュレーション特有の処理

### フェーズ2: 共通関数の設計

1. **関数インターフェース設計**
   ```python
   def _apply_monthly_investment_returns(
       stocks: float,
       nisa_balance: float,
       monthly_return_rate: float
   ) -> Dict[str, float]:
       """
       月次運用リターンを適用（株式とNISA両方）

       重要: この関数は3つの月次処理関数から呼び出される
       """
       pass
   ```

2. **共通化する処理の候補**
   - 運用リターン適用
   - 株式売却（NISA優先）
   - 最低現金残高維持
   - 年変わり処理

### フェーズ3: 段階的リファクタリング

1. **最も安全な処理から開始**
   - まず運用リターン適用ロジックを共通化
   - 不変条件アサーションを含める

2. **各関数を順次更新**
   - `_process_post_fire_monthly_cycle` から開始（最もシンプル）
   - `_process_future_monthly_cycle` に適用
   - `_process_withdrawal_monthly_cycle` に適用

3. **各ステップでテスト実行**
   ```bash
   python tests/test_simulation_convergence.py
   ```

### フェーズ4: テストと検証

1. **統合テスト実行**
   - 全4テストが合格することを確認
   - 特に `test_standard_vs_monte_carlo_convergence` に注目

2. **ダッシュボード生成確認**
   ```bash
   python scripts/generate_dashboard.py
   ```

3. **詳細診断実行**
   ```bash
   python tests/test_mc_standard_comparison.py
   ```

---

## 重要な注意点

### ⚠️ CRITICAL: NISA残高への運用リターン適用

**絶対に忘れてはいけない処理:**
```python
# 運用リターン（株式とNISA両方に適用）
stocks += stocks * monthly_return_rate
nisa_balance *= (1 + monthly_return_rate)  # ← これを忘れると2倍の乖離が発生！

# 不変条件チェック
assert nisa_balance <= stocks + 1e-6, "NISA残高が株式残高を超えています"
```

### 影響範囲が大きい変更
- 3つの主要関数を修正するため、バグのリスクが高い
- **必ず小さなステップで進め、各ステップでテストを実行すること**

### テストが失敗した場合
1. まずバックアップから復元を検討
2. `test_mc_standard_comparison.py` で詳細診断
3. FIRE達成時点が一致しているか確認
4. NISA残高への運用リターン適用を確認

### コミット戦略
- 各フェーズごとにコミット
- テスト合格を確認してからコミット
- コミットメッセージに影響範囲を明記

---

## 成功基準

### 必須条件
- [ ] 全ての統合テストが合格（4テスト）
- [ ] 標準 vs MC中央値の乖離が10%以内
- [ ] NISA残高の不変条件が全期間で維持
- [ ] ダッシュボードが正常に生成される

### 推奨条件
- [ ] コード行数が10%以上削減される
- [ ] 共通関数に明確なdocstringとアサーションがある
- [ ] リファクタリング前後で結果が完全に一致する

---

## 参考情報

### ドキュメント
- [DEVELOPMENT.md](../DEVELOPMENT.md) - 開発ガイドライン
- [.serena/analysis-bug-root-cause.md](../.serena/analysis-bug-root-cause.md) - バグ分析

### 関連ファイル
- `src/simulator.py` - 対象ファイル（2300行超）
- `tests/test_simulation_convergence.py` - 統合テスト
- `tests/test_mc_standard_comparison.py` - 詳細診断

### 過去のコミット参考
```bash
# NISA運用リターンバグ修正
git show d427b52

# 不変条件アサーション追加
git show 10a7f4e

# デッドコード削除
git show d7d0b02
```

---

## 開始時の指示プロンプト例

```
私はFIREダッシュボードプロジェクトのリファクタリングを行います。

目的: 月次処理ロジックの共通化によるバグリスク削減

背景:
- 3つの月次処理関数に類似ロジックが重複している
- 過去にNISA運用リターン適用漏れバグが発生（一部関数のみ修正）
- コード重複を削減し、メンテナンス性を向上させたい

実施計画:
1. 3つの関数を読み込み、共通処理を特定
2. 運用リターン適用ロジックを共通関数化
3. 段階的に各関数を更新
4. 各ステップでテスト実行・検証

重要な制約:
- NISA残高への運用リターン適用を絶対に忘れない
- 小さなステップで進め、各ステップでテストを実行
- テスト合格を確認してからコミット

参考資料: .plans/next-session-refactoring.md を読んでください

準備ができたら、フェーズ1（現状分析）から開始してください。
```

---

## チェックリスト

リファクタリング開始前:
- [ ] このドキュメントを全て読んだ
- [ ] DEVELOPMENT.mdを読んだ
- [ ] .serena/analysis-bug-root-cause.md を読んだ
- [ ] テストが現在全て合格することを確認した
- [ ] バックアップブランチを作成した（推奨）

リファクタリング中:
- [ ] 各ステップでテストを実行している
- [ ] NISA残高への運用リターン適用を確認した
- [ ] 不変条件アサーションを維持している
- [ ] コミットメッセージに影響範囲を記載している

リファクタリング完了後:
- [ ] 全テストが合格した
- [ ] ダッシュボードが正常に生成される
- [ ] 詳細診断で異常がない
- [ ] コードレビュー（セルフチェック）を実施した
