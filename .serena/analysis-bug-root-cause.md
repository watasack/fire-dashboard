# バグ根本原因分析と再発防止策

## 発見されたバグ

**NISA残高に運用リターンが適用されていない**
- 場所: `_process_post_fire_monthly_cycle` 関数（標準シミュレーション用）
- 影響: 51年間のFIRE後シミュレーションでNISA資産が放置され、約2倍の資産差が発生

## 根本原因

### 1. **コードの重複**

FIRE後の月次処理ロジックが3箇所に重複実装されている:

```
_process_post_fire_monthly_cycle()        # 標準シミュレーション用
_simulate_post_fire_with_random_returns() # MCシミュレーション用
simulate_with_random_returns()            # 旧実装？
```

**問題点:**
- 同じロジックを複数箇所でメンテナンス
- 一箇所を更新すると、他の箇所も更新が必要
- 更新漏れが発生しやすい

### 2. **テストの欠如**

- 単体テスト: 個別関数のテストなし
- 統合テスト: 標準とMCシミュレーションの整合性チェックなし
- リグレッションテスト: 過去のバグ再発防止テストなし

### 3. **コードレビュープロセスの不在**

- MCシミュレーション追加時に標準シミュレーションとの整合性を確認していない
- NISA機能追加時に全ての関連箇所を更新していない

### 4. **ドキュメント不足**

- 各シミュレーション関数の責任範囲が不明確
- NISA処理の仕様書なし
- 期待される動作の記述なし

## 他のバグの可能性

### 重複コードパターンの検出結果

1. **株式リターン適用**: 2箇所
2. **収入加算**: 4箇所
3. **支出控除**: 3箇所
4. **株式売却**: 10箇所以上の呼び出し

### 高リスク領域

#### A. `simulate_with_random_returns` 関数

```python
# Line 2487: NISA返却適用あり
nisa_balance *= (1 + monthly_return)
```

この関数は使われているか？重複実装の可能性。

#### B. FIRE前の月次処理

FIRE前とFIRE後で別々の処理ロジックが存在。同様の不整合が潜在する可能性。

#### C. 課税計算ロジック

`_sell_stocks_with_tax` が10箇所以上で呼ばれているが、全箇所で正しく使用されているか不明。

## 再発防止策

### 【優先度: 高】即座に実施すべき対策

#### 1. コードの共通化（リファクタリング）

**目標:** 月次処理ロジックを単一の関数に統合

```python
def _apply_monthly_returns(
    stocks: float,
    nisa_balance: float,
    monthly_return_rate: float
) -> Tuple[float, float]:
    """運用リターンを適用（株式とNISA両方）"""
    stocks += stocks * monthly_return_rate
    nisa_balance *= (1 + monthly_return_rate)
    return stocks, nisa_balance
```

**メリット:**
- 1箇所のみメンテナンス
- バグ混入リスク低減
- 可読性向上

#### 2. 統合テストの追加

```python
def test_standard_vs_monte_carlo_convergence():
    """標準シミュレーションとMC中央値が近似することを検証"""
    # 同じ条件でシミュレーション
    standard_result = simulate_future_assets(...)
    mc_result = run_monte_carlo_simulation(...)

    # MC中央値と標準シミュレーションの差が5%以内
    assert abs(mc_median - standard_final) / standard_final < 0.05
```

#### 3. 重要な不変条件のアサーション追加

```python
# NISA残高は必ず株式残高以下
assert nisa_balance <= stocks, "NISA cannot exceed total stocks"

# 資産合計は単調減少しない（リターン適用前後）
assert new_assets >= old_assets * 0.95, "Unexpected asset decrease"
```

### 【優先度: 中】中期的に実施すべき対策

#### 4. ドキュメント整備

- [ ] `README.md` に各シミュレーション関数の役割を明記
- [ ] NISA処理の仕様書を作成
- [ ] 期待される動作をdocstringに記載

#### 5. 静的解析ツールの導入

```bash
# 型チェック
mypy src/

# コード品質チェック
pylint src/

# 重複コード検出
pylint --disable=all --enable=duplicate-code src/
```

#### 6. コードレビューチェックリスト

- [ ] 重複ロジックがないか？
- [ ] 全ての関連箇所を更新したか？
- [ ] テストを追加/更新したか？
- [ ] ドキュメントを更新したか？

### 【優先度: 低】長期的な改善

#### 7. 継続的インテグレーション（CI）

GitHub Actions等でテスト自動実行:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: pytest tests/
```

#### 8. プロパティベーステスト

Hypothesis等を使用して広範な入力でテスト:
```python
from hypothesis import given, strategies as st

@given(
    annual_return=st.floats(min_value=0.0, max_value=0.15),
    years=st.integers(min_value=1, max_value=50)
)
def test_simulation_always_positive_or_zero(annual_return, years):
    result = simulate_future_assets(...)
    assert result >= 0, "Assets cannot be negative"
```

## 即座に確認すべき箇所

### チェックリスト

1. [ ] `simulate_with_random_returns` は使用されているか？削除可能か？
2. [ ] FIRE前の月次処理でNISA返却は正しく適用されているか？
3. [ ] `_sell_stocks_with_tax` の全ての呼び出し箇所で戻り値を正しく処理しているか？
4. [ ] 年金計算、児童手当計算が全てのシミュレーションで同じロジックか？
5. [ ] インフレ率の適用が全てのシミュレーションで整合しているか？

## まとめ

**今回のバグは氷山の一角である可能性が高い。**

コードの重複と
テスト不足により、同様の不整合が他にも潜んでいる可能性がある。

**最優先アクション:**
1. 重複コードのリファクタリング
2. 統合テストの追加
3. 上記チェックリストの実施

これにより、同様のバグの再発を防ぎ、コード品質を大幅に向上できる。
