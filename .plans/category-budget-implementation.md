# 実装計画: カテゴリ別予算機能（20+カテゴリ、詳細金額設定）

## 概要

### ユーザー要求
- **設定方式**: 詳細設定（全カテゴリの金額を明示）
- **カテゴリ粒度**: 詳細（20+カテゴリ）
- **目的**: 基本生活費を総額ではなく、カテゴリ別に管理

### 現状の問題点
- **基本生活費は総額のみ**: `base_expense_by_stage` で280-340万円/年の総額管理
- **削減ロジックの粗さ**: 裁量的支出比率（25-40%）で一律に「基礎/裁量」を分離
- **透明性の欠如**: 何にいくら使っているか不明確

### 実装目標
1. **20+カテゴリの詳細管理**: 食費（自炊/外食）、光熱費、通信費、娯楽、旅行など
2. **カテゴリ別の基礎/裁量フラグ**: 削減可否を個別に定義
3. **ライフステージ別の金額設定**: 各ステージで全カテゴリの金額を明示
4. **後方互換性の維持**: 既存の総額方式も継続サポート

---

## カテゴリ定義（22カテゴリ）

### 基礎生活費（削減対象外）
1. `food_home` - 食費（自炊）
2. `utilities_electricity` - 光熱費（電気）
3. `utilities_gas` - 光熱費（ガス）
4. `utilities_water` - 光熱費（水道）
5. `communication_mobile` - 通信費（携帯）
6. `communication_internet` - 通信費（インターネット）
7. `transport_commute` - 交通費（定期券）
8. `insurance_life` - 保険（生命）
9. `insurance_casualty` - 保険（損害）
10. `medical` - 医療費
11. `household_goods` - 日用品

### 裁量的支出（削減対象）
12. `food_out` - 食費（外食）
13. `transport_other` - 交通費（その他）
14. `clothing` - 被服費
15. `entertainment_movies` - 娯楽（映画/コンサート）
16. `entertainment_other` - 娯楽（その他）
17. `travel_domestic` - 旅行（国内）
18. `travel_international` - 旅行（海外）
19. `hobby` - 趣味
20. `education_books` - 教養（書籍）
21. `education_courses` - 教養（講座）
22. `beauty` - 美容・理容
23. `other` - その他

---

## Phase 1: config.yaml構造設計

### 新しいセクション構造

```yaml
fire:
  # 【新機能】カテゴリ別予算管理
  expense_categories:
    enabled: true  # true: カテゴリ別予算使用、false: 従来方式

    # カテゴリ定義
    definitions:
      - id: food_home
        name: '食費（自炊）'
        discretionary: false  # 基礎生活費
        description: '家での食事、食材費'

      - id: food_out
        name: '食費（外食）'
        discretionary: true   # 裁量的支出
        description: '外食、テイクアウト'

      # ... 全23カテゴリ定義 ...

    # ライフステージ別の金額設定（年額・円）
    budgets_by_stage:
      young_child:
        food_home: 600000
        food_out: 240000
        utilities_electricity: 120000
        # ... 全カテゴリの金額 ...
        # 合計: 2,800,000円

      elementary:
        food_home: 660000
        # ...
        # 合計: 3,000,000円

      # ... 全6ステージ分 ...

  # 【既存】後方互換性のため保持
  base_expense_by_stage:
    young_child: 2800000
    # ...
```

**設計の要点**:
- `expense_categories.enabled: false` → 従来の`base_expense_by_stage`使用
- `expense_categories.enabled: true` → カテゴリ別予算使用
- カテゴリ定義（id, name, discretionary, description）と金額設定を分離

---

## Phase 2: カテゴリ別計算関数実装

### 新規関数1: `calculate_base_expense_by_category()`

**配置**: `src/simulator.py` L2282付近

**目的**: カテゴリ別予算に基づく基本生活費を計算

