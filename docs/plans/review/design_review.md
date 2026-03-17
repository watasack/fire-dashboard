# 設計書レビュー結果

レビュー実施日: 2026-03-17
レビュワー: Reviewer Agent（Claude Sonnet 4.6）

---

## 総合判定

| Phase | 判定 | 重大問題 | 軽微な問題 |
|-------|------|---------|----------|
| P1 年収（税引き前）入力 | ⚠️要修正 | 2 | 3 |
| P2A ライフステージ別生活費 | ⚠️要修正 | 1 | 2 |
| P2B 住宅ローン | ✅承認 | 0 | 1 |
| P2C 産休・育休 | ⚠️要修正 | 2 | 2 |
| P2D 児童手当 | ⚠️要修正 | 1 | 1 |
| P3 年金詳細計算 | ⚠️要修正 | 1 | 2 |
| P4A 現金・株式分離管理 | ⚠️要修正 | 2 | 2 |
| P4B NISA年間枠管理 | ⚠️要修正 | 1 | 1 |
| P4C iDeCo 60歳制約 | ⚠️要修正 | 1 | 1 |
| P4D 株式売却税 | ✅承認 | 0 | 2 |
| P5 セミFIRE | ✅承認 | 0 | 2 |
| P6 FIRE後税金・社会保険 | ⚠️要修正 | 2 | 2 |
| P7 取り崩し戦略 | ⚠️要修正 | 1 | 2 |
| P8 UI拡張 | ✅承認 | 0 | 1 |
| P9 MCシミュレーション精度 | ✅承認 | 0 | 1 |
| P10 シナリオA/B比較 | ⚠️要修正 | 1 | 1 |

---

## Phase別レビュー詳細

---

### Phase 1: 年収（税引き前）入力 ＋ 税計算リアーキテクチャ

#### 判定: ⚠️要修正

#### 重大問題（実装前に必ず解決）

**[P1-CRIT-1] 「既存テスト変更不要」戦略の主張は部分的に誤り**

設計書は「テストの期待値は一切変更不要。`cfg()` マッピングで対応可能」と主張しているが、
これはオプション A（Phase 1.0: フィールド名変更のみ）の場合に限り正しい。

設計書自身が第5節「実装上の注意点」で認めているように、給与所得控除を追加すると
手取り計算結果が変わるため既存66テストの期待値が全て無効になる。
設計書内で「オプション A / B」として両案を示しているが、実際に選択すべきアプローチが
確定していないまま「変更不要」と断言している箇所があり、読み手が誤解するリスクが高い。

現在の `__tests__/simulator.test.ts` を精査した結果:
- `収入計算` `税計算ブラケット` `FIRE後の取り崩しモード` 等の全テストが
  `currentIncome` を税引き前年収として渡し、`calculateTax` が社保15%+所得税+住民税10%
  を計算した結果を手取りとして期待値に書いている
- 給与所得控除（例: 年収500万円で約144万円控除）を追加すれば課税所得が大幅に下がり、
  テスト `'20% ブラケット: 年収 7,000,000'` などの期待値 `4_421_500` は成立しなくなる

**修正案**: 設計書の「段階的移行」方針を明文化し直すこと。
- Phase 1.0（フィールド名変更のみ）: テスト期待値変更不要と明記
- Phase 1.1（給与所得控除・社保上限追加）: 全66テストの期待値を一度更新すると明記
- 2段階の完了条件を設計書に追記し、実装者が混乱しないようにする

**[P1-CRIT-2] `calculateTax` の後方互換ラッパーの設計が自己矛盾している**

設計書のコードスニペット（`calculateTax` のラッパー）が以下のようになっている:
```typescript
function calculateTax(income: number): number {
    const si = calculateSocialInsurance(income, 'employee', 35)   // 使われていない
    const breakdown = calculateTaxBreakdown(income, 'employee', 35)
    return breakdown.totalTax
}
```

`si` を計算した直後に `breakdown` で全部やり直すため `si` の行が無意味なデッドコードになっている。
さらに `calculateTaxBreakdown` が給与所得控除を適用すると、この「後方互換ラッパー」の
計算結果が現行 `calculateTax` と異なる値を返し、「後方互換」の目的を果たせなくなる。

**修正案**: 後方互換ラッパーには「給与所得控除なし・社保15%フラット」という
旧計算式を明示的にハードコードするか、Phase 1.1 実施時に正直に「テスト期待値を更新する」
方針を徹底して後方互換ラッパー自体を削除する。

#### 軽微な問題・改善提案

**[P1-MINOR-1] `standardMonthlyRemuneration` の計算式が実務と若干ずれる**

設計書:
```
標準報酬月額（健保）= min(grossIncome / 12, 1_390_000)
```
実際の協会けんぽの標準報酬月額は等級表（32等級）に基づく離散値であり、
`grossIncome / 12` の連続値をそのまま使うのは厳密には誤り。
シミュレーターとしての近似は許容範囲だが、設計書内に「近似として連続値を使用」と
明記することを推奨する。

**[P1-MINOR-2] 復興特別所得税の適用期間の扱いが未確定のまま**

2037年以降も一律適用する（保守的）と方針を示しているが、
`simulationYears=55` などで2038年以降のシナリオが当然発生する。
テスト期待値にどう影響するか（一律2.1%加算か年ごとの分岐か）を
設計書に確定値として記載すべき。

