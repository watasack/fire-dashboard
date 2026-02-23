# 高度リスク管理機能の設計書

## 概要

最悪ケース対応のための4つの機能を実装します：
1. ✅ **FIRE後の現金管理戦略**（実装完了）
2. ✅ **年金繰り下げ受給戦略**（実装完了）
3. 資産配分の見直し（リバランシング戦略）
4. 大型支出のタイミング調整

## 実装状況

### フェーズ1: 基盤機能（完了）
- ✅ FIRE後の現金管理戦略
- ✅ 年金繰り下げ受給戦略

### フェーズ2-3: 拡張機能（未実装）
- ⏸️ 資産配分の見直し
- ⏸️ 大型支出のタイミング調整

---

## 1. FIRE後の現金管理戦略 ✅ 実装完了

### 設計の変更履歴

**初期設計:** 3層構造の緊急時資金管理
**最終設計:** シンプルな500万円安全マージン + 暴落時株式売却停止戦略
**変更理由:** 3層構造は過剰に複雑であり、シンプルな戦略で十分な効果が得られると判断

### 実装された設計

**設定:**
```yaml
post_fire_cash_strategy:
  enabled: true                      # FIRE後の現金管理戦略を有効化

  # 基本設定
  safety_margin: 5000000             # 安全マージン: 500万円（常時確保）
  monthly_buffer_months: 1           # 生活費バッファ: 1ヶ月分

  # 暴落時の株式売却停止ルール
  market_crash_threshold: -0.20      # ドローダウン-20%以下で暴落と判定
  recovery_threshold: -0.10          # ドローダウン-10%以上で回復と判定
  emergency_cash_floor: 250000       # 緊急時最低現金（25万円、これを下回ったら強制売却）
```

### 実装ロジック

**FIRE後の現金管理フロー:**

```
【平常時】
現金 = 500万（安全マージン）+ 25万（生活費1ヶ月分）= 525万円
月初: 株式25万円売却 → 現金+25万（550万円）
月中: 生活費25万円支出 → 現金-25万（525万円に戻る）

【暴落時】（ドローダウン ≤ -20%）
月初: 株式売却停止（底値売却回避）
月中: 安全マージンから支出 → 現金減少
...
復帰条件: 現金 < 25万円 or ドローダウン ≥ -10%
```

**実装関数:**
```python
def _manage_post_fire_cash(
    cash: float,
    stocks: float,
    monthly_expense: float,
    drawdown: float,
    config: Dict[str, Any],
    is_start_of_month: bool,
    ...
) -> Dict[str, Any]:
    """
    FIRE後専用の現金管理戦略を実行

    平常時: 月初に生活費1ヶ月分を株式売却
    暴落時: 株式売却停止、安全マージンから取り崩し
    緊急時: 現金25万円未満で強制売却
    """
```

### 実装された効果

- ✅ **平常時**: 月初に生活費25万円を株式売却、現金バッファを維持
- ✅ **暴落時**: 株式売却を停止、安全マージン500万円から取り崩し
- ✅ **回復時**: ドローダウン-10%以上で株式売却を再開
- ✅ **緊急時**: 現金25万円未満で暴落中でも強制売却

### テスト結果

全てのテストケースが合格:
- ✅ 平常時の月初株式売却
- ✅ 暴落時の株式売却停止
- ✅ 回復時の株式売却再開
- ✅ 緊急時の強制売却

テストファイル: `scripts/test_post_fire_cash_strategy.py`

---

## 2. 年金繰り下げ受給戦略 ✅ 実装完了

### 設計

