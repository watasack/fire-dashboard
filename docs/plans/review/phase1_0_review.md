# Phase 1.0 実装レビュー

## 判定: ✅承認

## チェック結果

| 観点 | 判定 | 備考 |
|------|------|------|
| スコープ遵守 | ✅ | フィールド名変更と `employmentType` 追加のみ。計算ロジック変更なし |
| currentIncome 残存なし（本体） | ✅ | `lib/simulator.ts`・UI コンポーネントとも `grossIncome` で統一済み |
| currentIncome 後方互換フィールド | ✅ | `@deprecated optional` として型定義・フォールバック実装ともに仕様通り |
| employmentType 追加 | ✅ | `EmploymentType` 型定義・`Person` の optional フィールド・`DEFAULT_CONFIG` 双方に正しく追加 |
| 計算ロジック未変更 | ✅ | `calculateTax` の実装は一切変更なし（Phase 1.1 へ持ち越し） |
| テスト期待値未変更 | ✅ | テスト内 `cfg()` が `grossIncome: 0` を直接使用。期待値の数値変更はゼロ |
| 型安全性 | ✅ | 軽微な懸念あり（下記参照）。ブロッカーレベルではない |

---

## 詳細確認結果

### スコープ遵守

- `Person` インターフェースに `grossIncome: number`（必須）と `currentIncome?: number`（deprecated optional）が共存している
- `calculateIncome` 内のフォールバック `person.grossIncome ?? person.currentIncome ?? 0` は設計書の指示通り
- `generateScenarios` の副業シナリオも `baseConfig.person1.grossIncome ?? baseConfig.person1.currentIncome ?? 0` でフォールバック済み
- `calculateTax` の実装コードは Phase 1.0 スコープで変更なし（確認済み）

### currentIncome 残存チェック

ソースコード（`.ts` / `.tsx`）に残る `currentIncome` 参照は以下の3箇所のみ、いずれも意図した残存:

| ファイル | 行 | 内容 |
|---|---|---|
| `lib/simulator.ts:20` | `currentIncome?: number` | deprecated フィールド定義（仕様通り） |
| `lib/simulator.ts:260` | `person.grossIncome ?? person.currentIncome ?? 0` | フォールバック（仕様通り） |
| `lib/simulator.ts:575` | `generateScenarios` 内フォールバック | フォールバック（仕様通り） |

`docs/` 内の markdown はコード本体ではないため対象外。

### employmentType フィールド

- `EmploymentType = 'employee' | 'selfEmployed' | 'homemaker'` を型として正しく定義
- `Person.employmentType` は `optional`（`?`）となっており、省略時は `'employee'` とコメントで明示
- `DEFAULT_CONFIG` の `person1` / `person2` 双方に `employmentType: 'employee'` を設定済み
- `config-panel.tsx` の `togglePerson2` で person2 初期化時にも `employmentType: 'employee'` を設定済み
- テスト `cfg()` のベース定義にも `employmentType: 'employee'` を明示しており、全テストが型エラーなしで動作する

### 計算ロジック未変更

`calculateTax(income)` の本体（社会保険 15% + 所得税累進 + 住民税 10%）は変更なし。
`runSingleSimulation` の年次ループも変更なし。Phase 1.1 で予定されている税計算リアーキテクチャは含まれていない。

### テスト

- `cfg()` ヘルパーが `grossIncome: 0` を直接デフォルト値として使用しており、`currentIncome` のマッピング処理も設計書で示された形ではなく、シンプルに `grossIncome` を直接渡す方式に統一されている
- 設計書が提案していた「`currentIncome` → `grossIncome` 自動マッピング」コードは `cfg()` に実装されていないが、テスト内のオーバーライドが全て `grossIncome:` キーで書かれているため問題なし
- 全 66 テストの期待値数値に変更なし

---

## 型安全性の軽微な懸念（非ブロッカー）

### 1. `employmentType` が optional である点

設計書（`phase1_gross_income.md`）の「後方互換性」セクションでは `employmentType` を必須フィールドとして定義しているが、実装では `optional`（`?`）となっている。

```typescript
// 設計書の記述
employmentType: EmploymentType  // 必須（新フィールド）、デフォルト: 'employee'

// 実装
employmentType?: EmploymentType  // 雇用形態（省略時は 'employee'）
```

Phase 1.0 の目的（`calculateTax` を使い続ける間は `employmentType` が実際には使われない）を考慮すると、optional のままにしておくのは理にかなっている。Phase 1.1 で `calculateTaxBreakdown` に切り替える際に必須化を検討すること。

### 2. `metrics-summary.tsx` の `savingsRate` 計算

```typescript
// 現行コード
const totalIncome = config.person1.grossIncome + (config.person2?.grossIncome ?? 0)
const savingsRate = (totalIncome - annualExpenses) / totalIncome
```

`savingsRate` を**税引き前年収**と**支出**の差分で計算しているため、実態よりも貯蓄率が高く表示される。ただしこれは表示専用の UI コンポーネントであり、シミュレーションのコア計算（`lib/simulator.ts`）とは独立しているため、Phase 1.0 のスコープ外かつ計算結果に影響しない。Phase 1.1 以降で手取りベースの計算に修正することを推奨する。

---

## 問題点

ブロッカーレベルの問題: なし

---

## コミット可否

✅ コミット可能
