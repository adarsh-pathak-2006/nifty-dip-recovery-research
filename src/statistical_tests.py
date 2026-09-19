"""
Statistical Tests — Hypothesis testing, confidence intervals, and bootstrap.

Methods implemented:
    1. One-sample t-test (H0: mean forward return = 0)
    2. Wilcoxon signed-rank test (non-parametric alternative)
    3. Parametric 95% confidence interval for the mean
    4. Bootstrap resampling for robust CI estimation
    5. Two-sample t-test (event returns vs baseline returns)

Why these methods:
    - The t-test assesses whether the mean forward return is significantly
      different from zero.  It assumes approximate normality of returns,
      which is reasonable with sufficient sample size (CLT).
    - The Wilcoxon test does NOT assume normality and tests whether the
      median return is significantly different from zero — useful as a
      robustness check.
    - Confidence intervals quantify the uncertainty around the estimated
      mean return — more informative than a simple p-value.
    - Bootstrap resampling provides a distribution-free CI estimate by
      repeatedly sampling with replacement, making it robust to outliers
      and non-normal distributions.
"""

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from config import BOOTSTRAP_ITERATIONS, BOOTSTRAP_CI, HOLDING_PERIODS


def one_sample_ttest(returns: np.ndarray, alternative: str = "greater") -> dict:
    """
    One-sample t-test: H0: mean = 0 vs H1: mean > 0

    We use a one-sided test because the hypothesis specifically predicts
    RECOVERY (positive returns), not just any deviation from zero.
    """
    t_stat, p_value = sp_stats.ttest_1samp(returns, popmean=0)

    # Adjust p-value for one-sided test
    if alternative == "greater":
        p_one_sided = p_value / 2 if t_stat > 0 else 1 - p_value / 2
    else:
        p_one_sided = p_value

    return {
        "test": "One-sample t-test",
        "h0": "Mean forward return = 0",
        "h1": "Mean forward return > 0",
        "t_statistic": t_stat,
        "p_value_two_sided": p_value,
        "p_value_one_sided": p_one_sided,
        "significant_5pct": p_one_sided < 0.05,
        "significant_1pct": p_one_sided < 0.01,
        "n": len(returns),
        "mean": returns.mean(),
        "se": returns.std(ddof=1) / np.sqrt(len(returns)),
    }


def wilcoxon_test(returns: np.ndarray) -> dict:
    """
    Wilcoxon signed-rank test: H0: median = 0 vs H1: median ≠ 0

    Non-parametric alternative — does not assume normality.
    Useful as a robustness check against the t-test.
    """
    # Remove zeros (Wilcoxon can't handle them)
    non_zero = returns[returns != 0]
    if len(non_zero) < 10:
        return {
            "test": "Wilcoxon signed-rank",
            "note": "Insufficient non-zero observations",
            "n": len(non_zero),
        }

    stat, p_value = sp_stats.wilcoxon(non_zero, alternative="greater")
    return {
        "test": "Wilcoxon signed-rank",
        "h0": "Median forward return = 0",
        "h1": "Median forward return > 0",
        "statistic": stat,
        "p_value": p_value,
        "significant_5pct": p_value < 0.05,
        "n": len(non_zero),
        "median": np.median(non_zero),
    }


def confidence_interval(returns: np.ndarray,
                        confidence: float = 0.95) -> dict:
    """
    Parametric confidence interval for the mean using the t-distribution.
    """
    n = len(returns)
    mean = returns.mean()
    se = returns.std(ddof=1) / np.sqrt(n)
    t_crit = sp_stats.t.ppf((1 + confidence) / 2, df=n - 1)

    ci_lower = mean - t_crit * se
    ci_upper = mean + t_crit * se

    return {
        "method": "Parametric (t-distribution)",
        "confidence": confidence,
        "mean": mean,
        "se": se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "contains_zero": ci_lower <= 0 <= ci_upper,
    }


def bootstrap_ci(returns: np.ndarray,
                 n_iterations: int = BOOTSTRAP_ITERATIONS,
                 confidence: float = BOOTSTRAP_CI) -> dict:
    """
    Bootstrap confidence interval for the mean.

    Process: Resample with replacement N times, compute the mean of each
    bootstrap sample, then take the (1-CI)/2 and (1+CI)/2 percentiles.
    """
    np.random.seed(42)
    boot_means = np.array([
        np.random.choice(returns, size=len(returns), replace=True).mean()
        for _ in range(n_iterations)
    ])

    alpha = 1 - confidence
    ci_lower = np.percentile(boot_means, 100 * alpha / 2)
    ci_upper = np.percentile(boot_means, 100 * (1 - alpha / 2))

    return {
        "method": "Bootstrap",
        "n_iterations": n_iterations,
        "confidence": confidence,
        "mean": returns.mean(),
        "bootstrap_mean": boot_means.mean(),
        "bootstrap_std": boot_means.std(),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "contains_zero": ci_lower <= 0 <= ci_upper,
        "boot_means": boot_means,  # for plotting
    }


