"""Valuation model configurations.

Each module holds the assumption set used for a published run so results are
reproducible from the repository rather than from a notebook.
"""

from . import blended_model, comps_model, dcf_model

REGISTRY = {
    "dcf": dcf_model.value_company,
    "comps": comps_model.value_company,
    "blended": blended_model.value_company,
}

__all__ = ["REGISTRY", "dcf_model", "comps_model", "blended_model"]
