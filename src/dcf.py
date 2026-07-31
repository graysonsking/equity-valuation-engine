"""Discounted cash flow valuation.

A DCF output is dominated by two inputs: the discount rate and the terminal
growth rate. Together they typically determine the majority of the present
value, because terminal value is usually the majority of the total.

For that reason this module produces a sensitivity grid rather than a single
number. A point estimate from a DCF conveys a precision the method does not
possess, and reporting one to the dollar is the most common way these models
mislead.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class DCFResult:
    """Valuation output with the assumptions that produced it."""

    enterprise_value: float
    equity_value: float
    value_per_share: float
    terminal_value: float
    pv_explicit: float
    pv_terminal: float
    wacc: float
    terminal_growth: float

    @property
    def terminal_share(self) -> float:
        """Fraction of enterprise value coming from terminal value.

        Above roughly 75 percent, the valuation is mostly an assumption about
        perpetuity rather than an analysis of the forecast period. Report it.
        """
        return self.pv_terminal / self.enterprise_value if self.enterprise_value else np.nan

    def to_series(self) -> pd.Series:
        return pd.Series({
            "Enterprise Value": self.enterprise_value,
            "Equity Value": self.equity_value,
            "Value Per Share": self.value_per_share,
            "PV Explicit": self.pv_explicit,
            "PV Terminal": self.pv_terminal,
            "Terminal Share": self.terminal_share,
            "WACC": self.wacc,
            "Terminal Growth": self.terminal_growth,
        })


def project_fcff(
    base_revenue: float,
    growth_rates: list[float],
    ebit_margin: float,
    tax_rate: float,
    reinvestment_rate: float,
) -> pd.DataFrame:
    """Project free cash flow to the firm over the explicit forecast period.

    FCFF = EBIT x (1 - tax) x (1 - reinvestment rate)

    Reinvestment is modeled as a fraction of NOPAT rather than as separate
    capex and working capital lines. Less granular, but it enforces the link
    between growth and the investment required to fund it, which separately
    forecast lines routinely violate.
    """
    rows = []
    revenue = base_revenue
    for year, g in enumerate(growth_rates, start=1):
        revenue *= 1.0 + g
        ebit = revenue * ebit_margin
        nopat = ebit * (1.0 - tax_rate)
        rows.append({
            "year": year,
            "revenue": revenue,
            "ebit": ebit,
            "nopat": nopat,
            "reinvestment": nopat * reinvestment_rate,
            "fcff": nopat * (1.0 - reinvestment_rate),
        })
    return pd.DataFrame(rows).set_index("year")


def damped_growth(initial: float, terminal: float, years: int) -> list[float]:
    """Fade growth linearly from initial toward terminal.

    A company growing at 25 percent will not still be growing at 25 percent in
    year ten. Holding the initial rate flat across the forecast and then
    dropping to terminal growth in a single step is the most common structural
    error in an automated DCF.
    """
    return list(np.linspace(initial, terminal, years))


def terminal_value_perpetuity(final_fcff: float, wacc: float, growth: float) -> float:
    """Gordon growth terminal value.

    Requires wacc > growth. If terminal growth approaches the discount rate
    the value diverges toward infinity, which is a modeling artifact and not
    a valuation.
    """
    if wacc <= growth:
        raise ValueError(f"wacc ({wacc:.4f}) must exceed terminal growth ({growth:.4f})")
    return final_fcff * (1.0 + growth) / (wacc - growth)


def terminal_value_multiple(final_ebitda: float, exit_multiple: float) -> float:
    """Exit multiple terminal value. Use as a cross-check on perpetuity."""
    return final_ebitda * exit_multiple


def discount(cash_flows: pd.Series, wacc: float) -> float:
    """Present value of a year-indexed cash flow series."""
    periods = np.asarray(cash_flows.index, dtype=float)
    return float((cash_flows.values / np.power(1.0 + wacc, periods)).sum())


def value(
    base_revenue: float,
    growth_rates: list[float],
    ebit_margin: float,
    tax_rate: float,
    reinvestment_rate: float,
    wacc: float,
    terminal_growth: float,
    net_debt: float,
    shares_outstanding: float,
) -> DCFResult:
    """Full DCF from operating assumptions to value per share."""
    projection = project_fcff(base_revenue, growth_rates, ebit_margin, tax_rate, reinvestment_rate)

    pv_explicit = discount(projection["fcff"], wacc)
    tv = terminal_value_perpetuity(projection["fcff"].iloc[-1], wacc, terminal_growth)
    pv_terminal = tv / (1.0 + wacc) ** len(growth_rates)

    ev = pv_explicit + pv_terminal
    equity = ev - net_debt

    return DCFResult(
        enterprise_value=ev,
        equity_value=equity,
        value_per_share=equity / shares_outstanding if shares_outstanding else np.nan,
        terminal_value=tv,
        pv_explicit=pv_explicit,
        pv_terminal=pv_terminal,
        wacc=wacc,
        terminal_growth=terminal_growth,
    )


def sensitivity_grid(
    wacc_range: list[float],
    growth_range: list[float],
    **kwargs,
) -> pd.DataFrame:
    """Value per share across discount rate and terminal growth.

    This, not the point estimate, is the output of a DCF. The spread across
    the grid is the honest statement of what the model knows.
    """
    grid = {}
    for g in growth_range:
        col = {}
        for w in wacc_range:
            try:
                col[w] = value(wacc=w, terminal_growth=g, **kwargs).value_per_share
            except ValueError:
                col[w] = np.nan  # wacc <= growth, undefined
        grid[g] = col

    out = pd.DataFrame(grid)
    out.index.name = "WACC"
    out.columns.name = "Terminal Growth"
    return out
