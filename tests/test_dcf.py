"""Tests for DCF mechanics and cost of capital."""

import numpy as np
import pandas as pd
import pytest

from src import comps, dcf, report, wacc


BASE = dict(
    base_revenue=1000.0,
    growth_rates=[0.05] * 10,
    ebit_margin=0.20,
    tax_rate=0.21,
    reinvestment_rate=0.40,
    net_debt=200.0,
    shares_outstanding=100.0,
)


def test_terminal_value_requires_wacc_above_growth():
    with pytest.raises(ValueError):
        dcf.terminal_value_perpetuity(100.0, wacc=0.03, growth=0.05)


def test_value_rises_as_discount_rate_falls():
    low = dcf.value(wacc=0.07, terminal_growth=0.025, **BASE).value_per_share
    high = dcf.value(wacc=0.11, terminal_growth=0.025, **BASE).value_per_share
    assert low > high


def test_value_rises_with_terminal_growth():
    slow = dcf.value(wacc=0.09, terminal_growth=0.015, **BASE).value_per_share
    fast = dcf.value(wacc=0.09, terminal_growth=0.035, **BASE).value_per_share
    assert fast > slow


def test_terminal_value_dominates_the_valuation():
    """Most of a DCF is the perpetuity. This is why sensitivity matters."""
    assert dcf.value(wacc=0.09, terminal_growth=0.025, **BASE).terminal_share > 0.5


def test_damped_growth_fades_to_terminal():
    g = dcf.damped_growth(0.25, 0.025, 10)
    assert g[0] == pytest.approx(0.25)
    assert g[-1] == pytest.approx(0.025)
    assert all(a >= b for a, b in zip(g, g[1:])), "growth should decline monotonically"


def test_discounting_matches_manual_calculation():
    cf = pd.Series([100.0, 100.0], index=[1, 2])
    expected = 100 / 1.1 + 100 / 1.21
    assert dcf.discount(cf, 0.10) == pytest.approx(expected)


def test_sensitivity_grid_masks_invalid_combinations():
    grid = dcf.sensitivity_grid([0.02, 0.09], [0.025, 0.05], **BASE)
    assert grid.isna().any().any(), "wacc below growth should produce NaN"


def test_sensitivity_grid_spread_is_wide():
    """A DCF point estimate is not precise. The grid should show that."""
    grid = dcf.sensitivity_grid([0.07, 0.09, 0.11], [0.015, 0.025, 0.035], **BASE)
    flat = grid.values.flatten()
    assert np.nanmax(flat) / np.nanmin(flat) > 2.0


def test_wacc_is_between_debt_and_equity_cost():
    c = wacc.CostOfCapital(0.10, 0.05, 0.21, 800, 200)
    assert c.after_tax_cost_of_debt < c.wacc < c.cost_of_equity


def test_wacc_equals_cost_of_equity_with_no_debt():
    c = wacc.CostOfCapital(0.10, 0.05, 0.21, 1000, 0)
    assert c.wacc == pytest.approx(0.10)


def test_relevering_beta_roundtrips():
    unlevered = wacc.unlevered_beta(1.4, 0.5, 0.21)
    assert wacc.levered_beta(unlevered, 0.5, 0.21) == pytest.approx(1.4)
