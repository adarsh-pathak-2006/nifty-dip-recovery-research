"""
Event Detector — Identifies significant single-day falls in NIFTY.

Definition of a "significant fall":
    A trading day where the close-to-close daily return is ≤ EVENT_THRESHOLD
    (default: -2%).  This threshold is configurable in config.py.

Overlap handling:
    If multiple qualifying events occur within OVERLAP_COOLDOWN_DAYS of each
    other, only the FIRST event is retained.  This ensures that overlapping
    recovery windows do not inflate the sample and violate independence
    assumptions in downstream statistical tests.

Entry price rationale:
    We use the NEXT trading day's Open as the entry price.  At the close of
    the event day, a trader would observe the large fall and decide to buy.
    The earliest realistic execution is the next day's open.  This avoids
    look-ahead bias — we never use information that was unknowable at the
    time of the trading decision.
"""

import pandas as pd
import numpy as np
from config import EVENT_THRESHOLD, OVERLAP_COOLDOWN_DAYS, HOLDING_PERIODS


def compute_daily_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'daily_return' column (close-to-close percentage change)."""
    df = df.copy()
    df["daily_return"] = df["Close"].pct_change()
    return df


def detect_events(df: pd.DataFrame,
                  threshold: float = EVENT_THRESHOLD,
                  cooldown: int = OVERLAP_COOLDOWN_DAYS) -> pd.DataFrame:
    """
    Detect significant single-day fall events.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain: Date, Open, High, Low, Close, daily_return
    threshold : float
        Maximum daily return to qualify as an event (e.g., -0.02)
    cooldown : int
        Minimum trading days between consecutive events

    Returns
    -------
    pd.DataFrame — one row per qualifying event, with columns:
        event_date, event_return, event_close, entry_price,
        entry_date, event_idx
    """
    if "daily_return" not in df.columns:
        df = compute_daily_returns(df)

    # All days where the return meets the threshold
    raw_events = df[df["daily_return"] <= threshold].copy()

    if len(raw_events) == 0:
        print(f"[EventDetector] No events found with threshold {threshold:.2%}")
        return pd.DataFrame()

    # Apply overlap cooldown filter
    filtered_indices = []
    last_idx = -999  # impossibly early

    for idx in raw_events.index:
        if idx - last_idx >= cooldown:
            filtered_indices.append(idx)
            last_idx = idx

    events = df.loc[filtered_indices].copy()

    # Build event table
    records = []
    for idx in events.index:
        # Next trading day (for entry price)
        next_idx = idx + 1
        if next_idx >= len(df):
            continue  # cannot enter if there is no next day

        records.append({
            "event_date": df.loc[idx, "Date"],
            "event_return": df.loc[idx, "daily_return"],
            "event_close": df.loc[idx, "Close"],
            "entry_date": df.loc[next_idx, "Date"],
            "entry_price": df.loc[next_idx, "Open"],
            "event_idx": idx,
        })

    event_df = pd.DataFrame(records)
    print(f"[EventDetector] Found {len(raw_events)} raw events, "
          f"{len(event_df)} after cooldown filter (threshold={threshold:.2%}, "
          f"cooldown={cooldown} days)")
    return event_df


def compute_forward_returns(df: pd.DataFrame,
                            event_df: pd.DataFrame,
                            holding_periods: list = HOLDING_PERIODS) -> pd.DataFrame:
    """
    For each event, compute forward returns over each holding period.

    Forward return = (exit_price - entry_price) / entry_price
    Entry price  = Next day's Open
    Exit price   = Close of the holding-period-th day after entry

    Parameters
    ----------
    df : pd.DataFrame — full price data
    event_df : pd.DataFrame — output of detect_events()
    holding_periods : list of int

    Returns
    -------
    pd.DataFrame — event_df enriched with forward return columns
    """
    event_df = event_df.copy()

    for hp in holding_periods:
        col_name = f"fwd_return_{hp}d"
        returns = []

        for _, row in event_df.iterrows():
            entry_idx = row["event_idx"] + 1  # next day
            exit_idx = entry_idx + hp

            if exit_idx >= len(df):
                returns.append(np.nan)
                continue

            entry_price = df.loc[entry_idx, "Open"]
            exit_price = df.loc[exit_idx, "Close"]

            if entry_price > 0:
                fwd_ret = (exit_price - entry_price) / entry_price
            else:
                fwd_ret = np.nan

            returns.append(fwd_ret)

        event_df[col_name] = returns

    # Drop events where we couldn't compute any forward return
    fwd_cols = [f"fwd_return_{hp}d" for hp in holding_periods]
    event_df = event_df.dropna(subset=fwd_cols, how="all").reset_index(drop=True)

    return event_df