```yaml
pension:
  enabled: true
  start_age: 65                      # デフォルト受給開始年齢

  # 年金繰り下げ受給戦略
  deferral_strategy:
    enabled: true
    description: "資産状況に応じて年金受給開始時期を最適化"

    # 決定基準
    decision_criteria:
      # 資産が十分（目標の150%以上）→ 繰り下げで年金額を最大化
      defer_condition:
        enabled: true
        assets_threshold: 1.5        # FIRE目標資産の150%以上
        defer_to_age: 70             # 70歳まで繰り下げ（最大+42%）

      # 資産が不足（目標の80%以下）→ 予定通り受給
      normal_condition:
        enabled: true
        assets_threshold_min: 0.8    # FIRE目標資産の80%以上
        assets_threshold_max: 1.5    # FIRE目標資産の150%未満
        start_at_age: 65             # 予定通り65歳

      # 資産が危機的（目標の50%以下）→ 早期受給も検討
      early_condition:
        enabled: true
        assets_threshold: 0.5        # FIRE目標資産の50%未満
        start_at_age: 62             # 62歳から受給可能（-18%）

    # 繰り下げ受給の増額率
    increase_rate_per_year: 0.084    # 年8.4%増（0.7%×12ヶ月）
    decrease_rate_per_year: 0.056    # 年5.6%減（繰り上げ時）

    # 評価タイミング
    evaluation_timing:
      check_age: 64                  # 64歳時点で評価
      reevaluate_interval_years: 1  # 毎年再評価
```

### 実装ロジック

```python
def determine_pension_start_age(
    current_age: int,
    current_assets: float,
    fire_target: float,
    config: dict
) -> dict:
    """
    資産状況に応じて年金受給開始年齢を決定

    Returns:
        {
            'start_age': 受給開始年齢,
            'multiplier': 年金額の倍率,
            'reason': 判断理由
        }
    """
    asset_ratio = current_assets / fire_target

    # 資産が十分 → 繰り下げ
    if asset_ratio >= 1.5:
        defer_years = 70 - 65  # 5年繰り下げ
        multiplier = 1 + (defer_years * 0.084)
        return {
            'start_age': 70,
            'multiplier': multiplier,
            'reason': f'資産十分（目標の{asset_ratio:.1%}）→ 繰り下げで年金額最大化'
        }

    # 資産が危機的 → 早期受給
    elif asset_ratio < 0.5:
        early_years = 65 - 62  # 3年繰り上げ
        multiplier = 1 - (early_years * 0.056)
        return {
            'start_age': 62,
            'multiplier': multiplier,
            'reason': f'資産不足（目標の{asset_ratio:.1%}）→ 早期受給で生活維持'
        }

    # 通常 → 予定通り
    else:
        return {
            'start_age': 65,
            'multiplier': 1.0,
            'reason': f'資産通常（目標の{asset_ratio:.1%}）→ 予定通り受給'
        }
```

### 期待効果

**繰り下げ受給（70歳）の効果:**
- 年金額: 232万円 → **329万円（+42%）**
- 支出カバー率: 93% → **132%**
- 効果: 年金のみで生活可能、資産の減少を抑制

### 実装状況 ✅

**実装済み機能:**
- ✅ 資産ベースの受給開始年齢判定
- ✅ 繰り下げ受給（最大70歳、+8.4%/年）
- ✅ 繰り上げ受給（最小62歳、-4.8%/年）
- ✅ 動的な年金額調整

**実装された判定基準:**
- 資産 ≥ 目標の150% → 70歳まで繰り下げ（+42%）
- 資産 ≥ 目標の120% → 68歳まで繰り下げ（+25.2%）
- 資産 50-120% → 65歳で通常受給
- 資産 < 目標の50% → 62歳から繰り上げ（-14.4%）

**実装関数:**
- `_determine_optimal_pension_start_age()`: 最適受給開始年齢を決定
- `calculate_pension_income()`: 年金額を計算（繰り下げ・繰り上げ調整を反映）

**テスト結果:**
- ✅ 資産豊富時の繰り下げ判定
- ✅ 資産不足時の繰り上げ判定
- ✅ 年金額の正確な調整率（+42%, -14.4%）
- ✅ 繰り下げ中の年金0円

テストファイル: `scripts/test_emergency_fund_pension.py`

---

## 3. 資産配分の見直し（リバランシング戦略）

### 設計

