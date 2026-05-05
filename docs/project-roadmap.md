# Project Roadmap

Last updated: 2026-05-05

This document records the intended direction after v1.4.0. The goal is to keep the project architecture simple, explicit, and easy to extend while the product grows from a portfolio dashboard into a broader portfolio analysis system.

## Product North Star

The project should become a clean personal investment analysis site with:

- clear folder boundaries between data ingestion, calculations, view models, templates, and frontend behavior
- support for multiple asset classes, including ETF, Taiwan stocks, US stocks, crypto, and investment cash
- historical portfolio snapshots as the foundation for performance, risk, allocation, and rebalance logic
- interactive views that can be filtered by asset class
- static-site deployment that remains simple to update

## Suggested Major Update Order

Completed baseline:

- **Data Pipeline & Snapshot Foundation**
  v1.4.0 added local canonical transactions, Firstrade-to-transaction generation, public daily portfolio snapshots, total portfolio value, cash balance, TWR, IRR, CAGR, drawdown, Sharpe, Alpha, and Beta.

Next major updates:

1. **Investment Overview 2.0**
   Upgrade the current overview page after the historical portfolio data model is strong enough to support real portfolio health metrics.

2. **Allocation & Rebalancing System**
   Add target allocation, cash allocation, drift, rebalance status, and rebalance hints after portfolio value and asset classification are stable.

3. **Positions 2.0**
   Expand holdings details into a multi-asset positions page that supports ETF, Taiwan stocks, US stocks, and crypto without forcing every asset into stock-specific fields.

4. **Settings & Dynamic View**
   Add a full settings panel and asset-class filters after multi-asset data exists, so filtering can update the entire site meaningfully.

5. **Market Pulse 2.0**
   Expand the current market observation page into sentiment, trend, valuation, macro, dip signals, news, and external project links.

6. **UI Polish & Documentation**
   Finalize visual polish, fake data scenarios, README, implementation notes, design decisions, and the Codex experience-sharing article.

## Major Update 1: Investment Overview 2.0

Rename `Holdings Overview` to `Investment Overview` and turn it from a holdings summary into a true portfolio overview page.

Planned direction:

- Split the top area into **Portfolio Summary / 投組總覽** and **Risk Analysis / 風險分析**
- Build on the v1.4.0 cash and total-value cards with a clearer portfolio value trend
- Keep one return vocabulary: `Portfolio YTD` displays `TWR`; `IRR` is the money-weighted return; `CAGR` remains the period annualized growth rate
- Extend portfolio-level drawdown metrics with `Drawdown Duration`
- Continue refining `Sharpe`, `Alpha`, and `Beta` from historical portfolio snapshots instead of current-holdings estimates
- Support total Taiwan / US Alpha and Beta, plus separate Taiwan-stock and US-stock Alpha / Beta
- Keep `Top 10 Holdings`
- Add asset-class allocation and core / satellite allocation visuals
- Optional: add a portfolio value trend chart

## Major Update 2: Allocation & Rebalancing

Build target allocation and rebalance logic so the site can judge whether the current portfolio has drifted away from the long-term strategy.

Planned direction:

- Add target allocations such as `0050 / VTI / VXUS / 個股 / 加密貨幣`
- Show `Current Allocation vs Target Allocation`
- Add `Drift`
- Add `Rebalance Status`, such as `On Track / Watch / Rebalance Needed`
- Add `Rebalance Hint` that suggests which asset class should be funded first
- Support two rebalance views:
  - cash-aware rebalance, including investment cash
  - invested-assets-only rebalance
- Decide the best allocation chart style, such as pie chart, stacked bar, progress bar, or allocation grid

## Major Update 3: Positions 2.0

Rename `Stock Details` to `Positions / 持倉明細` and make it support multiple asset classes.

Planned direction:

- Rename `Stock Details` to `Positions / 持倉明細`
- Show sub-tabs based on enabled asset classes from Settings
- Candidate sub-tabs:
  - `All`
  - `ETF`
  - `Taiwan Stocks`
  - `US Stocks`
  - `Crypto`
- Use asset-class-specific fields instead of forcing crypto and other assets into stock-only columns
- Make values, sorting, classification, and filtering respond to global asset-class filters
- Optional: add a watchlist with decision criteria, such as technical-line breakdowns or buy-zone notes
- Optional: add a recent buy / sell banner

## Major Update 4: Market Pulse 2.0

Expand `Market Pulse` from sentiment and technical observation into a broader market environment page.

Planned direction:

- Keep the current three core blocks:
  - `Market Sentiment`
  - `Market Trend`
  - `Dip-Buying Indicators`
- Add Macro / Valuation indicators:
  - `Fed Funds Rate`
  - `10Y Treasury Yield`
  - `CPI / Inflation`
  - `Earnings Yield`
  - `Equity Risk Premium`
  - `USD Index / DXY`
- Reclassify indicators into groups:
  - Sentiment / 市場情緒
  - Trend / 技術趨勢
  - Valuation / 市場估值
  - Macro / 總經環境
  - Dip Signals / 抄底訊號
- Give every indicator clear Chinese / English explanations and tooltips
- Add latest market news summaries with source links
- Add an external link to the separate 股癌 podcast summary project

## Major Update 5: Settings & Dynamic View

Turn the current light / dark toggle area into a full settings entry point.

Planned direction:

- Replace the current theme toggle position with a `Settings` entry
- Keep Light / Dark Mode inside Settings
- Add Asset Class Filters:
  - ETF
  - Taiwan Stocks
  - US Stocks
  - Crypto
- Make filters dynamically update:
  - Investment Overview values
  - Allocation charts
  - Risk metrics
  - Positions sub-tabs
  - Market value / portfolio value
  - Rebalance hints
