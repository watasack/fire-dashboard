# Phase 4: 資産管理高度化（4A〜4D）

## 概要

現在の単一 `assets` 変数を「現金・NISA・iDeCo・課税口座株式」の4つに分離し、
NISA年間360万円枠・iDeCo60歳制約・売却益課税（20.315%）を実装する。
4A（分離管理）が基盤で、4B〜4Dはその上に積み上がる。

## 依存Phase

- 前提: P1（税計算基盤）
- 影響: P6（FIRE後税金の売却益計算）、P7（取り崩し戦略で資産種別ごとの処理が必要）

---

# Phase 4A: 現金・株式分離管理

## インターフェース変更

```typescript
// 変更前
export interface SimulationConfig {
    currentAssets: number   // 単一の総資産
    // ...
}

// 変更後
export interface SimulationConfig {
    currentAssets?: number        // @deprecated: 後方互換（cashAssets + stockAssets に分割）
    cashAssets: number            // 追加: 現金・普通預金（投資対象外）
    taxableStockAssets: number    // 追加: 課税口座の株式・投信評価額
    stocksCostBasis: number       // 追加: 課税口座の取得原価（税計算用）
    // ...
}
```

### 後方互換マッピング

```typescript
// SimulationConfig の読み込み時（UI層またはrunSingleSimulation冒頭）
if (config.currentAssets !== undefined && config.cashAssets === undefined) {
    // 旧設定: currentAssets を全て現金として扱う
    config.cashAssets = config.currentAssets
    config.taxableStockAssets = 0
    config.stocksCostBasis = 0
}
```

## 関数仕様

### 資産管理の年次更新ロジック

```typescript
/**
 * 年次の資産更新を行う
 * 優先順位: 余剰資金 → NISA枠投資 → 課税口座投資
 * 不足時: NISA → 課税口座 → 現金の順で取り崩し
 */
function updateAssets(
    assets: AssetState,
    savings: number,         // netIncome - expenses（正=余剰, 負=不足）
    returnRate: number,
    config: SimulationConfig,
    isPostFire: boolean,
    personAge: number
): AssetState
```

型定義:
```typescript
interface AssetState {
    cashAssets: number
    taxableStockAssets: number
    stocksCostBasis: number
    nisaAssets: number
    idecoAssets: number
}
```

アルゴリズム:
```
1. 投資リターンを全資産に適用:
   newTaxableStock = taxableStockAssets * (1 + returnRate)
   newNisa = nisaAssets * (1 + returnRate)
   newIdeco = idecoAssets * (1 + returnRate)
   // 現金はリターンなし（利子は省略）

2. 余剰資金の投資（savings > 0 かつ就労中）:
   余剰 = savings
   // NISA枠に優先投資（P4B で枠制限追加）
   nisaContrib = min(余剰, config.nisa.annualContribution)  // P4B: 360万/年上限
   余剰 -= nisaContrib
   newNisa += nisaContrib
   // iDeCo拠出
   idecoContrib = config.ideco.enabled ? config.ideco.monthlyContribution * 12 : 0
   newIdeco += idecoContrib
   // 残りは課税口座投資
   newTaxableStock += max(0, 余剰 - idecoContrib)
   newStocksCostBasis += max(0, 余剰 - idecoContrib)  // 取得原価も更新

3. 支出不足時の資産取り崩し（savings < 0）:
   shortfall = abs(savings)
   // NISA → 課税口座 → 現金の順（P4D: 課税口座売却時は税計算あり）
   {shortfall, newNisa} = withdrawFromNisa(shortfall, newNisa)
   {shortfall, newTaxableStock, newStocksCostBasis, capitalGains} =
       withdrawFromTaxable(shortfall, newTaxableStock, newStocksCostBasis)  // P4D
   cashAssets -= shortfall  // 残りは現金から
```

## DEFAULT_CONFIG変更

```typescript
// 変更前
currentAssets: 10000000,

// 変更後
currentAssets: undefined,      // @deprecated
cashAssets: 2000000,           // 現金200万円（生活防衛資金）
taxableStockAssets: 8000000,   // 課税口座800万円
stocksCostBasis: 6000000,      // 取得原価600万円（含み益200万円）
```

