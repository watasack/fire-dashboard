# 次セッション開始プロンプト

---

## コピペ用プロンプト

```
FIREシミュレーターの UI 改善 Phase 3 を進めます。
まず @.plans/ui_redesign_status.md を読んで現状を把握してください。

## 前回までの完了事項

- Phase 1（構造整理）・Phase 2（クイック試算導線）完了
- Issue #16（低資産時 ValueError クラッシュ）・#17（plan_a 消失）修正済み
- 最新コミット: 542972f

## 今回やること：Phase 3 Block A（Step 1）

結果画面のヒーローカード直下に「次の一手」インサイトを追加します。

### 仕様

MCシミュレーション完了後（`_sim` in session_state かつ `not mc_res.get('impossible')`）、
ヒーローカードの直下に以下を表示する：

- `simulate_future_assets` を2ケース計算（軽量・決定論的）
  - ケース①: 支出 −3万円/月
  - ケース②: 月収 +10万円
- 現状の fire_month と比較し、短縮年数を表示
- 短縮幅が大きい方を「▲優先」ラベルでハイライト
- 「※確定論的概算（年金・教育費含む）」の注記を必須表示

### 制約

- 計算ロジック変更禁止（simulate_future_assets をそのまま流用）
- full_app.py のみ変更
- `_sim` には追加格納しない（サイドバー変数から monthly_income / monthly_expense を再構築）
- cfg の修正は `copy.deepcopy` してから行う

### 進め方

実装前に以下3点を確認してください：
1. デルタ値（支出-3万・収入+10万）はハードコードでよいか
2. 配置はヒーローカード直下か、別タブ「📊改善提案」か
3. FIRE未達成（fire_rows が空）の場合の fallback 表示はどうするか

確認後、段階的に実装してください。
```

---

## 補足メモ（作業担当者向け）

- Block A → Block B（3シナリオ比較）→ Block C（導線整理）の順で進める
- 各 Step 完了後に本番確認してからコミット・プッシュ
- UI 変更後は必ず Playwright テスト（`tests/test_ui_phase1.py`）を実行すること
- `session_state['_sim']` に新変数を追加した場合は `CLAUDE.md` の変数一覧も更新すること
