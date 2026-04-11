# サービス開始チェックリスト

最終更新: 2026-04-11

関連ドキュメント:
- [monetization_strategy.md](./monetization_strategy.md) — 全体戦略
- [access-code-auth.md](./access-code-auth.md) — 認証の技術設計

---

## 残タスク一覧

### B. コンテンツ準備

- [ ] **B-1. スクリーンショット撮影**
  - ケース別3パターン（育休なし / 妻のみ育休 / 夫婦育休）
  - ツール全体（`result_top.png` / `full_page.png` / `mobile_top.png` / `mobile_chart.png`）
  - 記事内の `<!-- 📷 -->` コメント位置に対応

- [ ] **B-2. サムネイル画像作成**
  - note記事4本分のサムネイル
  - 方法: Canva or ツールスクショ加工

- [ ] **B-3. note記事のプレースホルダー埋め込み（残り）**
  - `note_article_draft.md` の `[note有料記事URL]` → 販売記事のnote URL（B-4で確定）
  - `note_sales_article.md` の `[育休×FIRE記事URL]` → article_draftのnote URL（B-4で確定）
  - `note_sales_article.md` の `○○○円` → 販売価格（¥980想定）

- [ ] **B-4. note有料記事の設定・公開**
  - 価格設定: ローンチ価格 ¥980（5件売れたら ¥1,980 に値上げ）
  - 有料エリアの境界線設定
  - 有料部分に共通アクセスコードとフル版URLを記載
  - 公開順（同日に投稿）:
    1. `note_self_intro.md` — 自己紹介・信頼構築
    2. `note_tool_story.md` — 開発ストーリー・共感
    3. `note_article_draft.md` — 育休×FIRE計算・集客
    4. `note_sales_article.md` — 有料販売

### C. 法的確認

- [ ] **C-1. 特定商取引法の表示確認**
  - note販売の場合、note側の対応範囲を確認
  - 必要に応じて自サイトにも表示

---

## 依存関係

```
B-1 + B-2 + B-3 → B-4 (note公開)
```

---

## ローンチ後すぐにやること（Phase 1: 検証）

- デモ → 購入ボタンのクリック率を計測
- 3ヶ月間は機能追加禁止（訴求改善に集中）
- X/noteで週1〜2回発信を継続
- 数字は月1回だけ確認（毎日見ない）
