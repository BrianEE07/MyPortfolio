# Holdings Import

## Purpose
This project uses a local import flow to update holdings without putting broker credentials or raw export files into the public site or deployment workflow.

## Source Of Truth
- `data/holdings.json` is the only canonical holdings file used by the app
- `data/portfolio_metrics.json` is the generated companion file for realized-performance metrics
- `imports/` is a local-only input area for manual source files
- files under `imports/` are ignored by git and are not part of deployment

## Supported Source Types
- `canonical_csv`
- `canonical_json`
- `firstrade_csv`
- `auto` detection by file extension

The canonical holdings schema remains:

```json
[
  {
    "symbol": "NVDA",
    "shares": 0.43347,
    "cost_basis": 173.02
  }
]
```

## Commands
Import the default canonical CSV into `data/holdings.json`:

```bash
python3 scripts/import_holdings.py imports/holdings.csv
```

Import a canonical JSON file into `data/holdings.json`:

```bash
python3 scripts/import_holdings.py data/holdings.json --source-type canonical_json
```

Import and rebuild a static preview in one command:

```bash
python3 scripts/import_holdings.py imports/holdings.csv --build-output /tmp/portfolio-preview/index.html
```

Import a Firstrade Account History / Transactions CSV into canonical holdings:

```bash
python3 scripts/import_holdings.py imports/firstrade/FT_CSV_91323853.csv --source-type firstrade_csv
```

Each successful import also refreshes `data/portfolio_metrics.json`.

Preview the app with local-only holdings or metrics files without replacing the canonical runtime data:

```bash
PORTFOLIO_HOLDINGS_PATH=/private/tmp/preview-holdings.json \
PORTFOLIO_METRICS_PATH=/private/tmp/preview-portfolio-metrics.json \
PORT=5002 python3 portfolio.py --serve
```

Run the focused automated checks after import-related changes:

```bash
PYTHONPATH=. .venv/bin/pytest
```

## Validation Rules
- `symbol` is required and normalized to uppercase
- `shares` must be numeric
- `cost_basis` must be numeric and may include `$`
- Firstrade import currently supports `RecordType=Trade` rows with `BUY` and `SELL`
- Non-trade financial rows such as wire transfers are ignored during holdings reconstruction
- Firstrade import also calculates:
  - `realized_pl`
  - `realized_return_pct`
- Realized return is calculated as cumulative realized P/L divided by the cumulative cost basis of sold shares
- Sell-side commission and fee reduce realized results
- Canonical CSV and canonical JSON imports reset generated realized metrics to `null`
- invalid rows fail the entire import
- invalid imports do not overwrite the existing canonical JSON or generated metrics files

## Security Notes
- Keep local source files under `imports/`
- Do not commit `.env`, API keys, certificates, or raw account exports
- Only generated files under `data/` should be treated as canonical runtime data
