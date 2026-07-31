"""Run configuration.

Everything you would want to change lives here. `run_results.py` reads this
and does not need editing.

No credentials required. yfinance is unauthenticated.
"""

from __future__ import annotations

from pathlib import Path

# ================================================================= universe
# Large caps with clean statement data. Financials and Real Estate are
# included deliberately so the confidence flag can demote them: the default
# FCFF model does not fit those sectors, and showing that the engine knows it
# is more useful than quietly excluding them.

UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AVGO", "TSLA", "ORCL", "CRM",
    "ADBE", "AMD", "INTC", "CSCO", "ACN", "IBM", "TXN", "QCOM", "NOW", "INTU",
    "JNJ", "UNH", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "AMGN",
    "BMY", "GILD", "CVS", "MDT", "SYK", "ISRG", "ZTS", "REGN", "VRTX", "HCA",
    "JPM", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "AXP", "C", "SPGI",
    "PG", "KO", "PEP", "WMT", "COST", "MCD", "NKE", "SBUX", "TGT", "MDLZ",
    "XOM", "CVX", "COP", "SLB", "EOG", "PSX", "MPC", "VLO", "OXY", "KMI",
    "CAT", "HON", "GE", "UNP", "RTX", "LMT", "DE", "BA", "UPS", "MMM",
    "LIN", "APD", "SHW", "NEM", "FCX", "DOW", "NUE", "ECL", "PPG", "VMC",
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "PEG", "ED",
]

BENCHMARK = "SPY"          # beta is estimated against this

# ============================================================ model settings

BETA_YEARS = 5             # monthly returns used for the beta regression
BETA_MIN_MONTHS = 36
BETA_FLOOR, BETA_CAP = 0.3, 3.0   # guard against regression artifacts

# Blume adjustment. Raw five-year betas are noisy and mean-revert toward 1.0,
# so the standard practice is to shrink them. Without this, a handful of
# defensive names print betas near 0.3, which produces a cost of equity below
# investment grade bond yields and mechanically inflates their DCF.
BLUME_WEIGHT = 0.67               # adjusted = w * raw + (1 - w) * 1.0

# Floor on the discount rate. CAPM with a very low beta can produce a WACC
# that no company could actually raise capital at. This is a judgment call and
# it is stated in the output rather than hidden.
WACC_FLOOR = 0.065

RISK_FREE = 0.042
EQUITY_RISK_PREMIUM = 0.055
TERMINAL_GROWTH = 0.025
FORECAST_YEARS = 10
REINVESTMENT_RATE = 0.40

DCF_WEIGHT = 0.60          # blend weight on DCF versus the comps median
PEER_SIZE_TOLERANCE = 3.0
MIN_PEERS = 5

TOP_N = 20                 # rows in the published ranking table

# ==================================================================== paths

ROOT = Path(__file__).parent
CACHE_DIR = ROOT / "cache"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "docs" / "images"