```python
def calculate_base_expense_by_category(
    year_offset: float,
    config: Dict[str, Any],
    fallback_expense: float
) -> Tuple[float, Dict[str, Any]]:
    """
    Returns:
        (total_expense, breakdown):
            - total_expense: 年間基本生活費合計
            - breakdown: {
                'categories': {cat_id: amount, ...},
                'essential_total': 基礎生活費合計,
                'discretionary_total': 裁量的支出合計,
                'stage': ライフステージ,
                'total': 合計
              }
    """
```

**処理フロー**:
1. カテゴリ別予算が無効 → `None, {}` を返す（フォールバック）
2. ライフステージ決定（第一子の年齢から）
3. 該当ステージの予算を取得
4. カテゴリ定義から基礎/裁量を判定
5. 基礎/裁量の集計、第二子以降の追加費用加算
6. 内訳辞書を返す

### 既存関数の修正: `calculate_base_expense()`

**修正内容**:
- カテゴリ別予算が有効 → `calculate_base_expense_by_category()` を呼び出す
- 無効/失敗 → 既存ロジックを実行（後方互換性）

```python
def calculate_base_expense(year_offset, config, fallback_expense):
    # カテゴリ別予算を試す
    category_expense, breakdown = calculate_base_expense_by_category(
        year_offset, config, fallback_expense
    )
    if category_expense is not None:
        return category_expense

    # 従来方式（既存ロジック維持）
    # ...
```

---

## Phase 3: 動的削減ロジック修正

### 既存関数の修正: `apply_dynamic_expense_reduction()`

**修正方針**:
- カテゴリ別内訳が提供された場合 → カテゴリごとに削減を適用
- 内訳がない場合 → 従来の比率ベース削減（後方互換性）

**新しいシグネチャ**:
```python
def apply_dynamic_expense_reduction(
    base_expense: float,
    stage: str,
    drawdown_level: int,
    config: Dict[str, Any],
    category_breakdown: Optional[Dict[str, float]] = None  # 【新規】
) -> Tuple[float, Dict[str, Any]]:
```

**処理分岐**:
- `category_breakdown is not None` → `_apply_category_based_reduction()` を呼び出す
- `category_breakdown is None` → 従来の比率ベース削減

### 新規関数2: `_apply_category_based_reduction()`

**目的**: カテゴリ別内訳に基づいて削減を適用

**処理フロー**:
1. カテゴリ定義から基礎/裁量フラグを取得
2. カテゴリごとに削減を適用
   - 裁量的カテゴリ: `amount × (1 - reduction_rate)`
   - 基礎カテゴリ: 削減なし
3. 削減後の内訳を返す

### `_precompute_monthly_cashflows()` の拡張

**追加内容**:
- カテゴリ内訳配列を追加で返す

```python
def _precompute_monthly_cashflows(...) -> Tuple[
    np.ndarray,  # expenses
    np.ndarray,  # income
    np.ndarray,  # base_expenses
    np.ndarray,  # life_stages
    np.ndarray   # category_breakdowns 【新規】
]:
```

**月次ループでの使用**:
```python
# 動的削減適用時
category_breakdown = category_breakdowns[month_idx]  # 【新規】

reduced_expense, breakdown = apply_dynamic_expense_reduction(
    base_expenses[month_idx],
    stage,
    drawdown_level,
    config,
    category_breakdown=category_breakdown  # 【新規】
)
```

---

## Phase 4: テスト追加

### ユニットテスト1: `tests/test_category_expense.py`（新規）

**テストケース**:
1. `test_category_based_calculation_young_child()` - カテゴリ別計算の基本動作
2. `test_category_based_essential_discretionary_split()` - 基礎/裁量の分類
3. `test_fallback_to_traditional_when_disabled()` - 無効時のフォールバック
4. `test_all_stages_sum_correctly()` - 全ステージの合計チェック
5. `test_calculate_base_expense_uses_category_when_enabled()` - 統合確認

### ユニットテスト2: `tests/test_category_dynamic_reduction.py`（新規）

