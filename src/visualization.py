"""
Visualization — All charts and plots for the research report.

Generates publication-quality matplotlib figures saved to output/plots/.
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from config import PLOTS_DIR, HOLDING_PERIODS, EVENT_THRESHOLD


def setup_plot_style():
    """Set a clean, publication-ready plot style."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update({
        "figure.figsize": (12, 6),
        "figure.dpi": 150,
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "legend.fontsize": 10,
        "figure.facecolor": "white",
    })


def ensure_plot_dir():
    os.makedirs(PLOTS_DIR, exist_ok=True)


def plot_daily_returns_distribution(df: pd.DataFrame, threshold: float = EVENT_THRESHOLD):
    """Plot distribution of daily returns with event threshold line."""
    setup_plot_style()
    ensure_plot_dir()

    returns = df["daily_return"].dropna()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.hist(returns, bins=100, color="#4C72B0", alpha=0.7, edgecolor="white",
            label="Daily Returns")
    ax.axvline(threshold, color="#C44E52", linestyle="--", linewidth=2,
               label=f"Event Threshold ({threshold:.1%})")
    ax.axvline(0, color="gray", linestyle="-", linewidth=0.8, alpha=0.5)

    event_count = (returns <= threshold).sum()
    ax.set_title(f"Distribution of NIFTY Daily Returns\n"
                 f"({event_count} days below {threshold:.1%} threshold)")
    ax.set_xlabel("Daily Return (Close-to-Close)")
    ax.set_ylabel("Frequency")
    ax.legend()

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "01_daily_returns_distribution.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"[Plot] Saved: {path}")


def plot_forward_returns_distribution(event_df: pd.DataFrame,
                                     holding_periods: list = HOLDING_PERIODS):
    """Plot distribution of forward returns after events for each holding period."""
    setup_plot_style()
    ensure_plot_dir()

    n_hp = len(holding_periods)
    fig, axes = plt.subplots(1, n_hp, figsize=(5 * n_hp, 5), sharey=False)
    if n_hp == 1:
        axes = [axes]

    colors = ["#4C72B0", "#55A868", "#C44E52", "#8172B2"]

    for i, hp in enumerate(holding_periods):
        col = f"fwd_return_{hp}d"
        if col not in event_df.columns:
            continue
        returns = event_df[col].dropna()

        ax = axes[i]
        ax.hist(returns, bins=25, color=colors[i % len(colors)], alpha=0.7,
                edgecolor="white")
        ax.axvline(0, color="red", linestyle="--", linewidth=1.5, alpha=0.7)
        ax.axvline(returns.mean(), color="black", linestyle="-", linewidth=1.5,
                   label=f"Mean: {returns.mean():.4f}")
        ax.axvline(returns.median(), color="orange", linestyle="-.", linewidth=1.5,
                   label=f"Median: {returns.median():.4f}")

        win_pct = (returns > 0).mean()
        ax.set_title(f"{hp}-day Forward Return\n"
                     f"(n={len(returns)}, win={win_pct:.0%})")
        ax.set_xlabel("Forward Return")
        ax.legend(fontsize=8)

    fig.suptitle("Forward Returns After Significant NIFTY Falls",
                 fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "02_forward_returns_distribution.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"[Plot] Saved: {path}")


def plot_event_timeline(df: pd.DataFrame, event_df: pd.DataFrame):
    """Plot NIFTY price with event dates marked."""
    setup_plot_style()
    ensure_plot_dir()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8),
                                    gridspec_kw={"height_ratios": [3, 1]})

    # Price chart
    ax1.plot(df["Date"], df["Close"], color="#4C72B0", linewidth=0.8,
             alpha=0.9, label="NIFTY Close")
    if len(event_df) > 0:
        ax1.scatter(event_df["event_date"], event_df["event_close"],
                    color="#C44E52", s=15, zorder=5, alpha=0.7,
                    label=f"Events ({len(event_df)})")
    ax1.set_title("NIFTY 50 Price & Significant Fall Events")
    ax1.set_ylabel("Close Price")
    ax1.legend()

    # Daily returns
    if "daily_return" in df.columns:
        colors = np.where(df["daily_return"] <= EVENT_THRESHOLD, "#C44E52", "#4C72B0")
        ax2.bar(df["Date"], df["daily_return"], color=colors, width=1, alpha=0.6)
        ax2.axhline(EVENT_THRESHOLD, color="red", linestyle="--",
                    linewidth=1, alpha=0.7)
        ax2.set_ylabel("Daily Return")
        ax2.set_xlabel("Date")

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "03_event_timeline.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"[Plot] Saved: {path}")


def plot_equity_curve(equity_df: pd.DataFrame, holding_period: int):
    """Plot backtest equity curve."""
    setup_plot_style()
    ensure_plot_dir()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(equity_df["Date"], equity_df["Equity"],
            color="#55A868", linewidth=1.5, label="Strategy Equity")
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1, alpha=0.5,
               label="Starting Capital")

    # Drawdown fill
    equity_arr = equity_df["Equity"].values
    peak = np.maximum.accumulate(equity_arr)
    drawdown = (equity_arr - peak) / peak

    ax2 = ax.twinx()
    ax2.fill_between(equity_df["Date"], drawdown, 0,
                     color="#C44E52", alpha=0.15, label="Drawdown")
    ax2.set_ylabel("Drawdown", color="#C44E52")

    final_eq = equity_arr[-1]
    total_ret = final_eq - 1
    ax.set_title(f"Event-Driven Backtest Equity Curve "
                 f"(HP={holding_period}d)\n"
                 f"Final Equity: {final_eq:.4f} | "
                 f"Total Return: {total_ret:.2%}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity (starting at 1.0)")
    ax.legend(loc="upper left")

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "04_equity_curve.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"[Plot] Saved: {path}")


