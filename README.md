# FIRE Simulator — シミュレーション仕様書

> **注記**: このドキュメントはシミュレーションの設計仕様書です。実装は `lib/simulator.ts` を参照してください。
> 個人用ダッシュボード（Python）の詳細仕様も含まれていますが、汎用 TypeScript 実装の参考仕様として維持しています。

---

## TypeScript 実装

```bash
# 開発サーバー起動
pnpm dev        # http://localhost:3000

# 本番ビルド確認
npx next build

# テスト実行
npx vitest run
```

シミュレーション本体: `lib/simulator.ts`
開発ガイド: `docs/DEVELOPMENT.md`

---

## 月次シミュレーションの処理順序

各月の処理は以下の順序で行われる。

```
① 年変わりチェック
   → NISA年間投資額をリセット
   → prev_year_capital_gains = 今年の実現益（翌年の健康保険料計算に使用）

② 収入計算
   → 労働収入（person1・person2）、年金、児童手当を合算

③ 支出計算
   → 基本生活費、教育費、住宅ローン、メンテナンス、
      社会保険料（FIRE後のみ）を合算

④ 収入を現金に加算
   cash += total_income

④.5 FIRE後のみ: 現金管理戦略を適用（支出処理の前）
   安全マージン + 生活費1ヶ月分を確保するよう月初に株式を売却
   暴落時（ドローダウン≤-20%）は売却を停止し安全マージンから取り崩す
   ※ 支出処理の前に実行することで、⑤での二重売却を回避する

⑤ 支出を現金から差し引き
   cash >= expense → cash -= expense
   cash <  expense → 不足分を株式から売却（NISA→課税口座の順）

⑥ 株式の月次リターンを計上
   stocks += stocks × monthly_return_rate
   ※ 簿価は増えない（含み益）

⑦ FIRE前のみ: 余剰現金を自動投資
   cash が (月次支出 × auto_invest_threshold) を超えた分を投資
   NISA枠優先 → 枠超過分は課税口座

⑧ FIREチェック（FIRE前のみ・2ヶ月目以降）
   「今退職した場合、90歳まで資産が持つか」を判定
   → 初めてTrueになった月 = FIRE達成日
```

---

## 収入の計算

### FIRE前の労働収入

```
person1の月収 = grossIncome × (1 + incomeGrowthRate) ^ 経過年数 × 時短比率
person2の月収 = 通常時: grossIncome × (1 + incomeGrowthRate) ^ 経過年数 × 時短比率
               産休育休期間中: 給付金（雇用形態に応じて計算）
世帯月収 = person1の月収 + person2の月収
```

### 産休・育休期間

`maternityLeaveConfig`（月単位精度）または `maternityLeaveChildBirthYears`（年単位近似・後方互換）で設定。

**月単位精度（maternityLeaveConfig）:**
```
産前休暇: prenatalWeeks × 7 / 30.44 ヶ月（デフォルト 6週）
産後休暇: postnatalWeeks × 7 / 30.44 ヶ月（デフォルト 8週）
育休前半（産後180日まで）: 標準報酬月額 × 67%
育休後半（前半終了〜育休終了）: 標準報酬月額 × 50%
```

`maternityLeaveConfig.childBirthDate`（YYYY-MM）を起点に月単位で判定。
雇用形態が `selfEmployed` / `homemaker` の場合は給付金ゼロ（上限: 月額635,000円）。

**年単位近似（後方互換）:**
```
出生年:   産前産後+育休前半 = 8ヶ月 @ 2/3、育休後半 = 4ヶ月 @ 50%
翌年:     育休後半 = 8ヶ月 @ 50%
翌々年以降: 通常収入に復帰
```

### 税・社会保険料（FIRE前）

```
給与所得 = calculateEmploymentIncome(grossIncome, employmentType)
社会保険料 = grossIncome × 0.1449（会社員・40歳以上）/ 0.1449（40歳未満） 等
課税所得 = 給与所得 - 社会保険料 - 基礎控除(48万) - 配偶者控除
所得税 = 課税所得 × 累進税率
住民税 = 課税所得 × 10% + 均等割5,000円
```

**配偶者控除（2024年度）:**
- 申告者の合計所得 > 1,000万 → 控除なし
- 配偶者の給与所得 ≤ 48万 → 38万控除（申告者所得900万超で逓減）
- 配偶者の給与所得 48万〜133万 → 配偶者特別控除（逓減テーブル）

### FIRE後・年金受給前

```
postFireIncome（設定値）を終了年齢まで収入として計上
```

### 年金収入

受給開始年齢: `pensionStartAge`（デフォルト 65歳）

```
厚生年金 = 標準報酬月額 × 加入月数 × 0.005481
  加入月数 = pastEmployeeMonths + FIRE達成時までの追加月数

国民年金 = 816,000円/年（満額）× 実加入年数 / 40年
  ※ 加入年数 = 20歳〜min(退職年齢, 60歳)

合計 = 厚生年金 + 国民年金
```

**インフレ調整（マクロ経済スライド）:**
```
pension_factor = (1 + pensionGrowthRate) ^ 年金受給開始後の経過年数
```

`pensionConfig` を設定しない場合は `pensionAmount`（固定値）を使用。

### 児童手当（2024年10月改定後）

```
第1子・3歳未満            → 15,000円/月
第2子以降・3歳未満        → 20,000円/月
3歳以上・高校生以下（18歳未満） → 10,000円/月
```

---

## 支出の計算

### 基本生活費

`expenseMode: 'fixed'`（固定額）または `'lifecycle'`（ライフステージ別）で設定。

**ライフステージ別（lifecycle モード）:**

`children[0]`（第1子）の年齢で判定。

