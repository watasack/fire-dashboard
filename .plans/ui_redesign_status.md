# UI再設計 作業状況

最終更新: 2026-03-16

---

## 採用方針

**3フェーズアプローチ**

- **Phase 1:** 案Aの構造整理（完了）
- **Phase 2:** 案Bの3入力→簡易試算導線を追加（完了）
- **Phase 3:** 結果画面の価値向上（設計完了・実装待ち）

最終ゴール: 案B「段階起動型」＋ 改善提案
- クイック入力（3項目）→ 軽量簡易試算 → 「精度を上げる」→ 既存MCシミュレーション → 改善提案

---

## Phase 1 完了状況

| Block | 内容 | コミット | Playwright確認 |
|---|---|---|---|
| Block 2 | KPI → HTMLヒーローカード（緑グラデーション・44px） | `40002f1` | ✅ |
| Block 1 | サイドバー「FIRE後の設定（副収入・取り崩し）」をexpander折り畳み | `fae523b` | ✅ |
| Block 3 | 失敗メッセージ st.error→st.warning＋改善ヒント表示 | `7c444b7` | ✅（#16修正後） |
| Block 4 | 実行ボタン全幅化・説明文・余白追加 | `59d88e5` | ✅ |

---

## Phase 2 完了状況

| Block | 内容 | コミット |
|---|---|---|
| Block A | クイック試算入力3項目 + simulate_future_assets 計算 | `952a424` |
| Block B | 紫グラデーション結果カード + ※注記 + 「詳細へ▼」ボタン | `952a424` |
| Block C | 詳細エリアを expander で包む（show_detail フラグで自動展開） | `0be0733` |
| hotfix | ボタン文字色を white に統一（CSS修正） | `557667c` |

---

## Issue 対処済み

| # | 内容 | 修正コミット |
|---|---|---|
| #16 | 低資産・高支出条件でMCシミュレーターがValueError（33%で停止） | `542972f` |
| #17 | plan_a が2回目のシミュレーション実行後に session_state から消える | `d1ee3d7` / `fc971c6` |

---

## Phase 3 設計方針（次セッションの作業）

### 目的

結果を説明で終わらせず、「次に何を変えると未来が動くか」が一目で分かるUIにする。

### 3ブロック構成

#### Block A（Step 1）: 「次の一手」インサイト

**配置:** ヒーローカード直下
**計算:** `simulate_future_assets` × 2ケース（軽量・即時）

| ケース | 変更内容 |
|---|---|
| ケース① | 支出 −3万円/月 |
| ケース② | 月収 +10万円 |

**表示イメージ:**
```
┌────────────────────────────────────────────────────┐
│ 💡 最も効く改善                                       │
│  支出を月3万円下げると → X年早くFIRE（約○歳）  ▲優先  │
│  月収を10万円増やすと  → Y年早くFIRE（約○歳）          │
│  ※確定論的概算（年金・教育費含む）                      │
└────────────────────────────────────────────────────┘
```

**実装メモ:**
- `cfg` は `_sim` から復元済みのものを `copy.deepcopy` して修正
- 支出変更: `cfg['fire']['manual_annual_expense']` と `base_expense_by_stage` 全ステージを両方更新、`expense_categories.enabled = False` を明示セット
- 収入変更: `monthly_income` パラメータのみ変更（cfg は触れない）
- `monthly_income = (income_h + income_w) * 10000`、`monthly_expense = expense * 10000` はサイドバー変数から再構築（`_sim` には格納していない）

#### Block B（Step 2）: 3シナリオ比較カード

**配置:** Block A を拡張して置き換え
**表示:** 3列カード（現状 / 支出-3万 / 収入+10万）

```
┌─────────┐  ┌─────────┐  ┌─────────┐
│  現状   │  │支出-3万 │  │収入+10万│
│  ○○歳  │  │  △△歳  │  │  □□歳  │
│         │  │ -2.4年↑ │  │ -1.1年↑ │
│ 資産XX  │  │ 資産YY  │  │ 資産ZZ  │
└─────────┘  └─────────┘  └─────────┘
```

- 最も効果の高いケースをハイライト（背景色や枠線で区別）
- 「※確定論的概算」注記を必須表示

#### Block C（Step 3）: 導線整理

1. クイック試算結果カード（紫）に「この数値を詳細試算へ反映」ボタン追加
   → サイドバーの入力値に q_income / q_expense / q_assets を反映 + expander を展開
2. 改善シナリオカードに「この設定で再試算」ボタン（サイドバー値を一時上書き）

### 未確認の設計判断（次セッション開始時に確認）

| 項目 | 選択肢 |
|---|---|
| ① デルタ値 | ハードコード（支出-3万・収入+10万）or スライダーで可変 |
| ② 比較カードの配置 | ヒーローカード直下（直感的）or 別タブ「📊改善提案」（既存タブ変更なし） |
| ③ Block C の優先度 | Step 1・2完了後に判断 or スコープアウト |

---

## 技術情報

### デプロイURL
```
https://fire-dashboard-n4bdcefvcuu3ytl68fwtrw.streamlit.app/
```
アクセスコード: `DEV-LOCAL-ONLY`

### Playwrightテスト

```bash
# 全テスト実行
python -m pytest tests/test_ui_phase1.py -v --timeout=180

# Block 1-2 のみ（速い）
python -m pytest tests/test_ui_phase1.py -k "block1 or block2" -v --timeout=180
```

- `tests/test_ui_phase1.py` に Block 1〜4 のテスト実装済み
- Streamlit は `iframe[src*='/~/+/']` 内にレンダリングされるため `get_app_frame()` 経由でアクセス
- `get_by_label` はヘルプボタンとinputの2要素にマッチするため `get_by_role("spinbutton", name=...)` を使用
- MCシミュレーションは最大90秒かかるため `page.wait_for_timeout(90_000)` で待機

### 重要な不変条件（変更禁止）

- `nisa_balance <= stocks` （`_build_simulation_config` 内でクランプ処理済み）
- `run_mc_fixed_fire(cash, stocks, cfg, ...)` の引数順
- `children_ui` の dict 構造（w_lp, w_la, w_li, w_re, w_ri, h_la, h_li, h_re, h_ri）
- コード変更後は必ず `python -m pytest tests/test_simulation_convergence.py` を実行
- UI変更後は必ず Playwright テストを実行してからコミット・プッシュ

### session_state のキー

- `password_correct`: 認証状態
- `quick_result`: クイック試算結果（success, fire_age）
- `show_detail`: 詳細エリア expander の展開状態
- `_sim`: MCシミュレーション結果（mc_res, df, cfg, cash, stocks, current_date）
- `plan_a`: 比較用プランA（df, fire_date, fire_age_h/w, assets_at_fire, years_to_fire）

### ファイル構成（重要なもの）

```
full_app.py          # Streamlit フル版（メイン作業対象）
demo_app.py          # 無料デモ版（simulate_future_assets を使用）
src/simulator.py     # MCシミュレーションエンジン
src/visualizer.py    # Plotlyグラフ生成
src/html_generator.py# 静的HTMLダッシュボード生成
config.yaml          # 本番用パラメータ
demo_config.yaml     # full_app.py が読み込むベース設定（full版もこちらを使用）
CLAUDE.md            # Claude Code 向け作業ルール（テスト手順・不変条件）
tests/test_ui_phase1.py   # Playwright UIテスト（Phase1）
tests/test_simulation_convergence.py  # 計算ロジックの回帰テスト
```
