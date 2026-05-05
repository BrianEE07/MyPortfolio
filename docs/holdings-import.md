# Holdings Import

## Purpose
This project uses local import and build flows to update public portfolio data without putting broker credentials or raw export files into the public site or deployment workflow.

## Source Of Truth
- `data/holdings.json` is the only canonical holdings file used by the app
- `data/portfolio_metrics.json` is the generated companion file for realized-performance metrics
- `data/portfolio_snapshots.json` is the generated public daily portfolio summary file
- `imports/` is a local-only input area for manual source files
- files under `imports/` are ignored by git and are not part of deployment

For v1.4.0 and later, the preferred full portfolio refresh command is `scripts/build_portfolio_data.py`. It rebuilds holdings, realized metrics, portfolio metrics, daily snapshots, and optional static output from one source. `scripts/import_holdings.py` remains useful for legacy canonical holdings previews and simple holdings-only validation.

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

Preferred Firstrade full refresh:

```bash
python3 scripts/build_portfolio_data.py \
  --firstrade-csv imports/firstrade/FT_CSV_91323853.csv \
  --refresh-prices \
  --build-output docs/index.html
```

Legacy Firstrade import path:

```bash
python3 scripts/import_holdings.py imports/firstrade/FT_CSV_91323853.csv --source-type firstrade_csv
```

Firstrade imports now run through the canonical transaction engine and refresh:

- `data/holdings.json`
- `data/portfolio_metrics.json`
- `data/portfolio_snapshots.json`

Canonical CSV and JSON imports refresh holdings and reset generated metrics. They do not rebuild daily portfolio snapshots.

For the v1.4.0 private transaction pipeline that can regenerate public holdings, metrics, and portfolio snapshots from `private/transactions.json`, see [data-foundation.md](data-foundation.md).

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
- Firstrade import currently supports trade rows with `BUY` and `SELL`, plus first-version cash rows such as deposits, withdrawals, fees, and interest when routed through the transaction engine
- Non-trade financial rows are validated by the adapter; unsupported broker events should fail clearly or remain out of the generated public files
- Firstrade import also calculates:
  - `realized_pl`
  - `realized_return_pct`
  - `twr`
  - `irr`
  - `cagr`
  - `current_drawdown`
  - `max_drawdown`
  - `sharpe`
  - `alpha`
  - `beta`
- Realized return is calculated as cumulative realized P/L divided by the cumulative cost basis of sold shares
- Sell-side commission and fee reduce realized results
- Canonical CSV and canonical JSON imports reset generated realized metrics to `null`
- invalid rows fail the entire import
- invalid imports do not overwrite the existing canonical JSON or generated metrics files

## Security Notes
- Keep local source files under `imports/`
- Do not commit `.env`, API keys, certificates, or raw account exports
- Only generated files under `data/` should be treated as canonical runtime data