## YearlyData への追加フィールド

```typescript
// YearlyData に追加
cashAssets: number           // 現金残高
taxableStockAssets: number   // 課税口座残高
// 既存フィールドは維持
assets: number               // 後方互換: cashAssets + taxableStockAssets（旧 assets と等価）
nisaAssets: number           // 維持
idecoAssets: number          // 維持
```

## テスト影響分析

### 既存テストへの影響

`cfg()` ヘルパーで `currentAssets` を使っているテストは全て影響を受ける可能性があるが、
後方互換マッピング（`currentAssets` → `cashAssets`）で吸収する。

**テスト修正が必要なもの:**
- `result.yearlyData[i].assets` を参照するテスト:
  変更後は `assets = cashAssets + taxableStockAssets` として `assets` フィールドを維持すれば影響なし

### 新規テストケース

```typescript
describe('現金・株式分離管理', () => {
    test('currentAssets の後方互換: 全額 cashAssets に変換される', () => {})
    test('余剰資金は NISA → 課税口座の順に投資される', () => {})
    test('不足時は NISA → 課税口座 → 現金の順に取り崩し', () => {})
    test('assets フィールドは cashAssets + taxableStockAssets と等しい', () => {})
})
```

---

# Phase 4B: NISA年間枠管理（360万円上限）

## インターフェース変更

```typescript
// NISAConfig に年間上限枠を追加
export interface NISAConfig {
    enabled: boolean
    annualContribution: number    // 希望拠出額（上限360万円）
    // 追加:
    annualLimit: number           // NISA年間投資枠上限（デフォルト: 3,600,000）
    lifetimeLimit: number         // 生涯非課税限度額（デフォルト: 18,000,000）
    totalContributed: number      // 累計拠出元本（生涯限度額との比較用）
}
```

## 関数仕様

### `getNisaContributionForYear` — 当年のNISA拠出可能額

```typescript
/**
 * NISA年間枠と生涯限度額を考慮した当年の実際の拠出額を返す
 * @param desiredContribution 希望拠出額
 * @param nisaConfig NISA設定
 * @param currentNisaAssets 現在のNISA残高（取得原価ベース）
 * @returns 実際に拠出できる金額
 */
function getNisaContributionForYear(
    desiredContribution: number,
    nisaConfig: NISAConfig,
    totalContributedSoFar: number
): number {
    // 年間360万円上限
    const withinAnnual = Math.min(desiredContribution, nisaConfig.annualLimit)
    // 生涯1800万円上限
    const remainingLifetime = Math.max(0, nisaConfig.lifetimeLimit - totalContributedSoFar)
    return Math.min(withinAnnual, remainingLifetime)
}
```

## DEFAULT_CONFIG変更

```typescript
nisa: {
    enabled: true,
    annualContribution: 1200000,   // 希望120万円/年
    annualLimit: 3600000,          // 追加: 360万円/年上限
    lifetimeLimit: 18000000,       // 追加: 1800万円生涯限度額
    totalContributed: 0,           // 追加: 初期値ゼロ
},
```

## `NISAConfig.totalContributed` の管理方法

**[P4B-CRIT-1] 対応**: `NISAConfig.totalContributed` の定義と管理方法を明確化する。

- `NISAConfig.totalContributed` は「シミュレーション開始時点の累積拠出元本（円）」として定義する
- `SimulationConfig` に持つことで「シミュレーション開始時点の累積拠出額」として機能する
- 年次ループでは `let nisaTotalContributed = config.nisa.totalContributed` でローカル変数として初期化し、毎年の拠出後に更新する（元の `SimulationConfig` への副作用なし）
- 生涯上限チェック: `nisaTotalContributed + contribution <= 18_000_000`
  （新NISAでは売却後に枠が復活するが、初期実装では無視する）

```typescript
// runSingleSimulation 内
let nisaTotalContributed = config.nisa.totalContributed  // ローカル変数として初期化

for (const year of years) {
    // NISA拠出可能額の計算
    const contribution = getNisaContributionForYear(
        config.nisa.annualContribution,
        config.nisa,
        nisaTotalContributed  // ローカル変数を渡す
    )
    nisaTotalContributed += contribution  // ローカル変数を更新（config は変更しない）
    // ...
}
```

