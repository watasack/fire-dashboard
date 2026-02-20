# 改善計画8: 設定ファイルの検証機能

## 目的
Pydanticを使った設定検証で、不正な設定値を早期発見する。

---

## 実装計画

### Step 8.1: Pydantic モデル定義

```python
# src/config_schema.py (新規作成)
from pydantic import BaseModel, validator, Field
from typing import Dict, List, Optional

class ScenarioConfig(BaseModel):
    annual_return_rate: float = Field(..., ge=-0.5, le=0.3)
    inflation_rate: float = Field(..., ge=0, le=0.1)
    income_growth_rate: float = Field(..., ge=-0.1, le=0.1)
    expense_growth_rate: float = Field(..., ge=0, le=0.1)

    @validator('annual_return_rate')
    def validate_return_rate(cls, v):
        if not -0.5 <= v <= 0.3:
            raise ValueError('年率リターンは-50%〜30%の範囲で設定してください')
        return v

class ChildConfig(BaseModel):
    name: str
    birthdate: str
    nursery: str
    kindergarten: str
    elementary: str
    junior_high: str
    high: str
    university: str

    @validator('birthdate')
    def validate_birthdate(cls, v):
        try:
            datetime.strptime(v, '%Y/%m/%d')
        except ValueError:
            raise ValueError('誕生日はYYYY/MM/DD形式で入力してください')
        return v

class SimulationConfig(BaseModel):
    years: int = Field(..., ge=1, le=100)
    life_expectancy: int = Field(..., ge=60, le=120)
    shuhei_income: float = Field(..., ge=0)
    sakura_income: float = Field(..., ge=0)
    standard: ScenarioConfig
    optimistic: ScenarioConfig
    pessimistic: ScenarioConfig

class EducationConfig(BaseModel):
    enabled: bool
    children: List[ChildConfig]

class FIREConfig(BaseModel):
    simulation: SimulationConfig
    education: EducationConfig
    # ... 他のセクション

    @validator('simulation')
    def validate_simulation(cls, v):
        # 楽観シナリオのリターンが標準より高いことをチェック
        if v.optimistic.annual_return_rate <= v.standard.annual_return_rate:
            raise ValueError(
                '楽観シナリオのリターンは標準シナリオより高く設定してください'
            )
        return v
```

### Step 8.2: 設定読み込み時の検証

```python
# src/config.py を更新

from src.config_schema import FIREConfig

def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """設定ファイル読み込み（検証付き）"""
    with open(config_path, 'r', encoding='utf-8') as f:
        raw_config = yaml.safe_load(f)

    # Pydantic で検証
    try:
        validated_config = FIREConfig(**raw_config)
        return validated_config.dict()
    except Exception as e:
        print(f"❌ 設定ファイルにエラーがあります: {e}")
        raise
```

### Step 8.3: エラーメッセージの改善

```python
validation error for FIREConfig
simulation -> optimistic -> annual_return_rate
  年率リターンは-50%〜30%の範囲で設定してください (type=value_error)
```

---

## 検証方法

### 正常系

```bash
python scripts/generate_dashboard.py
# → 正常に実行される
```

### 異常系

```yaml
# config.yaml に不正な値を設定
simulation:
  standard:
    annual_return_rate: 1.5  # 150% → 異常
```

```bash
python scripts/generate_dashboard.py
# → エラーメッセージが表示される
```

---

## 所要時間見積もり

3-4時間
