# Codebase Review

## Project Overview
This repository is now a modular Flask application that supports two runtime paths:

- local serving through Flask
- static HTML export for GitHub Pages deployment

v1.0.0 already separated the original prototype into clearer modules. The current v1.1.0 direction is to keep the UI and snapshot layer stable while making holdings updates easier and safer through local import flows.

## Current Architecture
The current structure is organized around four main layers:

- `portfolio_app/holdings.py` for canonical holdings schema validation and persistence
- `portfolio_app/market_data.py` for external market data access and caching
- `portfolio_app/snapshot.py` for portfolio calculations and view-model assembly
- `portfolio_app/web.py` plus templates and static assets for Flask routes and rendering

`portfolio.py` is now a thin wrapper that preserves the existing serve and static-export entrypoints.

## Main Files And Responsibilities
### `portfolio.py`
Thin CLI and application entry wrapper.

### `portfolio_app/config.py`
Shared paths and site-level constants.

### `portfolio_app/holdings.py`
Canonical holdings schema validation, optional local canonical CSV parsing, JSON loading, and JSON persistence.

### `portfolio_app/holdings_import.py`
Local source import entrypoint for supported holdings source types. This layer is the main extension point for future broker-specific adapters and now includes the first conservative Firstrade CSV adapter.

### `portfolio_app/snapshot.py`
Builds the snapshot used by the template from canonical holdings and external market data.

### `portfolio_app/market_data.py`
Fetches and caches prices, valuation data, and macro indicators.

### `portfolio_app/web.py`
Defines Flask routes and static export behavior.

### `scripts/import_holdings.py`
Local CLI for importing manual source files under `imports/` into canonical JSON and optionally rebuilding static output.

## Current Technical Debt
- `portfolio_app/market_data.py` still carries many responsibilities and multiple upstream integrations in one file
- The import layer is intentionally minimal and currently supports only canonical CSV and canonical JSON
- There is still no broker-specific adapter contract beyond the local source type boundary
- The repo only has focused import tests today; market data and snapshot logic still rely mostly on smoke verification

## Maintainability Risks
- Future broker exports will drift in column names and formatting unless adapter-specific normalization stays isolated from the canonical schema layer
- `snapshot.py` still assumes canonical `data/holdings.json` is always present locally; future multi-source or scheduled ingestion must keep that boundary explicit
- Generated static output under `docs/` can create review noise if rebuilds are mixed into unrelated code changes

## v1.1.0 Focus
The recommended low-risk path remains:

- keep one canonical holdings schema
- keep `data/holdings.json` as the single runtime source of truth
- import external files locally, not through the public website
- fail fast on invalid data and avoid partial writes
- keep broker credentials, raw exports, and local-only config outside the repo

This keeps the codebase easy to reason about while leaving room for future FT or 永豐專用 adapters without forcing a backend rewrite.