## テスト影響分析

### 既存テストへの影響

既存テストの拠出額（120万円/年）は年間上限（360万円）内のため影響なし。

### 新規テストケース

```typescript
describe('NISA年間枠', () => {
    test('希望拠出額 ≤ 年間360万: そのまま拠出', () => {})
    test('希望拠出額 > 年間360万: 360万にキャップ', () => {
        // annualContribution: 4_000_000 → 実際は 3_600_000
    })
    test('生涯1800万に達したら拠出停止', () => {
        // totalContributed = 18_000_000 → contribution = 0
    })
    test('生涯限度額が途中で満たされる: 残り枠だけ拠出', () => {
        // totalContributed = 17_000_000, desired = 1_200_000 → 実際は 1_000_000
    })
})
```

---

# Phase 4C: iDeCo 60歳制約

## インターフェース変更

```typescript
// IDeCoConfig に追加
export interface IDeCoConfig {
    enabled: boolean
    monthlyContribution: number
    // 追加:
    withdrawalStartAge: number    // 受取開始年齢（デフォルト: 60）
    isLocked: boolean             // 60歳未満は true（UI表示用）
}
```

## 関数仕様

### iDeCo の取り崩し制約

```typescript
/**
 * iDeCo資産が取り崩し可能かどうかを返す
 * @param personAge person1の年齢
 * @param withdrawalStartAge 受取開始年齢
 * @returns true = 取り崩し可能
 */
function isIDeCoWithdrawable(
    personAge: number,
    withdrawalStartAge: number = 60
): boolean {
    return personAge >= withdrawalStartAge
}
```

### iDeCo 受取時の課税計算（案1採用: 最簡略）

**[P4C-CRIT-1] 対応**: 案1（最簡略）を採用する。

**採用する方針: 案1（最簡略）**
- 60歳以降は `idecoAssets` も `totalAssets` に統合して自由に使えるものとする
- 課税は概算20%を一時金受取時にかける
- 年次ループ: `person1Age === config.person1.idecoWithdrawalStartAge`（デフォルト60）の年に
  `idecoAfterTax = idecoAssets * 0.8` を `taxableStockAssets` に加算し `idecoAssets = 0` にする

```typescript
// 年次ループ内（P4C: iDeCo 60歳時の一時受取処理）
if (person1Age === config.ideco.withdrawalStartAge) {
    const idecoAfterTax = idecoAssets * 0.8  // 概算20%課税
    newTaxableStock += idecoAfterTax          // taxableStockAssets に加算
    newIdeco = 0                              // iDeCo残高をゼロに
}
```

**この方針を採用した理由**:
- 毎年 `idecoAssets / 20` の均等受取方式は「残高が増えれば取り崩し額も増える」という
  奇妙な挙動を引き起こし（複利成長中に毎年の取り崩し額が増大）、実態と乖離する
- 一時金受取として60歳で一括処理することで、シミュレーションがシンプルになる
- 60歳以降は全資産が自由に使える状態になり、FIRE後の生活費計算が統一できる

## DEFAULT_CONFIG変更

```typescript
ideco: {
    enabled: true,
    monthlyContribution: 23000,
    withdrawalStartAge: 60,   // 追加
    isLocked: true,           // 追加（初期値: ロック中）
},
```

## テスト影響分析

### 既存テストへの影響

既存テストは iDeCo の取り崩しを行っていない（拠出・成長のみ確認）。
`isLocked` がデフォルト true でも拠出・成長のみのテストは変更なし。

### 新規テストケース

```typescript
describe('iDeCo 60歳制約', () => {
    test('60歳未満: idecoAssets は取り崩し不可（不足が発生しても取り崩せない）', () => {
        // personAge=55, isPostFire=true, shortfall発生
        // → idecoAssets は変化しない（cashAssets や taxableStockAssets から取り崩し）
    })
    test('60歳以降: idecoAssets が取り崩し可能になる', () => {
        // personAge=60 → idecoAssets から不足分を補填できる
    })
    test('60歳で受取開始: idecoAssets が年々減少する', () => {
        // calculateIDeCoAnnualWithdrawal による毎年の受取確認
    })
})
```

