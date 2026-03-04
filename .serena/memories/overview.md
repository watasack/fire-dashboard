# プロジェクト概要

## 目的
個人のFIRE（経済的自立・早期退職）達成時期をシミュレートするダッシュボードツール。
家族構成（修平・桜・颯・楓）に特化したパラメータで月次シミュレーションを実行し、
`dashboard/index.html` にインタラクティブなHTMLダッシュボードを生成する。

## 技術スタック
- **言語**: Python 3.x
- **主要ライブラリ**: pandas, numpy, plotly
- **設定**: config.yaml（全パラメータ一元管理）
- **OS**: Windows 11

## プロジェクト構造
```
config.yaml          # シミュレーション設定（唯一の設定ファイル）
src/
  simulator.py       # シミュレーションエンジン本体（最重要・最大ファイル）
  pension_optimizer.py  # FIRE時期最適化（決定論的Phase 2、ProcessPoolExecutor並列）
  config_schema.py   # Pydanticスキーマによるconfig.yaml厳密バリデーション
  data_loader.py     # CSVデータ読み込み
  data_processor.py  # データ前処理
  analyzer.py        # 現状分析（現在資産・収支トレンド）
  data_schema.py     # データスキーマ定義
  visualizer.py      # Plotlyグラフ生成
  html_generator.py  # HTMLダッシュボード組み立て
scripts/
  generate_dashboard.py   # メインエントリポイント（ダッシュボード生成）
  optimize_pension.py     # FIRE時期最適化 → pareto_frontier.json + config.yaml更新
  sensitivity_analysis.py # FIRE達成時期の感度分析
  validate_category_budgets.py  # 予算カテゴリ設定検証
tests/
  test_simulation_convergence.py  # 統合テスト（主要）
  test_simulation_integrity.py    # 包括的テストスイート（169件）
  test_mc_standard_comparison.py  # MC vs 標準の詳細診断
  test_unified_calculation.py     # FIRE前後の統一計算ロジック検証
  test_post_fire_cash_strategy.py # FIRE後現金管理戦略テスト
  + その他カテゴリ・動的削減・年金等のテストファイル
data/                # 実績CSVデータ（コードではない、検索対象外）
dashboard/
  index.html         # 生成済みHTML
  data/pareto_frontier.json  # 最適化結果（optimize_pension.py が出力）
.serena/memories/    # このメモリファイル群
```

## コアドメイン知識
- **月次処理順序**: 年変わりチェック→収入→支出→株式リターン→自動投資→FIREチェック
- **NISA残高の不変条件**: `nisa_balance <= stocks` 常に成立必須
- **FIRE判定**: 「今退職すれば90歳まで資産が持つか」を毎月チェック
- **MCシミュレーション**: 1000回, 年率リターン正規分布N(期待リターン, 6%²), AR平均回帰
- **動的支出削減**: ドローダウン監視で3段階削減（-10%, -20%, -35%でL1/L2/L3）
- **拡張GARCHモデル**: `enhanced_model.enabled: true` でオプトイン
