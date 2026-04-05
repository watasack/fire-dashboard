# FIRE Simulator

日本の税制・社会保険制度に対応した FIRE（経済的自立・早期退職）シミュレーター。
モンテカルロシミュレーションにより、資産推移の確率分布を可視化します。

## 主な機能

- FIRE達成年齢の自動算出（二分探索による実収支ベース判定）
- モンテカルロシミュレーション（1,000回試行・成功確率・信頼区間）
- 配偶者収入・産休育休・教育費・住宅ローン対応
- 3種の取り崩し戦略（固定額・定率・ガードレール）
- NISA / iDeCo の税制優遇シミュレーション
- URL シェアによる設定共有

## クイックスタート

```bash
pnpm install
pnpm dev          # → http://localhost:3000
npx next build    # 本番ビルド確認
npx vitest run    # ユニットテスト
```

## ドキュメント

| ファイル | 内容 |
|---|---|
| [docs/SPECIFICATION.md](docs/SPECIFICATION.md) | シミュレーション仕様書（計算ロジック詳細） |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | 開発者向けガイド（テスト・トラブルシューティング） |
| [CLAUDE.md](CLAUDE.md) | Claude Code 向け作業ルール |

## 技術スタック

Next.js 15 / React 19 / TypeScript / Tailwind CSS v4 / Recharts / Vercel
