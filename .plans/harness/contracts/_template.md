# Sprint Contract: [機能名]

## Meta
- **ID**: sprint-NNN
- **Created**: YYYY-MM-DD
- **Status**: PENDING
- **Priority**: HIGH | MEDIUM | LOW

## Scope
[実装内容の簡潔な説明。何を、なぜ変更するのかを1-3文で記述。]

### In Scope
- [具体的な変更点1]
- [具体的な変更点2]
- [具体的な変更点3]

### Out of Scope
- [明示的に触らないもの1]
- [明示的に触らないもの2]

## Affected Files
- `lib/simulator.ts` — [どの関数・型をどう変更するか]
- `components/fire/config-panel.tsx` — [UI変更内容]
- `__tests__/simulator.test.ts` — [追加するテスト]

## Acceptance Criteria
1. `npx next build` がエラーなしで完了
2. `npx vitest run` が全テストパス（既存 + 新規）
3. `python -X utf8 tools/ui_test.py` が全211テストパス（UI変更がある場合）
4. [機能固有の検証基準1]
5. [機能固有の検証基準2]

## Known Pitfalls
- [CLAUDE.md から関連する注意事項]
- [過去のスプリントで遭遇した問題]

## Context From Previous Sprint
- [前スプリントで変更された関連事項 (3-5行)]
- [なければ "初回スプリント" と記載]