**[P1-MINOR-3] `Person` インターフェースに `employmentType` が必須フィールドとして追加されるが、
`DEFAULT_CONFIG` の `person2` を `homemaker` にするのが自然なシナリオで欠落している**

設計書の `DEFAULT_CONFIG` 変更例では `employmentType: 'employee'` をboth personに設定しているが、
典型ユーザー（共働き）は妻側を時短や専業主婦と設定したいケースが多い。
デフォルトを `'employee'` にするのは問題ないが、UI側で
`employmentType` 選択UIを設けることを設計書に明記しておくべき。

#### 良い点

- 現行実装の `currentIncome` が事実上税引き前として扱われていることを正確に分析できている
- `TaxBreakdown` 型に `standardMonthlyRemuneration` を含め、P3・P6 で再利用する設計は優れている
- `localStorage` マイグレーション関数 `migrateConfig()` を設計書に組み込んだのは実用的
- オプション A/B の2段階移行案を検討している姿勢は評価できる（ただし選択を確定させること）

---

### Phase 2A: ライフステージ別基本生活費

#### 判定: ⚠️要修正

#### 重大問題（実装前に必ず解決）

**[P2A-CRIT-1] 既存の `calculateChildCosts`（教育費）との二重計上リスク**

設計書の `getAdditionalChildCost` の注記に「教育費（EDUCATION_COSTS）との重複計上に注意。
ライフステージ費用には子に関わる全生活費が含まれるため、第1子分は baseExpenses に内包済み」
と書かれているが、実際の年次ループでは現行の `calculateChildCosts` が引き続き呼ばれる。

`expenseMode: 'lifecycle'` を有効にした場合、
- ライフステージ費用（baseExpenses）に第1子の教育費が含まれる（設計意図）
- さらに `calculateChildCosts` が第1子の EDUCATION_COSTS を加算する（二重計上）

この矛盾を解決するロジック（例: `lifecycle` モード時は `calculateChildCosts` をスキップする）
が年次ループの変更仕様として記載されていない。

**修正案**:
- `expenseMode === 'lifecycle'` のとき `calculateChildCosts` の呼び出しを無効化する、または
- ライフステージ費用から教育費を分離して「生活費（食費・住居費等）」のみを対象にする。
どちらの設計を選ぶか明記すること。

#### 軽微な問題・改善提案

**[P2A-MINOR-1] `getLifecycleStageExpenses` 関数に `currentSimYear` 引数が欠落している**

設計書の疑似コード内で `currentSimYear - c.birthYear` を使っているが、
関数シグネチャには `currentSimYear` が存在しない。`person1Age` と `children` だけでは
子の年齢を計算できない（`birthYear` と `currentSimYear` の差が必要）。

**修正案**: シグネチャを以下に変更:
```typescript
function getLifecycleStageExpenses(
    person1Age: number,
    children: Child[],
    currentSimYear: number,      // 追加
    config?: LifecycleExpenseConfig
): number
```

**[P2A-MINOR-2] `expenseMode: 'fixed'` がデフォルトなのに `lifecycleExpenses` を
`SimulationConfig` に必須フィールドとして定義するか `optional` にするかが不明確**

設計書では `lifecycleExpenses?: LifecycleExpenseConfig` と `?` がついているが、
`DEFAULT_CONFIG` の変更例には `lifecycleExpenses` が記載されておらず、
TypeScript の型として `SimulationConfig.lifecycleExpenses` がオプショナルであることを
型定義コードに明示する必要がある。

#### 良い点

- `expenseMode: 'fixed'` をデフォルトにすることで後方互換を完全に維持している
- 第2子以降の追加費用を分離して計算している設計は妥当
- ライフステージ区分（7段階）が実際の生活費統計に基づいており合理的

---

### Phase 2B: 住宅ローン

#### 判定: ✅承認

#### 軽微な問題・改善提案

**[P2B-MINOR-1] 繰り上げ返済が考慮されていない**

`endYear` を固定値として持つ設計は、当初の設計上シンプルで良いが、
繰り上げ返済による完済年前倒しシナリオが実際に多い。
将来拡張として「繰り上げ返済額を `YearlyData` に追跡する」フィールドの
追加を検討リストに入れておくことを推奨する。

#### 良い点

- 設計がシンプルで `mortgage: null` による後方互換が完全
- `calculateMortgageCost` のアルゴリズムが明確で実装ミスが起きにくい
- テストケース（期間中・完済後・FIRE達成比較）が必要十分

---

### Phase 2C: 産休・育休 ＋ 育休給付金

#### 判定: ⚠️要修正

#### 重大問題（実装前に必ず解決）

**[P2C-CRIT-1] 年次近似の精度問題：2年にわたる給付が1年に集約される設計の不整合**

設計書のアルゴリズム疑似コードは「出産年（birthYear）の1年間を産休育休給付金モードとして扱う」
としているが、産前2ヶ月+産後12ヶ月 = 14ヶ月分の給付を1年（12ヶ月）に収めようとしている。

さらに設計書内で:
```
// 翌年（birthYear+1）の1年間を「育休給付金モードの継続」として扱う場合もある
```
と「場合もある」として処理が不確定のまま。

出産月が1月なら産休育休が当年にほぼ収まるが、出産月が11月なら当年は産前2ヶ月のみで
残り12ヶ月（育休）は翌年に跨がる。年次シミュレーターの限界として誤差を許容することは
理解できるが、「年次ループでの適用方法」が確定していないため実装者が判断に迷う。

