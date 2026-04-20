# Codebase Review

## Project Overview
This repository is a modular Flask application with two supported runtime paths:

- local serving through Flask for interactive review
- static HTML export under `docs/` for GitHub Pages deployment

The original refactor goals from `v1.0.0` and `v1.1.0` have largely landed. The current codebase centers on a canonical holdings source, a generated companion metrics file, and a snapshot-driven UI with responsive overview and details tabs.

## Current Architecture
The main responsibilities are now separated into these layers:

- `portfolio_app/holdings.py` for canonical holdings schema validation, normalization, and persistence
- `portfolio_app/holdings_import.py` for local source import flows and broker-specific normalization
- `portfolio_app/market_data.py` for external market data access and cache-oriented helpers
- `portfolio_app/snapshot.py` for portfolio calculations and view-model assembly
- `portfolio_app/web.py` plus templates and static assets for Flask routes, static export, and frontend rendering

`portfolio.py` remains a thin wrapper around the modular app package so the repo keeps a stable CLI surface for serve and export workflows.

## Main Files And Responsibilities
### `portfolio.py`
Thin CLI entrypoint for local serving and static export.

### `portfolio_app/config.py`
Shared paths, runtime constants, tab definitions, and site-level defaults.

### `portfolio_app/holdings.py`
Canonical holdings schema validation, JSON persistence, and canonical CSV conversion.

### `portfolio_app/holdings_import.py`
Local source import entrypoint for canonical CSV, canonical JSON, and Firstrade transaction CSV inputs. This module also writes generated realized-performance metrics to `data/portfolio_metrics.json`.

### `portfolio_app/snapshot.py`
Builds the snapshot used by templates and static export, including overview cards, holdings detail rows, chart payloads, and footer metadata.

### `portfolio_app/market_data.py`
Fetches and formats market prices, technical indicators, benchmark metrics, and macro sentiment inputs.

### `portfolio_app/web.py`
Defines Flask routes, asset versioning, and static export behavior.

### `scripts/import_holdings.py`
CLI wrapper for local holdings imports and optional post-import static rebuilds.

### `tests/test_holdings_import.py`
Focused coverage for canonical imports, Firstrade normalization, realized-metrics generation, and failure safety.

### `tests/test_snapshot.py`
Focused coverage for overview snapshot assembly and generated metrics fallbacks.

## Runtime Data Boundaries
- `data/holdings.json` is the canonical holdings file used at runtime
- `data/portfolio_metrics.json` is a generated companion file for realized-performance metrics
- `imports/` is a local-only source area for raw files and should stay outside deployment concerns

This keeps the public runtime model minimal while still allowing richer local ingestion logic.

## Current Technical Debt
- `portfolio_app/market_data.py` still concentrates multiple upstream integrations and parsing strategies in one module
- `portfolio_app/snapshot.py` has become the highest-coupling assembly layer and will keep growing unless future UI sections extract smaller view-model helpers
- Frontend behavior in `portfolio_app/static/app.js` now coordinates tabs, tooltips, sorting, symbol-link reveals, and chart relayout, which is practical today but increasingly dense
- Static output under `docs/` remains necessary for deployment, but it also creates review noise whenever UI changes are rebuilt

## Maintainability Risks
- Broker exports will continue to drift in format, so adapter-specific normalization should stay isolated inside the import layer instead of leaking into snapshot or template logic
- Responsive UI fixes can regress quietly because some issues only appear during tab switches, orientation changes, or device-specific viewport behavior
- Generated runtime data in `data/` can become stale if local import flows and manual edits are mixed without a clear operating habit

## Recommended Near-Term Maintenance Focus
- Keep one canonical holdings schema and continue treating `data/holdings.json` as the single runtime source of truth
- Preserve `data/portfolio_metrics.json` as a generated companion output rather than expanding the canonical holdings schema
- Add small, focused tests whenever overview card behavior, import normalization, or responsive rendering logic changes
- Prefer updating version notes and operational docs alongside implementation changes so release behavior stays traceable without relying only on commit history
