# Research Note: NIFTY Dip-Recovery Hypothesis

## 1. Hypothesis

**"After a significant one-day fall in NIFTY 50, the market tends to recover over the next few trading days."**

**Precise formulation**: If the NIFTY 50 index experiences a daily close-to-close return of -2% or worse, the mean forward return (measured from the next day's Open to the Close of day N) is positive and statistically significantly greater than zero, and also greater than the unconditional forward return over the same period.

## 2. Definitions

| Term | Definition | Rationale |
|------|-----------|-----------|
| **Significant fall** | Daily return <= -2% | Captures roughly the worst 4.4% of trading days. A -2% move in NIFTY is approximately 1.5 standard deviations below the mean, representing a genuinely unusual negative day without being so extreme as to yield too few observations. |
| **Recovery** | Positive forward return over the holding period | Measured as (Exit_Price - Entry_Price) / Entry_Price |
| **Entry price** | Next trading day's Open | The earliest price at which a trader could realistically execute after observing the event at market close. Avoids look-ahead bias. |
| **Exit price** | Close of the holding-period-th day after entry | Standard convention for daily backtests. |
| **Event independence** | Minimum 5-day gap between events | Prevents overlapping recovery windows from inflating sample size and violating independence assumptions. |

## 3. Test Design

- **Data source**: Yahoo Finance (^NSEI), 2007-09-17 to 2025-09-17 (4,416 trading days)
- **Holding periods**: 1, 3, 5, 10 days
- **Transaction costs**: 0.20% round-trip (brokerage + slippage)
- **Statistical tests**: One-sample t-test (H1: mean > 0), Wilcoxon signed-rank test, 95% parametric and bootstrap confidence intervals, two-sample Welch's t-test vs baseline
- **In-sample / Out-of-sample split**: 70/30 chronological

**Key assumption**: We treat the NIFTY 50 index as directly tradable. In practice, execution would involve index futures or ETFs, introducing tracking error.

## 4. Results

**128 qualifying events** were detected after applying the 5-day cooldown filter (from 194 raw events).

### Forward Return Statistics

| Holding | N | Mean | Median | Std | Win% | t-stat | p-value |
|:-------:|:-:|:----:|:------:|:---:|:----:|:------:|:-------:|
| 1d | 128 | -0.0026 | -0.0021 | 0.0301 | 46.9% | -0.982 | 0.836 |
| 3d | 128 | +0.0004 | +0.0007 | 0.0413 | 50.0% | 0.120 | 0.452 |
| 5d | 128 | +0.0033 | +0.0012 | 0.0477 | 50.0% | 0.778 | 0.219 |
| 10d | 128 | +0.0090 | +0.0171 | 0.0652 | 57.0% | 1.556 | 0.061 |

No holding period achieves statistical significance at the 5% level via the t-test. The 10-day period is closest (p=0.061), and the Wilcoxon test for 10-day returns *is* significant (p=0.010), suggesting that while the mean is noisy, the median recovery is positive.

### Baseline Comparison

Event forward returns are **not statistically distinguishable** from unconditional (all-day) forward returns. The two-sample Welch's t-test p-values range from 0.20 to 0.83 across holding periods.

### Robustness

Across 30 parameter combinations (5 thresholds x 6 holding periods), only 8 (27%) show significance at 5%. Significance concentrates at longer holding periods (15-20 days) and stricter thresholds (-2.5% to -3.0%), but these involve fewer events (55-78).

### Out-of-Sample

The out-of-sample period (2020-2025, 23 events) shows markedly stronger recovery: 10-day mean return = 3.21% vs in-sample 0.50%. However, this is dominated by V-shaped COVID recoveries and the sample size is too small for reliable inference.

## 5. Conclusion

**The evidence does not support the hypothesis** that NIFTY systematically recovers after significant single-day falls. While there is a suggestive positive trend at longer holding periods, it is not statistically significant, not distinguishable from baseline returns, and the robustness analysis shows sensitivity to parameter choices.

The backtest produces a positive total return (42.57% over 18 years) but with a max drawdown of -36.83% and a CAGR of only 2.05% -- well below buy-and-hold NIFTY performance over the same period.

**A negative result is completely acceptable.** The absence of a reliable mean-reversion effect after single-day dips is consistent with the efficient market hypothesis: large price drops may reflect genuine information rather than temporary overreaction, and any systematic recovery pattern would likely be arbitraged away by institutional participants.
