# AI Usage Note

## Tools Used

- **Claude (Anthropic)** via Antigravity IDE: Used as the primary AI coding assistant for code generation, debugging, and structural design.

## How AI Was Used

1. **Code scaffolding**: AI generated the initial structure of all Python modules (data_loader, data_validator, event_detector, research_engine, statistical_tests, baseline_robustness, backtest, visualization, main orchestrator).

2. **Bug fixing**: AI identified and fixed a Windows-specific encoding issue where Unicode checkmark characters (U+2713, U+2717) caused `UnicodeEncodeError` on the cp1252 Windows console. It replaced these with ASCII alternatives.

3. **Statistical method selection**: AI suggested using a combination of parametric (t-test), non-parametric (Wilcoxon), confidence intervals, and bootstrap methods, which provides a well-rounded evidence base.

4. **Documentation**: AI helped draft the README, research note, and this AI usage note based on the actual computed results.

## My Own Decisions

- **Event threshold (-2%)**: Chosen based on the reasoning that it captures roughly the worst 4-5% of trading days, providing a meaningful sample size (~128 events) while representing genuinely unusual negative days.

- **5-day cooldown**: A deliberate choice to address overlapping events. Without this, sustained crashes would generate many correlated observations, inflating the sample and violating independence assumptions.

- **Entry at next-day Open**: This is a critical design decision for avoiding look-ahead bias. A trader cannot act on today's close until the next trading session.

- **Interpreting the negative result**: The finding that the hypothesis is NOT supported is an honest conclusion. I did not attempt to tune parameters to find a positive result.

## Suggestions Changed or Disagreed With

- AI initially used Unicode checkmarks in output formatting. These broke on Windows (cp1252 encoding). Changed to ASCII `[OK]`/`[FAIL]` and `YES`/`NO` markers.

- AI's initial import in `main.py` missed `TOTAL_ROUND_TRIP_COST` from the config. This was caught at runtime and fixed.

## Incorrect AI Suggestions Identified

- No fundamentally incorrect statistical or financial suggestions were identified. The generated code produced reasonable results consistent with manual spot-checks.

## What I Learned

- **Negative results matter**: The absence of a statistically significant recovery effect is itself informative and consistent with market efficiency.

- **Bootstrap vs parametric CI**: In this case, the bootstrap and parametric CIs were very close, suggesting the return distribution is approximately normal for the sample size (n=128) -- CLT at work.

- **Out-of-sample divergence**: The stark difference between in-sample and out-of-sample results (driven by COVID-era V-shaped recoveries) illustrates why out-of-sample validation is essential and why a single positive period doesn't validate a strategy.
