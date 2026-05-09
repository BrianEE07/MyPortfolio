# Wei's Portfolio

[Portfolio site](https://portfolio.weiweifan.com)

Wei's Portfolio is a personal investment dashboard that publishes a clean, public view of a private portfolio. It combines generated portfolio data, live local market overlays, market pulse panels, stock details, and a lightweight watchlist for stocks worth tracking.

The project is designed around a privacy boundary: raw broker exports, transaction records, local notes, and secrets stay on the local machine. The repo only keeps public-safe generated data and static site output.

Credit to the original reference project: [huangchink/portfolio](https://github.com/huangchink/portfolio).

## What It Shows

- Holdings overview, total value, cash, cost basis, unrealized and realized P&L.
- Top holdings, concentration, stock detail table, valuation, drawdown, trend, and P&L.
- Watchlist table with price, trailing P/E, forward P/E, one-year drawdown, and alert signals.
- Market pulse panels for sentiment, S&P 500 trend, estimated trailing P/E, VIX, put/call, and margin data.
- Project roadmap modal documenting completed milestones and upcoming work.

## Project Shape

- `portfolio.py`: thin CLI wrapper for serving or exporting the site.
- `portfolio_app/`: Flask app, data loading, snapshot assembly, market data access, templates, and static assets.
- `data/`: public-safe generated JSON used by the runtime and static site.
- `docs/`: GitHub Pages output and project documentation.
- `scripts/`: local import/build helpers.
- `imports/` and `private/`: local-only source material, ignored by git.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the local server:

```bash
PORT=5002 .venv/bin/python portfolio.py --serve
```

Open [http://localhost:5002](http://localhost:5002). The health check is available at [http://localhost:5002/health](http://localhost:5002/health).

## Static Export

Generate the GitHub Pages HTML output:

```bash
.venv/bin/python portfolio.py --output docs/index.html
```

## Portfolio Data Refresh

Keep raw Firstrade CSV files local under `imports/firstrade/`. To rebuild public-safe portfolio data from the latest CSV:

```bash
.venv/bin/python scripts/build_portfolio_data.py \
  --firstrade-csv imports/firstrade/FT_CSV_91323853.csv \
  --refresh-prices \
  --build-output docs/index.html
```

This updates generated public files such as `data/holdings.json`, `data/portfolio_metrics.json`, `data/portfolio_snapshots.json`, and `docs/index.html`. Do not commit raw broker exports or `private/transactions.json`.

## Verification

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile portfolio.py
PYTHONPATH=. .venv/bin/pytest
.venv/bin/python portfolio.py --output docs/index.html
```

## More Docs

- [Holdings import](docs/holdings-import.md)
- [Data foundation](docs/data-foundation.md)
- [Local automation](docs/local-automation.md)
- [Project roadmap](docs/project-roadmap.md)
