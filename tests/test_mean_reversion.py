#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
平均回帰機能のテスト

generate_random_returns()の平均回帰モデルが正しく機能することを検証
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from src.simulator import generate_random_returns


def test_baseline_no_reversion():
    """
    テスト1: mean_reversion_speed = 0.0 は独立な乱数を生成

    平均回帰なしの場合、リターンの自己相関は0に近いはず
    """
    print("=" * 80)
    print("テスト1: 平均回帰なし（baseline）")
    print("=" * 80)

    np.random.seed(42)
    returns = generate_random_returns(
        annual_return_mean=0.05,
        annual_return_std=0.06,
        total_months=1000,
        mean_reversion_speed=0.0,
        random_seed=42
    )

    # 自己相関係数を計算（lag=1）
    autocorr = np.corrcoef(returns[:-1], returns[1:])[0, 1]

    print(f"生成されたリターン数: {len(returns)}")
    print(f"平均リターン: {np.mean(returns):.4f} (期待値: 0.0041)")
    print(f"標準偏差: {np.std(returns):.4f} (期待値: 0.0173)")
    print(f"自己相関係数 (lag=1): {autocorr:.4f}")
    print()

    # 自己相関は0に近いはず（-0.1 ~ 0.1）
    assert abs(autocorr) < 0.1, \
        f"平均回帰なしの場合、自己相関は0に近いはず: {autocorr:.4f}"

    print("[OK] 平均回帰なしのテスト合格")
    print()


def test_mean_reversion_property():
    """
    テスト2: mean_reversion_speed > 0 は負の自己相関を生成

    平均回帰ありの場合、リターンは負の自己相関を持つはず
    （大きな下落の後は上昇しやすい、大きな上昇の後は下落しやすい）
    """
    print("=" * 80)
    print("テスト2: 平均回帰の基本特性（負の自己相関）")
    print("=" * 80)

    np.random.seed(42)
    returns = generate_random_returns(
        annual_return_mean=0.05,
        annual_return_std=0.06,
        total_months=1000,
        mean_reversion_speed=0.3,
        random_seed=42
    )

    # 自己相関係数を計算（lag=1）
    autocorr = np.corrcoef(returns[:-1], returns[1:])[0, 1]

    print(f"生成されたリターン数: {len(returns)}")
    print(f"平均リターン: {np.mean(returns):.4f}")
    print(f"標準偏差: {np.std(returns):.4f}")
    print(f"自己相関係数 (lag=1): {autocorr:.4f}")
    print()

    # 自己相関は負であるべき
    assert autocorr < -0.05, \
        f"平均回帰ありの場合、自己相関は負であるはず: {autocorr:.4f}"

    print("[OK] 負の自己相関を確認")
    print()


def test_reversion_after_large_drop():
    """
    テスト3: 大幅下落後は反発する傾向

    連続する大幅下落（-10%以下）の後、次月が上昇する確率を検証
    """
    print("=" * 80)
    print("テスト3: 大幅下落後の反発傾向")
    print("=" * 80)

    # 平均回帰なし
    np.random.seed(42)
    returns_no_reversion = generate_random_returns(
        annual_return_mean=0.05,
        annual_return_std=0.06,
        total_months=10000,
        mean_reversion_speed=0.0,
        random_seed=42
    )

    # 平均回帰あり
    np.random.seed(42)
    returns_with_reversion = generate_random_returns(
        annual_return_mean=0.05,
        annual_return_std=0.06,
        total_months=10000,
        mean_reversion_speed=0.3,
        random_seed=42
    )

    # 大幅下落（-5%以下）の後の反発率を計算
    def calc_rebound_rate(returns, threshold=-0.05):
        """大幅下落後に反発する確率を計算"""
        large_drops = returns < threshold
        rebounds_after_drop = []

        for i in range(len(returns) - 1):
            if large_drops[i]:
                # 次月が上昇したか
                rebounds_after_drop.append(returns[i + 1] > 0)

        if len(rebounds_after_drop) == 0:
            return 0.0

        return np.mean(rebounds_after_drop)

    rebound_rate_no_rev = calc_rebound_rate(returns_no_reversion)
    rebound_rate_with_rev = calc_rebound_rate(returns_with_reversion)

    print(f"大幅下落（-5%以下）の発生回数:")
    print(f"  平均回帰なし: {np.sum(returns_no_reversion < -0.05)}回")
    print(f"  平均回帰あり: {np.sum(returns_with_reversion < -0.05)}回")
    print()
    print(f"大幅下落後の反発率（次月がプラス）:")
    print(f"  平均回帰なし: {rebound_rate_no_rev:.1%}")
    print(f"  平均回帰あり: {rebound_rate_with_rev:.1%}")
    print()

    # 平均回帰ありの方が反発率が高いはず
    assert rebound_rate_with_rev > rebound_rate_no_rev, \
        f"平均回帰ありの方が反発率が高いはず: {rebound_rate_with_rev:.1%} > {rebound_rate_no_rev:.1%}"

    # 反発率の差が少なくとも5%ポイント以上
    improvement = rebound_rate_with_rev - rebound_rate_no_rev
    assert improvement >= 0.05, \
        f"反発率の改善が不十分: {improvement:.1%}"

    print(f"[OK] 反発率が {improvement:.1%} ポイント向上")
    print()


