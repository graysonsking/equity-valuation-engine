"""Comparable company analysis.

Multiples are simpler than a DCF and carry a different failure mode. A DCF is
wrong when its assumptions are wrong. Comps are wrong when the peer set is
wrong, and peer selection is where nearly all the judgment lives.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MULTIPLES = ("ev_ebitda", "ev_sales", "pe", "pb")


def compute_multiples(financials: pd.DataFrame) -> pd.DataFrame:
    """Derive valuation multiples from statement data.

    Negative denominators produce meaningless multiples. A company with
    negative earnings has no meaningful P/E, and carrying a negative value
    into a peer median corrupts it, so these are set to NaN.
    """
    out = pd.DataFrame(index=financials.index)

    ev = financials["market_cap"] + financials["total_debt"] - financials["cash"]
    out["ev_ebitda"] = ev / financials["ebitda"].where(financials["ebitda"] > 0)
    out["ev_sales"] = ev / financials["revenue"].where(financials["revenue"] > 0)
    out["pe"] = financials["market_cap"] / financials["net_income"].where(
        financials["net_income"] > 0
    )
    out["pb"] = financials["market_cap"] / financials["book_value"].where(
        financials["book_value"] > 0
    )
    return out


def peer_group(
    financials: pd.DataFrame,
    ticker: str,
    size_tolerance: float = 3.0,
    min_peers: int = 5,
) -> list[str]:
    """Select peers by sector and size band.

    Size matters beyond sector. A 500 billion dollar company and a 2 billion
    dollar company in the same sector trade on different multiples for
    structural reasons, so pooling them produces a median that describes
    neither.
    """
    if ticker not in financials.index:
        raise KeyError(f"{ticker} not in the financials frame")

    row = financials.loc[ticker]
    same_sector = financials[financials["sector"] == row["sector"]].drop(index=ticker)
    if same_sector.empty:
        return []

    size = row["market_cap"]
    banded = same_sector[
        (same_sector["market_cap"] >= size / size_tolerance)
        & (same_sector["market_cap"] <= size * size_tolerance)
    ]

    # Fall back to the full sector rather than returning too thin a group.
    if len(banded) < min_peers:
        return list(same_sector.index)
    return list(banded.index)


def peer_statistics(multiples: pd.DataFrame, peers: list[str], trim: float = 0.1) -> pd.DataFrame:
    """Median and quartiles of peer multiples with outlier trimming.

    Median rather than mean throughout. Multiples are right skewed and a
    single high growth peer at 80x drags a mean far from anything typical.
    """
    subset = multiples.loc[[p for p in peers if p in multiples.index]]
    rows = {}
    for col in subset.columns:
        s = subset[col].dropna()
        if len(s) < 3:
            continue
        s = s.clip(s.quantile(trim), s.quantile(1 - trim))
        rows[col] = {
            "median": s.median(),
            "q1": s.quantile(0.25),
            "q3": s.quantile(0.75),
            "n": len(s),
        }
    return pd.DataFrame(rows).T


def implied_value(
    financials: pd.Series,
    peer_stats: pd.DataFrame,
    multiples: tuple[str, ...] = MULTIPLES,
) -> pd.Series:
    """Equity value per share implied by each peer multiple."""
    shares = financials.get("shares_outstanding", np.nan)
    net_debt = financials.get("total_debt", 0.0) - financials.get("cash", 0.0)
    out = {}

    for m in multiples:
        if m not in peer_stats.index:
            continue
        median = peer_stats.loc[m, "median"]

        if m == "ev_ebitda" and financials.get("ebitda", 0) > 0:
            equity = median * financials["ebitda"] - net_debt
        elif m == "ev_sales" and financials.get("revenue", 0) > 0:
            equity = median * financials["revenue"] - net_debt
        elif m == "pe" and financials.get("net_income", 0) > 0:
            equity = median * financials["net_income"]
        elif m == "pb" and financials.get("book_value", 0) > 0:
            equity = median * financials["book_value"]
        else:
            continue

        out[m] = equity / shares if shares else np.nan

    return pd.Series(out, name="implied_value_per_share")
