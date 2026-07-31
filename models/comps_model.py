"""Comparable company configuration."""

from __future__ import annotations

import pandas as pd

from src import comps

SIZE_TOLERANCE = 3.0
MIN_PEERS = 5
TRIM = 0.10


def value_company(financials: pd.DataFrame, ticker: str, **kwargs) -> dict:
    """Value one company against its peer group."""
    multiples = comps.compute_multiples(financials)
    peers = comps.peer_group(
        financials,
        ticker,
        size_tolerance=kwargs.get("size_tolerance", SIZE_TOLERANCE),
        min_peers=kwargs.get("min_peers", MIN_PEERS),
    )
    stats = comps.peer_statistics(multiples, peers, trim=kwargs.get("trim", TRIM))
    implied = comps.implied_value(financials.loc[ticker], stats)

    return {"implied": implied, "peer_stats": stats, "peers": peers}