---

# Phase 4D: 株式売却税（20.315%）

## インターフェース変更

```typescript
// SimulationConfig に追加（4A で既に追加済みのため参照のみ）
// stocksCostBasis は 4A で追加済み

// YearlyData に追加
export interface YearlyData {
    // ...既存
    capitalGains: number          // 当年の実現益（課税口座売却時）
    capitalGainsTax: number       // 当年の売却税額
}
```

## 関数仕様

### `withdrawFromTaxableAccount` — 課税口座売却と税計算

```typescript
/**
 * 課税口座から指定額を取り崩す際の売却税を計算する
 * 含み益割合に基づいて課税額を計算し、手取り売却額を返す
 *
 * @param targetAmount 必要な手取り金額（税引き後）
 * @param currentStockValue 現在の評価額
 * @param costBasis 取得原価
 * @returns 売却に必要な評価額・実現益・税額
 */
function withdrawFromTaxableAccount(
    targetAmount: number,
    currentStockValue: number,
    costBasis: number
): {
    sellAmount: number        // 売却する評価額
    realizedGains: number     // 実現益（売却額 - 取得原価相当）
    capitalGainsTax: number   // 売却税
    netProceeds: number       // 手取り（targetAmount と等しくなるよう逆算）
    remainingValue: number    // 売却後の残評価額
    remainingCostBasis: number // 売却後の残取得原価
}
```

アルゴリズム:
```
TAX_RATE = 0.20315  // 所得税15.315% + 住民税5%

// 含み益割合
if currentStockValue <= 0: return { sellAmount: 0, ... }
gainRatio = (currentStockValue - costBasis) / currentStockValue
// gainRatio = 0 → 全額元本（益なし）, gainRatio = 1 → 全額益

// targetAmount（手取り）を得るために必要な売却額の逆算:
// netProceeds = sellAmount - sellAmount * gainRatio * TAX_RATE
// targetAmount = sellAmount * (1 - gainRatio * TAX_RATE)
// sellAmount = targetAmount / (1 - gainRatio * TAX_RATE)
sellAmount = targetAmount / (1 - gainRatio * TAX_RATE)
sellAmount = min(sellAmount, currentStockValue)  // 残高上限

// 実際の計算
gainRatioOfSale = (currentStockValue - costBasis) / currentStockValue
costBasisSold = sellAmount * (costBasis / currentStockValue)  // 売却分の取得原価
realizedGains = sellAmount - costBasisSold
capitalGainsTax = realizedGains * TAX_RATE
netProceeds = sellAmount - capitalGainsTax

remainingValue = currentStockValue - sellAmount
remainingCostBasis = costBasis - costBasisSold
```

### `capitalGainsThisYear` の追跡と `assets` フィールドの明示

**[P4A-CRIT-2] 対応**: 年次ループ内で `assets` フィールドを明示的に計算して `yearlyData` に記録する。

年次ループ内で実現した売却益を蓄積し、`YearlyData` に記録:

```typescript
// runSingleSimulation 内
let capitalGainsThisYear = 0
// ...
const withdrawal = withdrawFromTaxableAccount(shortfall, taxableStockAssets, stocksCostBasis)
capitalGainsThisYear += withdrawal.realizedGains
// ...
yearlyData.push({
    cashAssets: newCashAssets,
    taxableStockAssets: newTaxableStock,
    assets: newCashAssets + newTaxableStock,   // 後方互換フィールド（NISA・iDeCoを除く）
    // 注意: assets は cashAssets + taxableStockAssets の合計として毎年末に明示的に計算する
    // NISA・iDeCo は含まない（後方互換のため従来の assets フィールドと等価）
    capitalGains: capitalGainsThisYear,
    capitalGainsTax: withdrawal.capitalGainsTax,  // withdrawFromTaxableAccount の計算値を使用
    // ...
})
// P6 の国保計算用に前年の capitalGains を繰り越す
capitalGainsLastYear = capitalGainsThisYear  // 次の年のループで使用（ループ外で let 宣言）
```

## DEFAULT_CONFIG変更

変更なし（4A での `stocksCostBasis` 追加で対応済み）。

