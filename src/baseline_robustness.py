"""
Baseline & Robustness — Compares event returns to unconditional returns
and tests sensitivity across different parameter choices.

Purpose:
    1. Baseline comparison: Are post-dip returns genuinely different from
       what you'd get on any random day?
    2. Robustness sweep: Does the result hold across different event
       thresholds and holding periods, or is it an artefact of one
       specific parameter combination?
    3. Risk discussion: Data snooping, multiple testing, post-hoc
       parameter selection, overfitting.
"""

import pandas as pd
import numpy as np
from scipy import stats as sp_stats
from src.event_detector import detect_events, compute_forward_returns
from src.research_engine import compute_event_statistics
from config import (ROBUSTNESS_THRESHOLDS, ROBUSTNESS_HOLDING_PERIODS,
                    OVERLAP_COOLDOWN_DAYS)


def robustness_sweep(df: pd.DataFrame,
                     thresholds: list = ROBUSTNESS_THRESHOLDS,
                     holding_periods: list = ROBUSTNESS_HOLDING_PERIODS,
                     cooldown: int = OVERLAP_COOLDOWN_DAYS) -> pd.DataFrame:
    """
    Sweep across different (threshold, holding_period) combinations.

    Returns a DataFrame with columns:
        threshold, holding_period, n_events, mean_return, median_return,
        win_rate, t_stat, p_value
    """
    results = []

    for thresh in thresholds:
        event_df = detect_events(df, threshold=thresh, cooldown=cooldown)
        if len(event_df) == 0:
            continue

        event_df = compute_forward_returns(df, event_df,
                                           holding_periods=holding_periods)

        for hp in holding_periods:
            col = f"fwd_return_{hp}d"
            if col not in event_df.columns:
                continue

            returns = event_df[col].dropna().values
            if len(returns) < 5:
                continue

            t_stat, p_val = sp_stats.ttest_1samp(returns, 0)
            p_one_sided = p_val / 2 if t_stat > 0 else 1 - p_val / 2

            results.append({
                "threshold": thresh,
                "holding_period": hp,
                "n_events": len(returns),
                "mean_return": returns.mean(),
                "median_return": np.median(returns),
                "std_return": returns.std(),
                "win_rate": (returns > 0).mean(),
                "t_stat": t_stat,
                "p_value": p_one_sided,
                "significant": p_one_sided < 0.05,
            })

    return pd.DataFrame(results)


def in_sample_out_of_sample_split(df: pd.DataFrame,
                                  ratio: float = 0.70) -> tuple:
    """
    Split the data chronologically into in-sample and out-of-sample.

    Parameters
    ----------
    df : pd.DataFrame
    ratio : float — fraction of data for in-sample

    Returns
    -------
    (df_in, df_out) — both as DataFrames with reset indices
    """
    split_idx = int(len(df) * ratio)
    df_in = df.iloc[:split_idx].reset_index(drop=True)
    df_out = df.iloc[split_idx:].reset_index(drop=True)

    print(f"[Split] In-sample:  {len(df_in)} days "
          f"({df_in['Date'].min().strftime('%Y-%m-%d')} to "
          f"{df_in['Date'].max().strftime('%Y-%m-%d')})")
    print(f"[Split] Out-of-sample: {len(df_out)} days "
          f"({df_out['Date'].min().strftime('%Y-%m-%d')} to "
          f"{df_out['Date'].max().strftime('%Y-%m-%d')})")

    return df_in, df_out


def oos_comparison(df_in: pd.DataFrame, df_out: pd.DataFrame,
                   threshold: float, holding_periods: list,
                   cooldown: int = OVERLAP_COOLDOWN_DAYS) -> dict:
    """
    Compare in-sample vs out-of-sample results for the same parameters.
    """
    results = {"in_sample": {}, "out_of_sample": {}}

    for label, data in [("in_sample", df_in), ("out_of_sample", df_out)]:
        event_df = detect_events(data, threshold=threshold, cooldown=cooldown)
        if len(event_df) == 0:
            results[label] = {"n_events": 0}
            continue

        event_df = compute_forward_returns(data, event_df,
                                           holding_periods=holding_periods)
        stats = compute_event_statistics(event_df, holding_periods)
        results[label] = {
            "n_events": len(event_df),
            "stats": stats,
        }

    return results


def format_oos_results(oos_results: dict, holding_periods: list) -> str:
    """Pretty-print in-sample vs out-of-sample comparison."""
    lines = []
    lines.append("\n" + "=" * 70)
    lines.append("IN-SAMPLE vs OUT-OF-SAMPLE COMPARISON")
    lines.append("=" * 70)

    for label in ["in_sample", "out_of_sample"]:
        display = label.replace("_", "-").title()
        lines.append(f"\n{display}:")
        data = oos_results[label]
        if data.get("n_events", 0) == 0:
            lines.append("  No events found.")
            continue

        lines.append(f"  Events: {data['n_events']}")
        for hp in holding_periods:
            s = data["stats"].get(hp, {})
            if s.get("n", 0) == 0:
                continue
            lines.append(f"  {hp}d: mean={s['mean']:.4f}, "
                         f"median={s['median']:.4f}, "
                         f"win_rate={s['win_rate']:.1%}, n={s['n']}")

    lines.append("\n" + "=" * 70)
    result = "\n".join(lines)
    print(result)
    return result