```yaml
asset_allocation:
  enabled: true

  # 年齢別の目標配分（グライドパス戦略）
  glide_path:
    enabled: true
    description: "年齢に応じて徐々にリスク資産を減らす"

    age_based_allocation:
      - age: 50
        stocks: 1.00
        bonds: 0.00
        description: "FIRE直後：100%株式でリターン最大化"

      - age: 60
        stocks: 0.80
        bonds: 0.20
        description: "60歳：リスク軽減開始"

      - age: 70
        stocks: 0.60
        bonds: 0.40
        description: "70歳：バランス重視"

      - age: 80
        stocks: 0.40
        bonds: 0.60
        description: "80歳：安定性重視"

    # 年齢間の線形補間
    interpolation: "linear"

  # リバランシング戦略
  rebalancing:
    enabled: true
    description: "定期的に目標配分に戻す（ボラティリティ抑制・利益確定）"

    # 実行条件
    frequency: "annual"                # 年1回（毎年1月）
    threshold: 0.05                    # 目標配分から±5%以上のズレで実行

    # 例: 目標80/20の場合、株式が75%以下または85%以上でリバランス

    # リバランシングコスト
    transaction_cost: 0.0              # 取引コスト（NISA内なので0円と仮定）
    tax_rate: 0.20315                  # 課税口座の場合の税率

  # 債券の想定リターン
  bond_parameters:
    expected_return: 0.02              # 期待リターン2%/年
    volatility: 0.03                   # ボラティリティ3%/年
    correlation_with_stocks: 0.2       # 株式との相関係数0.2（低相関）
```

### 実装ロジック

```python
def calculate_target_allocation(age: int, glide_path: dict) -> dict:
    """
    年齢に基づく目標配分を計算（線形補間）

    Returns:
        {'stocks': 株式比率, 'bonds': 債券比率}
    """
    allocations = glide_path['age_based_allocation']

    # 年齢が範囲外の場合
    if age <= allocations[0]['age']:
        return {'stocks': allocations[0]['stocks'], 'bonds': allocations[0]['bonds']}
    if age >= allocations[-1]['age']:
        return {'stocks': allocations[-1]['stocks'], 'bonds': allocations[-1]['bonds']}

    # 線形補間
    for i in range(len(allocations) - 1):
        if allocations[i]['age'] <= age < allocations[i+1]['age']:
            age1, age2 = allocations[i]['age'], allocations[i+1]['age']
            ratio = (age - age1) / (age2 - age1)

            stocks = allocations[i]['stocks'] + ratio * (allocations[i+1]['stocks'] - allocations[i]['stocks'])
            bonds = allocations[i]['bonds'] + ratio * (allocations[i+1]['bonds'] - allocations[i]['bonds'])

            return {'stocks': stocks, 'bonds': bonds}


def should_rebalance(
    current_stocks_ratio: float,
    target_stocks_ratio: float,
    threshold: float
) -> dict:
    """
    リバランシングが必要かどうかを判定

    Returns:
        {
            'should_rebalance': bool,
            'deviation': 現在のズレ,
            'action': 'sell_stocks' | 'buy_stocks' | None
        }
    """
    deviation = current_stocks_ratio - target_stocks_ratio

    if abs(deviation) > threshold:
        return {
            'should_rebalance': True,
            'deviation': deviation,
            'action': 'sell_stocks' if deviation > 0 else 'buy_stocks'
        }
    else:
        return {
            'should_rebalance': False,
            'deviation': deviation,
            'action': None
        }
```

### 期待効果

**60歳時点（80/20配分）の効果:**
- 期待リターン: 5.00% → 4.40%（-0.6%）
- ボラティリティ: 6.00% → 4.84%（-19%）
- **リスク軽減しつつ、十分なリターンを確保**

---

## 4. 大型支出のタイミング調整

### 設計

