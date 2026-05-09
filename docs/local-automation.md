# Local Portfolio Update Flow

This project keeps private broker exports on this machine and publishes only generated portfolio summaries.

## Recommended Flow

1. Put the latest Firstrade account history CSV under `imports/firstrade/`.
2. Rebuild public data and static output locally:

```bash
python3 scripts/build_portfolio_data.py \
  --firstrade-csv imports/firstrade/FT_CSV_91323853.csv \
  --refresh-prices \
  --build-output docs/index.html
```

3. Verify the project:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile portfolio.py
PYTHONPATH=. .venv/bin/pytest
```

4. Commit and push the generated public files.
5. GitHub Actions deploys the committed public output to GitHub Pages.

## What Stays Local

These paths stay ignored and should not be committed:

- `imports/`
- `private/`
- `secrets/`

Raw broker CSV files and canonical private transactions should stay there. Do not put them in the public repository.

## What Gets Published

The public site uses generated and intentionally public files:

- `data/holdings.json`
- `data/portfolio_metrics.json`
- `data/portfolio_snapshots.json`
- `data/watchlist.json`
- `docs/index.html`
- `docs/static/`

## GitHub Actions Boundary

GitHub Actions currently runs `python portfolio.py --output docs/index.html` and deploys `docs/`. That step can refresh display-time market data, but it does not rebuild transaction-derived snapshots because the raw transaction CSV is not available in the public repository.

Keeping snapshot generation local protects private trading history while still allowing the deployed site to show updated public summary data.
