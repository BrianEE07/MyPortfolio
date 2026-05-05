# Data Foundation

## Purpose
v1.4.0 introduces the first local transaction-to-public-data pipeline. The goal is to keep sensitive transaction history on this machine while generating only public portfolio summary files for the site.

## Private Inputs
Keep these files outside git:

- `private/transactions.json`
- `private/market_prices/`
- raw broker exports under `imports/`

`private/transactions.json` is the local canonical transaction file. It is intentionally ignored by git.

## Canonical Transaction Schema
All first-version transactions use USD and daily dates.

Shared fields:

```json
{
  "id": "2026-04-02-aapl-buy-1",
  "date": "2026-04-02",
  "account": "firstrade",
  "type": "BUY",
  "currency": "USD"
}
```

Trade fields for `BUY` and `SELL`:

```json
{
  "symbol": "AAPL",
  "quantity": 1.5,
  "price": 120.25,
  "fee": 0
}
```

Cash fields for `DEPOSIT`, `WITHDRAWAL`, and `FEE`:

```json
{
  "amount": 500
}
```

Supported transaction types:

- `BUY`
- `SELL`
- `DEPOSIT`
- `WITHDRAWAL`
- `FEE`
- `INTEREST`

`INTEREST` is treated as internal portfolio cash income. It increases portfolio cash but is not counted as an external deposit.

## Public Generated Outputs
The pipeline writes these repo-visible runtime files:

- `data/holdings.json`
- `data/portfolio_metrics.json`
- `data/portfolio_snapshots.json`

`data/holdings.json` keeps the existing schema:

```json
[
  {
    "symbol": "NVDA",
    "shares": 0.43347,
    "cost_basis": 173.02
  }
]
```

`data/portfolio_snapshots.json` stores portfolio-level daily summaries only:

```json
[
  {
    "date": "2026-04-02",
    "holdings_market_value": 1200.0,
    "portfolio_cash": 300.0,
    "total_portfolio_value": 1500.0,
    "invested_cost_basis": 1000.0,
    "unrealized_pl": 200.0,
    "realized_pl": 0.0,
    "net_external_cash_flow": 1500.0
  }
]
```

Metric values in `data/portfolio_metrics.json` use percentage numbers for return-style fields such as `twr`, `irr`, `cagr`, and drawdown fields. `Portfolio YTD` displays `twr`; `irr` is the money-weighted return.

## Price History
Optional local price history can be stored in `private/market_prices/prices.json`:

```json
{
  "AAPL": {
    "2026-04-02": 120.25,
    "2026-04-03": 123.1
  }
}
```

The snapshot builder uses the latest available price on or before each snapshot date. If a buy date does not have a market price, the trade price is used as the first fallback.

## Command
Generate public portfolio data from private transactions:

```bash
python3 scripts/build_portfolio_data.py
```

Generate public portfolio data directly from a Firstrade export through the same canonical transaction engine:

```bash
python3 scripts/build_portfolio_data.py \
  --firstrade-csv imports/firstrade/FT_CSV_91323853.csv
```

Refresh market prices while building from Firstrade:

```bash
python3 scripts/build_portfolio_data.py \
  --firstrade-csv imports/firstrade/FT_CSV_91323853.csv \
  --refresh-prices
```

Generate data and rebuild static output:

```bash
python3 scripts/build_portfolio_data.py \
  --firstrade-csv imports/firstrade/FT_CSV_91323853.csv \
  --refresh-prices \
  --build-output docs/index.html
```

Use temporary files for local preview without touching public runtime files:

```bash
python3 scripts/build_portfolio_data.py \
  --transactions private/transactions.json \
  --holdings-output /tmp/portfolio-holdings.json \
  --metrics-output /tmp/portfolio-metrics.json \
  --snapshots-output /tmp/portfolio-snapshots.json
```

## Current Limits
v1.4.0 intentionally does not model TWD, FX, dividends, taxes, transfers, stock splits, or full broker event coverage. Those should be added as adapter-style extensions after the USD transaction foundation is stable.

## Performance Metrics
The site now reads generated portfolio metrics instead of estimating `Portfolio YTD`, `Sharpe`, `Alpha`, and `Beta` from the current holdings list. If daily market price history or benchmark data is missing, those fields should stay `null` and render as `N/A` rather than showing a misleading current-holdings backtest.

Displayed overview metrics:

- `Portfolio YTD` displays generated `twr`, which neutralizes deposits and withdrawals.
- `IRR` is the single money-weighted return field and reflects when cash entered or left the portfolio.
- `CAGR` annualizes the full-period portfolio growth rate; it can look similar to `IRR` in a short, simple cash-flow history but is not the same formula.
- `Current Drawdown` and `Max Drawdown` come from daily total portfolio value snapshots.
