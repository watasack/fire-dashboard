# Review Report
- **Date**: 2026-04-04
- **Mode**: Custom（実装仕様書レビュー）
- **Scope**: `docs/plans/access-code-auth.md` — アクセスコード認証 技術設計

## Summary

全体的に副業規模に適切な「割り切り」が随所に見られる、実用的な設計。
ただし `/api/ping` のトークン検証ロジックに設計上の曖昧さがあり、実装時に詰まるリスクがある。
また、ページロード中のローディング状態とネットワーク障害時の挙動が未定義で、UX に影響する。

---

## Findings

### Finding 1: `/api/ping` のトークン検証ロジックが未定義 (Severity: HIGH)

- **Location**: `docs/plans/access-code-auth.md` — アーキテクチャ図
- **Problem**: `/api/validate` では `token = HMAC(SECRET, code)` を生成するが、`/api/ping` でこのトークンをどう検証するかが書かれていない。
  サーバー側はコードを保存していないため、検証するには以下のいずれかの方法が必要になる：
  - **方法A**: `VALID_CODES` 全件に対して `HMAC(SECRET, code)` を再計算して一致確認（100件なら現実的）
  - **方法B**: トークンにコードも含める（例: `code + "." + HMAC(SECRET, code)`）
- **Impact**: 実装者がここで詰まり、誤った実装（例: VALID_CODES をクライアントに露出させる）をしてしまうリスクがある。
- **Suggested Fix**: 仕様書に方法Bを明示する。

  ```typescript
  // /api/validate
  const token = `${code}.${createHmac("sha256", AUTH_SECRET).update(code).digest("hex")}`;

  // /api/ping
  const [code, sig] = token.split(".");
  const expected = createHmac("sha256", AUTH_SECRET).update(code).digest("hex");
  const valid = timingSafeEqual(Buffer.from(sig), Buffer.from(expected))
             && validCodes.includes(code);
  ```
  
  `timingSafeEqual` を使うことでタイミング攻撃も防げる。

---

### Finding 2: ページロード中のローディング状態が未定義 (Severity: MEDIUM)

- **Location**: `docs/plans/access-code-auth.md` — UI 設計方針
- **Problem**: `<AccessGate>` が `/api/ping` を叩いている間（isAuthed が未確定の状態）、画面に何を表示するか定義されていない。
  - デモ版を表示してしまうと、フル版ユーザーに一瞬デモ版が見えて不信感を与える
  - 何も表示しないとレイアウトシフトが起きる
- **Impact**: フル版ユーザーのUX劣化、またはCLS（Cumulative Layout Shift）によるCore Web Vitals 悪化。
- **Suggested Fix**: 仕様書にローディング状態を明記する。推奨はスケルトン表示またはデモ版のままフェードイン（後者の方が実装コストが低い）。

---

### Finding 3: ネットワーク障害時の挙動が未定義 (Severity: MEDIUM)

- **Location**: `docs/plans/access-code-auth.md` — アーキテクチャ図
- **Problem**: `/api/ping` がネットワークエラーやタイムアウトで失敗した場合の挙動が定義されていない。
  - フェールオープン（エラー時はフル版を表示）にすると、ping を妨害すれば認証をバイパスできる
  - フェールクローズ（エラー時はデモ版を表示）にすると、正規ユーザーがオフライン時に使えなくなる
- **Impact**: フェールオープンはセキュリティホール、フェールクローズはUX問題。
- **Suggested Fix**: 副業規模ならフェールオープン（利便性優先）を採用し、仕様書に明記する。
  「コードの共有は防止しない」と同じ割り切りの文脈で説明できる。

---

### Finding 4: `/api/ping` のレートリミットが未記載 (Severity: LOW)

- **Location**: `docs/plans/access-code-auth.md` — セキュリティ上の割り切り
- **Problem**: セキュリティ割り切りのセクションでは `/api/validate` のレートリミットのみ言及されているが、`/api/ping` はページロードごとに呼ばれるため、こちらもDoSの対象になり得る。
- **Impact**: 悪意あるスクリプトによる `/api/ping` の大量リクエストで Vercel の無料枠を消費される。
- **Suggested Fix**: `/api/ping` にも同様のレートリミットを適用する旨を明記。実装は同じミドルウェアで対応可能。

---

### Finding 5: モンテカルロ成功率のデモ版表示が矛盾している (Severity: LOW)

- **Location**: `docs/plans/access-code-auth.md` — デモ版の制限仕様（テーブル）
- **Problem**: デモ版制限のテーブルで「モンテカルロ成功確率: ○（参考値）」とあるが、モンテカルロは詳細タブの設定（投資・ライフ・詳細）に依存する。それらの設定タブをロックしながら成功率だけ表示するのは、数値の信頼性の観点で混乱を招く可能性がある。
- **Impact**: ユーザーが「参考値」の意味を理解せず、不正確な確率を信頼してしまうリスク。
- **Suggested Fix**: 「参考値」であることをUIにも明示するか、デモ版ではモンテカルロも非表示にするか、どちらかに統一する。

---

## Good Practices Noted

- **`NEXT_PUBLIC_` を使わない**: サーバーサイド専用の環境変数設計は正しい。クライアントバンドルへの秘密漏洩を防いでいる。
- **props バケツリレーの採用**: Context を使わず1段のprops渡しに留めるのは、この規模では適切。シンプルさを優先した正しい判断。
- **ロックオーバーレイの購買動機設計**: 「触ったときに初めてロックに気づく」体験は、SaaS の freemium UX として理にかなっている。
- **コード無効化の即時性**: 環境変数削除→再デプロイで即時反映できる設計はオペレーション上シンプルで良い。
- **段階的な監視戦略**: レベル1〜3の段階設計が現実的。Vercel ログ目視 → コンソールログ → Axiom の順は費用対効果が高い。
- **Notion DB への移行パスの明記**: スケール時の出口戦略が最初から考慮されている。

---

## Recommendations

優先度順:

1. **(HIGH) Finding 1 を修正**: `/api/ping` のトークン検証ロジックを仕様書に追記する。`code.sig` 形式 + `timingSafeEqual` の具体的な実装例を載せる。
2. **(MEDIUM) Finding 2 を修正**: `<AccessGate>` のローディング状態（isAuthed が未確定の間）の挙動を仕様書に追記する。
3. **(MEDIUM) Finding 3 を修正**: `/api/ping` 失敗時（ネットワークエラー）の挙動をフェールオープン or フェールクローズのどちらかに明記する。
4. **(LOW) Finding 4 を修正**: `/api/ping` のレートリミットについて一言追記する。
5. **(LOW) Finding 5 を検討**: モンテカルロ「参考値」の表示方針を確定する。
