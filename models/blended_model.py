"""Blended DCF and comparables valuation.

The blend is a 50/50 weighting, chosen because there is no principled basis
for preferring one method over the other across a whole universe. Where the
two disagree sharply, that disagreement is more informative than the blend and
is surfaced as a confidence flag rather than averaged away.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import report

from . import comps_model, dcf_model

DCF_WEIGHT = 0.5


def value_company(
    financials: pd.DataFrame,
    ticker: str,
    beta: float,
    current_price: float,
    **kwargs,
) -> pd.Series:
    """Full valuation for one company."""
    row = financials.loc[ticker]

    dcf_out = dcf_model.value_company(row, beta=beta, **kwargs)
    comps_out = comps_model.value_company(financials, ticker, **kwargs)

    dcf_value = dcf_out["result"].value_per_share
    comps_value = comps_out["implied"].dropna().median()

    fair = report.blend(dcf_value, comps_out["implied"], kwargs.get("dcf_weight", DCF_WEIGHT))

    gap = np.nan
    if comps_value and not np.isnan(comps_value) and not np.isnan(dcf_value):
        gap = dcf_value / comps_value - 1.0

    out = pd.Series({
        "sector": row.get("sector"),
        "current_price": current_price,
        "dcf_value": dcf_value,
        "comps_value": comps_value,
        "fair_value": fair,
        "upside": report.upside(fair, current_price),
        "terminal_share": dcf_out["result"].terminal_share,
        "peer_count": len(comps_out["peers"]),
        "dcf_vs_comps_gap": gap,
        "wacc": dcf_out["cost_of_capital"].wacc,
    }, name=ticker)

    out["confidence"] = report.confidence_flag(out)
    return out
