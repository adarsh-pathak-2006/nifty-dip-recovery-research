"""
Simple Event-Driven Backtest — Tests the hypothesis as a trading strategy.

Rules:
    - Signal: NIFTY daily close-to-close return ≤ EVENT_THRESHOLD
    - Entry:  BUY at the next trading day's Open
    - Exit:   SELL at the Close of the holding-period-th day after entry
    - Costs:  TOTAL_ROUND_TRIP_COST deducted per trade (brokerage + slippage)
    - No overlapping positions: if already in a trade, skip new signals

This is an EXTENSION of the research, not the primary objective.
The assignment explicitly says: "Research quality matters more than return."
"""

import pandas as pd
import numpy as np
from config import (EVENT_THRESHOLD, HOLDING_PERIODS, TOTAL_ROUND_TRIP_COST,
                    OVERLAP_COOLDOWN_DAYS)


def run_backtest(df: pd.DataFrame,
                 threshold: float = EVENT_THRESHOLD,
                 holding_period: int = 5,
                 round_trip_cost: float = TOTAL_ROUND_TRIP_COST) -> dict:
    """
    Run a simple event-driven backtest.

    Parameters
    ----------
    df : pd.DataFrame — must have Date, Open, High, Low, Close, daily_return
    threshold : float — event threshold
    holding_period : int — days to hold after entry
    round_trip_cost : float — total cost per trade (entry + exit)

    Returns
    -------
    dict with:
        trades : list of trade dicts
        equity_curve : pd.DataFrame
        summary : dict of performance metrics
    """
    if "daily_return" not in df.columns:
        df = df.copy()
        df["daily_return"] = df["Close"].pct_change()

    trades = []
    equity = [1.0]  # start with 1 unit of capital
    equity_dates = [df.loc[0, "Date"]]
    in_trade = False
    exit_day_idx = -1

    for i in range(1, len(df) - holding_period - 1):
        # Check if we exited a trade
        if in_trade and i > exit_day_idx:
            in_trade = False

        # Check for event signal
        if not in_trade and df.loc[i, "daily_return"] <= threshold:
            entry_idx = i + 1  # next day
            exit_idx = entry_idx + holding_period

            if exit_idx >= len(df):
                break

            entry_price = df.loc[entry_idx, "Open"]
            exit_price = df.loc[exit_idx, "Close"]

            if entry_price <= 0:
                continue

            gross_return = (exit_price - entry_price) / entry_price
            net_return = gross_return - round_trip_cost

            trade = {
                "signal_date": df.loc[i, "Date"],
                "entry_date": df.loc[entry_idx, "Date"],
                "exit_date": df.loc[exit_idx, "Date"],
                "entry_price": entry_price,
                "exit_price": exit_price,
                "gross_return": gross_return,
                "net_return": net_return,
                "signal_return": df.loc[i, "daily_return"],
            }
            trades.append(trade)

            # Update equity
            equity.append(equity[-1] * (1 + net_return))
            equity_dates.append(df.loc[exit_idx, "Date"])

            in_trade = True
            exit_day_idx = exit_idx

    # Build equity curve
    equity_df = pd.DataFrame({
        "Date": equity_dates,
        "Equity": equity,
    })

    # Compute summary statistics
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    summary = compute_backtest_summary(trades_df, equity)

    return {
        "trades": trades_df,
        "equity_curve": equity_df,
        "summary": summary,
    }


def compute_backtest_summary(trades_df: pd.DataFrame,
                             equity: list) -> dict:
    """Compute summary performance metrics."""
    if len(trades_df) == 0:
        return {"n_trades": 0, "note": "No trades executed"}

    net_returns = trades_df["net_return"].values
    equity = np.array(equity)

    # Maximum drawdown
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_drawdown = drawdown.min()

    # CAGR (approximate)
    if len(trades_df) > 0:
        first_date = trades_df["entry_date"].iloc[0]
        last_date = trades_df["exit_date"].iloc[-1]
        years = (last_date - first_date).days / 365.25
        if years > 0 and equity[-1] > 0:
            cagr = (equity[-1] / equity[0]) ** (1 / years) - 1
        else:
            cagr = 0
    else:
        cagr = 0

    summary = {
        "n_trades": len(trades_df),
        "total_return": equity[-1] / equity[0] - 1,
        "cagr": cagr,
        "mean_return_per_trade": net_returns.mean(),
        "median_return_per_trade": np.median(net_returns),
        "std_return_per_trade": net_returns.std(),
        "win_rate": (net_returns > 0).mean(),
        "avg_win": net_returns[net_returns > 0].mean() if (net_returns > 0).any() else 0,
        "avg_loss": net_returns[net_returns < 0].mean() if (net_returns < 0).any() else 0,
        "max_drawdown": max_drawdown,
        "profit_factor": (
            net_returns[net_returns > 0].sum() / abs(net_returns[net_returns < 0].sum())
            if (net_returns < 0).any() and net_returns[net_returns < 0].sum() != 0
            else np.inf
        ),
        "best_trade": net_returns.max(),
        "worst_trade": net_returns.min(),
        "final_equity": equity[-1],
    }

    return summary


def format_backtest_summary(summary: dict, holding_period: int) -> str:
    """Pretty-print backtest results."""
    lines = []
    lines.append("\n" + "=" * 60)
    lines.append(f"BACKTEST RESULTS (Holding Period: {holding_period} days)")
    lines.append("=" * 60)

    if summary.get("n_trades", 0) == 0:
        lines.append("No trades executed.")
        result = "\n".join(lines)
        print(result)
        return result

    lines.append(f"  Total Trades:          {summary['n_trades']}")
    lines.append(f"  Total Return:          {summary['total_return']:.2%}")
    lines.append(f"  CAGR:                  {summary['cagr']:.2%}")
    lines.append(f"  Mean Return/Trade:     {summary['mean_return_per_trade']:.4f}")
    lines.append(f"  Median Return/Trade:   {summary['median_return_per_trade']:.4f}")
    lines.append(f"  Win Rate:              {summary['win_rate']:.1%}")
    lines.append(f"  Avg Win:               {summary['avg_win']:.4f}")
    lines.append(f"  Avg Loss:              {summary['avg_loss']:.4f}")
    lines.append(f"  Profit Factor:         {summary['profit_factor']:.2f}")
    lines.append(f"  Max Drawdown:          {summary['max_drawdown']:.2%}")
    lines.append(f"  Best Trade:            {summary['best_trade']:.4f}")
    lines.append(f"  Worst Trade:           {summary['worst_trade']:.4f}")
    lines.append(f"  Final Equity (1→):     {summary['final_equity']:.4f}")
    lines.append("=" * 60)

    result = "\n".join(lines)
    print(result)
    return result