```yaml
house_maintenance:
  enabled: true
  construction_year: 2025

  items:
    - name: '白アリ対策'
      cost: 150000
      frequency_years: 10
      first_year: 2035

      # タイミング調整設定
      timing_strategy:
        enabled: true
        deferrable: true              # 延期可能
        max_defer_years: 2            # 最大2年延期可能
        urgent: false                 # 緊急性は低い

        # 実行条件
        execute_conditions:
          baseline_ratio_min: 1.0     # ベースライン資産の100%以上
          drawdown_max: -0.15         # ドローダウン-15%より浅い

    - name: '外壁補修'
      cost: 4000000
      frequency_years: 30
      first_year: 2055

      timing_strategy:
        enabled: true
        deferrable: true
        max_defer_years: 3            # 最大3年延期可能
        urgent: false

        execute_conditions:
          baseline_ratio_min: 1.1     # ベースライン資産の110%以上
          drawdown_max: -0.10         # ドローダウン-10%より浅い
```

### 実装ロジック

```python
def should_execute_maintenance(
    item: dict,
    current_year: int,
    current_assets: float,
    baseline_assets: float,
    drawdown: float
) -> dict:
    """
    住宅メンテナンスを実行すべきかを判定

    Returns:
        {
            'should_execute': bool,
            'reason': 理由,
            'defer_until': 延期先の年（Noneなら延期不可）
        }
    """
    scheduled_year = item['first_year'] + \
        ((current_year - item['first_year']) // item['frequency_years']) * item['frequency_years']

    # 予定年でない場合
    if current_year != scheduled_year:
        return {'should_execute': False, 'reason': '予定年ではない', 'defer_until': None}

    # タイミング調整が無効
    if not item['timing_strategy']['enabled']:
        return {'should_execute': True, 'reason': 'タイミング調整無効', 'defer_until': None}

    # 緊急性が高い場合は即実行
    if item['timing_strategy']['urgent']:
        return {'should_execute': True, 'reason': '緊急性が高い', 'defer_until': None}

    # 資産状況をチェック
    baseline_ratio = current_assets / baseline_assets if baseline_assets > 0 else 0
    conditions = item['timing_strategy']['execute_conditions']

    # 実行条件を満たす
    if baseline_ratio >= conditions['baseline_ratio_min'] and \
       drawdown >= conditions['drawdown_max']:
        return {'should_execute': True, 'reason': '市況良好', 'defer_until': None}

    # 延期可能
    elif item['timing_strategy']['deferrable']:
        max_defer = item['timing_strategy']['max_defer_years']
        defer_until = scheduled_year + max_defer

        return {
            'should_execute': False,
            'reason': f'市況不良のため延期（最大{max_defer}年）',
            'defer_until': defer_until
        }

    # 延期不可 → 実行
    else:
        return {'should_execute': True, 'reason': '延期不可のため実行', 'defer_until': None}
```

### 期待効果

**外壁補修（400万円）の場合:**
- 通常: 予定年に自動実行
- 暴落時: 最大3年延期 → 株式売却を回避、市況回復を待つ
- 効果: ドローダウンを最小化、資産の減少を抑制

---

## 実装優先順位

### ✅ フェーズ1: 基盤機能（完了）
1. ✅ **FIRE後の現金管理戦略**
   - 実装日: 2026年2月
   - 影響範囲: FIRE後の全シミュレーション
   - 効果: 暴落時の底値売却回避、500万円安全マージン確保
   - テスト: 合格（scripts/test_post_fire_cash_strategy.py）

2. ✅ **年金繰り下げ受給戦略**
   - 実装日: 2026年2月
   - 影響範囲: 62-75歳の年金受給期間
   - 効果: 資産状況に応じた年金額最大化（最大+42%）
   - テスト: 合格（scripts/test_emergency_fund_pension.py）

### フェーズ2: 拡張機能（中優先度）
3. **大型支出のタイミング調整**
   - 影響範囲: メンテナンス発生時
   - 効果: ドローダウン抑制

### フェーズ3: 高度機能（低優先度）
4. **資産配分の見直し**
   - 影響範囲: 全期間（特に高齢期）
   - 効果: リスク軽減、ボラティリティ抑制
   - 備考: 実装が複雑、債券のリターン生成が必要

---