```
0〜5歳（未就学）     → withPreschooler
6〜11歳（小学生）    → withElementaryChild
12〜14歳（中学生）   → withJuniorHighChild
15〜17歳（高校生）   → withHighSchoolChild
18〜21歳（大学生）   → withCollegeChild
22歳以降（独立後）
  〜69歳            → emptyNestActive
  70〜79歳          → emptyNestSenior
  80歳〜            → emptyNestElderly
```

**インフレ適用:**
```
年次支出 = monthlyExpenses × 12 × (1 + expenseGrowthRate) ^ 経過年数
```

### 教育費

文部科学省「子供の学習費調査」令和3年度データ準拠。

```
0〜2歳:  保育園 → daycareAnnualCost（デフォルト 360,000円/年）
3〜5歳:  幼稚園
6〜11歳: 小学校
12〜14歳: 中学校
15〜17歳: 高校
18〜21歳: 大学（22歳以降はゼロ）
```

educationPath の3択: `public`（公立）/ `private`（私立）/ `mixed`（公立小中高・私立大）

インフレ適用なし（固定値）。

### 住宅ローン

```
monthlyPayment × 12（endYear 完済年まで）
```

### 住宅メンテナンス費用（周期型）

```
MaintenanceCost { amount, intervalYears, firstYear, label? } を複数設定可能
→ (currentYear - firstYear) % intervalYears === 0 の年に amount を加算
```

### 社会保険料（FIRE後のみ計上）

**国民年金保険料:**
```
FIRE後かつ 60歳未満 → nationalPensionMonthlyPremium/月（2024年度: 16,980円）
```

**国民健康保険料（前年所得から動的計算）:**
```
所得割 = max(0, 合計所得 − 430,000) × nhisoIncomeRate（デフォルト 11.0%）
固定部分 = nhisoFixedAmountPerPerson × 人数 + nhisoHouseholdFixed
国民健康保険料 = min(所得割 + 固定部分, nhisoMaxAnnual)
```

---

## 資産運用の計算

### 月次リターン

```
monthly_return_rate = (1 + investmentReturn) ^ (1/12) − 1
月末の株式残高 = 月初残高 × (1 + monthly_return_rate)
※ 簿価は変化しない（含み益は売却時に課税対象）
```

### モンテカルロシミュレーション

```
iterations = 1000回（デフォルト）

リターンモデル（mcReturnModel）:
  normal:        正規分布 N(μ, σ²) で毎年独立にサンプル
  meanReversion: AR型平均回帰（前年偏差に比例して翌年に引き戻し）
  bootstrap:     historicalReturns からブロックサンプリング
```

**MCシミュレーション出力:**

| フィールド | 型 | 説明 |
|----------|----|------|
| `successRate` | number | FIRE成功確率（0〜1） |
| `medianFinalAssets` | number | 90歳時点の最終資産中央値 |
| `percentile5` | number | 最終資産の下位5%（P5） |
| `percentile10` | number | 最終資産の下位10%（P10） |
| `percentile90` | number | 最終資産の上位10%（P90） |
| `bankruptcyRate` | number | 破産率（資産≤100万円に到達した割合） |
| `depletionAgeP10` | number\|null | P10資産が破綻ラインを下回る年齢 |
| `fireMonth` | number | FIRE達成月（シミュレーション先頭からの経過月数） |

### 動的取り崩し戦略（ガードレール）

ドローダウン（ピーク資産からの下落率）に応じて裁量支出を自動削減。

```
レベル0（正常）:   ドローダウン > threshold1      → 削減なし
レベル1（警戒）:   threshold2 < ドローダウン ≤ threshold1 → reduction1 削減
レベル2（深刻）:   threshold3 < ドローダウン ≤ threshold2 → reduction2 削減
レベル3（危機）:   ドローダウン ≤ threshold3             → reduction3 削減
```

**裁量支出比率（useLifecycleDiscretionary: true の場合）:**

総務省家計調査2023年ベースのライフステージ別比率。`discretionaryRatio` を上書き。

---

## FIRE判定ロジック

### 二分探索による実収支ベースのFIRE年齢特定

従来の「資産 ≥ 年間支出 × 25（4%ルール）」ではなく、**実際の収支シミュレーションで資産が尽きない最早の退職年齢**を二分探索で特定します。

```
findEarliestFireAge(config):
  lo = currentAge, hi = maxAge
  while lo < hi:
    mid = (lo + hi) / 2
    result = runSingleSimulation(config, fireAtAge=mid)
    if 全期間で資産 > 0: hi = mid   // もっと早くできるか探す
    else:                 lo = mid+1 // まだ早い
  return lo  // 最早FIRE可能年齢
```

年金・セミFIRE収入・教育費・住宅ローン・社会保険料など将来の収支変動をすべて織り込んで判定します。

---

## 重要な不変条件

```
nisaAssets <= stocks（常に成立）
```

NISA残高は株式資産の一部であるため、この条件は常に真でなければならない。

---

## 定数一覧

| 定数 | 値 | 意味 |
|------|----|------|
| 国民年金満額 | 816,000円 | 2024年度 |
| 厚生年金乗率 | 0.005481 | 2003年4月以降 |
| 国民年金最大加入年数 | 40年 | |
| 破綻ライン | 1,000,000円 | |
| 健保基礎控除 | 430,000円 | 2024年度 |
| 健保所得割率（デフォルト） | 11.0% | 40歳以上全国平均 |
| 育休給付金上限 | 635,000円/月 | 標準報酬月額上限 |
| 育休前半給付率 | 67% | 産後180日 |
| 育休後半給付率 | 50% | 前半終了後 |

---

## 開発者向け情報

開発者向けガイド（テスト実行方法、プロジェクト構造、トラブルシューティング等）は [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) を参照してください。
