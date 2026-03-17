# Phase 9: MCシミュレーション精度向上

## 概要

現行の Monte Carlo シミュレーションは毎年のリターンが独立した正規分布（IID）を仮定している。
実際の株式市場には「平均回帰」の傾向があり、暴落後はリターンが回復しやすい。
Phase 9 では Mean-Reversion（AR型）モデルとブートストラップ法を追加し、
現実に近い市場シナリオを生成できるようにする。

## 依存Phase

- 前提: なし（他フェーズと独立して実施可能）
- 影響: P8（MC結果の精度向上が枯渇年齢・成功率の信頼性に直結）

---

## インターフェース変更

### SimulationConfig

```typescript
// 変更前
export interface SimulationConfig {
    investmentReturn: number       // 期待リターン
    investmentVolatility: number   // ボラティリティ
    // ...
}

// 変更後
export interface SimulationConfig {
    investmentReturn: number
    investmentVolatility: number
    // 追加:
    mcReturnModel: MCReturnModel            // MCモデルの選択
    meanReversionConfig?: MeanReversionConfig  // meanReversion モード用
    bootstrapConfig?: BootstrapConfig          // bootstrap モード用
}

// 追加
export type MCReturnModel = 'normal' | 'meanReversion' | 'bootstrap'

export interface MeanReversionConfig {
    speed: number           // 平均回帰速度（0.0〜1.0、推奨: 0.3）
    // 解釈: 0 = ランダムウォーク（= normal と同じ）, 1 = 完全平均回帰
}

export interface BootstrapConfig {
    historicalReturns: number[]    // 過去の年次リターンデータ（小数: 0.10 = 10%）
    // デフォルトデータ: 日経225 or S&P500 の過去30〜50年分
    blockSize?: number             // ブロックブートストラップのブロックサイズ（デフォルト: 1）
    // blockSize > 1 にすると連続した複数年を一括サンプリング（時系列依存性を保持）
}
```

---

## 関数仕様

### `generateNormalRandom` — 現行（変更なし）

```typescript
// 変更なし（後方互換）
function generateNormalRandom(mean: number, stdDev: number): number {
    const u1 = Math.random()
    const u2 = Math.random()
    const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
    return mean + stdDev * z
}
```

### `generateMeanReversionReturns` — AR(1) 型 Mean-Reversion リターン生成

```typescript
/**
 * AR(1) モデルによる平均回帰型リターン系列を生成する
 *
 * モデル式:
 *   r_t = mu + speed * (mu - r_{t-1}) + epsilon_t
 *   epsilon_t ~ N(0, volatility)
 *
 * 解釈:
 *   前年リターンが期待値より低い → 正のバイアスが加わる（平均回帰）
 *   前年リターンが期待値より高い → 負のバイアスが加わる
 *
 * @param years シミュレーション年数
 * @param mean 長期期待リターン
 * @param volatility ボラティリティ
 * @param speed 平均回帰速度（0.0〜1.0）
 * @returns 年次リターン配列
 */
function generateMeanReversionReturns(
    years: number,
    mean: number,
    volatility: number,
    speed: number
): number[]
```

アルゴリズム:
```
returns = []
prevReturn = mean  // 初期値: 期待値から開始

for t in 0..years:
    // ランダム誤差
    epsilon = generateNormalRandom(0, volatility)
    // AR(1) 更新式
    r_t = mean + speed * (mean - prevReturn) + epsilon
    returns.push(r_t)
    prevReturn = r_t

return returns
```

**数学的性質**:
- `speed = 0` のとき: `r_t = mean + epsilon` → 正規分布と同じ（IID）
- `speed = 0.3` のとき: 前年の偏差の30%が逆方向に補正される
- `speed = 1.0` のとき: 前年の偏差が完全に補正される（理論的すぎる）

**長期分散**:
- AR(1)モデルの長期分散 = `volatility^2 / (1 - speed^2)`
- `speed > 0` のとき長期分散が小さくなり、長期リターンが安定する

