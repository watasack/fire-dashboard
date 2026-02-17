"""
設定管理モジュール
config.yamlの読み込みと検証を担当
"""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """
    設定ファイルを読み込む

    Args:
        config_path: 設定ファイルのパス

    Returns:
        設定辞書

    Raises:
        FileNotFoundError: 設定ファイルが見つからない場合
        ValueError: 必須パラメータが不足している場合
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 設定の検証
    _validate_config(config)

    return config


def _validate_config(config: Dict[str, Any]) -> None:
    """
    設定の妥当性を検証

    Args:
        config: 設定辞書

    Raises:
        ValueError: 必須パラメータが不足している場合
    """
    # 必須セクションの確認
    required_sections = ['data', 'simulation', 'fire', 'visualization', 'output']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required section: {section}")

    # データ設定の確認
    data_config = config['data']
    if 'asset_file' not in data_config:
        raise ValueError("Missing required parameter: data.asset_file")
    if 'transaction_pattern' not in data_config:
        raise ValueError("Missing required parameter: data.transaction_pattern")

    # シミュレーション設定の確認
    sim_config = config['simulation']
    required_scenarios = ['standard', 'optimistic', 'pessimistic']
    for scenario in required_scenarios:
        if scenario not in sim_config:
            raise ValueError(f"Missing required scenario: simulation.{scenario}")

        scenario_config = sim_config[scenario]
        required_params = ['annual_return_rate', 'inflation_rate',
                          'income_growth_rate', 'expense_growth_rate']
        for param in required_params:
            if param not in scenario_config:
                raise ValueError(f"Missing parameter: simulation.{scenario}.{param}")



def get_scenario_config(config: Dict[str, Any], scenario: str = 'standard') -> Dict[str, Any]:
    """
    特定のシナリオ設定を取得

    Args:
        config: 設定辞書
        scenario: シナリオ名（'standard', 'optimistic', 'pessimistic'）

    Returns:
        シナリオ設定辞書
    """
    if scenario not in config['simulation']:
        raise ValueError(f"Unknown scenario: {scenario}")

    return config['simulation'][scenario]
