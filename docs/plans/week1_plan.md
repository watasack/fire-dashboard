# 販売準備 作業計画

最終更新: 2026-03-11

---

## 販売戦略（決定事項）

**販売プラットフォーム: note 有料記事**

| 項目 | 内容 |
|------|------|
| 販売場所 | note 有料記事 |
| 販売物 | Webツール（Streamlit）のアクセスコード |
| コード管理 | 購入者ごとに個別アクセスコードを発行 |
| 価格 | **¥980**（5件売れたら ¥1,980 に値上げ） |

**詳細**: [monetization_strategy.md](monetization_strategy.md)

---

## 技術的前提

```
デモ版: demo_app.py → FIRE到達年齢（即時・機能制限あり）
フル版: full_app.py → アクセスコード認証 + MC1,000回 + 育休・時短 + 最悪ケース
```

| ユーザー入力 | 実装方法 |
|------------|---------|
| 夫/妻の月手取り | income_husband + income_wife → monthly_income |
| 月間支出 | manual_annual_expense = 支出 × 12 |
| 現在の金融資産 | current_cash = 資産 × 0.3, current_stocks = 資産 × 0.7 |
| 夫/妻の年齢 | start_age = age_husband（計算の基準） |

---

## 完了済み作業（3/8時点）

| 作業 | 状態 |
|------|------|
| demo_app.py 作成・Streamlit Cloud 公開 | ✅ https://m2sbgpwr7ogazgwrxsqqsg.streamlit.app/ |
| demo_app.py: 夫妻別収入・年齢入力に変更 | ✅ |
| demo_app.py: 育休/時短ティーザーセクション追加 | ✅ |
| demo_app.py: Google Form ・ note 記事 URL 設定 | ✅ |
| Google Form 作成（メール登録） | ✅ https://forms.gle/mqrmGXNzy73Q1qb67 |
| note アカウント作成（FIREwithKids） | ✅ |
| ブランド確定（FIREwithKids） | ✅ |
| note 記事草稿作成 | ✅ docs/content/note_article_draft.md |
| スクリーンショット撮影（2ケース） | ✅ docs/screenshots/ |
| 入力ガイド草稿 | ✅ docs/product/input_guide_draft.md |
| FAQ草稿 | ✅ docs/product/faq_draft.md |
| X 投稿下書き（4週分12本） | ✅ docs/content/x_posts_drafts.md |
| src/data_loader.py バグ修正 | ✅ |
| 販売資料のスプレッドシート→Webツール統一 | ✅ |

---

## 残りタスク

### タスク A：フル版Webツール完成（✅ 完了）

対象: `full_app.py`（Streamlit）

**作業手順：**
1. ~~full_app.py の個人名（修平・桜）を汎用化~~ ✅
2. ~~購入者ごとの個別アクセスコード認証ロジックを実装~~ ✅
3. ~~MC計算・グラフ表示・最悪ケース分析の動作確認~~ ✅（25件テスト + Playwrightデプロイテスト）
4. 入力ガイド・FAQをツール内に組み込み（サイドバー or ヘルプセクション）⬜ 後回し可
5. ~~Streamlit Cloud にフル版をデプロイ~~ ✅ https://fire-dashboard-n4bdcefvcuu3ytl68fwtrw.streamlit.app/
6. ~~ダミーデータ3パターンで動作確認~~ ✅（Playwrightで自動確認済み）

**完了基準：** アクセスコード入力 → 育休設定 → MC計算 → グラフ・成功確率が表示される ✅

---

### タスク B：note 記事の公開（タスクA完了後）

**note記事の最終構成：**

```
【無料部分（誰でも読める）】
 1. タイトル・はじめに
 2. 前提条件（ダミーデータ）
 3. ケース1: 育休なしの結果 + スクリーンショット
 4. ケース2: 育休ありの結果 + スクリーンショット
 5. 差分の考察（4年遅れ・成功確率4%低下）
 6. 成功確率の意味（1,000通りの未来）
 7. 「このシミュレーターを公開しました」+ 無料デモURL

─── 有料ライン ───

【有料部分（購入者のみ）】
 8. フル版WebツールのURL
 9. 購入者専用アクセスコード
10. 入力ガイド（input_guide_draft.md の内容を転記）
11. FAQ（faq_draft.md の内容を転記）
12. サポート連絡先（メール）
13. 免責文言
```

**注意**: 入力ガイド・FAQはnote記事にもフル版ツール内にも両方掲載する。

**手順：**
1. note 編集画面で `docs/content/note_article_draft.md` の内容を貼り付け
2. `[ここにスクリーンショット]` の箇所に `docs/screenshots/` の画像をアップロード
3. 有料部分にフル版URL + アクセスコードを記載
4. 入力ガイド・FAQ の内容を有料部分に追記
5. 免責文言を追記
6. 価格を設定
7. 公開

---

### タスク C：X アカウント（後回し可）

- 登録: @FIREwithKids
- 最初の投稿は `docs/content/x_posts_drafts.md` の「投稿1-A」

---

## ゴール

| 項目 | 完了基準 | 状態 |
|------|---------|------|
| デモ URL | 公開済み | ✅ |
| フル版Webツール | アクセスコード認証・デプロイ完了 | ✅ https://fire-dashboard-n4bdcefvcuu3ytl68fwtrw.streamlit.app/ |
| note 記事 | 有料記事として公開 | ⬜ 次のタスク |
| X 登録 | アカウント作成（投稿は任意） | ⬜ 後回し可 |

---

## ブロッカー・未決事項

- [x] フル版Webツール完成（タスクA）✅ デプロイ・テスト完了
- [x] note 有料記事の価格設定：**ローンチ価格 ¥980**（5件売れたら ¥1,980 に値上げ）
- [ ] アクセスコードの管理方法（DB / スプレッドシート / st.secrets の辞書）を決定する必要あり
