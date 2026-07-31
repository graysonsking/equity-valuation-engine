"""Reproduce the published results.

Pulls statement data, estimates beta from price history, values every company
in the universe by DCF and by comparables, blends the two, and writes a ranked
fair value table.

    python run_results.py              # real data
    python run_results.py --offline    # synthetic data, tests the plumbing
    python run_results.py --risk-free 0.045

Settings live in `config.py`. Everything in the README results section comes
from this script.

The output is a screen, not a set of price targets. Identical projection logic
is applied to businesses with very different cash flow profiles, so the
extremes of the ranking are as likely to be modelling artifacts as
opportunities. The confidence column exists to say so.
"""

from __future__ import annotations

import argparse
import sys
import warnings

import numpy as np
import pandas as pd

import config
from src import comps, report
from models import dcf_model

warnings.filterwarnings("ignore", category=FutureWarning)

REQUIRED = [
    "sector", "price", "market_cap", "shares_outstanding", "revenue",
    "revenue_growth", "ebit", "ebitda", "net_income", "book_value",
    "total_debt", "cash", "interest_expense", "tax_rate",
]


# --------------------------------------------------------------- data layer


def _safe(d: dict, *keys, default=np.nan):
    for k in keys:
        v = d.get(k)
        if v is not None and not (isinstance(v, float) and np.isnan(v)):
            return float(v)
    return default


def _from_statement(stmt: pd.DataFrame, *names) -> float:
    """First matching row of the most recent statement column."""
    if stmt is None or stmt.empty:
        return np.nan
    for n in names:
        if n in stmt.index:
            s = stmt.loc[n].dropna()
            if not s.empty:
                return float(s.iloc[0])
    return np.nan


def fetch_fundamentals(tickers):
    """Statement data and market values, cached to parquet."""
    config.CACHE_DIR.mkdir(exist_ok=True)
    key = config.CACHE_DIR / f"fundamentals_{len(tickers)}.parquet"
    if key.exists():
        print(f"cache hit: {key.name}  (delete to refresh)")
        return pd.read_parquet(key)

    try:
        import yfinance as yf
    except ImportError:
        sys.exit("yfinance not installed. Run: python -m pip install yfinance")

    rows = {}
    for i, t in enumerate(tickers, 1):
        try:
            tk = yf.Ticker(t)
            info = tk.info or {}
            inc = tk.income_stmt
        except Exception as e:
            print(f"  {t}: skipped ({type(e).__name__})")
            continue

        ebit = _from_statement(inc, "EBIT", "Operating Income")
        pretax = _from_statement(inc, "Pretax Income")
        taxes = _from_statement(inc, "Tax Provision")
        tax_rate = taxes / pretax if pretax and pretax > 0 and not np.isnan(taxes) else 0.21

        rows[t] = {
            "sector": info.get("sector", "Unknown"),
            "price": _safe(info, "currentPrice", "regularMarketPrice"),
            "market_cap": _safe(info, "marketCap"),
            "shares_outstanding": _safe(info, "sharesOutstanding"),
            "revenue": _safe(info, "totalRevenue"),
            "revenue_growth": _safe(info, "revenueGrowth", default=0.04),
            "ebit": ebit,
            "ebitda": _safe(info, "ebitda"),
            "net_income": _safe(info, "netIncomeToCommon"),
            "book_value": _safe(info, "bookValue") * _safe(info, "sharesOutstanding"),
            "total_debt": _safe(info, "totalDebt", default=0.0),
            "cash": _safe(info, "totalCash", default=0.0),
            "interest_expense": abs(_from_statement(inc, "Interest Expense")),
            "tax_rate": float(np.clip(tax_rate, 0.0, 0.45)),
        }
        if i % 10 == 0:
            print(f"  fetched {i}/{len(tickers)}")

    df = pd.DataFrame(rows).T
    for c in df.columns:
        if c != "sector":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df.to_parquet(key)
    print(f"cached {len(df)} companies to {key.name}")
    return df


