# CLAUDE.md — Claude Code 向け作業ルール

## 必須テスト手順

### 1. コード変更後（毎回）

```bash
# 回帰テスト（src/ の計算ロジック変更後は必須、約30秒）
python -m pytest tests/test_simulation_convergence.py -v
```

期待結果: `2 passed, 2 xfailed, 1 xpassed`（この組み合わせが正常）

### 2. full_app.py の UI 変更後（必須）

```bash
# Playwright UI テスト（Streamlit が起動中であること）
python -m pytest tests/test_ui_phase1.py -v --timeout=180

# 特定ブロックのみ（速い）
python -m pytest tests/test_ui_phase1.py -k "block1 or block2" -v --timeout=180
```

**以下の変更を行った場合は必ず Playwright テストを実行してからコミット・プッシュすること:**
- セッション状態（`session_state`）の構造変更
- ボタンや条件分岐の追加・削除
- インデント変更（expander / if ブロックの包み直し）

### 3. full_app.py の構造変更後（静的解析）

```bash
# NameError 予防（実行前に未定義変数を検出）
python -m py_compile full_app.py

# より詳細なチェック（pyflakes が使える場合）
pyflakes full_app.py
```

---

## full_app.py の重要な不変条件

### session_state['_sim'] に含める変数

シミュレーション実行後に保存し、結果表示ブロックで復元する変数一覧。
**新たに表示コードで変数を使う場合は必ずここに追加すること。**

```python
st.session_state['_sim'] = {
    'mc_res':       mc_res,
    'df':           df,
    'cfg':          cfg,
    'cash':         cash,
    'stocks':       stocks,
    'current_date': current_date,
}
```

### nisa_balance <= stocks（変更禁止）

`_build_simulation_config` 内でクランプ処理済み。常に成立していること。

### run_mc_fixed_fire の引数順（変更禁止）

```python
run_mc_fixed_fire(cash, stocks, cfg, target_success_rate=..., monthly_income=..., ...)
```

---

## Streamlit アプリの確認先

| 環境 | URL |
|---|---|
| 本番 | `https://fire-dashboard-n4bdcefvcuu3ytl68fwtrw.streamlit.app/` |
| ローカル | `streamlit run full_app.py` |

アクセスコード: `.streamlit/secrets.toml` の `access_codes` 参照

---

## Playwright スクリーンショット手法（確定版）

本番アプリは Streamlit Cloud で iframe 内にレンダリングされる。
スクリーンショット取得には以下のパターンを使うこと。

```python
from playwright.sync_api import sync_playwright

URL = 'https://fire-dashboard-n4bdcefvcuu3ytl68fwtrw.streamlit.app/'
ACCESS_CODE = 'DEV-LOCAL-ONLY'  # .streamlit/secrets.toml 参照
TIMEOUT = 60000

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    # 高さ5000pxで全体を一度に表示（スクロール不要）
    page = browser.new_page(viewport={'width': 1440, 'height': 5000})

    page.goto(URL, timeout=TIMEOUT)
    page.wait_for_load_state('domcontentloaded', timeout=TIMEOUT)
    page.wait_for_timeout(6000)  # Streamlit JS 初期化待ち

    # iframe 内のアプリにアクセス
    app = page.frame_locator("iframe[src*='/~/+/']")

    # ログイン
    app.locator("input[type='password']").wait_for(timeout=TIMEOUT)
    app.locator("input[type='password']").fill(ACCESS_CODE)
    page.keyboard.press('Enter')
    app.locator("[data-testid='stSidebar']").wait_for(timeout=TIMEOUT)
    page.wait_for_timeout(4000)

    # シミュレーション実行
    app.locator('button:has-text("まず試算する")').click()
    page.wait_for_timeout(20000)
    app.locator('text=詳細な確率計算へ').click()
    page.wait_for_timeout(5000)
    app.locator('button:has-text("シミュレーションを開始")').click()
    page.wait_for_timeout(60000)  # MC 1000回の計算待ち

    # スクリーンショット（全体）
    page.screenshot(path='dashboard_screenshots/result_full.png')

    # 特定領域のクロップ（x=290 がサイドバー右端）
    page.screenshot(path='dashboard_screenshots/main_area.png',
                    clip={'x': 290, 'y': 0, 'width': 1150, 'height': 2000})

    browser.close()
```

**重要ポイント:**
- Streamlit Cloud はコンテンツが `iframe[src*='/~/+/']` の中にある
- `window.scrollTo()` はフレーム内では効かない → **viewport height=5000px** で代替
- フレームは `page.frames[2]` でも参照可能（0=outer, 1=statuspage, 2=app）
- スクリーンショットは `dashboard_screenshots/` に保存（.gitignore済み）

---

## 過去の失敗から学んだルール

- **UI 変更は必ず Playwright で動作確認してからプッシュする**（目視のみ・回帰テストのみでは不十分）
- `session_state` の構造変更後は、表示コードで参照している全変数が `_sim` に含まれているか確認する
- `st.rerun()` はボタン押下の自然なリレンダーで代替できる場合は使わない
