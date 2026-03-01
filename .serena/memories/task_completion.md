# タスク完了時のチェックリスト

## コード変更後（必須）

```bash
# 統合テストを実行（約2-3分）
python tests/test_simulation_convergence.py
```

**期待される出力:**
```
============================================================
全テスト合格 [OK]
============================================================
```

## 月次処理ロジックを変更した場合（追加チェック）

- [ ] NISA残高への運用リターン適用を忘れていないか？
  ```python
  stocks += stocks * monthly_return_rate
  nisa_balance *= (1 + monthly_return_rate)  # これも必須
  ```
- [ ] 類似処理が他の月次関数にも存在しないか？（`_process_post_fire_monthly_cycle`, `_process_future_monthly_cycle`）
- [ ] 不変条件アサーション `assert nisa_balance <= stocks` が維持されているか？

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
python tests/test_mc_standard_comparison.py
```

- **標準 vs MC中央値の乖離 > 10%** → NISA運用リターン適用漏れを疑う
- **NISA残高不変条件違反** → `_sell_stocks_with_tax` の NISA売却ロジックを確認
- **NISA年間枠超過** → `_auto_invest_surplus` の年変わりリセットを確認
