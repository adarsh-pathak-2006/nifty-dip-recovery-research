"""
Configuration file for the NIFTY Dip-Recovery Research Engine.

All configurable parameters are defined here so that changing the event
threshold, holding period, or cost assumptions does NOT require rewriting
any analysis code.

Parameters can be overridden via a .env file (see .env.example).
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# ─────────────────────────────────────────────
# Data sourcing
# ─────────────────────────────────────────────
TICKER = os.getenv("NIFTY_TICKER", "^NSEI")          # Yahoo Finance ticker for NIFTY 50
DATA_START = os.getenv("DATA_START_DATE", "2005-01-01")  # Start date for historical data
DATA_END = os.getenv("DATA_END_DATE", "2025-09-18")     # End date for historical data
DATA_FILE = "data/nifty_data.csv"                        # Local cache path

# ─────────────────────────────────────────────
# Event definition
# ─────────────────────────────────────────────
EVENT_THRESHOLD = float(os.getenv("EVENT_THRESHOLD", "-0.02"))
                                          # Daily close-to-close return threshold
                                          # (e.g., -0.02 means a >=2% fall)
OVERLAP_COOLDOWN_DAYS = int(os.getenv("OVERLAP_COOLDOWN_DAYS", "5"))
                                          # Minimum trading days between events
                                          # to ensure statistical independence

# ─────────────────────────────────────────────
# Holding periods (in trading days)
# ─────────────────────────────────────────────
HOLDING_PERIODS = [1, 3, 5, 10]           # Forward return windows to analyse

# ─────────────────────────────────────────────
# Entry / Exit assumptions
# ─────────────────────────────────────────────
# Entry: Next trading day's Open  (avoids look-ahead bias)
# Exit : Close of the last day in the holding period

# ─────────────────────────────────────────────
# Transaction costs & slippage
# ─────────────────────────────────────────────
TRANSACTION_COST_PCT = float(os.getenv("TRANSACTION_COST_PCT", "0.0005"))
                                          # 0.05% per leg (brokerage + charges)
SLIPPAGE_PCT = float(os.getenv("SLIPPAGE_PCT", "0.0005"))
                                          # 0.05% per leg
TOTAL_ROUND_TRIP_COST = 2 * (TRANSACTION_COST_PCT + SLIPPAGE_PCT)  # 0.20%

# ─────────────────────────────────────────────
# In-sample / Out-of-sample split
# ─────────────────────────────────────────────
IN_SAMPLE_RATIO = float(os.getenv("IN_SAMPLE_RATIO", "0.70"))
                                          # First 70% of data for research
                                          # Last 30% reserved for OOS validation

# ─────────────────────────────────────────────
# Robustness sweep ranges
# ─────────────────────────────────────────────
ROBUSTNESS_THRESHOLDS = [-0.01, -0.015, -0.02, -0.025, -0.03]
ROBUSTNESS_HOLDING_PERIODS = [1, 3, 5, 10, 15, 20]

# ─────────────────────────────────────────────
# Bootstrap parameters
# ─────────────────────────────────────────────
BOOTSTRAP_ITERATIONS = int(os.getenv("BOOTSTRAP_ITERATIONS", "10000"))
BOOTSTRAP_CI = 0.95                       # 95% confidence interval

# ─────────────────────────────────────────────
# Output directories
# ─────────────────────────────────────────────
OUTPUT_DIR = "output"
PLOTS_DIR = "output/plots"
RESULTS_DIR = "output/results"
