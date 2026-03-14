"""
analytics.py — MCシミュレーション結果の分析ユーティリティ
"""
from __future__ import annotations

import numpy as np
from typing import Any, Dict


def calc_depletion_age(mc_res: Dict[str, Any], percentile: float, config: Dict[str, Any]) -> float:
    """
    MCパスのうち percentile 分位のパスが何歳で資産枯渇するかを返す。

    Args:
        mc_res:     run_mc_fixed_fire / run_monte_carlo_simulation の返り値
        percentile: 0–1 の実数（例: 0.05 = 下位5%）
        config:     設定辞書（safety_margin の参照に使用）

    Returns:
        枯渇年齢（夫の年齢）。枯渇しなかったパスはシミュレーション終端（90歳相当）
        として扱う。
    """
    all_paths = mc_res.get("all_paths")
    if all_paths is None or len(all_paths) == 0:
        return float("nan")

    fire_age_h: float = mc_res.get("fire_age_h", 35.0)
    safety_margin: float = config["post_fire_cash_strategy"]["safety_margin"]

    n_paths, n_months = all_paths.shape

    depletion_months = []
    for path in all_paths:
        zero_crossings = np.where(path <= safety_margin)[0]
        if len(zero_crossings) > 0:
            depletion_months.append(int(zero_crossings[0]))
        else:
            depletion_months.append(n_months - 1)  # 枯渇なし → 終端

    depletion_month = float(np.percentile(depletion_months, percentile * 100))
    # index 0 = FIRE時点、index m = FIRE後 m ヶ月
    depletion_age = fire_age_h + depletion_month / 12.0
    return depletion_age


def get_bankrupt_depletion_ages(mc_res: Dict[str, Any], config: Dict[str, Any]) -> list[float]:
    """
    破産したパスの枯渇年齢リストを返す（ヒストグラム描画用）。
    """
    all_paths = mc_res.get("all_paths")
    if all_paths is None or len(all_paths) == 0:
        return []

    fire_age_h: float = mc_res.get("fire_age_h", 35.0)
    safety_margin: float = config["post_fire_cash_strategy"]["safety_margin"]

    ages = []
    for path in all_paths:
        zero_crossings = np.where(path <= safety_margin)[0]
        if len(zero_crossings) > 0:
            ages.append(fire_age_h + int(zero_crossings[0]) / 12.0)
    return ages
