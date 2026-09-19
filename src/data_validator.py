"""
Data Validator — Comprehensive quality checks on the NIFTY daily data.

Checks performed:
    1. Missing dates (gaps beyond weekends/holidays)
    2. Duplicate dates
    3. Incorrect chronological ordering
    4. Missing or invalid OHLC values
    5. OHLC consistency (High ≥ Low, High ≥ Open/Close, Low ≤ Open/Close)
    6. Suspicious observations (extreme single-day moves)
    7. Actual date coverage summary
"""

import pandas as pd
import numpy as np


def validate_data(df: pd.DataFrame) -> dict:
    """
    Run all data quality checks and return a report dict.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns: Date, Open, High, Low, Close

    Returns
    -------
    dict  — keys: check_name → result / details
    """
    report = {}

    # --- 1. Duplicate dates ---
    dup_dates = df[df["Date"].duplicated(keep=False)]
    report["duplicate_dates"] = {
        "count": len(dup_dates),
        "dates": dup_dates["Date"].tolist() if len(dup_dates) > 0 else [],
    }

    # --- 2. Chronological ordering ---
    is_sorted = df["Date"].is_monotonic_increasing
    report["chronologically_sorted"] = is_sorted

    # --- 3. Missing OHLC values ---
    ohlc_cols = ["Open", "High", "Low", "Close"]
    missing = df[ohlc_cols].isnull().sum().to_dict()
    report["missing_ohlc"] = missing
    total_missing = sum(missing.values())

    # --- 4. OHLC consistency ---
    inconsistent = []
    if total_missing == 0:
        bad_hl = df[df["High"] < df["Low"]]
        bad_ho = df[df["High"] < df["Open"]]
        bad_hc = df[df["High"] < df["Close"]]
        bad_lo = df[df["Low"] > df["Open"]]
        bad_lc = df[df["Low"] > df["Close"]]
        for label, subset in [("High<Low", bad_hl), ("High<Open", bad_ho),
                               ("High<Close", bad_hc), ("Low>Open", bad_lo),
                               ("Low>Close", bad_lc)]:
            if len(subset) > 0:
                inconsistent.append({
                    "issue": label,
                    "count": len(subset),
                    "dates": subset["Date"].dt.strftime("%Y-%m-%d").tolist()[:5],
                })
    report["ohlc_inconsistencies"] = inconsistent

    # --- 5. Suspicious observations (|daily return| > 10%) ---
    df_temp = df.copy()
    df_temp["daily_return"] = df_temp["Close"].pct_change()
    suspicious = df_temp[df_temp["daily_return"].abs() > 0.10]
    report["suspicious_observations"] = {
        "count": len(suspicious),
        "details": suspicious[["Date", "Close", "daily_return"]].to_dict("records")
        if len(suspicious) > 0 else [],
    }

    # --- 6. Date coverage ---
    report["date_coverage"] = {
        "start": df["Date"].min().strftime("%Y-%m-%d"),
        "end": df["Date"].max().strftime("%Y-%m-%d"),
        "trading_days": len(df),
        "calendar_days": (df["Date"].max() - df["Date"].min()).days,
    }

    # --- 7. Large gaps (> 5 calendar days between consecutive trading days) ---
    date_diffs = df["Date"].diff().dt.days
    large_gaps = df[date_diffs > 5].copy()
    large_gaps["gap_days"] = date_diffs[date_diffs > 5]
    report["large_gaps"] = {
        "count": len(large_gaps),
        "details": large_gaps[["Date", "gap_days"]].to_dict("records")
        if len(large_gaps) > 0 else [],
    }

    return report


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply cleaning steps and return a clean DataFrame.

    Cleaning steps:
        1. Remove duplicate dates (keep first)
        2. Sort by date
        3. Drop rows with any missing OHLC value
        4. Reset index
    """
    original_len = len(df)

    # Remove duplicates
    df = df.drop_duplicates(subset=["Date"], keep="first")

    # Sort
    df = df.sort_values("Date").reset_index(drop=True)

    # Drop rows with missing OHLC
    ohlc_cols = ["Open", "High", "Low", "Close"]
    df = df.dropna(subset=ohlc_cols).reset_index(drop=True)

    cleaned_len = len(df)
    removed = original_len - cleaned_len
    if removed > 0:
        print(f"[DataValidator] Removed {removed} rows during cleaning "
              f"({original_len} → {cleaned_len})")
    else:
        print(f"[DataValidator] No rows removed. {cleaned_len} rows retained.")

    return df


def print_validation_report(report: dict) -> str:
    """Pretty-print the validation report and return as string."""
    lines = []
    lines.append("=" * 60)
    lines.append("DATA VALIDATION REPORT")
    lines.append("=" * 60)

    # Date coverage
    cov = report["date_coverage"]
    lines.append(f"\nDate Coverage: {cov['start']} to {cov['end']}")
    lines.append(f"Trading Days:  {cov['trading_days']}")
    lines.append(f"Calendar Days: {cov['calendar_days']}")

    # Duplicates
    dup = report["duplicate_dates"]
    lines.append(f"\nDuplicate Dates: {dup['count']}")

    # Ordering
    lines.append(f"Chronologically Sorted: {report['chronologically_sorted']}")

    # Missing OHLC
    lines.append(f"\nMissing OHLC Values:")
    for col, cnt in report["missing_ohlc"].items():
        status = "[OK]" if cnt == 0 else f"[FAIL] ({cnt} missing)"
        lines.append(f"  {col}: {status}")

    # OHLC consistency
    incon = report["ohlc_inconsistencies"]
    if incon:
        lines.append(f"\nOHLC Inconsistencies:")
        for item in incon:
            lines.append(f"  {item['issue']}: {item['count']} rows")
    else:
        lines.append(f"\nOHLC Consistency: [OK] All checks passed")

    # Suspicious
    susp = report["suspicious_observations"]
    lines.append(f"\nSuspicious Observations (|return| > 10%): {susp['count']}")
    if susp["count"] > 0:
        for obs in susp["details"][:5]:
            lines.append(f"  {obs['Date']} — Close: {obs['Close']:.2f}, "
                         f"Return: {obs['daily_return']:.2%}")

    # Large gaps
    gaps = report["large_gaps"]
    lines.append(f"\nLarge Gaps (> 5 calendar days): {gaps['count']}")
    if gaps["count"] > 0:
        for g in gaps["details"][:5]:
            lines.append(f"  {g['Date']} — {g['gap_days']:.0f} day gap")

    lines.append("\n" + "=" * 60)
    result = "\n".join(lines)
    print(result)
    return result