def plot_robustness_heatmap(robustness_df: pd.DataFrame):
    """Plot heatmap of mean returns across threshold × holding period."""
    setup_plot_style()
    ensure_plot_dir()

    if len(robustness_df) == 0:
        print("[Plot] No robustness data to plot.")
        return

    pivot_mean = robustness_df.pivot_table(
        index="threshold", columns="holding_period",
        values="mean_return", aggfunc="first")
    pivot_sig = robustness_df.pivot_table(
        index="threshold", columns="holding_period",
        values="significant", aggfunc="first")

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(pivot_mean.values, cmap="RdYlGn", aspect="auto")

    ax.set_xticks(range(len(pivot_mean.columns)))
    ax.set_xticklabels([f"{c}d" for c in pivot_mean.columns])
    ax.set_yticks(range(len(pivot_mean.index)))
    ax.set_yticklabels([f"{t:.1%}" for t in pivot_mean.index])

    # Annotate cells
    for i in range(len(pivot_mean.index)):
        for j in range(len(pivot_mean.columns)):
            val = pivot_mean.values[i, j]
            sig = pivot_sig.values[i, j] if not np.isnan(pivot_sig.values[i, j]) else False
            star = "*" if sig else ""
            color = "white" if abs(val) > 0.01 else "black"
            ax.text(j, i, f"{val:.3f}{star}", ha="center", va="center",
                    color=color, fontsize=9)

    ax.set_title("Robustness: Mean Forward Return\n"
                 "(* = statistically significant at 5%)")
    ax.set_xlabel("Holding Period")
    ax.set_ylabel("Event Threshold")
    fig.colorbar(im, ax=ax, label="Mean Forward Return")

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "05_robustness_heatmap.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"[Plot] Saved: {path}")


def plot_bootstrap_distribution(boot_means: np.ndarray,
                                ci_lower: float, ci_upper: float,
                                observed_mean: float, holding_period: int):
    """Plot bootstrap distribution of mean returns."""
    setup_plot_style()
    ensure_plot_dir()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(boot_means, bins=80, color="#4C72B0", alpha=0.7,
            edgecolor="white", density=True)
    ax.axvline(observed_mean, color="#C44E52", linestyle="-", linewidth=2,
               label=f"Observed Mean: {observed_mean:.4f}")
    ax.axvline(ci_lower, color="orange", linestyle="--", linewidth=1.5,
               label=f"95% CI Lower: {ci_lower:.4f}")
    ax.axvline(ci_upper, color="orange", linestyle="--", linewidth=1.5,
               label=f"95% CI Upper: {ci_upper:.4f}")
    ax.axvline(0, color="gray", linestyle="-", linewidth=1, alpha=0.5)

    ax.set_title(f"Bootstrap Distribution of Mean {holding_period}-day "
                 f"Forward Return\n(10,000 iterations)")
    ax.set_xlabel("Mean Forward Return")
    ax.set_ylabel("Density")
    ax.legend()

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, f"06_bootstrap_{holding_period}d.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"[Plot] Saved: {path}")


def plot_oos_comparison(oos_results: dict, holding_periods: list):
    """Plot in-sample vs out-of-sample comparison bar chart."""
    setup_plot_style()
    ensure_plot_dir()

    is_data = oos_results.get("in_sample", {})
    oos_data = oos_results.get("out_of_sample", {})

    if is_data.get("n_events", 0) == 0 or oos_data.get("n_events", 0) == 0:
        print("[Plot] Insufficient OOS data for comparison plot.")
        return

    hps = []
    is_means = []
    oos_means = []
    is_wins = []
    oos_wins = []

    for hp in holding_periods:
        is_stats = is_data.get("stats", {}).get(hp, {})
        oos_stats = oos_data.get("stats", {}).get(hp, {})
        if is_stats.get("n", 0) > 0 and oos_stats.get("n", 0) > 0:
            hps.append(hp)
            is_means.append(is_stats["mean"])
            oos_means.append(oos_stats["mean"])
            is_wins.append(is_stats["win_rate"])
            oos_wins.append(oos_stats["win_rate"])

    if not hps:
        return

    x = np.arange(len(hps))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Mean return comparison
    ax1.bar(x - width / 2, is_means, width, label="In-Sample",
            color="#4C72B0", alpha=0.8)
    ax1.bar(x + width / 2, oos_means, width, label="Out-of-Sample",
            color="#C44E52", alpha=0.8)
    ax1.axhline(0, color="gray", linestyle="-", linewidth=0.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"{hp}d" for hp in hps])
    ax1.set_title("Mean Forward Return")
    ax1.set_ylabel("Mean Return")
    ax1.legend()

    # Win rate comparison
    ax2.bar(x - width / 2, is_wins, width, label="In-Sample",
            color="#4C72B0", alpha=0.8)
    ax2.bar(x + width / 2, oos_wins, width, label="Out-of-Sample",
            color="#C44E52", alpha=0.8)
    ax2.axhline(0.5, color="gray", linestyle="--", linewidth=0.8)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{hp}d" for hp in hps])
    ax2.set_title("Win Rate")
    ax2.set_ylabel("Win Rate")
    ax2.legend()

    fig.suptitle("In-Sample vs Out-of-Sample Comparison",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "07_oos_comparison.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"[Plot] Saved: {path}")
