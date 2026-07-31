"""Tests for comparable analysis and reporting."""

import numpy as np
import pandas as pd
import pytest

from src import comps, report


@pytest.fixture
def financials():
    return pd.DataFrame({
        "sector": ["Tech"] * 6 + ["Energy"] * 2,
        "market_cap": [1000, 1200, 900, 1100, 800, 50_000, 700, 600],
        "total_debt": [100] * 8,
        "cash": [50] * 8,
        "revenue": [500, 600, 450, 550, 400, 20_000, 350, 300],
        "ebitda": [100, 120, 90, 110, 80, 4_000, -10, 60],
        "net_income": [50, 60, 45, 55, 40, 2_000, -20, 30],
        "book_value": [300, 350, 280, 320, 250, 12_000, 200, 180],
        "shares_outstanding": [100] * 8,
    }, index=list("ABCDEFGH"))


def test_negative_denominators_produce_nan(financials):
    m = comps.compute_multiples(financials)
    assert np.isnan(m.loc["G", "ev_ebitda"]), "negative EBITDA must not yield a multiple"
    assert np.isnan(m.loc["G", "pe"]), "negative earnings must not yield a P/E"


def test_peer_group_excludes_self(financials):
    assert "A" not in comps.peer_group(financials, "A")


def test_peer_group_is_sector_constrained(financials):
    peers = comps.peer_group(financials, "A")
    assert all(financials.loc[p, "sector"] == "Tech" for p in peers)


def test_size_band_excludes_the_outlier(financials):
    """F is 50x the size of A and should not anchor its multiple.

    min_peers is lowered so the band is tested in isolation, without the
    thin-peer fallback kicking in.
    """
    peers = comps.peer_group(financials, "A", size_tolerance=3.0, min_peers=3)
    assert "F" not in peers
    assert set(peers) == {"B", "C", "D", "E"}


def test_thin_peer_group_falls_back_to_full_sector(financials):
    """When the size band leaves too few peers, widen rather than report on three.

    The fallback re-admits the size outlier, which is a real tradeoff: a
    distorted median beats a median computed from two companies. `peer_count`
    is reported so the reader can see which path was taken.
    """
    peers = comps.peer_group(financials, "A", size_tolerance=3.0, min_peers=5)
    assert "F" in peers, "fallback should widen to the full sector"
    assert len(peers) == 5


def test_peer_statistics_use_median(financials):
    m = comps.compute_multiples(financials)
    stats = comps.peer_statistics(m, ["A", "B", "C", "D", "E"], trim=0.0)
    assert stats.loc["ev_ebitda", "median"] == pytest.approx(
        m.loc[["A", "B", "C", "D", "E"], "ev_ebitda"].median()
    )


def test_blend_falls_back_when_comps_missing():
    assert report.blend(50.0, pd.Series([np.nan, np.nan])) == pytest.approx(50.0)


def test_blend_is_a_weighted_average():
    assert report.blend(100.0, pd.Series([50.0]), dcf_weight=0.5) == pytest.approx(75.0)


def test_upside_calculation():
    assert report.upside(120.0, 100.0) == pytest.approx(0.20)


def test_confidence_downgraded_on_terminal_dominance():
    flagged = pd.Series({"terminal_share": 0.90, "peer_count": 10, "dcf_vs_comps_gap": 0.1})
    clean = pd.Series({"terminal_share": 0.60, "peer_count": 10, "dcf_vs_comps_gap": 0.1})
    assert report.confidence_flag(flagged) == "medium"
    assert report.confidence_flag(clean) == "high"


def test_confidence_low_when_multiple_issues():
    bad = pd.Series({
        "terminal_share": 0.90, "peer_count": 2,
        "dcf_vs_comps_gap": 0.9, "sector": "Financials",
    })
    assert report.confidence_flag(bad) == "low"


def test_ranking_sorts_by_upside():
    df = pd.DataFrame({"upside": [0.1, 0.5, -0.2]}, index=list("ABC"))
    assert list(report.rank_universe(df).index) == ["B", "A", "C"]