def estimate_betas(tickers, benchmark, years, offline=False):
    """Levered beta from a monthly regression against the benchmark.

    yfinance reports a beta, but it does not say over what window or against
    what index. Estimating it here means the number is reproducible and its
    window is stated.
    """
    if offline:
        rng = np.random.default_rng(1)
        return pd.Series(rng.uniform(0.6, 1.8, len(tickers)), index=tickers)

    config.CACHE_DIR.mkdir(exist_ok=True)
    key = config.CACHE_DIR / f"betas_{len(tickers)}_{years}y.parquet"
    if key.exists():
        print(f"cache hit: {key.name}")
        return pd.read_parquet(key)["beta"]

    import yfinance as yf

    print(f"downloading {years}y of prices for beta...")
    raw = yf.download(
        list(tickers) + [benchmark], period=f"{years}y", interval="1mo",
        auto_adjust=True, progress=False,
    )
    px = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    rets = px.pct_change().dropna(how="all")

    if benchmark not in rets.columns:
        sys.exit(f"no benchmark data for {benchmark}")
    mkt = rets[benchmark]
    var = mkt.var()

    out = {}
    for t in tickers:
        if t not in rets.columns:
            continue
        pair = pd.concat([rets[t], mkt], axis=1).dropna()
        if len(pair) < config.BETA_MIN_MONTHS or var == 0:
            continue
        raw = pair.iloc[:, 0].cov(pair.iloc[:, 1]) / var
        adj = config.BLUME_WEIGHT * raw + (1.0 - config.BLUME_WEIGHT) * 1.0
        out[t] = float(np.clip(adj, config.BETA_FLOOR, config.BETA_CAP))

    s = pd.Series(out, name="beta")
    s.to_frame().to_parquet(key)
    print(f"estimated {len(s)} betas")
    return s


def synthetic_fundamentals(tickers):
    """Deterministic fake statements so the pipeline runs without network."""
    rng = np.random.default_rng(0)
    sectors = ["Technology", "Healthcare", "Financials", "Consumer", "Energy",
               "Industrials", "Materials", "Utilities", "Real Estate"]
    rows = {}
    for t in tickers:
        rev = rng.uniform(5e9, 4e11)
        margin = rng.uniform(0.08, 0.35)
        shares = rng.uniform(3e8, 8e9)
        mcap = rev * rng.uniform(1.5, 8.0)
        rows[t] = {
            "sector": sectors[hash(t) % len(sectors)],
            "price": mcap / shares,
            "market_cap": mcap,
            "shares_outstanding": shares,
            "revenue": rev,
            "revenue_growth": rng.uniform(-0.02, 0.20),
            "ebit": rev * margin,
            "ebitda": rev * (margin + 0.05),
            "net_income": rev * margin * 0.75,
            "book_value": mcap * rng.uniform(0.15, 0.7),
            "total_debt": rev * rng.uniform(0.05, 0.8),
            "cash": rev * rng.uniform(0.02, 0.3),
            "interest_expense": rev * rng.uniform(0.002, 0.02),
            "tax_rate": rng.uniform(0.12, 0.28),
        }
    return pd.DataFrame(rows).T.infer_objects()


# ---------------------------------------------------------------- valuation


def clean(fin):
    """Drop companies the model cannot value, and say how many and why."""
    n0 = len(fin)
    fin = fin.dropna(subset=["price", "market_cap", "revenue", "ebit",
                             "shares_outstanding"])
    fin = fin[(fin["revenue"] > 0) & (fin["market_cap"] > 0)
              & (fin["shares_outstanding"] > 0)]
    dropped = n0 - len(fin)
    if dropped:
        print(f"dropped {dropped} of {n0} companies for missing or invalid data")
    return fin


