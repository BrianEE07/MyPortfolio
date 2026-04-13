# v1.0.0 Implementation Log

## Summary
This document records the first implementation pass of the approved v1.0.0 plan. The project was moved from a single-file prototype toward a maintainable application structure while preserving the existing Flask and static-export workflow.

## v1.0.1
### Scheduled Updates
- Updated [deploy-pages.yml](/Users/ywfan/Documents/Side_Projects/MySite/myportfolio/.github/workflows/deploy-pages.yml) to run one automatic GitHub Pages refresh per day.
- The new schedule is based on Taipei time:
  - `08:00 Asia/Taipei`
- The corresponding GitHub Actions cron entry was set to:
  - `00:00 UTC`
- `push` on `main` and `workflow_dispatch` remain available.
- No UI, data model, or application behavior was changed in this version.
- For ad-hoc refreshes, the recommended manual path remains GitHub Actions `Run workflow`.

## What Changed
### Data and Holdings
- Added canonical holdings input in [data/holdings.csv](/Users/ywfan/Documents/Side_Projects/MySite/myportfolio/data/holdings.csv).
- Added canonical holdings storage in [data/holdings.json](/Users/ywfan/Documents/Side_Projects/MySite/myportfolio/data/holdings.json).
- Added a reusable CSV-to-JSON import flow in [scripts/import_holdings.py](/Users/ywfan/Documents/Side_Projects/MySite/myportfolio/scripts/import_holdings.py).
- Defined the v1 holdings schema as `symbol`, `shares`, and `cost_basis`.

### Application Structure
- Reduced [portfolio.py](/Users/ywfan/Documents/Side_Projects/MySite/myportfolio/portfolio.py) to a thin CLI and app entry wrapper.
- Added `portfolio_app/` to separate configuration, holdings loading, market data access, snapshot assembly, templates, static assets, and Flask routing.
- Updated [Procfile](/Users/ywfan/Documents/Side_Projects/MySite/myportfolio/Procfile) to point to the new Flask app module.
- Expanded [requirements.txt](/Users/ywfan/Documents/Side_Projects/MySite/myportfolio/requirements.txt) to include the packages used directly by the code.

### UI and Information Architecture
- Replaced the one-page layout with three tabs:
  - `持倉總覽 / Holdings Overview`
  - `個股明細 / Stock Details`
  - `市場觀察 / Market Pulse`
- Introduced a new neutral theme with amber accent tokens.
- Added light mode as the default and a manual dark-mode toggle with saved preference.
- Removed the Buffett quote section, watchlist section, and strategy signal section from the main UI.
- Kept Fear & Greed and macro cards, but moved them into the dedicated `Market Pulse` tab.

### Static Output
- Generated the updated static site at [docs/index.html](/Users/ywfan/Documents/Side_Projects/MySite/myportfolio/docs/index.html).
- Added static assets under [docs/static](/Users/ywfan/Documents/Side_Projects/MySite/myportfolio/docs/static).

### Deployment Preparation
- Updated [deploy-pages.yml](/Users/ywfan/Documents/Side_Projects/MySite/myportfolio/.github/workflows/deploy-pages.yml) to deploy from the `main` branch through GitHub Pages Actions.
- Added [docs/CNAME](/Users/ywfan/Documents/Side_Projects/MySite/myportfolio/docs/CNAME) for the custom domain `portfolio.weiweifan.com`.
- Configured the local `origin` remote for the GitHub repository `BrianEE07/MyPortfolio`.
- Corrected the GitHub account typo during deployment setup and confirmed the remote now points to `BrianEE07`.

## Verification
- Python syntax check passed for the new application modules.
- The holdings import script completed successfully against the canonical CSV input.
- `GET /health` returned `200` with `{"status": "ok"}`.
- `GET /` returned `200`.
- Static export completed successfully with `python portfolio.py --output docs/index.html`.

## Notes
- During local verification in this environment, external market data providers were not reachable because DNS/network access was unavailable. The app still rendered successfully through fallback paths, which confirmed that the main UI and export flow do not crash when upstream data is unavailable.
