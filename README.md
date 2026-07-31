[README.md](https://github.com/user-attachments/files/30569264/README.md)
# Equity Valuation Engine

An automated fundamental valuation framework covering the S&P 500. Pulls financial statement data, builds a discounted cash flow model and a comparables screen for each name, and outputs a ranked valuation table.

## What It Does

Sell-side style valuation is usually done one company at a time. This runs the same process across the full index so relative dislocations are visible in one view. Every company gets a DCF, a multiples-based comparable valuation, and a blended fair value estimate with the assumptions recorded.

## Model Components

**Discounted cash flow**
- Free cash flow to firm projected over an explicit forecast horizon
- Revenue growth from trailing realized growth, damped toward a terminal rate
- WACC built from a CAPM cost of equity and observed cost of debt
- Terminal value via perpetuity growth, with a multiple-based cross-check

**Comparables**
- Peers grouped by sector and size
- EV/EBITDA, EV/Sales, P/E, and P/B against the peer median
- Outliers trimmed before computing peer statistics

**Blend**
- Weighted combination of DCF and comparable estimates
- Output includes implied upside or downside against current price

## Sensitivity

DCF output is dominated by two inputs: the discount rate and the terminal growth rate. The engine produces a sensitivity grid across both for every name rather than reporting a single point estimate, because a point estimate from a DCF conveys false precision.

## Repository Layout

```
equity-valuation-engine/
|
|-- README.md
|-- LICENSE
|-- .gitignore
|-- requirements.txt
|
|-- src/
|   |-- __init__.py
|   |-- comps.py
|   |-- dcf.py
|   |-- report.py
|   `-- wacc.py
|
|-- models/
|   |-- __init__.py
|   |-- blended_model.py
|   |-- comps_model.py
|   `-- dcf_model.py
|
|-- docs/
|   |-- methodology.md
|   `-- roadmap.md
|
|-- results/
|   `-- .gitkeep
|
|-- tests/
|   |-- __init__.py
|   |-- test_comps.py
|   `-- test_dcf.py
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

API credentials are read from environment variables and are never committed.

## Usage

Value a single company:

```bash
python -m src.report --ticker AAPL --sensitivity
```

Run the full index:

```bash
python -m src.report --universe sp500 --out output/valuations.csv
```

## Tests

```bash
python -m pytest tests -q
```

23 tests covering DCF mechanics, sensitivity spread, peer selection, and confidence flagging.

## Sample Output

Add a screenshot or a small excerpt of the ranked table here. A recruiter will look at this before reading any code.

## Limitations

Automated valuation cannot capture business-specific judgment, and it applies the same projection logic to companies with very different cash flow profiles. Financials and REITs need different treatment than the default model provides. Results should be read as a screen that flags candidates for manual review, not as a set of price targets.

## License

MIT

---

*Research code. Not investment advice.*
