"""汎用ユーティリティ関数"""


def fmt_oku(yen: float) -> str:
    """円単位の値を億/万円で表記する"""
    man = yen / 10000
    if man >= 10000:
        return f"{man/10000:.1f}億円"
    return f"{man:,.0f}万円"
