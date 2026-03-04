# よく使うコマンド

## メイン操作

```bash
# ダッシュボード生成（最もよく使う）
python scripts/generate_dashboard.py
# → dashboard/index.html に出力

# 年金受給年齢の最適化（config.yaml と dashboard/data/pareto_frontier.json を更新）
python scripts/optimize_pension.py

# FIRE達成時期の感度分析（収入・支出・リターンの変化影響を定量化）
python scripts/sensitivity_analysis.py

# 予算カテゴリ設定の検証（config.yaml 編集後に実行）
python scripts/validate_category_budgets.py
```

## テスト

```bash
# 統合テスト（コード変更後は必ず実行、約2-3分）
python -m tests.test_simulation_convergence

# 包括的テストスイート（169件、シミュレーション整合性全般）
python -m pytest tests/test_simulation_integrity.py -v

# MC vs 標準の詳細診断（乖離が大きい場合のデバッグ用）
python -m tests.test_mc_standard_comparison

# pytestで特定テスト実行
python -m pytest tests/test_category_expense.py -v
python -m pytest tests/test_category_dynamic_reduction.py -v
python -m pytest tests/test_unified_calculation.py -v
```

## Git

```bash
git status
git diff
git log --oneline -10
git add <file>
git commit -m "fix: ..."
```

## ユーティリティ（Windows）

```bash
ls <dir>      # ディレクトリ一覧
cat <file>    # ファイル内容表示
python --version
```

## 注意事項
- テストは `python tests/xxx.py` の直実行ではなく `python -m tests.xxx` で実行すること（`src` モジュール解決のため）
- `optimize_pension.py` は ProcessPoolExecutor を使うため、必ず .py ファイルから実行すること（`python -` stdin実行は不可）
- ダッシュボードはCDN経由でPlotly.jsを読み込むため、スクリーンショット取得時はネットワーク接続必要