**修正案**: 以下のいずれかを設計書で確定させること。
- 案1（シンプル）: `birthYear` の年は `maternityLeaveIncome` を使い、`birthYear+1` は
  通常の `grossIncome * 0.67` として計算する（翌年も部分的に育休と仮定）
- 案2（精度重視）: `birthDate` が指定された場合のみ月単位で計算し、未指定なら年単位近似

**[P2C-CRIT-2] 産休育休給付金の非課税処理が年次収入 `income` フィールドと矛盾する**

設計書「産休育休給付金は非課税なので手取りそのまま」としているが、
現行の年次ループでは `totalIncome → calculateTax → netIncome` の流れで
`income` フィールドが設定される。

給付金を「非課税の手取りそのまま」として処理するには、年次ループで
税計算をバイパスして直接 `netIncome` に設定する特別な分岐が必要。
この分岐の実装コードが設計書に示されていない。

**修正案**: 年次ループ内の擬似コードを以下まで具体化すること:
```
if maternityLeaveYear:
    grossIncome = 0  // 就労収入ゼロ
    tax = 0          // 税計算スキップ
    netIncome = calculateMaternityLeaveIncome(...)  // 給付金を直接手取りとして設定
```

#### 軽微な問題・改善提案

**[P2C-MINOR-1] `maternityLeaveChildBirthYears` に person2 への適用が暗黙のうちに前提されているが、
インターフェース上は `Person` に追加されている**

設計書では「Person2（妻）の産前2ヶ月〜産後12ヶ月の収入計算を切替」と説明しているが、
インターフェース変更では `Person` 共通に `maternityLeaveChildBirthYears` を追加している。
person1 も産休を取れるの? という疑問が実装者に生じる。
Person に追加するなら「どの Person の産休育休を計算するか」を設計書で明確化すること。

**[P2C-MINOR-2] 時短勤務の開始年齢が設計されていない**

`partTimeUntilAge` は「時短終了年齢」だが、「時短開始年齢」が定義されていないため、
産休明け（出産翌年）から自動的に時短になるのか、特定の年齢から開始するのか不明。
`partTimeFromAge: number | null` または `partTimeFromChildBirthYear: number | null`
などのフィールド追加を検討すること。

#### 良い点

- 年次シミュレーターとしての誤差範囲（1年以内）を設計書に明記している点は誠実
- `birthDate` オプションによる将来の月次精度向上への拡張ポイントが設計されている
- `selfEmployed` の給付ゼロ処理が明確

---

### Phase 2D: 児童手当

#### 判定: ⚠️要修正

#### 重大問題（実装前に必ず解決）

**[P2D-CRIT-1] 既存の教育費テスト（13本）への影響が設計書で過小評価されている**

設計書「既存テストへの影響: なし（子なしテストが多数）」としているが、
既存の教育費テスト群（`describe('教育費（子ども）')`）では `children` に子を設定しており、
P2D 実装後は `childAllowanceEnabled: true` のデフォルト設定により
`income` フィールドに児童手当が加算される。

`__tests__/simulator.test.ts` の教育費テスト群を確認すると、
テストが直接 `income` を参照しているかは確認できていないが、
設計書内で「`YearlyData.income = netIncome + childAllowance`」と明記しているため、
`income` を参照するテストでは期待値の変化が起きる可能性がある。

精査すると、既存の教育費テストは `childCosts` フィールドのみを確認しており、
`income` は直接見ていないため実際の影響はゼロに近い。しかし設計書の「影響なし」
の根拠説明が不足しており、実装者が油断する恐れがある。

**修正案**: 設計書の影響分析セクションに「教育費テストは `income` を参照しないため
安全であることを確認済み」と明記すること。また `childAllowanceEnabled` のデフォルトを
`false` にして、テスト安全性を高めることも検討。

#### 軽微な問題・改善提案

**[P2D-MINOR-1] 所得制限の扱いについて明記が必要**

2024年10月改定で所得制限撤廃とされているが、設計書にはその根拠（法令・施行日）が
明記されていない。将来の制度改正リスクに対して「2024年10月改定後の制度を使用」と
出典を明記することを推奨。

#### 良い点

- 2024年10月改定後（所得制限撤廃）の最新制度に準拠している
- 第1子と第2子以降の差額（0〜2歳: 15,000 vs 20,000）を正しく区別している
- 非課税給付として `netIncome` への直接加算方式を採用しており合理的

---

### Phase 3: 年金詳細計算

#### 判定: ⚠️要修正

#### 重大問題（実装前に必ず解決）

**[P3-CRIT-1] 2パス問題の解決策に計算上の課題がある**

設計書「実装上の注意点 2」の推奨解決策:
```typescript
const finalGrossIncome = config.person1.grossIncome
    * Math.pow(1 + config.person1.incomeGrowthRate, yearsToRetirement)
const finalMonthlyRemuneration = calculateSocialInsurance(
    finalGrossIncome, 'employee', retirementAge
).standardMonthlyRemuneration
```
この「退職時点の標準報酬月額を平均として使う」アプローチは、
収入が成長する場合（`incomeGrowthRate > 0`）に過大評価になる。