**テストケース**:
1. `test_reduction_only_affects_discretionary_categories()` - 裁量的カテゴリのみ削減
2. `test_category_breakdown_in_result()` - 削減後の内訳確認
3. `test_100_percent_reduction_eliminates_discretionary()` - 100%削減で裁量的支出ゼロ
4. `test_traditional_reduction_without_category_breakdown()` - 後方互換性

### 統合テスト: `tests/test_dynamic_expense_reduction.py`（既存修正）

**修正内容**:
- カテゴリ別予算を無効化した設定でテスト実行
- 既存の全テストケースが変更なく通ることを確認

---

## Phase 5: バリデーション実装

### 新規関数3: `validate_expense_categories_config()`

**配置**: `src/simulator.py` L50-100付近

**目的**: カテゴリ別予算設定の妥当性をチェック

**検証内容**:
1. カテゴリIDの重複チェック
2. 各ステージの合計が想定総額と一致するかチェック（警告のみ）
3. 未定義カテゴリ/未使用カテゴリのチェック
4. 裁量的支出比率が想定値と一致するかチェック（参考情報）

**実行タイミング**:
- `scripts/generate_dashboard.py` の冒頭で実行
- 警告メッセージを表示（エラーにはしない）

### バリデーションテスト: `tests/test_config_validation.py`（新規）

**テストケース**:
1. `test_valid_config_no_warnings()` - 正しい設定で警告なし
2. `test_total_mismatch_warning()` - 合計不一致で警告
3. `test_missing_category_warning()` - 未定義カテゴリで警告
4. `test_duplicate_category_id_warning()` - ID重複で警告

---

## 実装スケジュール（3週間）

### Week 1: Phase 1 & 2（設計 + カテゴリ別計算）

**Day 1-2**: config.yaml構造設計
- 23カテゴリ定義の確定
- ライフステージ別予算の計算（家計調査2024参照）
- 合計が既存の総額（280-340万円）と一致するよう調整

**Day 3-4**: カテゴリ別計算関数実装
- `calculate_base_expense_by_category()` 実装
- `calculate_base_expense()` 修正（フォールバック機能）
- 基本的なユニットテスト作成

**Day 5**: 統合テスト
- 既存の`calculate_base_expense()`が動作することを確認
- ライフステージ遷移の動作確認

### Week 2: Phase 3 & 4（動的削減 + テスト）

**Day 6-7**: 動的削減ロジック修正
- `apply_dynamic_expense_reduction()` 修正
- `_apply_category_based_reduction()` 実装
- `_precompute_monthly_cashflows()` 拡張

**Day 8-9**: テスト作成
- `test_category_expense.py` 作成（5テスト）
- `test_category_dynamic_reduction.py` 作成（4テスト）
- 既存テストの互換性確認

**Day 10**: モンテカルロ統合
- モンテカルロシミュレーション実行確認（1000回）
- パフォーマンステスト（目標: 30秒以内）

### Week 3: Phase 5 & 最終調整（バリデーション + ドキュメント）

**Day 11-12**: バリデーション実装
- `validate_expense_categories_config()` 実装
- `scripts/generate_dashboard.py` 修正
- `test_config_validation.py` 作成

**Day 13-14**: ドキュメント作成
- `DEVELOPMENT.md` にカテゴリ別予算の説明追加
- `README.md` に設定例追加
- コード内のコメント・docstring整備

**Day 15**: 最終テスト & リリース
- 全テストスイート実行（`pytest tests/`）
- サンプルダッシュボード生成確認
- パフォーマンス確認

---

## 重要ファイル一覧

### 修正が必要なファイル

1. **config.yaml**
   - 新セクション `expense_categories` を追加（definitions + budgets_by_stage）
   - 既存の `base_expense_by_stage` も後方互換性のため維持

2. **src/simulator.py**
   - 新規関数: `calculate_base_expense_by_category()` (L2282付近)
   - 新規関数: `_apply_category_based_reduction()` (L510付近)
   - 新規関数: `validate_expense_categories_config()` (L50-100付近)
   - 修正関数: `calculate_base_expense()` - カテゴリ別計算を優先、フォールバック
   - 修正関数: `apply_dynamic_expense_reduction()` - カテゴリ内訳対応
   - 修正関数: `_precompute_monthly_cashflows()` - カテゴリ内訳配列追加

