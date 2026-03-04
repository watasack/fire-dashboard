# タスク完了時のチェックリスト

## コード変更後（必須）

```bash
# 統合テストを実行（約2-3分）
python -m tests.test_simulation_convergence
```

**期待される出力:**
```
============================================================
全テスト合格 [OK]
============================================================
```

※ 標準 vs MC中央値の収束テストは `[XFAIL]` になっている場合があります（既知の乖離）。
   `[ERROR]` が出た場合はCSVファイルのエンコーディングやパスを確認してください。

## 月次処理ロジックを変更した場合（追加チェック）

- [ ] NISA残高への運用リターン適用を忘れていないか？
  ```python
  stocks += stocks * monthly_return_rate
  nisa_balance *= (1 + monthly_return_rate)  # これも必須
  ```
- [ ] 類似処理が他の月次関数にも存在しないか？（`_process_post_fire_monthly_cycle`, `_process_future_monthly_cycle`）
- [ ] 不変条件アサーション `assert nisa_balance <= stocks` が維持されているか？
- [ ] FIRE前後で共通化された計算関数（`_apply_monthly_investment_returns`, `_process_monthly_expense`）を使っているか？

## config.yaml を変更した場合

```bash
# カテゴリ予算が変わった場合
python scripts/validate_category_budgets.py

# ダッシュボードを最新化
python scripts/generate_dashboard.py
```

## テスト失敗時の診断

```bash
# 詳細診断
python -m tests.test_mc_standard_comparison

# 包括的テスト（FIRE前後の整合性確認）
python -m pytest tests/test_simulation_integrity.py -v
```

- **標準 vs MC中央値の乖離 > 10%** → NISA運用リターン適用漏れを疑う
- **NISA残高不変条件違反** → `_sell_stocks_with_tax` の NISA売却ロジックを確認
- **NISA年間枠超過** → `_auto_invest_surplus` の年変わりリセットを確認