def test_reversion_strength_scaling():
    """
    テスト4: mean_reversion_speedの強度スケーリング

    より大きなmean_reversion_speedはより強い平均回帰を生成
    """
    print("=" * 80)
    print("テスト4: 平均回帰強度のスケーリング")
    print("=" * 80)

    speeds = [0.0, 0.2, 0.5, 0.8]
    autocorrs = []

    for speed in speeds:
        np.random.seed(42)
        returns = generate_random_returns(
            annual_return_mean=0.05,
            annual_return_std=0.06,
            total_months=1000,
            mean_reversion_speed=speed,
            random_seed=42
        )

        autocorr = np.corrcoef(returns[:-1], returns[1:])[0, 1]
        autocorrs.append(autocorr)

        print(f"mean_reversion_speed = {speed:.1f}: 自己相関 = {autocorr:.4f}")

    print()

    # 自己相関は単調減少するはず（より負になる）
    for i in range(len(autocorrs) - 1):
        assert autocorrs[i] > autocorrs[i + 1], \
            f"自己相関は単調減少するはず: {autocorrs[i]:.4f} > {autocorrs[i+1]:.4f}"

    print("[OK] 平均回帰強度のスケーリングを確認")
    print()


def test_consecutive_crashes_reduced():
    """
    テスト5: 連続暴落シナリオの抑制

    平均回帰により、3ヶ月以上連続でマイナスになる確率が減少
    """
    print("=" * 80)
    print("テスト5: 連続暴落シナリオの抑制")
    print("=" * 80)

    # 平均回帰なし
    np.random.seed(42)
    returns_no_reversion = generate_random_returns(
        annual_return_mean=0.05,
        annual_return_std=0.06,
        total_months=10000,
        mean_reversion_speed=0.0,
        random_seed=42
    )

    # 平均回帰あり
    np.random.seed(42)
    returns_with_reversion = generate_random_returns(
        annual_return_mean=0.05,
        annual_return_std=0.06,
        total_months=10000,
        mean_reversion_speed=0.3,
        random_seed=42
    )

    def count_consecutive_negative_runs(returns, min_length=3):
        """連続でマイナスになる期間の回数をカウント"""
        consecutive_count = 0
        run_count = 0

        for r in returns:
            if r < 0:
                consecutive_count += 1
            else:
                if consecutive_count >= min_length:
                    run_count += 1
                consecutive_count = 0

        # 最後の連続期間をチェック
        if consecutive_count >= min_length:
            run_count += 1

        return run_count

    runs_no_rev = count_consecutive_negative_runs(returns_no_reversion, min_length=3)
    runs_with_rev = count_consecutive_negative_runs(returns_with_reversion, min_length=3)

    print(f"3ヶ月以上連続でマイナスになった回数（10,000ヶ月中）:")
    print(f"  平均回帰なし: {runs_no_rev}回")
    print(f"  平均回帰あり: {runs_with_rev}回")
    print()

    # 平均回帰により連続暴落が減少
    reduction = (runs_no_rev - runs_with_rev) / runs_no_rev if runs_no_rev > 0 else 0
    print(f"連続暴落の減少率: {reduction:.1%}")
    print()

    # 平均回帰ありの方が連続暴落が少ないはず
    assert runs_with_rev < runs_no_rev, \
        f"平均回帰により連続暴落が減少するはず: {runs_with_rev} < {runs_no_rev}"

    # 少なくとも20%減少
    assert reduction >= 0.2, \
        f"連続暴落の減少が不十分: {reduction:.1%}"

    print(f"[OK] 連続暴落が {reduction:.1%} 減少")
    print()


def test_long_term_mean_preservation():
    """
    テスト6: 長期平均リターンの保存

    平均回帰を導入しても、長期的な平均リターンは期待値に収束
    """
    print("=" * 80)
    print("テスト6: 長期平均リターンの保存")
    print("=" * 80)

    expected_monthly_return = (1 + 0.05) ** (1/12) - 1

    for speed in [0.0, 0.3, 0.5]:
        np.random.seed(42)
        returns = generate_random_returns(
            annual_return_mean=0.05,
            annual_return_std=0.06,
            total_months=10000,
            mean_reversion_speed=speed,
            random_seed=42
        )

        mean_return = np.mean(returns)
        error = abs(mean_return - expected_monthly_return)

        print(f"mean_reversion_speed = {speed:.1f}:")
        print(f"  平均リターン: {mean_return:.6f}")
        print(f"  期待値: {expected_monthly_return:.6f}")
        print(f"  誤差: {error:.6f}")
        print()

        # 誤差は0.001以下（10,000サンプルなので十分収束）
        assert error < 0.001, \
            f"長期平均リターンが期待値から乖離: 誤差 {error:.6f}"

    print("[OK] すべての平均回帰速度で長期平均が保存")
    print()


def main():
    """すべてのテストを実行"""
    print("\n")
    print("=" * 80)
    print("平均回帰機能の統合テスト")
    print("=" * 80)
    print()

    try:
        test_baseline_no_reversion()
        test_mean_reversion_property()
        test_reversion_after_large_drop()
        test_reversion_strength_scaling()
        test_consecutive_crashes_reduced()
        test_long_term_mean_preservation()

        print("=" * 80)
        print("全テスト合格 [OK]")
        print("=" * 80)
        print()
        print("結論: 平均回帰モデルは期待通りに機能しています")
        print("  - 大幅下落後の反発が促進される")
        print("  - 連続暴落シナリオが抑制される")
        print("  - 長期平均リターンは保存される")
        print()

    except AssertionError as e:
        print()
        print("=" * 80)
        print("テスト失敗 [FAILED]")
        print("=" * 80)
        print(f"エラー: {e}")
        print()
        sys.exit(1)


if __name__ == '__main__':
    main()