def two_sample_test(event_returns: np.ndarray,
                    baseline_returns: np.ndarray) -> dict:
    """
    Two-sample t-test: Compare event forward returns vs baseline.
    H0: mean(event) = mean(baseline)
    H1: mean(event) > mean(baseline)
    """
    t_stat, p_value = sp_stats.ttest_ind(event_returns, baseline_returns,
                                          equal_var=False)
    p_one_sided = p_value / 2 if t_stat > 0 else 1 - p_value / 2

    return {
        "test": "Welch's two-sample t-test",
        "h0": "Mean event return = Mean baseline return",
        "h1": "Mean event return > Mean baseline return",
        "t_statistic": t_stat,
        "p_value_one_sided": p_one_sided,
        "significant_5pct": p_one_sided < 0.05,
        "event_mean": event_returns.mean(),
        "baseline_mean": baseline_returns.mean(),
        "difference": event_returns.mean() - baseline_returns.mean(),
    }


def run_all_tests(event_df: pd.DataFrame,
                  df: pd.DataFrame,
                  holding_periods: list = HOLDING_PERIODS) -> dict:
    """
    Run all statistical tests for each holding period.

    Returns
    -------
    dict : holding_period → {ttest, wilcoxon, ci, bootstrap, two_sample}
    """
    results = {}

    for hp in holding_periods:
        col = f"fwd_return_{hp}d"
        if col not in event_df.columns:
            continue

        event_returns = event_df[col].dropna().values
        if len(event_returns) < 5:
            results[hp] = {"note": "Insufficient data"}
            continue

        # Compute baseline returns for this holding period
        baseline_rets = []
        for i in range(len(df) - hp - 1):
            entry_idx = i + 1
            exit_idx = entry_idx + hp
            if exit_idx >= len(df):
                continue
            entry_p = df.loc[entry_idx, "Open"]
            exit_p = df.loc[exit_idx, "Close"]
            if entry_p > 0:
                baseline_rets.append((exit_p - entry_p) / entry_p)
        baseline_rets = np.array(baseline_rets)

        results[hp] = {
            "ttest": one_sample_ttest(event_returns),
            "wilcoxon": wilcoxon_test(event_returns),
            "ci": confidence_interval(event_returns),
            "bootstrap": bootstrap_ci(event_returns),
            "two_sample": two_sample_test(event_returns, baseline_rets),
        }

    return results


def format_test_results(results: dict) -> str:
    """Pretty-print all statistical test results."""
    lines = []
    lines.append("\n" + "=" * 70)
    lines.append("STATISTICAL TEST RESULTS")
    lines.append("=" * 70)

    for hp, tests in sorted(results.items()):
        lines.append(f"\n--- Holding Period: {hp} trading days ---")

        if "note" in tests:
            lines.append(f"  {tests['note']}")
            continue

        # T-test
        tt = tests["ttest"]
        lines.append(f"\n  1. {tt['test']}")
        lines.append(f"     H0: {tt['h0']}")
        lines.append(f"     Mean = {tt['mean']:.4f}, SE = {tt['se']:.4f}")
        lines.append(f"     t = {tt['t_statistic']:.3f}, "
                     f"p (one-sided) = {tt['p_value_one_sided']:.4f}")
        sig = "YES" if tt["significant_5pct"] else "NO"
        lines.append(f"     Significant at 5%: {sig}")

        # Wilcoxon
        wt = tests["wilcoxon"]
        lines.append(f"\n  2. {wt['test']}")
        if "note" in wt:
            lines.append(f"     {wt['note']}")
        else:
            lines.append(f"     Median = {wt['median']:.4f}")
            lines.append(f"     p = {wt['p_value']:.4f}")
            sig = "YES" if wt["significant_5pct"] else "NO"
            lines.append(f"     Significant at 5%: {sig}")

        # Confidence interval
        ci = tests["ci"]
        lines.append(f"\n  3. {ci['confidence']:.0%} Confidence Interval "
                     f"({ci['method']})")
        lines.append(f"     [{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}]")
        contains = "YES - includes zero" if ci["contains_zero"] else \
                   "NO - entirely above/below zero"
        lines.append(f"     Contains zero: {contains}")

        # Bootstrap
        bs = tests["bootstrap"]
        lines.append(f"\n  4. Bootstrap CI ({bs['n_iterations']} iterations)")
        lines.append(f"     [{bs['ci_lower']:.4f}, {bs['ci_upper']:.4f}]")
        contains = "YES" if bs["contains_zero"] else "NO"
        lines.append(f"     Contains zero: {contains}")

        # Two-sample
        ts = tests["two_sample"]
        lines.append(f"\n  5. {ts['test']} (Event vs Baseline)")
        lines.append(f"     Event mean: {ts['event_mean']:.4f}, "
                     f"Baseline mean: {ts['baseline_mean']:.4f}")
        lines.append(f"     Difference: {ts['difference']:.4f}")
        lines.append(f"     p (one-sided) = {ts['p_value_one_sided']:.4f}")
        sig = "YES" if ts["significant_5pct"] else "NO"
        lines.append(f"     Significant at 5%: {sig}")

    lines.append("\n" + "=" * 70)
    result = "\n".join(lines)
    print(result)
    return result