例: 年収500万円・2%成長・30年就労の場合、退職時年収は約905万円になり、
月額754,000円の標準報酬月額を30年間の平均として使うのは、
実際の平均（約630万円/12）と大きく乖離する。

**修正案**: 全就労期間の平均として等比数列の期待値を使う:
```
avgGrossIncome = grossIncome * (1.02^30 - 1) / (0.02 * 30)
```
または設計書に「退職時点の値を平均として使う近似であり、成長率が高い場合は
過大評価になる」と明示して許容範囲として記録すること。

#### 軽微な問題・改善提案

**[P3-MINOR-1] `pensionConfig.pastNationalPensionMonths` が厚生年金加入期間と重複している**

設計書のアルゴリズムでは:
```
totalPensionMonths = person.pensionConfig.pastNationalPensionMonths
    + person.pensionConfig.pastEmployeeMonths  // 厚生年金期間も国民年金加入
    + futureMonths
```
として厚生年金期間も国民年金加入月数に合算しているが、
`pastNationalPensionMonths` の定義が「第1号被保険者（国民年金のみ）の期間」なのか、
「総国民年金加入月数（第2号含む）」なのかが不明確。
実装者が `pastNationalPensionMonths` に厚生年金期間を含めて入力してしまうと
二重計上になる。

**修正案**: `pastNationalPensionMonths` を「第1号被保険者（自営業・学生等）期間のみ」と
明確に定義し、コメントを追加すること。

**[P3-MINOR-2] 専業主婦（`homemaker`）の将来の厚生年金加入が考慮されていない**

専業主婦が就労歴から専業主婦になった場合、`pastEmployeeMonths` を持つことがある。
しかし `homemaker` のアルゴリズムでは `futureMonths` を国民年金に加算しておらず、
シミュレーション期間中に「就労中 → 専業主婦」に切り替わるシナリオへの対応が不明確。

#### 良い点

- `pensionAmount` 固定値優先による後方互換は確実に機能する
- 乗率の簡略化（2003年4月以降の新乗率で統一）を設計書に明記している点は誠実
- マクロ経済スライドを独立した関数として分離したのは適切

---

### Phase 4A: 現金・株式分離管理

#### 判定: ⚠️要修正

#### 重大問題（実装前に必ず解決）

**[P4A-CRIT-1] `currentAssets` の後方互換マッピングが `cfg()` テストヘルパーと矛盾する**

`__tests__/simulator.test.ts` の `cfg()` ヘルパーは現在:
```typescript
const base: SimulationConfig = {
    currentAssets: 0,
    // ...
}
```
として `currentAssets` を使っている。P4A 後に `SimulationConfig` から `currentAssets`
が `@deprecated` の optional になった場合、既存テスト全体の `cfg()` が
`cashAssets: 0, taxableStockAssets: 0` にマッピングされるべきだが、
設計書の `cfg()` ヘルパー変更コード:
```typescript
cashAssets: overrides.currentAssets ?? 0,
```
は `overrides` の `currentAssets` をみているが、`base` の `currentAssets` は 0 のままで、
`base` 内の `currentAssets: 0` が `cashAssets` に変換されない。

実際のテストでは `currentAssets: 25_000_000` などを `overrides` で渡しているため
このケースは動作するが、`cfg()` の `base` 側の対応が不完全。

**修正案**: `cfg()` の `base` を:
```typescript
cashAssets: 0,
taxableStockAssets: 0,
stocksCostBasis: 0,
```
に変更し、`currentAssets` は `base` に含めない。`overrides.currentAssets` が
指定された場合に `cashAssets` に変換するロジックを `cfg()` に明示。

**[P4A-CRIT-2] 年次ループの `assets` フィールドが `cashAssets + taxableStockAssets` の
計算プロパティとして機能するか、別管理されるかが不明**

設計書「YearlyData への追加フィールド」で:
```
assets: number  // 後方互換: cashAssets + taxableStockAssets（旧 assets と等価）
```
と「後方互換」として記載しているが、年次ループ内での `assets` 変数の更新方法が
`cashAssets` と別々に管理するのか、毎年末に `assets = cashAssets + taxableStockAssets`
を自動計算するのかが不明。

既存テストの多くが `result.yearlyData[i].assets` を参照しており、
この値が正確に `cashAssets + taxableStockAssets` になることが保証されないと
テストが壊れる。

**修正案**: 年次ループの疑似コードに `assets` の更新行を明示すること:
```typescript
yearlyData.push({
    // ...
    cashAssets: newCashAssets,
    taxableStockAssets: newTaxableStock,
    assets: newCashAssets + newTaxableStock,  // 後方互換フィールドを明示
})
```

#### 軽微な問題・改善提案

**[P4A-MINOR-1] 余剰現金の投資優先順位でiDeCoが独立して処理されていない**

設計書の余剰資金投資アルゴリズム:
```
nisaContrib = min(余剰, config.nisa.annualContribution)
余剰 -= nisaContrib
idecoContrib = config.ideco.enabled ? ...
newIdeco += idecoContrib
newTaxableStock += max(0, 余剰 - idecoContrib)
```
`余剰` から `nisaContrib` を引いた後、`余剰` を更新しないまま
`余剰 - idecoContrib` を課税口座に投資する計算になっているため、
`余剰 < idecoContrib` の場合に `newTaxableStock` が負になる可能性がある。

**修正案**: iDeCo 拠出後の余剰を明示的に計算:
```
余剰 -= nisaContrib
余剰 -= idecoContrib
newTaxableStock += max(0, 余剰)
```