def value_universe(fin, betas, args):
    multiples = comps.compute_multiples(fin)
    rows = {}

    for t in fin.index:
        row = fin.loc[t]
        beta = float(betas.get(t, 1.0))

        try:
            out = dcf_model.value_company(
                row, beta=beta,
                risk_free=args.risk_free,
                equity_risk_premium=args.erp,
                terminal_growth=args.terminal_growth,
                forecast_years=config.FORECAST_YEARS,
                reinvestment_rate=config.REINVESTMENT_RATE,
            )
            res = out["result"]
            dcf_ps, terminal_share = res.value_per_share, res.terminal_share
            wacc_used = res.wacc
            # A non-positive DCF is a numerical artifact, not a valuation.
            if not np.isfinite(dcf_ps) or dcf_ps <= 0:
                dcf_ps, terminal_share = np.nan, np.nan
        except Exception:
            dcf_ps, terminal_share, wacc_used = np.nan, np.nan, np.nan

        try:
            peers = comps.peer_group(
                fin, t,
                size_tolerance=config.PEER_SIZE_TOLERANCE,
                min_peers=config.MIN_PEERS,
            )
            stats = comps.peer_statistics(multiples, peers)
            comp_vals = comps.implied_value(row, stats)
            comp_vals = pd.Series(comp_vals) if not isinstance(comp_vals, pd.Series) else comp_vals
        except Exception:
            peers, comp_vals = [], pd.Series(dtype=float)

        comps_median = comp_vals.dropna().median() if len(comp_vals) else np.nan
        fair = report.blend(dcf_ps, comp_vals, dcf_weight=args.dcf_weight)

        gap = np.nan
        if not np.isnan(dcf_ps) and not np.isnan(comps_median) and comps_median:
            gap = dcf_ps / comps_median - 1.0

        rec = {
            "sector": row["sector"],
            "price": row["price"],
            "dcf_value": dcf_ps,
            "comps_value": comps_median,
            "fair_value": fair,
            "upside": report.upside(fair, row["price"]),
            "wacc": wacc_used,
            "beta": beta,
            "terminal_share": terminal_share,
            "peer_count": len(peers),
            "dcf_vs_comps_gap": gap,
        }
        rec["dcf_failed"] = bool(np.isnan(dcf_ps))
        rec["confidence"] = report.confidence_flag(pd.Series(rec))
        if rec["dcf_failed"]:
            # No DCF means no blended view, only a comps read. Rank it, but
            # never at high confidence, and label why.
            rec["confidence"] = "low"
        rows[t] = rec

    return pd.DataFrame(rows).T


# ---------------------------------------------------------------- reporting


def write_outputs(results, meta, args):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    config.RESULTS_DIR.mkdir(exist_ok=True)
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(config.RESULTS_DIR / "valuations.csv")

    ranked = report.rank_universe(results).dropna(subset=["upside"])
    # The headline table is the blended view, so it needs both methods.
    ranked = ranked[~ranked["dcf_failed"].astype(bool)]
    num = ["price", "dcf_value", "comps_value", "fair_value", "upside", "wacc", "beta"]
    disp = ranked[["sector"] + num + ["confidence"]].copy()
    for c in num:
        disp[c] = pd.to_numeric(disp[c], errors="coerce")
    disp["upside"] = (disp["upside"] * 100).round(1).astype(str) + "%"
    disp["wacc"] = (disp["wacc"] * 100).round(1).astype(str) + "%"
    for c in ["price", "dcf_value", "comps_value", "fair_value"]:
        disp[c] = disp[c].round(2)
    disp["beta"] = disp["beta"].round(2)

    top = disp.head(config.TOP_N)
    bottom = disp.tail(10)

    lines = ["# Valuation Results", "", "Generated by `run_results.py`.", "",
             "## Run parameters", ""]
    lines += [f"- **{k}:** {v}" for k, v in meta.items()]
    lines += ["", f"## Most undervalued ({config.TOP_N})", "", top.to_markdown(),
              "", "## Most overvalued (10)", "", bottom.to_markdown(),
              "", "## Confidence distribution", "",
              results["confidence"].value_counts().to_frame("count").to_markdown(), ""]
    (config.RESULTS_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    # DCF versus comps scatter. Agreement is the diagonal.
    fig, ax = plt.subplots(figsize=(8, 8))
    d = results.dropna(subset=["dcf_value", "comps_value"])
    colors = {"high": "tab:green", "medium": "tab:orange", "low": "tab:red"}
    for conf, grp in d.groupby("confidence"):
        ax.scatter(grp["comps_value"], grp["dcf_value"], s=28, alpha=0.75,
                   label=f"{conf} confidence", color=colors.get(conf, "grey"))
    lim = float(np.nanpercentile(
        pd.concat([d["comps_value"], d["dcf_value"]]).astype(float), 97))
    ax.plot([0, lim], [0, lim], "k--", linewidth=1, label="agreement")
    ax.set_xlim(0, lim); ax.set_ylim(0, lim)
    ax.set_xlabel("Comparables value per share")
    ax.set_ylabel("DCF value per share")
    ax.set_title("DCF versus comparables, by confidence flag")
    ax.legend(frameon=False); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / "dcf_vs_comps.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    u = pd.to_numeric(results["upside"], errors="coerce").dropna() * 100
    ax.hist(u.clip(-100, 200), bins=40, color="tab:blue", alpha=0.8)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel("Implied upside to fair value (%)")
    ax.set_ylabel("Companies")
    ax.set_title("Distribution of implied upside")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / "upside_distribution.png", dpi=150)
    plt.close(fig)

    print(f"\nwrote {config.RESULTS_DIR / 'summary.md'}")
    print(f"wrote {config.FIGURES_DIR / 'dcf_vs_comps.png'}")
    print("\n" + "=" * 70)
    print("PASTE THIS INTO THE README RESULTS SECTION")
    print("=" * 70 + "\n")
    print(top.head(10).to_markdown())
    print()
    print(results["confidence"].value_counts().to_frame("count").to_markdown())
    print("\n![DCF versus comparables](docs/images/dcf_vs_comps.png)\n")


