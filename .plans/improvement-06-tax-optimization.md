# 改善計画6: 税金最適化の提案機能

## 目的
NISA活用度合いと節税機会を可視化し、税金最適化の提案を表示する。

---

## 実装計画

### Step 6.1: NISA活用度分析

```python
def analyze_nisa_utilization(
    simulations: Dict[str, pd.DataFrame]
) -> Dict[str, Any]:
    """
    NISA活用度を分析

    Returns:
        {
            'total_invested': NISA累計投資額,
            'total_limit': NISA累計上限額,
            'utilization_rate': 活用率（0-1）,
            'unused_limit': 未活用枠,
            'years_analyzed': 分析年数
        }
    """
```

### Step 6.2: 譲渡益課税の試算

```python
def estimate_capital_gains_tax_saved(
    simulations: Dict[str, pd.DataFrame]
) -> float:
    """
    NISA活用により節税できた譲渡益課税を試算

    Returns:
        節税額（円）
    """
```

### Step 6.3: 最適化提案の生成

```python
def generate_tax_optimization_suggestions(
    nisa_analysis: Dict,
    tax_saved: float
) -> List[str]:
    """
    税金最適化の提案を生成

    Returns:
        提案のリスト
    """
    suggestions = []

    if nisa_analysis['utilization_rate'] < 0.9:
        suggestions.append(
            f"NISA枠を{(1 - nisa_analysis['utilization_rate']) * 100:.1f}%"
            "活用できていません。月次投資額を増やすことを検討してください。"
        )

    if tax_saved > 1_000_000:
        suggestions.append(
            f"NISA活用により約{tax_saved/10000:.0f}万円の譲渡益課税を削減できています。"
        )

    return suggestions
```

---

## 検証方法

ダッシュボードに以下が表示されること:
- NISA活用率: 95%
- 節税額: 120万円
- 最適化提案のリスト

---

## 所要時間見積もり

2-3時間
