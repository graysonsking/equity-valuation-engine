# Roadmap

## Status

| Component | State |
|---|---|
| Cost of capital (CAPM, levering, blended WACC) | Complete, tested |
| FCFF projection with growth fading | Complete, tested |
| Terminal value (perpetuity and exit multiple) | Complete, tested |
| Sensitivity grid | Complete, tested |
| Multiple computation with negative screening | Complete, tested |
| Peer selection by sector and size | Complete, tested |
| Peer statistics with trimming | Complete, tested |
| Blending and ranking | Complete, tested |
| Confidence flagging | Complete, tested |
| Statement data connector | Complete |
| Beta estimation | Complete |
| Published output | Not started |

## Next

1. **Statement data connector.** The main gap. Needs revenue, EBIT, EBITDA, net income, book value, total debt, cash, shares outstanding, and sector, point-in-time where possible.
2. **Beta estimation.** Currently passed in. Add rolling regression against a market index with a peer-median fallback for thin histories.
3. **Run the full index.** Publish the ranked table and a handful of sensitivity grids to `results/`.
4. **Sample output in the README.** A recruiter looks at the table before reading any code. This is the highest leverage remaining item for portfolio purposes.

## Later

5. **Sector specific models.** A financials model built on residual income or dividend discount, and a REIT model built on FFO. This removes the largest category of flagged failures.
6. **Backtest the screen.** Do high upside, high confidence names outperform? Without this, the model produces opinions rather than evidence. This is the single most valuable addition and also the most work, since it needs point-in-time fundamentals.
7. **Stock based compensation and lease adjustments.** Material for technology and retail respectively.
8. **Monte Carlo over assumptions.** A distribution of fair values rather than a grid, which handles correlated assumption errors that a two-way grid cannot represent.