# ------------------------------------------------------------------- driver


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--risk-free", type=float, default=config.RISK_FREE)
    ap.add_argument("--erp", type=float, default=config.EQUITY_RISK_PREMIUM)
    ap.add_argument("--terminal-growth", type=float, default=config.TERMINAL_GROWTH)
    ap.add_argument("--dcf-weight", type=float, default=config.DCF_WEIGHT)
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    if args.offline:
        print("OFFLINE MODE: synthetic data. The numbers are meaningless.\n")
        fin = synthetic_fundamentals(config.UNIVERSE)
    else:
        fin = fetch_fundamentals(config.UNIVERSE)

    fin = clean(fin)
    betas = estimate_betas(list(fin.index), config.BENCHMARK,
                           config.BETA_YEARS, offline=args.offline)
    print(f"\nvaluing {len(fin)} companies...")

    results = value_universe(fin, betas, args)
    valued = results["fair_value"].notna().sum()
    print(f"produced a fair value for {valued} of {len(results)}")

    meta = {
        "Universe": f"{len(results)} large cap US companies",
        "Risk free rate": f"{args.risk_free:.2%}",
        "Equity risk premium": f"{args.erp:.2%}",
        "Terminal growth": f"{args.terminal_growth:.2%}",
        "Forecast horizon": f"{config.FORECAST_YEARS} years, damped growth",
        "Reinvestment rate": f"{config.REINVESTMENT_RATE:.0%} of NOPAT",
        "Beta": (f"{config.BETA_YEARS}y monthly regression against "
                 f"{config.BENCHMARK}, Blume adjusted "
                 f"({config.BLUME_WEIGHT} raw + {1 - config.BLUME_WEIGHT:.2f} toward 1.0), "
                 f"clipped to [{config.BETA_FLOOR}, {config.BETA_CAP}]"),
        "WACC floor": f"{config.WACC_FLOOR:.2%}",
        "Excluded from ranking": ("companies with a non-positive or missing DCF; "
                                  "they remain in valuations.csv flagged dcf_failed"),
        "Blend": f"{args.dcf_weight:.0%} DCF, {1 - args.dcf_weight:.0%} comparables median",
        "Peer selection": (f"same sector, market cap within "
                           f"{config.PEER_SIZE_TOLERANCE}x, minimum "
                           f"{config.MIN_PEERS} peers"),
        "Data source": "Synthetic" if args.offline else "yfinance statements and prices",
        "Interpretation": ("a screen for manual review, not price targets. "
                           "See the confidence column."),
    }

    write_outputs(results, meta, args)


if __name__ == "__main__":
    main()
