"""
シミュレーションデータのスキーマ定義

このモジュールでは、資産シミュレーションで使用するデータ項目を一元管理します。
新しい項目を追加する場合は、このファイルのみを修正すればよいようになっています。
"""

from typing import Dict, List
from collections import OrderedDict


# =============================================================================
# DataFrameカラム定義
# =============================================================================

# シミュレーション結果のDataFrameに保存される全カラム
# OrderedDictを使用して順序を保証
SIMULATION_COLUMNS = OrderedDict([
    # 基本情報
    ('date', {'type': 'datetime', 'description': '日付'}),
    ('month', {'type': 'int', 'description': 'シミュレーション開始からの月数'}),

    # 資産関連
    ('assets', {'type': 'float', 'description': '総資産（現金+株式）'}),
    ('cash', {'type': 'float', 'description': '現金・預金'}),
    ('stocks', {'type': 'float', 'description': '投資信託（株式）'}),
    ('stocks_cost_basis', {'type': 'float', 'description': '株式の取得価額（簿価）'}),
    ('nisa_balance', {'type': 'float', 'description': 'NISA口座残高'}),

    # 収入関連
    ('income', {'type': 'float', 'description': '月次総収入'}),
    ('labor_income', {'type': 'float', 'description': '労働収入'}),
    ('pension_income', {'type': 'float', 'description': '年金収入'}),
    ('child_allowance', {'type': 'float', 'description': '児童手当'}),

    # 支出関連
    ('expense', {'type': 'float', 'description': '月次総支出'}),
    ('base_expense', {'type': 'float', 'description': '基本生活費'}),
    ('education_expense', {'type': 'float', 'description': '教育費'}),
    ('mortgage_payment', {'type': 'float', 'description': '住宅ローン返済額'}),
    ('maintenance_cost', {'type': 'float', 'description': 'メンテナンス費用'}),
    ('workation_cost', {'type': 'float', 'description': 'ワーケーション費用'}),
    ('pension_premium', {'type': 'float', 'description': '国民年金保険料'}),
    ('health_insurance_premium', {'type': 'float', 'description': '国民健康保険料'}),

    # その他
    ('net_cashflow', {'type': 'float', 'description': '純キャッシュフロー（収入-支出）'}),
    ('investment_return', {'type': 'float', 'description': '運用益'}),
    ('auto_invested', {'type': 'float', 'description': '自動投資額（NISA）'}),
    ('capital_gains_tax', {'type': 'float', 'description': '譲渡益課税額'}),

    # FIRE関連
    ('fire_achieved', {'type': 'bool', 'description': 'FIRE達成フラグ'}),
    ('fire_month', {'type': 'int', 'description': 'FIRE達成月（未達成時はNone）'}),
])


# =============================================================================
# 詳細表示用のcustomdataカラム定義
# =============================================================================

# Plotlyのcustomdataとして渡すカラムリスト（順序重要）
# この順序がhtml_generator.pyでのインデックスアクセスに対応します
CUSTOMDATA_COLUMNS = [
    # 収入
    'labor_income',
    'pension_income',
    'child_allowance',

    # 支出
    'base_expense',
    'education_expense',
    'mortgage_payment',
    'maintenance_cost',
    'workation_cost',
    'pension_premium',
    'health_insurance_premium',

    # その他
    'investment_return',
    'cash',
    'stocks',
    'auto_invested',
    'capital_gains_tax',
]


# =============================================================================
# 表示名マッピング
# =============================================================================

DISPLAY_NAMES: Dict[str, str] = {
    # 基本情報
    'date': '日付',
    'month': '月',

    # 資産
    'assets': '総資産',
    'cash': '現金・預金',
    'stocks': '投資信託',
    'stocks_cost_basis': '株式簿価',
    'nisa_balance': 'NISA残高',

    # 収入
    'income': '収入合計',
    'labor_income': '労働収入',
    'pension_income': '年金収入',
    'child_allowance': '児童手当',

    # 支出
    'expense': '支出合計',
    'base_expense': '基本生活費',
    'education_expense': '教育費',
    'mortgage_payment': '住宅ローン',
    'maintenance_cost': 'メンテナンス費用',
    'workation_cost': 'ワーケーション費用',
    'pension_premium': '国民年金保険料',
    'health_insurance_premium': '国民健康保険料',

    # その他
    'net_cashflow': '純キャッシュフロー',
    'investment_return': '運用益',
    'auto_invested': '自動投資（NISA）',
    'capital_gains_tax': '譲渡益課税',

    # FIRE
    'fire_achieved': 'FIRE達成',
    'fire_month': 'FIRE達成月',
}


# =============================================================================
# カテゴリ分類
# =============================================================================

# 収入項目
INCOME_COLUMNS = [
    'labor_income',
    'pension_income',
    'child_allowance',
]

# 支出項目
EXPENSE_COLUMNS = [
    'base_expense',
    'education_expense',
    'mortgage_payment',
    'maintenance_cost',
    'workation_cost',
    'pension_premium',
    'health_insurance_premium',
]

# 資産項目
ASSET_COLUMNS = [
    'cash',
    'stocks',
    'nisa_balance',
]


# =============================================================================
# ヘルパー関数
# =============================================================================

def get_column_names() -> List[str]:
    """全カラム名のリストを取得"""
    return list(SIMULATION_COLUMNS.keys())


def get_customdata_column_names() -> List[str]:
    """customdata用カラム名のリストを取得"""
    return CUSTOMDATA_COLUMNS.copy()


def get_display_name(column: str) -> str:
    """カラムの表示名を取得"""
    return DISPLAY_NAMES.get(column, column)


def get_customdata_index(column: str) -> int:
    """customdata内でのカラムのインデックスを取得"""
    try:
        return CUSTOMDATA_COLUMNS.index(column)
    except ValueError:
        raise ValueError(f"Column '{column}' is not in CUSTOMDATA_COLUMNS")


def validate_customdata_length(length: int) -> bool:
    """customdataの長さが正しいかチェック"""
    return length >= len(CUSTOMDATA_COLUMNS)