**[P4A-MINOR-2] `DEFAULT_CONFIG` の変更（`currentAssets: 10M → cashAssets: 2M + taxableStock: 8M`）は
既存ユーザーのデフォルト体験を変化させる**

デフォルト値の変更自体は妥当だが、既存ユーザーが設定を持っていない場合（初回訪問）に
デフォルトが変わるため、UIでの初期表示が変化する。リリースノートへの明記を推奨。

#### 良い点

- 資産の取り崩し優先順位（NISA→課税口座→現金）が税効率上最適な順序
- `AssetState` 型を独立して定義することでロジックの分離が明確

---

### Phase 4B: NISA年間枠管理

#### 判定: ⚠️要修正

#### 重大問題（実装前に必ず解決）

**[P4B-CRIT-1] `NISAConfig.totalContributed` をどこで更新・管理するかが未定義**

設計書に `totalContributed: number` フィールドが追加されているが、
- 初期値はゼロ（設計書に記載）
- 毎年の拠出後にどこで更新するか（`runSingleSimulation` の年次ループ内？）
- 設定として `SimulationConfig` に持つと「シミュレーション開始時点の累積拠出額」
  として機能するが、年次ループで更新すると元の `SimulationConfig` が変更される
  （副作用）

UIから渡す設定値として初期値を使い、年次ループで `let localTotalContributed` として
管理するのが正しい実装だが、設計書には記述がない。

**修正案**: `NISAConfig.totalContributed` を「シミュレーション開始時点の累積拠出元本」
として明確に定義し、年次ループでは `let nisaTotalContributed = config.nisa.totalContributed`
として初期化してローカル変数で管理すると明記する。

#### 軽微な問題・改善提案

**[P4B-MINOR-1] 生涯1800万円上限の計算が「累積拠出元本」ベースであることを明示すべき**

NISA の生涯限度額（1800万円）は「購入簿価残高（元本）」ベースであり、
値上がりした分は含まない。売却によって枠が再利用可能になる（新NISA制度）点も
設計書に記載されていない。

#### 良い点

- `getNisaContributionForYear` の逆算アルゴリズムが明快
- 既存の120万円/年テストが360万円上限以内のため既存テストへの影響はゼロ

---

### Phase 4C: iDeCo 60歳制約

#### 判定: ⚠️要修正

#### 重大問題（実装前に必ず解決）

**[P4C-CRIT-1] iDeCo の毎年均等受取（`idecoAssets / 20`）モデルが現実と乖離しすぎる**

設計書「受取時課税計算（退職所得控除等）は簡略化して実装」として
`idecoAssets / 20`（20年均等受取）を採用しているが:
- `idecoAssets` は毎年変動する（複利成長）ため、年々取り崩し額が変わる
  （残高が増えれば取り崩し額も増えるという奇妙な挙動）
- 受取開始が60歳なら80歳で完了するが、simYears が90歳まであれば
  80歳以降 iDeCo 収入がゼロになる（設計書に記載なし）
- 一時金受取 vs 年金受取の選択による課税の差が無視されている

**修正案**: iDeCo の受取簡略化の方針を以下のいずれかで確定させること。
- 案1（最簡略）: 60歳以降は `idecoAssets` も `totalAssets` に統合して自由に使えるとする
  （課税は概算で20%をかける）
- 案2（現設計維持）: `idecoAssets / 20` だが、20年後に残高ゼロになる処理を明記

#### 良い点

- `withdrawalStartAge` を設定可能にして柔軟性を持たせている
- 60歳未満のロック制約をFIRE判定に反映する修正（`liquidAssets` の計算）が的確

---

### Phase 4D: 株式売却税（20.315%）

#### 判定: ✅承認

#### 軽微な問題・改善提案

**[P4D-MINOR-1] `capitalGainsTax` の `YearlyData` への記録方法に微妙な不整合がある**

設計書の年次ループコード:
```typescript
yearlyData.push({
    capitalGains: capitalGainsThisYear,
    capitalGainsTax: capitalGainsThisYear * TAX_RATE,
})
```
`capitalGainsTax` を `capitalGainsThisYear * TAX_RATE` として計算しているが、
`withdrawFromTaxableAccount` 関数は内部で既に `realizedGains * TAX_RATE` を
`capitalGainsTax` として計算している。年次ループで再度計算することで二重計算になる。
`withdrawal.capitalGainsTax` を合計する方が正確。

**[P4D-MINOR-2] 損益通算・繰越損失が未実装であることを設計書に明記すべき**

複数年にわたる売買で損失が出た場合の繰越控除は未実装。
「将来拡張」として明記しておくこと。

#### 良い点

- `gainRatio` を使った含み益割合による課税の逆算ロジックは数学的に正確
- 売却後の `remainingCostBasis` を按分計算するのは適切

---

### Phase 5: FIRE後収入（セミFIRE）

#### 判定: ✅承認

#### 軽微な問題・改善提案

**[P5-MINOR-1] NISA/iDeCo 拠出条件の修正コード（注意点 3）で `retirementAge` との関係が複雑**

設計書提案のコード:
```typescript
if (config.nisa.enabled && (!isPostFire || isSemiFire) && person1Age < config.person1.retirementAge) {
```
セミFIRE中に `person1Age >= config.person1.retirementAge` になることはあるか？
（FIREは早期退職が前提なのでretirementAgeより早くFIREする想定）
この条件の論理的な組み合わせをテストケースに追加することを推奨。

