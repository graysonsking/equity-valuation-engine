# Methodology

## What This Is

Sell-side valuation is normally done one company at a time. This runs the same process across an entire index so relative dislocations are visible in a single view. Every company gets a DCF, a comparables valuation, a blended fair value, and a confidence flag.

The output is a screen, not a set of price targets. That distinction is the most important thing in this document.

## Why Automated Valuation Is Hard

Applying identical logic across 500 companies means applying it to businesses it does not fit. A FCFF model built around reinvestment and operating margin does not describe a bank, where debt is raw material rather than financing, or a REIT, where the relevant metric is funds from operations.

The design response is not to special case these quietly. It is to flag them. `report.confidence_flag` downgrades financials and real estate automatically, along with three other known failure modes. A result nobody can tell is unreliable is worse than no result.

## DCF Construction

**Free cash flow to the firm.** FCFF = EBIT x (1 - tax) x (1 - reinvestment rate).

Reinvestment is modeled as a fraction of NOPAT rather than as separately forecast capex, depreciation, and working capital lines. This is less granular on purpose. It enforces the link between growth and the investment required to fund it, a constraint that independently forecast lines routinely violate, producing companies that grow 15 percent a year while investing nothing.

**Growth fading.** Growth declines linearly from the current rate toward terminal growth over the forecast period. A company growing 25 percent today will not be growing 25 percent in year ten. Holding the initial rate flat and then dropping to 2.5 percent in a single step is the most common structural error in an automated DCF, and it inflates valuations substantially.

**Terminal value.** Gordon growth, with an exit multiple available as a cross-check. Terminal growth defaults to 2.5 percent, roughly long run nominal GDP. A company cannot grow faster than the economy forever, because it would eventually become the economy.

The model raises an error rather than returning a number when the discount rate does not exceed terminal growth. That combination produces a divergent value, which is a modeling artifact rather than a valuation.

## Sensitivity Is the Output

A DCF's value is dominated by two inputs: the discount rate and the terminal growth rate. Terminal value is typically the majority of enterprise value, and terminal value is entirely determined by those two numbers.

On a representative set of assumptions, value per share ranges from roughly 24 to 65 across a defensible band of discount rates and terminal growth rates. That is a spread of more than 2.5x from parameter choices no one could call unreasonable.

Reporting a single number to the dollar from that range conveys a precision the method does not possess. `dcf.sensitivity_grid` is therefore the primary output and the point estimate is a summary of it. A test asserts the grid spread exceeds 2x, so the model cannot quietly start looking more confident than it is.

`terminal_share` is reported for every company. Above roughly 75 to 80 percent, the valuation is mostly an assumption about perpetuity rather than an analysis of the forecast period, and confidence is downgraded accordingly.

## Comparables

Multiples fail differently from a DCF. A DCF is wrong when its assumptions are wrong. Comps are wrong when the peer set is wrong, and peer selection is where nearly all the judgment lives.

**Peer selection** is by sector and size band, defaulting to companies within 3x market cap in either direction. Size matters beyond sector: a 500 billion dollar company and a 2 billion dollar company in the same sector trade on different multiples for structural reasons, and pooling them produces a median describing neither. Where the size band leaves too few peers, the model falls back to the full sector and reports the smaller peer count.

**Negative denominators** are set to NaN rather than computed. A company with negative earnings has no meaningful P/E, and carrying a negative multiple into a peer median corrupts it.

**Median rather than mean**, with trimming. Multiples are right skewed, and one high growth peer at 80x drags a mean far from anything typical.

## Blending

A 50/50 weighting of DCF and median comparable value. There is no principled basis for preferring one method across an entire universe, so an equal weight is the honest default rather than a tuned one.

Where the two methods disagree sharply, the disagreement is more informative than the blend. `dcf_vs_comps_gap` is reported and a gap beyond 50 percent downgrades confidence. Averaging a strong disagreement produces a number that neither method supports.

## How to Read the Output

The ranking flags candidates for manual review. The extremes are as likely to be modeling artifacts as opportunities, because the companies where a standardized model breaks are exactly the companies where it produces extreme output.

Work from the confidence flag inward. A high confidence name with 30 percent implied upside is worth an afternoon. A low confidence name with 300 percent implied upside is almost certainly a broken input.

## Limitations

- Financials and REITs need a different model than the default FCFF approach. They are flagged, not fixed.
- Beta is an input rather than estimated here, and beta estimates are themselves unstable.
- The implied cost of debt is backward looking, computed from interest expense over existing debt, so it understates marginal borrowing cost after rates rise.
- No adjustment for stock based compensation, operating leases, or off balance sheet items.
- Peer groups use current sector classification, so historical runs carry classification drift.
- Nothing here captures management quality, competitive position, or any of the qualitative judgment that separates a valuation from an arithmetic exercise.
