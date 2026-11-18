# Alpine Quantamental Investment

A Quarto website that publishes the latest signals and backtest results for three systematic strategies:

- **Global Equity Rotation:** weekly multi-factor long / short across 30 country ETFs
- **Gold Trend:** daily long / flat trend model on gold
- **Bitcoin Trend:** daily long / flat trend model on BTC/USD

The repository holds only the website and the **output data** it displays (`data/`). Strategy code is kept private.

## Layout

```
_quarto.yml            site settings, navbar, theme
index.qmd              overview page with the current signal for each strategy
strategies/*.qmd       one page per strategy: Latest signal · Backtest · How it works
journal.qmd, posts/    journal entries
about.qmd              methodology notes and disclaimer
site_helpers.py        charts, tables and stat tiles (Plotly + pandas)
data/                  published outputs (latest signal files, backtest series, meta.json)
```

## Data files

| File | Contents |
|---|---|
| `meta.json` | as-of dates and current positions |
| `btc_signals.csv`, `gold_signals.csv` | rows from the latest production signal file |
| `dca_signals.csv` | latest country ranking with factor scores and positions |
| `btc_backtest.csv`, `gold_backtest.csv` | daily growth of $1: strategy vs buy-and-hold |
| `dca_backtest_weekly_returns.csv` | weekly net returns of the strategy |

## Update the site

1. Refresh the files in `data/`.
2. Preview locally with `quarto preview` (needs Python with the packages in `requirements.txt`).
3. Commit and push to `main`. GitHub Actions renders the site and deploys it to GitHub Pages.

One-time setup: in the repo, go to **Settings → Pages → Source** and select **GitHub Actions**.

## Disclaimer

For informational and educational purposes only. Not investment advice. Backtests are hypothetical.