**[P5-MINOR-2] `semiFireIncome` フィールドが税引き前を示すが名前が紛らわしい**

`YearlyData.semiFireIncome` が「税引き前セミFIRE年収」と定義されているが、
`income` フィールドが「手取り」を示すことと対比すると混乱を招く。
`semiFireGrossIncome` と命名することを推奨。

#### 良い点

- `postFireIncome: null` によるデフォルト後方互換が確実
- FIRE未達成時にセミFIRE収入が加算されないガード条件が正確
- テストケースが6種類と充実しており、境界値（untilAge到達・null設定）が網羅されている

---

### Phase 6: FIRE後税金・社会保険

#### 判定: ⚠️要修正

#### 重大問題（実装前に必ず解決）

**[P6-CRIT-1] 国保の後期高齢者支援分の計算が「医療分の約30%」という粗い近似を設計書で確定させていない**

設計書:
```
// 後期高齢者支援分（簡略化: 医療分の約30%）
supportTotal = medicalTotal * 0.30
```
実際の後期高齢者支援金分の所得割率は自治体によって異なり、全国平均は約3〜4%程度
（所得ベース）であり、医療分の30%という計算は粗すぎる可能性がある。
設計書の国保計算全体が既に近似値ベースであることは理解できるが、
この近似が許容範囲かどうかを設計書内で検証・明記する必要がある。

また `nhisoMaxAnnual: 1_060_000` の上限は医療分+支援分+介護分の合計上限だが、
現行コードでは `min(total, config.nhisoMaxAnnual)` として合計に上限を適用しており、
介護分に個別上限（`longTermCareMax`）も別途かけているため、二重の上限適用になっている。

**修正案**:
```
// 正しい構造
medicalAndSupportTotal = min(medicalTotal + supportTotal, medicalAndSupportMax)
careTotal = min(careTotal, longTermCareMax)
total = medicalAndSupportTotal + careTotal
// 総合上限は含めても良いが上限の内訳を設計書に明記
```

**[P6-CRIT-2] 既存テストへの影響がゼロになるための `cfg()` デフォルト設定が矛盾している**

設計書は「`postFireSocialInsurance` のデフォルト値を全ゼロにすることで
既存テストへの影響をゼロにする」としているが、`DEFAULT_CONFIG` の変更例:
```typescript
postFireSocialInsurance: {
    nhisoIncomeRate: 0.1100,  // ← 本番デフォルト値
    ...
}
```
と `cfg()` ヘルパー用:
```typescript
postFireSocialInsurance: {
    nhisoIncomeRate: 0,       // ← テスト用ゼロ値
    ...
}
```
が別々に存在しており、どちらが `DEFAULT_CONFIG` として `simulator.ts` に実装されるかが
設計書内で確定していない。`DEFAULT_CONFIG` に実際の値を入れると、
既存のFIRE後テストは全て `totalExpenses` が増加して期待値がずれる。

**修正案**: `DEFAULT_CONFIG` には本番値（11%等）を入れ、`cfg()` ヘルパー内で
`postFireSocialInsurance` をゼロにオーバーライドすることを設計書に明示。

#### 軽微な問題・改善提案

**[P6-MINOR-1] 65歳以降の介護保険の扱いが「簡略化として無視も可」とされているが
実装方針を確定すべき**

65歳以降は介護保険が第1号被保険者として年金天引きになり、
国保の介護分ではなくなる。設計書では「簡略化して継続」と「無視も可」の両案が
書かれており、実装者が判断できない状態になっている。

**[P6-MINOR-2] `householdSize` の計算で子どもが均等割の計算に含まれない件を明記**

子どもも国保の被保険者になるため均等割の対象だが、
設計書では `person2 !== null ? 2 : 1` と2人固定。
簡略化として許容するなら「子どもの均等割は省略」と明記すること。

#### 良い点

- FIRE初年度スパイクを `lastYearFireIncome` を繰り越して計算する設計は的確
- 国民年金保険料の60歳以降ゼロ処理が正確
- `cfg()` ヘルパーにゼロ設定を提案して既存テストを保護しようとしている姿勢は評価できる

---

### Phase 7: 取り崩し戦略

#### 判定: ⚠️要修正

#### 重大問題（実装前に必ず解決）

**[P7-CRIT-1] `percentage` 戦略の `actualExpenses` の定義が設計書内で矛盾している**

設計書の `percentage` 戦略アルゴリズム:
```
return totalAssets * safeWithdrawalRate
// 注意: 支出ではなく「取り崩し可能額」として使用。
// 実際の支出は baseExpenses だが、取り崩し上限がこの値になる。
// ...
// 設計判断: ... → 後者を推奨（純粋な SWR引出）
```
として「純粋に `totalAssets * SWR` を年間支出とする」と結論づけているが、
この場合に年金収入やセミFIRE収入があると `savings = income - actualExpenses` が
プラスになり資産が増加するシナリオが発生し得る（支出より収入が多い場合）。
設計書「注意点 2」でこの点を触れているが、実際のループでの取り扱いが
`actualExpenses = totalAssets * SWR` として設定された後、
`savings = netIncome - actualExpenses` で計算されると、
収入があるとき資産が積み上がってしまう挙動になるかどうかを確認していない。