3. **tests/test_category_expense.py**（新規作成）
   - カテゴリ別計算のユニットテスト（5テストケース）

4. **tests/test_category_dynamic_reduction.py**（新規作成）
   - カテゴリ別動的削減のユニットテスト（4テストケース）

5. **tests/test_config_validation.py**（新規作成）
   - 設定バリデーションのテスト（4テストケース）

6. **tests/test_dynamic_expense_reduction.py**（既存修正）
   - 後方互換性テストを追加

7. **scripts/generate_dashboard.py**（既存修正）
   - バリデーション実行を追加

8. **DEVELOPMENT.md**（既存修正）
   - カテゴリ別予算の設定方法と説明を追加

9. **README.md**（既存修正）
   - カテゴリ別予算の概要と設定例を追加

---

## リスクと対策

### リスク1: 複雑性の増加
**影響**: 設定ファイルが肥大化、ユーザーが設定ミス

**対策**:
- 明確なドキュメント（設定例をコメント付きで記載）
- バリデーション強化（起動時に自動チェック）
- デフォルトは無効（既存ユーザーに影響なし）

### リスク2: 後方互換性の破壊
**影響**: 既存のシミュレーションが動作しなくなる

**対策**:
- フォールバック機能（カテゴリ別予算が無効/未設定で自動的に従来方式）
- 既存テストの維持（全テストが通ることを確認）
- デフォルトは無効（`expense_categories.enabled: false`）

### リスク3: パフォーマンス劣化
**影響**: カテゴリ別計算により処理速度が低下

**対策**:
- 事前計算の活用（`_precompute_monthly_cashflows()`でキャッシュ）
- パフォーマンステスト（モンテカルロ1000回: 30秒以内）
- 最適化（NumPy配列活用、ループ最小化）

### リスク4: 設定ミスによる不正確なシミュレーション
**影響**: カテゴリ合計が想定と異なり、FIRE達成時期が誤る

**対策**:
- バリデーション（合計チェック、警告表示）
- 可視化（ダッシュボードにカテゴリ別内訳グラフ追加）
- ドキュメント（各カテゴリの目安金額を記載）

---

## 検証方法

### ステップ1: ユニットテスト実行

```bash
# カテゴリ別計算テスト
python tests/test_category_expense.py

# カテゴリ別動的削減テスト
python tests/test_category_dynamic_reduction.py

# バリデーションテスト
python tests/test_config_validation.py
```

**期待結果**: 全テスト合格（13テストケース）

### ステップ2: 統合テスト実行

```bash
# 既存テストの後方互換性確認
python tests/test_dynamic_expense_reduction.py

# 全テストスイート実行
pytest tests/
```

**期待結果**: 全テスト合格（既存 + 新規）

### ステップ3: エンドツーエンドテスト

```bash
# config.yamlでカテゴリ別予算を有効化
# expense_categories.enabled: true に設定

# ダッシュボード生成
python scripts/generate_dashboard.py
```

**期待結果**:
- バリデーション警告なし（合計が一致）
- FIRE達成時期が従来方式と同じ（±1ヶ月以内）
- カテゴリ別内訳が正しく計算される

### ステップ4: パフォーマンステスト

```bash
# モンテカルロシミュレーション（1000回）
time python scripts/generate_dashboard.py
```

**期待結果**: 30秒以内（現行: 20秒、許容範囲: +50%）

---

## 成功基準

| 指標 | 目標 | 根拠 |
|------|------|------|
| カテゴリ数 | 23カテゴリ | ユーザー要求（20+） |
| 後方互換性 | 既存テスト全合格 | リグレッションなし |
| バリデーション | 合計誤差 < 0.1% | 設定ミスの検出 |
| パフォーマンス | MC1000回 < 30秒 | 実用性維持 |
| ドキュメント | 設定例完備 | ユーザーが設定可能 |