## テスト影響分析

### 既存テストへの影響

既存テストは課税口座の売却を行わないため影響なし（`taxableStockAssets = 0` または取り崩し発生しないケース）。

### 新規テストケース

```typescript
describe('株式売却税（20.315%）', () => {
    test('含み益ゼロ（取得原価 = 評価額）: 税ゼロ', () => {
        // costBasis = currentValue → realizedGains = 0, tax = 0
    })
    test('含み益100%（取得原価ゼロ）: 売却額の20.315%が税', () => {
        // costBasis = 0, currentValue = 1_000_000, targetAmount = 793_500
        // → sellAmount = 1_000_000, tax = 203_150, netProceeds = 796_850
    })
    test('含み益50%: 税が正しく計算される', () => {
        // costBasis = 500_000, currentValue = 1_000_000 → gainRatio = 0.5
        // targetAmount = 900_000 → sellAmount = 900_000 / (1 - 0.5 * 0.20315)
    })
    test('売却後の残評価額・残取得原価が正しく更新される', () => {
        // 売却比例で costBasis が按分される
    })
    test('capitalGains が YearlyData に記録される', () => {})
    test('売却が不要な年（余剰あり）: capitalGains = 0', () => {})
})
```

## 後方互換性

### 全体（4A〜4D）の後方互換戦略

**[P4A-CRIT-1] 対応**: `cfg()` の `base` 側で `currentAssets: 0` のままにせず、以下の修正版を使用する。

```typescript
// 修正版 cfg() ヘルパー（Phase 4A 後）
function cfg(overrides: Partial<SimulationConfig> = {}): SimulationConfig {
    const base: Partial<SimulationConfig> = {
        cashAssets: 0,               // currentAssets: 0 から変更
        taxableStockAssets: 0,       // 追加
        stocksCostBasis: 0,          // 追加
        // currentAssets は base に含めない
        // ...その他のフィールドは現状維持
    }
    return {
        ...base,
        ...overrides,
        // currentAssets が指定された場合は cashAssets にマッピング
        cashAssets: overrides.currentAssets ?? overrides.cashAssets ?? 0,
        taxableStockAssets: overrides.taxableStockAssets ?? 0,
    }
}
```

この修正により:
- `base` 側に `currentAssets: 0` を含めない（`cashAssets: 0` に変更）
- `overrides.currentAssets` が指定された場合に `cashAssets` に正しく変換される

既存テストの `currentAssets: N` 指定は `cashAssets: N` に自動マッピングされる。
`assets` フィールドは `cashAssets + taxableStockAssets` の合計として年次ループ内で明示的に計算する。

## 実装上の注意点

### 1. 資産更新の順序

年次ループ内の資産更新順序が重要:
1. 投資リターン適用（NISA・iDeCo・課税口座）
2. 収入・支出計算
3. 余剰/不足の計算
4. 余剰なら投資（NISA枠→課税口座）
5. 不足なら取り崩し（NISA→課税口座売却→現金）

### 2. NISA売却に非課税優遇

NISA口座からの売却は非課税（売却益に20.315%がかからない）。
取り崩し順位: NISA（非課税）→ 課税口座（課税あり）→ 現金 が最適。

### 3. iDeCo のロック期間と FIRE

FIRE達成後に iDeCo が60歳未満でロックされていると、FIRE後の生活費を
NISA・課税口座・現金のみで賄う必要がある。
この制約により実質的な「FIRE可能資産」は `totalAssets - idecoAssets`（60歳未満の場合）になる。
FIRE判定ロジックの修正が必要:

```typescript
// FIRE判定の修正（60歳未満はiDeCoを除外）
const liquidAssets = person1Age < 60
    ? assets + nisaAssets  // iDeCo除外
    : assets + nisaAssets + idecoAssets
const isFireAchieved = liquidAssets >= currentFireNumber
```

### 4. 年次ループの前年値繰り越し変数の初期値（全フェーズ共通）

```typescript
// runSingleSimulation 冒頭で初期化
let capitalGainsLastYear = 0        // P4D・P6で使用
let lastYearFireIncome = 0          // P6で使用（FIRE前は0）
// 全ての前年値変数の初期値はゼロ
```
