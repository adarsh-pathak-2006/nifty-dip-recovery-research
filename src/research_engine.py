"""
Research Engine — Core analysis module that aggregates event statistics.

This module takes the enriched event DataFrame (with forward returns) and
produces summary statistics that form the basis of the research findings.
"""

import pandas as pd
import numpy as np
from config import HOLDING_PERIODS


def compute_event_statistics(event_df: pd.DataFrame,
                             holding_periods: list = HOLDING_PERIODS) -> dict:
    """
    Compute aggregate statistics for forward returns after events.

    Parameters
    ----------
    event_df : pd.DataFrame — must contain fwd_return_{hp}d columns
    holding_periods : list of int

    Returns
    -------
    dict : holding_period → stats dict
    """
    stats = {}

    for hp in holding_periods:
        col = f"fwd_return_{hp}d"
        if col not in event_df.columns:
            continue

        returns = event_df[col].dropna()

        if len(returns) == 0:
            stats[hp] = {"n": 0}
            continue

        stats[hp] = {
            "n": len(returns),
            "mean": returns.mean(),
            "median": returns.median(),
            "std": returns.std(),
            "min": returns.min(),
            "max": returns.max(),
            "skew": returns.skew(),
            "kurtosis": returns.kurtosis(),
            "win_rate": (returns > 0).mean(),
            "loss_rate": (returns < 0).mean(),
            "avg_win": returns[returns > 0].mean() if (returns > 0).any() else 0,
            "avg_loss": returns[returns < 0].mean() if (returns < 0).any() else 0,
            "q25": returns.quantile(0.25),
            "q75": returns.quantile(0.75),
        }

    return stats


def format_statistics_table(stats: dict) -> str:
    """Format statistics dict as a readable table string."""
    lines = []
    lines.append(f"\n{'Holding':>10} | {'N':>5} | {'Mean':>8} | {'Median':>8} | "
                 f"{'Std':>8} | {'Win%':>6} | {'AvgWin':>8} | {'AvgLoss':>8}")
    lines.append("-" * 80)

    for hp, s in sorted(stats.items()):
        if s["n"] == 0:
            lines.append(f"{hp:>8}d | {'N/A':>5}")
            continue
        lines.append(
            f"{hp:>8}d | {s['n']:>5} | {s['mean']:>8.4f} | {s['median']:>8.4f} | "
            f"{s['std']:>8.4f} | {s['win_rate']:>5.1%} | {s['avg_win']:>8.4f} | "
            f"{s['avg_loss']:>8.4f}"
        )

    result = "\n".join(lines)
    print(result)
    return result


def compute_unconditional_forward_returns(df: pd.DataFrame,
                                          holding_periods: list = HOLDING_PERIODS) -> dict:
    """
    Compute forward returns for ALL days (unconditional baseline).

    This serves as the baseline comparison: "What is the typical
    forward return on any random day?"
    """
    stats = {}

    for hp in holding_periods:
        returns = []
        for i in range(len(df) - hp - 1):
            entry_price = df.loc[i + 1, "Open"] if i + 1 < len(df) else np.nan
            exit_idx = i + 1 + hp
            if exit_idx >= len(df):
                continue
            exit_price = df.loc[exit_idx, "Close"]
            if entry_price > 0:
                returns.append((exit_price - entry_price) / entry_price)

        returns = np.array(returns)
        if len(returns) == 0:
            stats[hp] = {"n": 0}
            continue

        stats[hp] = {
            "n": len(returns),
            "mean": returns.mean(),
            "median": np.median(returns),
            "std": returns.std(),
            "win_rate": (returns > 0).mean(),
        }

    return stats


def create_results_dataframe(event_stats: dict, baseline_stats: dict,
                             holding_periods: list = HOLDING_PERIODS) -> pd.DataFrame:
    """Create a comparison DataFrame: Event returns vs Baseline returns."""
    rows = []
    for hp in holding_periods:
        ev = event_stats.get(hp, {})
        bl = baseline_stats.get(hp, {})
        rows.append({
            "holding_period": hp,
            "event_n": ev.get("n", 0),
            "event_mean": ev.get("mean", np.nan),
            "event_median": ev.get("median", np.nan),
            "event_win_rate": ev.get("win_rate", np.nan),
            "event_std": ev.get("std", np.nan),
            "baseline_n": bl.get("n", 0),
            "baseline_mean": bl.get("mean", np.nan),
            "baseline_median": bl.get("median", np.nan),
            "baseline_win_rate": bl.get("win_rate", np.nan),
            "excess_return": ev.get("mean", np.nan) - bl.get("mean", np.nan)
            if ev.get("n", 0) > 0 and bl.get("n", 0) > 0 else np.nan,
        })

    return pd.DataFrame(rows)