### `generateBootstrapReturns` — ブートストラップ型リターン生成

```typescript
/**
 * 過去実績データからランダムサンプリングでリターン系列を生成する
 * ブロックブートストラップ（blockSize > 1）で時系列依存性を保持可能
 *
 * @param years シミュレーション年数
 * @param historicalReturns 過去の年次リターンデータ
 * @param blockSize ブロックサイズ（デフォルト: 1 = 単純ブートストラップ）
 * @returns 年次リターン配列
 */
function generateBootstrapReturns(
    years: number,
    historicalReturns: number[],
    blockSize: number = 1
): number[]
```

アルゴリズム（単純ブートストラップ, blockSize=1）:
```
returns = []
for t in 0..years:
    randomIndex = Math.floor(Math.random() * historicalReturns.length)
    returns.push(historicalReturns[randomIndex])
return returns
```

アルゴリズム（ブロックブートストラップ, blockSize > 1）:
```
returns = []
while returns.length < years + 1:
    startIndex = Math.floor(Math.random() * (historicalReturns.length - blockSize))
    block = historicalReturns[startIndex..startIndex+blockSize]
    returns = returns.concat(block)
return returns.slice(0, years + 1)
```

### `generateRandomReturns` — 統合関数（リファクタリング）

```typescript
/**
 * MCモデルに基づいてランダムリターン系列を生成する統合関数
 * @param years シミュレーション年数
 * @param config シミュレーション設定
 * @returns 年次リターン配列
 */
function generateRandomReturns(
    years: number,
    config: SimulationConfig
): number[] {
    switch (config.mcReturnModel) {
        case 'normal':
            return generateNormalReturns(years, config.investmentReturn, config.investmentVolatility)
        case 'meanReversion':
            return generateMeanReversionReturns(
                years,
                config.investmentReturn,
                config.investmentVolatility,
                config.meanReversionConfig?.speed ?? 0.3
            )
        case 'bootstrap':
            if (!config.bootstrapConfig?.historicalReturns) {
                // フォールバック: 正規分布モデル
                console.warn('bootstrap モードでは bootstrapConfig.historicalReturns が必要です。normal モードにフォールバックします。')
                return generateNormalReturns(years, config.investmentReturn, config.investmentVolatility)
            }
            return generateBootstrapReturns(
                years,
                config.bootstrapConfig.historicalReturns,
                config.bootstrapConfig.blockSize ?? 1
            )
        default:
            return generateNormalReturns(years, config.investmentReturn, config.investmentVolatility)
    }
}

// 分離した正規分布生成（既存関数のリネーム）
function generateNormalReturns(years: number, mean: number, volatility: number): number[] {
    return Array.from({ length: years + 1 }, () =>
        generateNormalRandom(mean, volatility)
    )
}
```

---

## DEFAULT_CONFIG変更

```typescript
// 追加
mcReturnModel: 'normal',     // デフォルト: 既存と同じ正規分布モデル
// meanReversionConfig と bootstrapConfig は省略（使用時のみ指定）
```

---

## YearlyData / SimulationResult への追加フィールド

```typescript
// MonteCarloResult に追加
export interface MonteCarloResult {
    // ...既存
    mcModel: MCReturnModel        // 使用したMCモデルの種類（結果の透明性のため）
}
```

---

## テスト影響分析

### 既存テストへの影響

`mcReturnModel: 'normal'` がデフォルトで、現行の `generateRandomReturns` の挙動を保つ。
既存の MC テストへの影響はゼロ。

`runMonteCarloSimulation` の内部で `generateRandomReturns(config.simulationYears, config)` に
シグネチャが変わるが、`config` から `investmentReturn` と `investmentVolatility` を取得するため
実質的に現行と同じ計算が行われる。

### 新規テストケース

