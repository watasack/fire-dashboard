# コードスタイル・規約

## 言語・フォーマット
- Python 3.x、UTF-8エンコーディング
- 型ヒントなし（既存コードに合わせる）
- docstringは主要な関数のみ（英語または日本語）
- 静的解析ツール未導入（pylint/flake8/mypy は将来計画）

## コミットメッセージ規約
プレフィックス必須：
- `fix:` バグ修正
- `feat:` 新機能追加
- `refactor:` リファクタリング
- `test:` テスト追加・修正
- `docs:` ドキュメント更新
- `chore:` ビルド・設定変更
- `perf:` パフォーマンス改善

スコープを括弧付きで追加可能（例: `feat(simulator):`, `fix(config):`）

末尾に共著者行を付ける：
```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

## 設計パターン
- **設定の一元管理**: すべてのパラメータは `config.yaml` から読み込む。ハードコードしない
- **後方互換性**: 新機能はオプトイン形式（`enabled: false` がデフォルト）
- **不変条件アサーション**: 重要な条件は `assert` で明示（例: `nisa_balance <= stocks`）
- **並列処理**: 重い計算は `ProcessPoolExecutor`（Windows spawn方式対応）

## 重要な注意点
- **NISAリターン適用漏れ注意**: 月次ループで `stocks` にリターン適用したら `nisa_balance` にも必ず適用
- **月次処理の3関数**: 類似ロジックが `_process_post_fire_monthly_cycle`, `_process_future_monthly_cycle` 等に存在。一か所修正したら他も確認
- スクリーンショットは `dashboard_screenshots/` に保存（.gitignore済み、コミット不要）
