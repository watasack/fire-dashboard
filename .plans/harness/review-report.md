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

---

### Finding A: `timingSafeEqual` がマルフォームトークンで例外を投げる (Severity: MEDIUM)

- **Location**: `docs/plans/access-code-auth.md` — トークン形式の詳細
- **Problem**: `timingSafeEqual` はバッファ長が異なると `TypeError` を投げる。攻撃者が `.` なしのトークンや不正な長さの署名を送ると `/api/ping` が 500 エラーになる。
- **Impact**: サービス障害（意図的なクラッシュ）およびエラーログ汚染。
- **Suggested Fix**: 仕様書に入力バリデーションを明記する。

  ```typescript
  const parts = token.split(".");
  if (parts.length !== 2) return { valid: false };
  const [code, sig] = parts;
  const expected = createHmac("sha256", AUTH_SECRET).update(code).digest("hex");
  if (sig.length !== expected.length) return { valid: false }; // 長さガード
  const valid = timingSafeEqual(Buffer.from(sig, "hex"), Buffer.from(expected, "hex"))
             && validCodes.includes(code);
  ```

---

### Finding B: コンポーネントツリーの props が `AuthState` と不整合 (Severity: LOW)

- **Location**: `docs/plans/access-code-auth.md` — UI 設計方針 → コンポーネントツリー図
- **Problem**: ツリー図では `isDemoMode={!isAuthed}`（boolean）のままだが、`AuthState = "loading" | "authed" | "demo"` に変わったため整合していない。`loading` 中に `isDemoMode={true}` が渡るとロックオーバーレイが表示されてしまう。
- **Impact**: ローディング中にフル版ユーザーへロックオーバーレイが表示される（Finding 2 の修正と矛盾）。
- **Suggested Fix**: コンポーネントツリー図の props を更新し、`loading` 中は `<FireDashboard>` 自体をレンダーしないことを明記する。

  ```typescript
  if (authState === "loading") return <DashboardSkeleton />;
  <FireDashboard isDemoMode={authState === "demo"} />
  ```

---

## Responses to Findings

対応日: 2026-04-04

---

### Response to Finding 1 (HIGH): トークン検証ロジック

**判断**: Suggested Fix の方法B（`code.sig` 形式）を採用。

理由: 方法A（全コードに対してHMACを再計算）はコード数が増えると線形にコストが増加するため、スケール性が低い。方法Bはトークンにコードを埋め込むことで検証が O(1) で済み、コード数に依存しない。

**修正内容** (`docs/plans/access-code-auth.md`):
- トークン形式を `{code}.{HMAC(SECRET, code)}` と明記
- `/api/ping` の検証ロジックを「分割→再計算→`timingSafeEqual`→`VALID_CODES`確認」の4ステップで明記
- `timingSafeEqual` 使用によるタイミング攻撃対策も併記

---

### Response to Finding 2 (MEDIUM): ローディング状態

**判断**: `loading / authed / demo` の3値で状態を定義し、`loading` 中はスケルトン表示（全タブをグレーアウト）を採用。

理由: レポートが挙げた「デモ版のままフェードイン」（後者の方が実装コストが低い）も検討したが、フル版ユーザーに一瞬でもロックオーバーレイが見えると不信感につながるリスクがある。`/api/ping` は Edge Function のため通常 100ms 以内に応答するため、スケルトンのちらつきは実用上問題ない。

**修正内容** (`docs/plans/access-code-auth.md`):
- `AuthState = "loading" | "authed" | "demo"` を明記
- `loading` 中の表示仕様（スケルトン or スピナー）を追記
- `/api/ping` の応答速度（通常 100ms 以内）の根拠も補足

---

### Response to Finding 3 (MEDIUM): ネットワーク障害時の挙動

**判断**: フェールオープン（障害時はフル版表示）を採用。

理由: レポートが指摘する通り「フェールオープンはセキュリティホール」だが、このシステムのセキュリティモデルは「コードの共有は防止しない」という割り切りとすでに一致している。正規購入者がオフライン・ネットワーク不安定な環境で「お金を払ったのに使えない」体験の方が損害が大きいと判断。フェールオープンの条件は「localStorage にトークンが存在する場合のみ」に限定し、トークンなし＋障害時はデモ版を表示することで完全な無認証バイパスは防ぐ。

**修正内容** (`docs/plans/access-code-auth.md`):
- フェールオープン採用とその理由を明記
- 「localStorage にトークンがあれば → フル版、なければ → デモ版」という条件分岐を明記

---

### Response to Finding 4 (LOW): `/api/ping` のレートリミット

**判断**: Vercel のデフォルト保護に委ねる方針を維持しつつ、無料枠（月100万リクエスト）への言及を追記。

理由: `/api/ping` はページロードごとに呼ばれるが、通常ユーザーの利用頻度（1セッション数回）では問題にならない。専用レートリミットミドルウェアの追加は副業規模では保守コストが見合わない。Vercel の DDoS 保護で十分と判断。

**修正内容** (`docs/plans/access-code-auth.md`):
- `/api/ping` のレートリミットについてセキュリティ割り切りセクションに追記
- Vercel 無料枠（月100万リクエスト）の数字を明記

---

### Response to Finding 5 (LOW): デモ版モンテカルロ表示

**判断**: デモ版でも成功確率を表示するが、「簡易計算値」であることをUIに明示する方針を採用。

理由: 成功確率を完全に非表示にすると、ユーザーがツールの価値を体感できず購買動機が生まれない。freemium の設計原則として「価値を見せてから壁を作る」ことが重要であり、数値を見せつつ「詳細設定を反映するにはフル版が必要」と明示する方が購買転換率の観点で優れると判断。

**修正内容** (`docs/plans/access-code-auth.md`):
- 制限仕様テーブルの「モンテカルロ成功確率」を「○（参考値・注1）」に変更
- 注1として「基本3項目のみの簡易計算値・フル版との違いをUIに明示」を追記