**修正案**: `percentage` 戦略では「取り崩し額 = `totalAssets * SWR`」として
支出と収入を独立させ、不足時は資産から補填、余剰は再投資という
フロー設計を年次ループの疑似コードで明示すること。

#### 軽微な問題・改善提案

**[P7-MINOR-1] `peakAssets` の初期値が P4A 後は `cashAssets + taxableStockAssets` だが
NISA・iDeCo を含めるかどうかが未確定**

設計書コード:
```typescript
let peakAssets = config.cashAssets + config.taxableStockAssets  // 初期値
```
ガードレール判定に使う `totalAssets` は `assets + nisaAssets + idecoAssets` だが、
`peakAssets` の初期値がNISA・iDeCoを含まないため、初期のドローダウン計算が正確でない。

**[P7-MINOR-2] `depletionAge` の計算がiDeCo60歳ロック後の資産を考慮しているか不明**

```typescript
if (data.assets + data.nisaAssets + data.idecoAssets <= 0) {
```
60歳未満でiDeCoがロックされている場合、`idecoAssets > 0` だが実際には使えないため
「資産枯渇」の判定が甘くなる。
`liquidAssets`（P4Cで定義した流動性判定）を使うべき。

#### 良い点

- `withdrawalStrategy: 'fixed'` デフォルトによる完全後方互換
- ガードレール戦略の3段階閾値・削減率のパラメータ化が適切
- `discretionaryRatio` を分離したことで必須支出を守れる設計

---

### Phase 8: UI拡張

#### 判定: ✅承認

#### 軽微な問題・改善提案

**[P8-MINOR-1] `calculateFireAchievementRate` の計算で `yearlyData[0]` が
シミュレーション年 0 の値（初年末）であることに注意が必要**

現行の年次ループは `year = 0` から始まり、`assets = config.currentAssets * (1 + return) + savings`
として「年初資産に運用収益と貯蓄を加えた年末残高」が記録される。
「現時点の資産」として `yearlyData[0]` の初期値ではなく、
シミュレーション開始時の `config.currentAssets`（または `cashAssets + taxableStockAssets`）
を分子に使うべきケースも考えられる。

#### 良い点

- CLAUDE.md の Recharts 制約（ComposedChart内フラグメント禁止・SVG fill CSS変数禁止）を
  設計書に明示しており、実装者が誤りを犯さないよう丁寧に記載されている
- `formatAnnualTableData` と `formatCashFlowChartData` を `simulator.ts` の一部として
  定義することで、UI コンポーネントとの責任分離が明確
- 枯渇年齢の表示UIとKPIカードの設計が具体的でユーザー価値が高い

---

### Phase 9: MCシミュレーション精度向上

#### 判定: ✅承認

#### 軽微な問題・改善提案

**[P9-MINOR-1] AR(1)モデルの長期分散の説明に誤りがある可能性**

設計書「数学的性質」:
```
AR(1)モデルの長期分散 = volatility^2 / (1 - speed^2)
```
AR(1)過程 `r_t = mu + speed*(mu - r_{t-1}) + epsilon` は、
一般的な AR(1) 形式 `r_t = c + phi * r_{t-1} + epsilon` に変換すると
`phi = -speed`（負の自己相関）になる。
定常分散は `sigma^2 / (1 - phi^2) = volatility^2 / (1 - speed^2)` となり
数式自体は正しいが、`speed > 0` の平均回帰モデルでは `phi = -speed`
（負の係数）を意味するため、`speed = 0.3` は「1期ラグの相関が -0.3」となる。
設計書に「負の自己相関（平均回帰）を意味する」と補足説明を追記することを推奨。

#### 良い点

- `mcReturnModel: 'normal'` デフォルトで完全後方互換を保証
- `generateRandomReturns` の統合関数リファクタリングで呼び出し側の変更なし
- S&P500の歴史的リターンデータ（50年分）を `DEFAULT_SP500_RETURNS` として提供する設計は実用的
- ブロックブートストラップによる時系列依存性保持の設計が学術的に妥当

---

### Phase 10: シナリオA/B比較

#### 判定: ⚠️要修正

#### 重大問題（実装前に必ず解決）

**[P10-CRIT-1] `runScenarioComparison` が `fireAchievementRate` を参照しているが
P8 実装前は `SimulationResult` にそのフィールドが存在しない**

設計書のコード:
```typescript
diffSummary: {
    fireAchievementRateDiff: planB.fireAchievementRate - planA.fireAchievementRate,
},
```
`fireAchievementRate` は P8 で `SimulationResult` に追加されるフィールドであり、
P10 は P8 完了後に実装する方針なので問題ないが、設計書に「P8 が前提」と
明示的に記載し、P8 未実装状態での P10 実装を防止する注意書きが必要。

また `diffSummary.fireAgeDiff` の計算:
```typescript
const fireAgeDiff = (planB.fireAge !== null && planA.fireAge !== null)
    ? planB.fireAge - planA.fireAge
    : null
```
はどちらか一方が null の場合に `null` を返しているが、
「AはFIREするがBはしない」「BはFIREするがAはしない」という重要な比較情報が
`null` に埋没してしまう。

**修正案**: `ScenarioDiffSummary` に:
```typescript
planAFiresOnly: boolean   // Aだけが指定期間内にFIREする
planBFiresOnly: boolean   // Bだけが指定期間内にFIREする
```
を追加し、`fireAgeDiff: null` の場合の意味を明確化すること。

