# Review Report
- **Date**: 2026-04-04
- **Mode**: Custom（note記事レビュー）
- **Scope**: `docs/content/note_article_draft.md` — 「育休を取るとFIREが何年遅れるか、1,000通りの未来で計算してみた」

## Summary

記事の本文・構成・説得力は高い水準にある。しかし、アプリがStreamlitからNext.js/Vercelに移行した際に更新されず残った旧URLと、デモ版の実際の機能と合わない説明文が存在する。公開前に必ず修正が必要な HIGH が2件（旧URL、デモ説明の乖離）と、プレースホルダー・画像の未解決事項が残っている。

---

## Findings

### Finding 1: 旧StreamlitのURLが残存している (Severity: HIGH)

- **Location**: `docs/content/note_article_draft.md:137`
- **Problem**: `https://m2sbgpwr7ogazgwrxsqqsg.streamlit.app/` はStreamlit時代の旧URLで、アプリはNext.js/Vercelに移行済み。
- **Impact**: 読者がクリックすると旧アプリ（または動作しないページ）に遷移する。信頼性の致命的な毀損。
- **Suggested Fix**: 実際のVercel URLに置き換える。URLが未確定の場合は `[デモURL]` プレースホルダーを使用（`docs/content/note_sales_article.md` に倣う）。

---

### Finding 2: デモ版の説明が実装と乖離している (Severity: HIGH)

- **Location**: `docs/content/note_article_draft.md:139`
- **Problem**: 記事には「年収・支出・資産を入力するだけで、FIRE到達年齢の推計が出ます」とあるが、現在の実装（`components/fire/config-panel.tsx`）では**デモ版で収入タブはロック済み**。年収・配偶者収入・退職年齢・年金などは入力できない。
- **Impact**: 読者がデモを試したとき「年収が入力できない」と感じ、ツールへの不信感につながる。
- **Suggested Fix**: デモで操作できる内容に限定した説明に修正する。
  ```
  現在の資産と月の支出を入力するだけで、FIRE到達年齢の目安が出ます。登録不要・スマホ対応。
  ```

---

### Finding 3: `[note有料記事URL]` プレースホルダーが未入力 (Severity: HIGH)

- **Location**: `docs/content/note_article_draft.md:153`
- **Problem**: `noteで購入するとアクセスコードが届きます：[note有料記事URL]` のリンクが未設定。
- **Impact**: 購入動線が壊れている。記事の最重要CTA（コールトゥアクション）が機能しない。
- **Suggested Fix**: note記事を公開後、実際のURLに置き換える。

---

### Finding 4: フル版でできることの説明が不完全 (Severity: MEDIUM)

- **Location**: `docs/content/note_article_draft.md:145-151`
- **Problem**: フル版の機能リストに「育休・産休・時短」「教育費」「モンテカルロ」は記載されているが、**年収・退職年齢・雇用形態・年金設定（収入タブ全体）** もデモではロックされているにも関わらず明示されていない。読者は「年収設定はデモでできる」と誤解しうる。
- **Impact**: デモで試した際に「収入設定もできないのか」という失望体験につながる可能性。
- **Suggested Fix**: 「夫・妻それぞれの年収・退職年齢・雇用形態の設定」をフル版機能リストの筆頭に追加する。

---

### Finding 5: ケース2の画像コメントの数値不一致 (Severity: LOW)

- **Location**: `docs/content/note_article_draft.md:64`
- **Problem**: 画像コメントに「デフォルト設定がケース2に近い: 49歳・76.7%」とあるが、記事本文のケース2はFIRE成功確率 **80%** 。`result_top.png` をそのまま使うと、画像の数値（76.7%）が記事テキスト（80%）と食い違う。
- **Impact**: 読者が「数字が違う」と気づいた場合、信頼性が低下する。
- **Suggested Fix**: ケース2の設定（妻育休のみ・FIRE 49歳・成功確率80%）で別途スクリーンショットを撮影するか、本文の数値をデフォルト設定の実際の値に合わせる。

---

### Finding 6: 画像プレースホルダーコメントが残存 (Severity: LOW)

- **Location**: `docs/content/note_article_draft.md:47-49, 80-82, 133-134`
- **Problem**: HTML コメント形式の `<!-- 📷 画像: ... -->` が残っており、公開時にそのまま含まれるとnote上では不可視だが草稿管理上の混乱を招く。`docs/images/note/` には `result_top.png`, `mobile_chart.png`, `full_page.png` などが確定済みとして存在するが、ケース1・ケース3専用の画像はまだない。
- **Impact**: 公開前の作業漏れリスク。
- **Suggested Fix**: 利用可能な画像（`result_top.png`、`mobile_chart.png` など）のコメントは「撮影済み・使用確定」に更新。未撮影分（ケース1・ケース3）は TODO として明記する。

---

## Good Practices Noted

- **導入の共感性が高い**: 「正直すぐに賛成できなかった」という著者の正直な葛藤から始まる構成は、ペルソナ（共働きFIRE層）の心理に直接刺さる。
- **数字の見せ方が明快**: 3ケースの比較（育休なし→妻のみ→夫婦）を段階的に示す構成は読みやすく、「3年遅れ」「5年遅れ」という数字が頭に残りやすい。
- **「思ったより小さい」という驚きの言語化**: 読者の先入観（「育休=大幅遅延」）を数字で崩す流れは、記事のUVP（独自の価値提案）として機能している。
- **法的免責事項**: 末尾の免責文は適切で、金融商品取引法上のリスクを回避している。
- **「確率5%の悪化をどう見るか」セクション**: 定量的な議論から定性的な判断へのつなぎが自然で、読者の意思決定プロセスを尊重している。

---

## Recommendations

優先度順:

1. **[公開ブロッカー] Finding 1**: 旧StreamlitのURLを正しいVercel URLまたは `[デモURL]` に置き換える
2. **[公開ブロッカー] Finding 3**: `[note有料記事URL]` を実際のURLに置き換える（note公開後）
3. **[公開前必須] Finding 2**: デモの説明文を「現在の資産と月の支出を入力するだけで」に修正
4. **[公開前推奨] Finding 4**: フル版機能リストに「年収・退職年齢・雇用形態の設定」を追加
5. **[公開前推奨] Finding 5**: ケース2の画像をデフォルト設定で撮影するか、本文の数値を合わせる
6. **[任意] Finding 6**: 画像コメントの状態を整理（撮影済み/未撮影）
