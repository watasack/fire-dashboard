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
| 本番 | `.plans/ui_redesign_status.md` 参照 |
| ローカル | `streamlit run full_app.py` |

アクセスコード: `.plans/ui_redesign_status.md` 参照

---

## 過去の失敗から学んだルール

- **UI 変更は必ず Playwright で動作確認してからプッシュする**（目視のみ・回帰テストのみでは不十分）
- `session_state` の構造変更後は、表示コードで参照している全変数が `_sim` に含まれているか確認する
- `st.rerun()` はボタン押下の自然なリレンダーで代替できる場合は使わない