#### 軽微な問題・改善提案

**[P10-MINOR-1] `applyScenarioChanges` での `person2: null` の処理に潜在的なバグがある**

```typescript
person2: changes.person2 !== undefined
    ? (changes.person2 === null ? null : { ...baseConfig.person2, ...changes.person2 })
    : baseConfig.person2,
```
`baseConfig.person2` が `null` のとき、`changes.person2` が非null の場合
`{ ...null, ...changes.person2 }` となるが、TypeScript で `{...null}` は
空オブジェクト `{}` になるため、`changes.person2` が `Partial<Person>` だと
必須フィールド（`grossIncome`, `currentAge` 等）が欠落した不完全な Person が生成される。

**修正案**: `baseConfig.person2` が null の場合は `changes.person2` をそのまま使うか、
エラーを投げる処理を追加すること。

#### 良い点

- `generateScenarios` との後方互換が `applyScenarioChanges` の設計で維持されている
- `localStorage` マイグレーション（P1の `migrateConfig`）を P10 でも再利用する設計が一貫
- グラフ重ね表示での Recharts 実装例が CLAUDE.md 制約（フラグメント禁止）に準拠している

---

## 横断的な懸念事項

### 1. YearlyData フィールドの急増による型管理の複雑化

P1〜P7 を経由すると `YearlyData` に追加されるフィールド数:
- P1: `grossIncome`, `totalTax` (+2)
- P2A: `lifecycleStage` (+1)
- P2B: `mortgageCost` (+1)
- P2D: `childAllowance` (+1)
- P4A: `cashAssets`, `taxableStockAssets` (+2)
- P4D: `capitalGains`, `capitalGainsTax` (+2)
- P5: `isSemiFire`, `semiFireIncome` (+2)
- P6: `nhInsurancePremium`, `nationalPensionPremium`, `postFireSocialInsurance`, `capitalGainsLastYear` (+4)
- P7: `withdrawalStrategy`, `drawdownFromPeak`, `discretionaryReductionRate`, `actualExpenses` (+4)

合計 **19フィールドが追加**される。現在の `YearlyData` は12フィールドなので最終的に31フィールドになる。
型定義のメンテナンスコストと、各フィールドが未設定（undefined）になるフェーズを
全設計書横断で管理するルールが必要。

**推奨**: 各フィールドに `?` (optional) を適切につけるか、関連するフィールドをサブオブジェクトに
グループ化する（例: `taxDetails: TaxDetails`, `assetDetails: AssetDetails`）ことを検討すること。

### 2. `calculateTax` と `calculateTaxBreakdown` の混在期間の管理

P1 実装後しばらくの間、内部で `calculateTax`（旧）と `calculateTaxBreakdown`（新）が
混在することになるが、どの関数をどのコードパスで使うかのルールが設計書横断で
一貫して記載されていない。特に P3 の `getPensionAmount` 内での税計算パスが不明確。

**推奨**: P1 完了後の「全コードパスで `calculateTaxBreakdown` を使う」移行完了基準を
チェックリストとして設計書に追記すること。

### 3. 年次ループへの前年値繰り越し変数の増加

P4D・P5・P6 を経ると、年次ループ外で管理する前年値変数が:
- `capitalGainsLastYear` (P4D)
- `semiFIREGrossLastYear` (P5+P6)
- `lastYearFireIncome` (P6)

として3変数増加する。これらの初期値（year=0 の前年値）をどう扱うかが
設計書で統一されていない（おそらく全ゼロだが明記されていない）。

**推奨**: `runSingleSimulation` の前年値変数の初期値を設計書に明示すること。

### 4. `expenseMode: 'lifecycle'` と `calculateChildCosts` の重複計上問題（P2A参照）

前述の通り、`lifecycle` モードでは `calculateChildCosts` との二重計上が発生するリスクがある。
これは P2A のみの問題ではなく、年次ループ全体の `totalExpenses` 計算ロジックを
変更する必要があるため横断的な対応が必要。

---

## 実装順序への推奨

現在の計画（P1 → P2A-D → P3 → P4A-D → P5 → P6 → P7 → P8 → P9 → P10）は
概ね適切だが、以下の変更を推奨する。

### 推奨変更点

1. **P1 を 1.0（フィールド名変更のみ）と 1.1（計算ロジック改善）の2段階に分割**
   - P1.0: `currentIncome → grossIncome` リネーム + `employmentType` 追加（テスト影響ゼロ）
   - P1.1: 給与所得控除・社保上限・介護保険を追加（全66テスト期待値を一括更新）

2. **P2A は P2A-lifecycle と P2A-fixedmode を分離してリリース**
   - `expenseMode: 'fixed'` のデフォルト動作確認後に `lifecycle` モードを追加
   - 教育費との二重計上問題（P2A-CRIT-1）を解決してから lifecycle を有効化

3. **P4A〜P4D は 4A 完了・テスト通過後に 4B〜4D を順次実装**
   - 特に 4A の `assets` フィールド後方互換が確認できてから次ステップへ

4. **P6 は `cfg()` ヘルパーへのゼロ設定追加を先に行い、既存テストの安全性を確認してから実装**

5. **P9 は依存関係がないため P1.0 直後に実装してもよい（高コスパ）**
