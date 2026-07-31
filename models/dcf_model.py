"""Standard DCF configuration.

Assumptions are declared here rather than passed ad hoc so every company in a
run is valued on the same basis. Where a company needs different treatment,
that is a reason to exclude it from the automated run, not to quietly special
case it.
"""

from __future__ import annotations

import pandas as pd

from src import dcf, wacc

FORECAST_YEARS = 10
TERMINAL_GROWTH = 0.025      # roughly long run nominal GDP
RISK_FREE = 0.042
EQUITY_RISK_PREMIUM = 0.055
REINVESTMENT_RATE = 0.40

WACC_RANGE = [0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12]
GROWTH_RANGE = [0.015, 0.020, 0.025, 0.030, 0.035]


def value_company(financials: pd.Series, beta: float, **kwargs) -> dict:
    """Value one company and return the point estimate plus its grid."""
    cost = wacc.build(
        financials,
        risk_free=kwargs.get("risk_free", RISK_FREE),
        beta=beta,
        equity_risk_premium=kwargs.get("equity_risk_premium", EQUITY_RISK_PREMIUM),
        market_cap=financials["market_cap"],
    )

    growth = dcf.damped_growth(
        initial=financials.get("revenue_growth", 0.05),
        terminal=kwargs.get("terminal_growth", TERMINAL_GROWTH),
        years=kwargs.get("forecast_years", FORECAST_YEARS),
    )

    common = dict(
        base_revenue=financials["revenue"],
        growth_rates=growth,
        ebit_margin=financials["ebit"] / financials["revenue"],
        tax_rate=financials.get("tax_rate", 0.21),
        reinvestment_rate=kwargs.get("reinvestment_rate", REINVESTMENT_RATE),
        net_debt=financials["total_debt"] - financials["cash"],
        shares_outstanding=financials["shares_outstanding"],
    )

    result = dcf.value(wacc=cost.wacc, terminal_growth=TERMINAL_GROWTH, **common)
    grid = dcf.sensitivity_grid(WACC_RANGE, GROWTH_RANGE, **common)

    return {"result": result, "grid": grid, "cost_of_capital": cost}