```typescript
describe('MC リターンモデル', () => {
    describe('normal（現行）', () => {
        test('mcReturnModel=normal: 既存と同じリターン分布になる', () => {
            // mean=0.05, std=0.15 → 生成されたリターンが正規分布に近い
        })
    })

    describe('meanReversion', () => {
        test('speed=0: normal モードと統計的に同等の分布', () => {
            // speed=0 → AR(1)の平均回帰項ゼロ → IIDと同じ
        })

        test('speed=0.3: 連続2年の下落後、翌年リターンが期待値に近づく傾向', () => {
            // 統計的検定: 前年リターン < mean の後のリターンの平均が normal より高い
        })

        test('speed=0.3: 長期シミュレーションのリターン分散が normal より小さい', () => {
            // 1000回MCで生成したリターン列の標準偏差を比較
        })

        test('meanReversion モードの MC 成功率が normal より高くなる（同一設定）', () => {
            // 平均回帰により暴落後の回復が安定するため、成功率が向上する
        })
    })

    describe('bootstrap', () => {
        test('historicalReturns からのみサンプリングされる', () => {
            // 生成されたリターンが historicalReturns の値のみ含む
        })

        test('blockSize=5: 5年ブロック単位でサンプリングされる', () => {
            // 生成系列の5年ブロックが historicalReturns の連続する5年分に一致する
        })

        test('historicalReturns 未指定: normal にフォールバック', () => {
            // bootstrapConfig なし → normal と同じ動作
        })
    })

    describe('モデル切り替え', () => {
        test('同一設定でモデルを切り替えると MC 結果が変化する', () => {
            // normal vs meanReversion vs bootstrap でsuccessRateが異なる
        })

        test('MonteCarloResult.mcModel に使用モデルが記録される', () => {})
    })
})
```

---

## 後方互換性

`mcReturnModel: 'normal'` がデフォルトのため既存のMCシミュレーション動作は完全に維持される。
`runMonteCarloSimulation` のシグネチャ変更はなし。

---

## 実装上の注意点

### 1. 決定論的テストとのコンフリクト

既存テスト `'同一コンフィグで再実行すると同じ結果（決定論的）'` はランダムリターンなしの
`runSingleSimulation` を対象としており、MCシミュレーションは対象外。
MCのテストは統計的な検証（平均・分散の比較）に留め、決定論的な期待値テストは避ける。

### 2. AR(1)モデルのバイアス

AR(1)モデルの `r_t = mu + speed * (mu - r_{t-1}) + epsilon` では、
初期値 `prevReturn = mean` から始めると数年間は過渡的な挙動を示す。
バーンイン期間（最初の10年程度を捨てる）は不要だが、
`speed` が大きいほど最初の数年のリターンが mean に近くなる点を設計書として記録。

### 3. 歴史的リターンデータのデフォルト値

ブートストラップモードのデフォルト `historicalReturns` として、
以下のデータセットを `DEFAULT_BOOTSTRAP_RETURNS` として提供することを検討:

```typescript
// S&P500の年次リターン（1970〜2024年の概算値, 50年分）
export const DEFAULT_SP500_RETURNS: number[] = [
    0.040, -0.146, 0.187, -0.145, -0.262,
    0.371, 0.238, -0.071, 0.065, 0.184,
    0.321, -0.049, 0.215, 0.223, 0.062,
    0.316, 0.185, 0.052, 0.166, 0.315,
    0.026, 0.076, 0.099, 0.013, 0.379,
    0.228, 0.333, 0.285, 0.210, -0.091,
    -0.119, -0.221, 0.287, 0.108, 0.048,
    0.158, 0.057, -0.370, 0.264, 0.152,
    0.021, 0.160, 0.323, 0.135, 0.014,
    0.119, 0.218, -0.044, 0.314, 0.245,
]
```

データの出典・精度についてはUIで明示する。

### 4. シミュレーション時間への影響

Mean-Reversion と Bootstrap は Normal と同等の計算コスト（1操作追加程度）のため、
1000回MCのパフォーマンスへの影響は無視できる。
