"""Blended output and ranked reporting."""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_DCF_WEIGHT = 0.5


def blend(
    dcf_value: float,
    comps_values: pd.Series,
    dcf_weight: float = DEFAULT_DCF_WEIGHT,
) -> float:
    """Weighted blend of DCF and the median comparable value."""
    comps_median = comps_values.dropna().median()
    if np.isnan(comps_median):
        return dcf_value
    if np.isnan(dcf_value):
        return float(comps_median)
    return dcf_weight * dcf_value + (1.0 - dcf_weight) * comps_median


def upside(fair_value: float, current_price: float) -> float:
    """Implied return to fair value."""
    return fair_value / current_price - 1.0 if current_price else np.nan


def rank_universe(results: pd.DataFrame, min_confidence: str | None = None) -> pd.DataFrame:
    """Sort by implied upside.

    Read the output as a screen that flags candidates for manual review, not
    as a set of price targets. The model applies identical projection logic to
    businesses with very different cash flow profiles, so the extremes of this
    ranking are as likely to be modeling artifacts as opportunities.
    """
    out = results.copy()
    if min_confidence and "confidence" in out.columns:
        order = {"low": 0, "medium": 1, "high": 2}
        out = out[out["confidence"].map(order) >= order[min_confidence]]
    return out.sort_values("upside", ascending=False)


def confidence_flag(result: pd.Series) -> str:
    """Heuristic confidence label based on known failure modes."""
    issues = 0

    if result.get("terminal_share", 0) > 0.80:
        issues += 1  # value is mostly a perpetuity assumption
    if result.get("peer_count", 99) < 5:
        issues += 1  # thin comparable set
    if abs(result.get("dcf_vs_comps_gap", 0)) > 0.50:
        issues += 1  # the two methods disagree sharply
    if result.get("sector") in ("Financials", "Real Estate"):
        issues += 1  # default FCFF model does not fit these

    return {0: "high", 1: "medium"}.get(issues, "low")


def summary_table(results: pd.DataFrame) -> pd.DataFrame:
    """Presentation-ready columns in a sensible order."""
    cols = [
        "sector", "current_price", "dcf_value", "comps_value",
        "fair_value", "upside", "terminal_share", "peer_count", "confidence",
    ]
    return results[[c for c in cols if c in results.columns]]
