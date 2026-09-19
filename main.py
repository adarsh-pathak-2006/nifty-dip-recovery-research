"""
Main Orchestrator — Runs the complete NIFTY Dip-Recovery Research Pipeline.

Usage:
    python main.py

This script executes all steps end-to-end:
    1. Data sourcing & validation
    2. Event detection & forward return computation
    3. Statistical evidence (tests, CI, bootstrap)
    4. Baseline comparison & robustness sweep
    5. Out-of-sample validation
    6. Simple event-driven backtest
    7. Visualization (all plots saved to output/plots/)
    8. Results summary (saved to output/results/)
"""

import os
import sys
import json
import warnings
warnings.filterwarnings("ignore")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    HOLDING_PERIODS, EVENT_THRESHOLD, IN_SAMPLE_RATIO,
    OVERLAP_COOLDOWN_DAYS, RESULTS_DIR, PLOTS_DIR, OUTPUT_DIR,
    ROBUSTNESS_THRESHOLDS, ROBUSTNESS_HOLDING_PERIODS,
    TOTAL_ROUND_TRIP_COST,
)
from src.data_loader import download_nifty_data, get_data_summary
from src.data_validator import validate_data, clean_data, print_validation_report
from src.event_detector import compute_daily_returns, detect_events, compute_forward_returns
from src.research_engine import (
    compute_event_statistics, format_statistics_table,
    compute_unconditional_forward_returns, create_results_dataframe,
)
from src.statistical_tests import run_all_tests, format_test_results
from src.baseline_robustness import (
    robustness_sweep, in_sample_out_of_sample_split,
    oos_comparison, format_oos_results,
)
from src.backtest import run_backtest, format_backtest_summary
from src.visualization import (
    plot_daily_returns_distribution, plot_forward_returns_distribution,
    plot_event_timeline, plot_equity_curve, plot_robustness_heatmap,
    plot_bootstrap_distribution, plot_oos_comparison,
)


