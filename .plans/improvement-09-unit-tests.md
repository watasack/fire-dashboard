# 改善計画9: ユニットテストの追加

## 目的
主要な計算ロジックにユニットテストを追加し、リファクタリング時の安全性を向上させる。

---

## 実装計画

### Step 9.1: テスト環境のセットアップ

```bash
# pytest のインストール
pip install pytest pytest-cov

# テストディレクトリ作成
mkdir tests
touch tests/__init__.py
```

### Step 9.2: simulator.py のテスト

```python
# tests/test_simulator.py
import pytest
from src.simulator import (
    _get_monthly_return_rate,
    calculate_education_expense,
    calculate_pension_income,
    _sell_stocks_with_tax,
    calculate_real_value
)

class TestMonthlyReturnRate:
    """月次リターン計算のテスト"""

    def test_5_percent_annual_return(self):
        """年率5%が正しく月率に変換されるか"""
        monthly_rate = _get_monthly_return_rate(0.05)
        expected = (1.05 ** (1/12)) - 1
        assert abs(monthly_rate - expected) < 0.0001

    def test_zero_return(self):
        """年率0%が月率0%になるか"""
        assert _get_monthly_return_rate(0.0) == 0.0

    def test_negative_return(self):
        """マイナスリターンも正しく変換されるか"""
        monthly_rate = _get_monthly_return_rate(-0.1)
        assert monthly_rate < 0


class TestEducationExpense:
    """教育費計算のテスト"""

    @pytest.fixture
    def config(self):
        return {
            'education': {
                'enabled': True,
                'children': [
                    {
                        'name': '颯',
                        'birthdate': '2022/02/26',
                        'nursery': 'standard',
                        'elementary': 'public',
                        # ...
                    }
                ],
                'costs': {
                    'nursery': {'standard': 714000},
                    'elementary': {'public': 320000},
                    # ...
                }
            }
        }

    def test_nursery_age_child(self, config):
        """0-2歳の教育費が保育園費用になるか"""
        year_offset = 1.0  # 2026年 → 颯は4歳
        expense = calculate_education_expense(year_offset, config)
        assert expense > 0  # 幼稚園費用

    def test_disabled_education(self):
        """教育費が無効の場合は0円か"""
        config = {'education': {'enabled': False}}
        expense = calculate_education_expense(0, config)
        assert expense == 0


class TestPensionIncome:
    """年金計算のテスト"""

    @pytest.fixture
    def config(self):
        return {
            'pension': {
                'enabled': True,
                'start_age': 65,
                'people': [
                    {
                        'name': '修平',
                        'birthdate': '1990/05/13',
                        'pension_type': 'employee',
                        'work_start_age': 23,
                        'avg_monthly_salary': 625615
                    }
                ]
            },
            'simulation': {'start_age': 35}
        }

    def test_before_pension_age(self, config):
        """年金受給前は0円か"""
        year_offset = 10  # 45歳
        total, shuhei, sakura = calculate_pension_income(
            year_offset, fire_achieved=True, config=config
        )
        assert total == 0

    def test_after_pension_age(self, config):
        """年金受給後は正の値か"""
        year_offset = 30  # 65歳
        total, shuhei, sakura = calculate_pension_income(
            year_offset, fire_achieved=True, config=config
        )
        assert total > 0
        assert shuhei > 0  # 厚生年金 + 国民年金


class TestStockSale:
    """株式売却・課税のテスト"""

    def test_nisa_sale_no_tax(self):
        """NISA売却は非課税か"""
        cash, stocks, nisa, _, _, gains = _sell_stocks_with_tax(
            cash=0,
            stocks=10_000_000,
            nisa_balance=10_000_000,
            stocks_cost_basis=8_000_000,
            nisa_cost_basis=8_000_000,
            shortage=1_000_000,
            tax_rate=0.20315
        )
        assert cash == 1_000_000  # 税金なし
        assert gains == 0  # 譲渡益計上なし

    def test_taxable_stock_sale(self):
        """課税口座売却は20.315%課税か"""
        cash, stocks, nisa, _, _, gains = _sell_stocks_with_tax(
            cash=0,
            stocks=10_000_000,
            nisa_balance=0,  # NISA残高なし
            stocks_cost_basis=5_000_000,
            nisa_cost_basis=0,
            shortage=1_000_000,
            tax_rate=0.20315
        )
        # 譲渡益 = 1,000,000 × (1 - 5M/10M) = 500,000
        # 税額 = 500,000 × 0.20315 = 101,575
        # 手取り = 1,000,000 - 101,575 = 898,425
        assert abs(cash - 898_425) < 100  # 誤差許容
        assert gains == pytest.approx(500_000, rel=0.01)


class TestRealValue:
    """実質価値計算のテスト"""

    def test_no_inflation(self):
        """インフレ0%なら名目=実質"""
        real = calculate_real_value(100_000_000, 2025, 2054, 0.0)
        assert real == 100_000_000

    def test_2_percent_inflation(self):
        """インフレ2%で29年後の実質価値"""
        real = calculate_real_value(100_000_000, 2025, 2054, 0.02)
        expected = 100_000_000 / (1.02 ** 29)
        assert abs(real - expected) < 1000

    def test_same_year(self):
        """同一年なら名目=実質"""
        real = calculate_real_value(100_000_000, 2025, 2025, 0.02)
        assert real == 100_000_000
```

### Step 9.3: テスト実行

```bash
# 全テスト実行
pytest tests/ -v

# カバレッジレポート
pytest tests/ --cov=src --cov-report=html
# → htmlcov/index.html でカバレッジ確認
```

### Step 9.4: CI/CD への統合（オプション）

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=src
```

---

## 検証方法

```bash
pytest tests/ -v
# → All tests passed
```

---

## 実装順序

1. Step 9.1: テスト環境セットアップ
2. Step 9.2: 基本的な計算関数のテスト作成
3. Step 9.3: テスト実行・カバレッジ確認
4. テストが通らない箇所の修正
5. Step 9.4: CI/CD統合（オプション）
6. コミット

---

## 期待される効果

- **リファクタリングの安全性**: 変更後もテストが通れば動作保証
- **バグの早期発見**: 計算ロジックのバグをテストで検出
- **ドキュメントとしての役割**: テストコードが使用例になる
- **信頼性向上**: テストカバレッジ80%以上を目指す

---

## 前提条件

改善計画1-2が完了していると、テストが書きやすい

---

## 関連ファイル

- `tests/test_simulator.py` (新規作成)
- `tests/test_analyzer.py` (新規作成)
- `tests/test_visualizer.py` (新規作成)
- `pytest.ini` (新規作成)

---

## 所要時間見積もり

4-6時間