## 設定ファイルの統合 ✅ 実装完了

フェーズ1で実装された `config.yaml` の設定:

```yaml
# config.yaml

# FIRE後の現金管理戦略（実装済み）
post_fire_cash_strategy:
  enabled: true                      # FIRE後の現金管理戦略を有効化
  safety_margin: 5000000             # 安全マージン: 500万円
  monthly_buffer_months: 1           # 生活費バッファ: 1ヶ月分
  market_crash_threshold: -0.20      # 暴落判定: -20%以下
  recovery_threshold: -0.10          # 回復判定: -10%以上
  emergency_cash_floor: 250000       # 緊急ライン: 25万円
  description: 'FIRE後専用の現金管理戦略。平常時は500万円+生活費1ヶ月分を確保し、月初に株式を売却して生活費を賄う。暴落時（ドローダウン-20%以下）は株式売却を停止し、安全マージンから取り崩す。回復（-10%以上）または現金25万円未満で株式売却を再開。'

# 年金繰り下げ受給戦略（実装済み）
pension_deferral:
  enabled: true                      # 年金繰り下げ戦略を有効化
  defer_to_70_threshold: 1.50        # 資産≥目標150% → 70歳まで繰り下げ
  defer_to_68_threshold: 1.20        # 資産≥目標120% → 68歳まで繰り下げ
  early_at_62_threshold: 0.50        # 資産<目標50% → 62歳から繰り上げ
  deferral_increase_rate: 0.084      # 繰り下げ: +8.4%/年
  early_decrease_rate: 0.048         # 繰り上げ: -4.8%/年
  min_start_age: 62                  # 最小受給開始年齢
  max_start_age: 75                  # 最大受給開始年齢
  description: '資産状況に応じて年金受給開始時期を最適化'

# 資産配分（拡張）
asset_allocation:
  enabled: true
  glide_path:
    enabled: false  # フェーズ3で有効化
    age_based_allocation:
      - {age: 50, stocks: 1.00, bonds: 0.00}
      - {age: 60, stocks: 0.80, bonds: 0.20}
      - {age: 70, stocks: 0.60, bonds: 0.40}
      - {age: 80, stocks: 0.40, bonds: 0.60}
  rebalancing:
    enabled: false  # フェーズ3で有効化
    frequency: "annual"
    threshold: 0.05
  bond_parameters:
    expected_return: 0.02
    volatility: 0.03
    correlation_with_stocks: 0.2

# 住宅メンテナンス（拡張）
house_maintenance:
  enabled: true
  items:
    - name: '白アリ対策'
      cost: 150000
      frequency_years: 10
      first_year: 2035
      timing_strategy:
        enabled: true
        deferrable: true
        max_defer_years: 2
        urgent: false
        execute_conditions:
          baseline_ratio_min: 1.0
          drawdown_max: -0.15
    # ... 他のアイテム
```

---

## 次のステップ

### ✅ 完了した作業（フェーズ1）
1. ✅ **設計レビュー**: ユーザーフィードバックに基づき3層構造をシンプル化
2. ✅ **FIRE後現金管理戦略の実装**: 完了（2026年2月）
3. ✅ **年金繰り下げ受給戦略の実装**: 完了（2026年2月）
4. ✅ **テスト**: 全テスト合格

### 今後の計画（フェーズ2-3）

**フェーズ2: 大型支出のタイミング調整**
- 優先度: 中
- 実装時期: 必要に応じて
- 効果: メンテナンス発生時のドローダウン抑制

**フェーズ3: 資産配分の見直し（グライドパス・リバランシング）**
- 優先度: 低
- 実装時期: 必要に応じて
- 効果: 高齢期のリスク軽減、ボラティリティ抑制
- 備考: 実装が複雑、債券リターン生成が必要

### 実装済み機能の利用開始

次回シミュレーション実行時から以下の機能が自動的に適用されます:
- FIRE後の現金管理戦略（暴落時の底値売却回避）
- 年金繰り下げ受給戦略（資産ベースの最適化）