def main():
    # Ensure Unicode characters print correctly on Windows (cp1252) terminals
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    # Create output directories
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    all_output = []

    def log(msg: str):
        print(msg)
        all_output.append(msg)

    log("=" * 70)
    log("NIFTY DIP-RECOVERY RESEARCH ENGINE")
    log(f"Hypothesis: 'After a significant one-day fall in NIFTY,")
    log(f"the market tends to recover over the next few trading days.'")
    log("=" * 70)

    # ─────────────────────────────────────────────
    # STEP 1: Data Sourcing
    # ─────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("STEP 1: DATA SOURCING")
    log("=" * 70)

    df = download_nifty_data()
    summary = get_data_summary(df)
    log(f"\nData Summary:")
    log(f"  Source:       Yahoo Finance ({summary['columns']})")
    log(f"  Ticker:       ^NSEI (NIFTY 50)")
    log(f"  Date Range:   {summary['start_date']} to {summary['end_date']}")
    log(f"  Trading Days: {summary['trading_days']}")

    # ─────────────────────────────────────────────
    # STEP 2: Data Validation & Cleaning
    # ─────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("STEP 2: DATA VALIDATION & CLEANING")
    log("=" * 70)

    report = validate_data(df)
    report_str = print_validation_report(report)
    all_output.append(report_str)

    df = clean_data(df)
    df = compute_daily_returns(df)

    # ─────────────────────────────────────────────
    # STEP 3: Event Detection & Analysis
    # ─────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("STEP 3: EVENT DETECTION & ANALYSIS")
    log(f"  Threshold: {EVENT_THRESHOLD:.2%}")
    log(f"  Cooldown:  {OVERLAP_COOLDOWN_DAYS} trading days")
    log(f"  Entry:     Next-day Open")
    log(f"  Exit:      Close of holding-period day")
    log("=" * 70)

    event_df = detect_events(df, threshold=EVENT_THRESHOLD,
                             cooldown=OVERLAP_COOLDOWN_DAYS)

    if len(event_df) == 0:
        log("ERROR: No events detected. Try a less strict threshold.")
        return

    event_df = compute_forward_returns(df, event_df,
                                       holding_periods=HOLDING_PERIODS)

    # Event statistics
    event_stats = compute_event_statistics(event_df, HOLDING_PERIODS)
    log("\nEvent Forward Return Statistics:")
    stats_str = format_statistics_table(event_stats)
    all_output.append(stats_str)

    # Baseline (unconditional) statistics
    baseline_stats = compute_unconditional_forward_returns(df, HOLDING_PERIODS)
    log("\nBaseline (All-Day) Forward Return Statistics:")
    for hp, s in sorted(baseline_stats.items()):
        if s.get("n", 0) > 0:
            log(f"  {hp}d: mean={s['mean']:.4f}, win_rate={s['win_rate']:.1%}, "
                f"n={s['n']}")

    # Comparison table
    comparison_df = create_results_dataframe(event_stats, baseline_stats,
                                             HOLDING_PERIODS)
    comparison_df.to_csv(os.path.join(RESULTS_DIR, "event_vs_baseline.csv"),
                         index=False)
    log(f"\n[Saved] Event vs baseline comparison → "
        f"{RESULTS_DIR}/event_vs_baseline.csv")

    # ─────────────────────────────────────────────
    # STEP 4: Statistical Evidence
    # ─────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("STEP 4: STATISTICAL EVIDENCE")
    log("=" * 70)

    test_results = run_all_tests(event_df, df, HOLDING_PERIODS)
    test_str = format_test_results(test_results)
    all_output.append(test_str)

    # ─────────────────────────────────────────────
    # STEP 5: Robustness Sweep
    # ─────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("STEP 5: ROBUSTNESS SWEEP")
    log(f"  Thresholds:      {ROBUSTNESS_THRESHOLDS}")
    log(f"  Holding Periods: {ROBUSTNESS_HOLDING_PERIODS}")
    log("=" * 70)

    robustness_df = robustness_sweep(df,
                                     thresholds=ROBUSTNESS_THRESHOLDS,
                                     holding_periods=ROBUSTNESS_HOLDING_PERIODS)
    robustness_df.to_csv(os.path.join(RESULTS_DIR, "robustness_sweep.csv"),
                         index=False)
    log(f"\n[Saved] Robustness results → {RESULTS_DIR}/robustness_sweep.csv")

    # Summary of significant cells
    sig_count = robustness_df["significant"].sum()
    total_count = len(robustness_df)
    log(f"\nRobustness: {sig_count}/{total_count} parameter combinations "
        f"are statistically significant at 5%")

    # ─────────────────────────────────────────────
    # STEP 6: Out-of-Sample Validation
    # ─────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("STEP 6: OUT-OF-SAMPLE VALIDATION")
    log(f"  Split Ratio: {IN_SAMPLE_RATIO:.0%} / {1-IN_SAMPLE_RATIO:.0%}")
    log("=" * 70)

    df_in, df_out = in_sample_out_of_sample_split(df, IN_SAMPLE_RATIO)
    oos_results = oos_comparison(df_in, df_out,
                                 threshold=EVENT_THRESHOLD,
                                 holding_periods=HOLDING_PERIODS)
    oos_str = format_oos_results(oos_results, HOLDING_PERIODS)
    all_output.append(oos_str)

    # ─────────────────────────────────────────────
    # STEP 7: Simple Event-Driven Backtest
    # ─────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("STEP 7: SIMPLE EVENT-DRIVEN BACKTEST")
    log("=" * 70)

    # Run backtest for the primary holding period (5 days)
    primary_hp = 5
    bt_results = run_backtest(df, threshold=EVENT_THRESHOLD,
                              holding_period=primary_hp)
    bt_str = format_backtest_summary(bt_results["summary"], primary_hp)
    all_output.append(bt_str)

    # Save trades
    if len(bt_results["trades"]) > 0:
        bt_results["trades"].to_csv(
            os.path.join(RESULTS_DIR, "backtest_trades.csv"), index=False)
        log(f"[Saved] Trade log → {RESULTS_DIR}/backtest_trades.csv")

    # ─────────────────────────────────────────────
    # STEP 8: Generate All Visualizations
    # ─────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("STEP 8: GENERATING VISUALIZATIONS")
    log("=" * 70)

    # 1. Daily returns distribution
    plot_daily_returns_distribution(df, EVENT_THRESHOLD)

    # 2. Forward returns distribution
    plot_forward_returns_distribution(event_df, HOLDING_PERIODS)

    # 3. Event timeline
    plot_event_timeline(df, event_df)

    # 4. Equity curve
    if len(bt_results["equity_curve"]) > 1:
        plot_equity_curve(bt_results["equity_curve"], primary_hp)

    # 5. Robustness heatmap
    plot_robustness_heatmap(robustness_df)

    # 6. Bootstrap distribution (for primary holding period)
    for hp in HOLDING_PERIODS:
        if hp in test_results and "bootstrap" in test_results[hp]:
            bs = test_results[hp]["bootstrap"]
            plot_bootstrap_distribution(
                bs["boot_means"], bs["ci_lower"], bs["ci_upper"],
                bs["mean"], hp
            )

    # 7. OOS comparison
    plot_oos_comparison(oos_results, HOLDING_PERIODS)

    # ─────────────────────────────────────────────
    # STEP 9: Challenge Your Own Result
    # ─────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("STEP 9: CHALLENGING THE RESULT")
    log("=" * 70)

    # Compute the challenges
    challenge_lines = []
    challenge_lines.append("\n--- Potential Sources of Spurious Results ---\n")

    challenge_lines.append("1. LOOK-AHEAD BIAS:")
    challenge_lines.append("   ✓ Mitigated: Entry at next-day Open (unknowable at event close).")
    challenge_lines.append("   ✓ Events detected using only close-to-close returns known at EOD.\n")

    challenge_lines.append("2. SLIPPAGE & TRANSACTION COSTS:")
    challenge_lines.append(f"   Applied {TOTAL_ROUND_TRIP_COST:.2%} round-trip cost per trade.")
    challenge_lines.append("   Real-world costs could be higher during volatile periods.\n")

    challenge_lines.append("3. SAMPLE SIZE:")
    n_events = len(event_df)
    challenge_lines.append(f"   {n_events} qualifying events over the full sample.")
    if n_events < 30:
        challenge_lines.append("   ⚠ Small sample — statistical power is limited.\n")
    else:
        challenge_lines.append("   Adequate for basic parametric tests.\n")

    challenge_lines.append("4. OVERLAPPING EVENTS:")
    challenge_lines.append(f"   Applied {OVERLAP_COOLDOWN_DAYS}-day cooldown to reduce overlap.")
    challenge_lines.append("   Events during sustained crashes may still be correlated.\n")

    challenge_lines.append("5. MARKET REGIMES:")
    challenge_lines.append("   The data spans multiple regimes (2008 GFC, 2020 COVID, etc.).")
    challenge_lines.append("   Results may be driven by a small number of extreme episodes.\n")

    challenge_lines.append("6. DATA QUALITY:")
    challenge_lines.append("   Yahoo Finance data is not exchange-official.")
    challenge_lines.append("   Minor discrepancies vs. NSE official data may exist.\n")

    challenge_lines.append("7. MULTIPLE TESTING:")
    challenge_lines.append("   We test multiple holding periods and thresholds.")
    challenge_lines.append("   Without Bonferroni or similar correction, some may be")
    challenge_lines.append("   significant by chance alone.\n")

    challenge_lines.append("--- Falsification Criteria ---")
    challenge_lines.append("The hypothesis would be rejected if:")
    challenge_lines.append("  • Mean forward returns are not significantly > 0 (p > 0.05)")
    challenge_lines.append("  • Event returns are not meaningfully different from baseline")
    challenge_lines.append("  • Results do not replicate out-of-sample")
    challenge_lines.append("  • Net-of-cost backtest returns are negative")
    challenge_lines.append("  • Results are driven by ≤ 3 extreme events")

    for line in challenge_lines:
        log(line)

    # ─────────────────────────────────────────────
    # STEP 10: Final Conclusion
    # ─────────────────────────────────────────────
    log("\n" + "=" * 70)
    log("STEP 10: CONCLUSION")
    log("=" * 70)

    # Programmatic conclusion based on evidence
    conclusions = []
    for hp in HOLDING_PERIODS:
        if hp not in test_results or "ttest" not in test_results[hp]:
            continue
        tt = test_results[hp]["ttest"]
        bs = test_results[hp].get("bootstrap", {})
        ts = test_results[hp].get("two_sample", {})

        mean_ret = tt["mean"]
        p_val = tt["p_value_one_sided"]
        bs_zero = bs.get("contains_zero", True)
        excess = ts.get("difference", 0)

        hp_conclusion = {
            "hp": hp,
            "mean": mean_ret,
            "p_value": p_val,
            "significant": p_val < 0.05,
            "bootstrap_excludes_zero": not bs_zero,
            "excess_vs_baseline": excess,
        }
        conclusions.append(hp_conclusion)
        log(f"\n  {hp}-day holding period:")
        log(f"    Mean return:    {mean_ret:.4f}")
        log(f"    p-value:        {p_val:.4f}")
        sig_str = "YES" if p_val < 0.05 else "NO"
        log(f"    Significant:    {sig_str}")
        log(f"    Bootstrap excl. zero: {'YES' if not bs_zero else 'NO'}")
        log(f"    Excess vs baseline:   {excess:.4f}")

    # Overall verdict
    n_sig = sum(1 for c in conclusions if c["significant"])
    log(f"\n  Summary: {n_sig}/{len(conclusions)} holding periods show "
        f"statistically significant positive returns after events.")

    if n_sig == len(conclusions) and len(conclusions) > 0:
        log("  → Evidence SUPPORTS the hypothesis across all tested periods.")
    elif n_sig > 0:
        log("  → MIXED evidence: some holding periods support the hypothesis.")
    else:
        log("  → Evidence does NOT support the hypothesis.")

    log("\n  NOTE: Statistical significance ≠ economic significance.")
    log("  Transaction costs, slippage, and market impact may erode")
    log("  any theoretical edge in practice.")

    # Save full output
    full_output = "\n".join(all_output)
    with open(os.path.join(RESULTS_DIR, "full_research_output.txt"), "w",
              encoding="utf-8") as f:
        f.write(full_output)
    log(f"\n[Saved] Full output → {RESULTS_DIR}/full_research_output.txt")

    # Save event data
    event_df.to_csv(os.path.join(RESULTS_DIR, "event_data.csv"), index=False)
    log(f"[Saved] Event data → {RESULTS_DIR}/event_data.csv")

    log("\n" + "=" * 70)
    log("RESEARCH PIPELINE COMPLETE")
    log("=" * 70)
    log(f"  Plots:   {PLOTS_DIR}/")
    log(f"  Results: {RESULTS_DIR}/")
    log("=" * 70)


if __name__ == "__main__":
    main()
