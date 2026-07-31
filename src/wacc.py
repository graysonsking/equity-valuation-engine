"""Cost of capital.

The discount rate is one of the two inputs that dominate a DCF. Small changes
move the output enormously, which is why `dcf.sensitivity_grid` exists and why
no single point estimate from this module should be treated as precise.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class CostOfCapital:
    """Decomposed WACC so each input can be inspected and challenged."""

    cost_of_equity: float
    cost_of_debt: float
    tax_rate: float
    equity_value: float
    debt_value: float

    @property
    def after_tax_cost_of_debt(self) -> float:
        return self.cost_of_debt * (1.0 - self.tax_rate)

    @property
    def total_capital(self) -> float:
        return self.equity_value + self.debt_value

    @property
    def equity_weight(self) -> float:
        return self.equity_value / self.total_capital if self.total_capital else 1.0

    @property
    def debt_weight(self) -> float:
        return self.debt_value / self.total_capital if self.total_capital else 0.0

    @property
    def wacc(self) -> float:
        return (
            self.equity_weight * self.cost_of_equity
            + self.debt_weight * self.after_tax_cost_of_debt
        )

    def to_series(self) -> pd.Series:
        return pd.Series({
            "Cost of Equity": self.cost_of_equity,
            "Cost of Debt": self.cost_of_debt,
            "After Tax Cost of Debt": self.after_tax_cost_of_debt,
            "Equity Weight": self.equity_weight,
            "Debt Weight": self.debt_weight,
            "WACC": self.wacc,
        })


def capm_cost_of_equity(
    risk_free: float,
    beta: float,
    equity_risk_premium: float,
    size_premium: float = 0.0,
) -> float:
    """CAPM cost of equity, optionally with a size premium."""
    return risk_free + beta * equity_risk_premium + size_premium


def levered_beta(unlevered_beta: float, debt_to_equity: float, tax_rate: float) -> float:
    """Hamada relevering. Use when applying a peer beta to a different capital structure."""
    return unlevered_beta * (1.0 + (1.0 - tax_rate) * debt_to_equity)


def unlevered_beta(levered: float, debt_to_equity: float, tax_rate: float) -> float:
    """Strip capital structure out of an observed beta."""
    return levered / (1.0 + (1.0 - tax_rate) * debt_to_equity)


def implied_cost_of_debt(interest_expense: float, total_debt: float, floor: float = 0.0) -> float:
    """Effective interest rate from the financials.

    Crude but observable. It is a backward looking average rate on existing
    debt, so it understates marginal borrowing cost when rates have risen.
    """
    if not total_debt:
        return floor
    return max(interest_expense / total_debt, floor)


def build(
    financials: pd.Series,
    risk_free: float,
    beta: float,
    equity_risk_premium: float,
    market_cap: float,
    tax_rate: float | None = None,
) -> CostOfCapital:
    """Assemble a CostOfCapital from a financial statement row."""
    debt = float(financials.get("total_debt", 0.0))
    interest = float(financials.get("interest_expense", 0.0))
    effective_tax = tax_rate if tax_rate is not None else float(financials.get("tax_rate", 0.21))

    return CostOfCapital(
        cost_of_equity=capm_cost_of_equity(risk_free, beta, equity_risk_premium),
        cost_of_debt=implied_cost_of_debt(interest, debt, floor=risk_free),
        tax_rate=effective_tax,
        equity_value=market_cap,
        debt_value=debt,
    )
