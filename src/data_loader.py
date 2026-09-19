"""
Data Loader — Fetches NIFTY 50 daily OHLCV data from Yahoo Finance.

Source justification:
    Yahoo Finance is a widely used, credible source for historical equity
    index data.  The yfinance library provides free, programmatic access.
    Limitations include occasional missing days and adjusted vs. unadjusted
    price discrepancies, which we handle in the data_validator module.
"""

import os
import pandas as pd
import yfinance as yf
from config import TICKER, DATA_START, DATA_END, DATA_FILE


def download_nifty_data(force_refresh: bool = False) -> pd.DataFrame:
    """
    Download NIFTY 50 daily OHLCV data from Yahoo Finance.

    If a local cache exists and force_refresh is False, the cached file is
    loaded instead of re-downloading.

    Returns
    -------
    pd.DataFrame
        Columns: Date, Open, High, Low, Close, Volume
        Sorted chronologically by Date.
    """
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    if os.path.exists(DATA_FILE) and not force_refresh:
        print(f"[DataLoader] Loading cached data from {DATA_FILE}")
        df = pd.read_csv(DATA_FILE, parse_dates=["Date"])
    else:
        print(f"[DataLoader] Downloading {TICKER} data from Yahoo Finance "
              f"({DATA_START} to {DATA_END})...")
        raw = yf.download(TICKER, start=DATA_START, end=DATA_END,
                          auto_adjust=True, progress=False)

        if raw.empty:
            raise RuntimeError(
                f"No data returned for {TICKER}. Check your internet "
                f"connection or the ticker symbol."
            )

        # yfinance returns a MultiIndex when downloading a single ticker
        # with newer versions — flatten if needed
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        df = raw.reset_index()
        # Keep only the columns we need
        expected_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
        available = [c for c in expected_cols if c in df.columns]
        df = df[available].copy()

        # Save to disk
        df.to_csv(DATA_FILE, index=False)
        print(f"[DataLoader] Saved {len(df)} rows to {DATA_FILE}")

    # Ensure correct types
    df["Date"] = pd.to_datetime(df["Date"])
    for col in ["Open", "High", "Low", "Close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("Date").reset_index(drop=True)
    return df


def get_data_summary(df: pd.DataFrame) -> dict:
    """Return a quick summary dict of the downloaded data."""
    return {
        "rows": len(df),
        "start_date": df["Date"].min().strftime("%Y-%m-%d"),
        "end_date": df["Date"].max().strftime("%Y-%m-%d"),
        "trading_days": len(df),
        "columns": list(df.columns),
    }
