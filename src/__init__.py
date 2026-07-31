"""Automated fundamental valuation across a large universe.

Pipeline: data -> wacc -> dcf / comps -> report
"""

from . import comps, dcf, report, wacc

__version__ = "0.1.0"
__all__ = ["wacc", "dcf", "comps", "report"]