- This should shift the site from a fixed dashboard into an interactive portfolio analysis view

## Major Update 6: Data Pipeline & Automation

Build a durable data pipeline so portfolio updates become low-friction.

Planned direction:

- Support importing historical transactions from:
  - Taiwan stock CSV
  - US stock CSV
  - Firstrade CSV
  - Crypto transaction CSV
  - On-chain or wallet data
- Rebuild from transaction data:
  - current holdings
  - cost basis
  - realized P&L
  - historical snapshots
  - TWR / MWR / IRR / CAGR
  - drawdown metrics
- Establish the snapshot system as the foundation for historical portfolio analytics
- Support manual trigger or periodic scan after CSV updates
- Automatically regenerate the static site after data import
- Final target: manually update CSV, then the system updates snapshots and deploys the site
- Build fake data / demo data / preview environments covering ETF, Taiwan stocks, US stocks, crypto, cash, multiple markets, and multiple currencies

## Major Update 7: UI Polish & Documentation

After the product capabilities settle, polish the interface and document the project as a mature product.

Planned direction:

- Polish:
  - card hierarchy
  - chart style
  - tooltip style
  - settings panel
  - mobile layout
  - tab / sub-tab interactions
- Unify Chinese / English naming, tooltip tone, and indicator explanation format
- Add fake-data visual tests for multiple scenarios
- Organize project records:
  - version notes
  - implementation log
  - design decisions
  - data pipeline notes
- Write a final README covering:
  - project goals
  - feature overview
  - data sources
  - import flow
  - metric definitions
  - deployment
  - update flow
- Prepare the Codex experience-sharing article:
  - title: **初嚐 Codex 的威力，全靠 AI Agent 從零到一的首個個人專案**
  - include how Codex helped build the first usable version
  - include a concrete feature-change example
  - preserve useful prompts, Plan Mode plans, and before / after screenshots

## Current Architecture Notes

Current structure after v1.3.4:

- `portfolio.py` is a thin wrapper.
- `portfolio_app/web.py` owns Flask routes, static export, and asset copying.
- `portfolio_app/holdings.py` owns the current canonical holdings schema: `symbol`, `shares`, `cost_basis`.
- `portfolio_app/holdings_import.py` owns current import normalization, mostly canonical JSON / CSV and Firstrade CSV.
- `portfolio_app/market_data.py` is the main external-data module and currently includes Yahoo, CNN, Multpl, FINRA fetching, parsing, formatting, and caching.
- `portfolio_app/snapshot.py` is the main view-model assembly module and currently includes many formatting helpers, portfolio calculations, market-signal view models, and page data assembly.
- `portfolio_app/templates/index.html` is still the single main template.
- `portfolio_app/static/app.js` contains tab behavior, chart rendering, tooltips, theme behavior, and gauge animation.
- `portfolio_app/static/styles.css` contains the full visual system and page-specific styling in one file.
- `docs/` contains generated static output plus version notes and project documentation.

Current architectural pressure points:

- `market_data.py` is doing too many jobs: external clients, response parsing, fallback data, caching, and some display formatting.
- `snapshot.py` is doing too many jobs: calculations, formatting, categorization, summary cards, market pulse view models, and final page assembly.
- The single `index.html` template will become hard to maintain once Investment Overview, Positions, Market Pulse, Settings, and sub-tabs grow.
- `app.js` will become hard to extend if charts, settings, filters, gauge behavior, and tab interactions keep living in one file.
- `styles.css` is already large and should eventually split into tokens, base layout, components, and page-specific modules.
- The current holdings schema is intentionally minimal, but future analytics require explicit transaction, snapshot, asset-class, cash, currency, benchmark, and target-allocation models.

## Future Architecture Direction

Keep the deployment flow simple, but introduce clearer module boundaries before the next large feature wave.

Potential future structure:

```text
portfolio_app/
  data_sources/
    yahoo.py
    cnn.py
    finra.py
    multpl.py
    fred.py
  ingestion/
    transactions.py
    firstrade.py
    taiwan_stock.py
    crypto.py
  models/
    holdings.py
    transactions.py
    snapshots.py
    allocation.py
    settings.py
  calculations/
    performance.py
    risk.py
    allocation.py
    rebalance.py
    market_signals.py
  view_models/
    investment_overview.py
    positions.py
    market_pulse.py
    settings.py
  templates/
    index.html
    components/
    tabs/
  static/
    app.js
    styles.css
```

This structure is a direction, not an immediate rewrite target. The preferred approach is still incremental extraction when a feature needs a boundary.

## Data Model Direction

The current canonical holdings file should stay stable until the transaction pipeline is ready. The next durable layer should add explicit source data instead of overloading holdings.

Likely future data files:

- `data/holdings.json`: current derived holdings or simple manual fallback
- `data/transactions/`: imported transaction history by source
- `data/snapshots/`: generated historical portfolio snapshots
- `data/allocation_targets.json`: target allocation and rebalance thresholds
- `data/settings.json`: public display settings and enabled asset classes
- `data/demo/`: fake data and preview scenarios

Key principle: raw private broker exports and secrets stay outside the repo; public derived data can be committed when intended for the site.

## Implementation Principles For Future Work

- Stabilize data boundaries before building UI that depends on them.
- Prefer derived view models over embedding business rules in templates.
- Keep static export and GitHub Pages deployment intact.
- Add tests around transaction normalization, snapshot generation, performance metrics, and rebalance logic before relying on them in UI.
- Avoid doing a full rewrite. Extract modules when a new feature would otherwise make `market_data.py`, `snapshot.py`, `app.js`, or `styles.css` significantly harder to reason about.
