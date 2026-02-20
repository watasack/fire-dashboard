# 改善計画7: 早期退職シナリオの比較

## 目的
複数の退職時期を比較し、「今退職したら？」「3年後なら？」を並べて表示する。

---

## 実装計画

### Step 7.1: 複数シナリオのシミュレーション

```python
def simulate_multiple_retirement_dates(
    current_cash: float,
    current_stocks: float,
    config: Dict[str, Any],
    retirement_years: List[int] = [0, 3, 5, 10]
) -> Dict[int, pd.DataFrame]:
    """
    複数の退職時期でシミュレーション

    Args:
        retirement_years: 今から何年後に退職するか

    Returns:
        {年数: シミュレーション結果}
    """
```

### Step 7.2: 比較グラフの作成

```python
def create_retirement_comparison_chart(
    scenarios: Dict[int, pd.DataFrame],
    config: Dict[str, Any]
) -> go.Figure:
    """
    複数退職シナリオの比較グラフ

    各シナリオの資産推移を1つのグラフに重ねて表示
    """
```

### Step 7.3: サマリーテーブルの作成

```html
<table>
  <tr>
    <th>退職時期</th>
    <th>退職時資産</th>
    <th>最終資産</th>
    <th>成功/失敗</th>
  </tr>
  <tr>
    <td>今すぐ</td>
    <td>¥56,338,172</td>
    <td>¥12,450,000</td>
    <td>❌ 失敗</td>
  </tr>
  <tr>
    <td>3年後</td>
    <td>¥72,000,000</td>
    <td>¥45,200,000</td>
    <td>⚠️ ギリギリ</td>
  </tr>
  <tr>
    <td>5年後</td>
    <td>¥85,091,728</td>
    <td>¥62,800,000</td>
    <td>✅ 成功</td>
  </tr>
</table>
```

---

## 検証方法

ダッシュボードに比較グラフとサマリーテーブルが表示されること

---

## 所要時間見積もり

3-4時間
