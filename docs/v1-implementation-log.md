# v1.0.0 Implementation Log

## Summary
This document records the first implementation pass of the approved v1.0.0 plan. The project was moved from a single-file prototype toward a maintainable application structure while preserving the existing Flask and static-export workflow.

## v1.1.5
### Header Responsive Fixes
- Reordered the header actions so `Last updated` now appears before the theme toggle in both DOM order and visual layout.
- Kept `Last updated` on the left when the header actions sit side by side, and moved it above the theme toggle when the actions stack vertically.
- Added explicit text-size-adjust rules to reduce real-mobile browser font inflation that was not reproducible in desktop device emulation.
- Added a small-screen landscape header rule so phone landscape layouts keep the subtitle compact, allow it to wrap, and hide the separator instead of falling back to the desktop one-line treatment.

### Tooltip Interaction
- Reworked the help `?` tooltip behavior around a single active tooltip state instead of one-off show and hide calls.
- On touch screens, tapping a help chip now toggles that tooltip, tapping another chip switches the active tooltip, and tapping outside closes it.
- Added `Escape`, scroll, resize, and tab-switch cleanup so floating tooltips do not remain visible after the user changes context.
- Kept desktop hover and keyboard focus behavior intact.

### Stock Details Sorting
- Preserved the existing three-step sort cycle for sortable headers.
- Tightened the reset-to-default path so returning to `持倉市值 / Position Value` restores the active header styling and descending state cleanly.
- Limited the inactive hover tint to hover-capable pointers so touch devices no longer keep a previously tapped header looking active after the table resets to the default sort.

### Verification
- Rebuilt the static site successfully with `python3 portfolio.py --output docs/index.html`.
- Verified the Flask app still serves `GET /` and `GET /health` successfully.
- Confirmed the header action order, tooltip dismissal behavior, and stock-details reset styling in the rendered output.

## v1.1.3
### Mobile Header Cleanup
- Reworked the hero header so the title block remains primary while the theme toggle and update metadata stay pinned in the top-right.
- Replaced the old `Last Updated / 最後更新` card with a lighter English-only inline `Last updated` block.
- Right-aligned the update metadata and kept healthier spacing between the label and timestamp in both side-by-side and stacked layouts.
- On phone widths, the update value now splits into date and time lines to avoid overlapping the hero title.
- Kept `Wei's Portfolio` on a single line and reduced the mobile title scale slightly when space becomes tight.
- The eyebrow copy now behaves as:
  - desktop and tablet: `Portfolio Dashboard / 投資儀表板`
  - phone: `Dashboard / 投資儀表板`

### Theme Toggle
- Replaced emoji-based theme icons with monochrome inline SVG so mobile browsers no longer render the sun as a yellow emoji glyph.
- Tightened the toggle into a smaller, less attention-grabbing pill while preserving the existing light/dark behavior and active-state indicator.

### Bottom Floating Tabs
- Kept the top tab row for desktop, but restyled it into equal-width bookmark-style tabs with lower visual weight.
- Added a bottom floating tab control for tablet and mobile breakpoints with glass-like styling, safe-area-aware spacing, and bilingual labels.
- Hid the large top tab cards on smaller screens so overview summary cards appear earlier in the first viewport.
- Added extra bottom page padding on smaller screens so the floating navigation does not cover content while scrolling.
- Removed size-changing active states from both desktop and floating tabs to avoid left-right jitter while switching sections.
- Preserved a softer mixed-surface active fill on desktop tabs so the selected state stays visually distinct without the harsher page-background cutout.

### Verification
- Rebuilt the static site successfully with `python portfolio.py --output docs/index.html`.
- Verified the Flask app still serves `GET /` and `GET /health` successfully.
- Confirmed the rendered HTML includes both desktop and floating tab controls and uses the English-only `Last updated` label.

## v1.1.4
### Hero Progress Subtitle
- Reduced the `Wei's Portfolio` hero title to 80% of the previous visual size across desktop and mobile layouts.
- Replaced the fixed subtitle with a server-side progress line:
  - `邁向財富自由之路的第 X 天｜Y% · $CURRENT / $1,000,000`
- Defined `X` from the first US stock purchase date `2026-04-02`, with the start date counted as Day 1.
- Calculated progress from current total market value toward a fixed `USD 1,000,000` goal.
- Kept the subtitle Chinese-only and server-rendered, with no client-side calculation.
- Added a fallback subtitle when live pricing is unavailable:
  - `邁向財富自由之路的第 X 天｜進度暫不可用`
- Split the subtitle into structured lead/progress segments so desktop keeps a single line with a `｜` separator while phone layouts stack into two lines without the separator.

### Verification
- Rebuilt the static site successfully with `python portfolio.py --output docs/index.html`.
- Verified the Flask app still serves `GET /` and `GET /health` successfully.

## v1.1.2
### Stock Details Sorting
- Added client-side sorting to the `個股明細 / Stock Details` table without changing the route interface or holdings schema.
- Enabled sortable columns for:
  - `Symbol`
  - `Price`
  - `Avg Cost`
  - `Shares`
  - `Market Value`
  - `1Y Drawdown`
  - `Trailing P/E`
  - `Forward P/E`
  - `P&L`
- Kept `Trend` as a static, non-sortable column.
- Set the default table order to `Market Value` descending.
- Added a three-state interaction for sortable headers:
  - primary direction
  - reverse direction
  - reset to `Market Value` descending

### Rank Highlighting
- Updated the rank badge behavior so the top three rows are highlighted.
- Made the rank order follow the current visible sort order.
- Kept the top-three highlight only when the table is in the default `Market Value` descending state.

### UI Cleanup
- Fixed the duplicate top divider line in the details table and reduced it to a single line.
- Added active sort styling and lightweight sort indicators to the sortable headers while preserving the existing light/dark theme palette.
- Tightened column sizing for a more even table width distribution.
- Switched the trend pill copy to English-only labels:
  - `Above 250D`
  - `Below 250D`
- Added `$` to the live price column.
- Added compact hover help icons for harder-to-read columns such as drawdown, P/E, 250D trend, and P&L.
- Reduced the table width further so desktop review requires less horizontal movement.
- Changed the help icon from `!` to a smaller `?` and moved tooltip rendering to a floating layer so it is not clipped by the table container.
- Updated tooltip copy to concise bilingual text with Chinese first and English on a new line.
- Added tone coloring to `Price` and `1Y Drawdown`, while keeping `Avg Cost` neutral.
- Renamed the value column label from `市值 / Market Value` to `持倉市值 / Position Value` for clearer portfolio context.
- Compressed detail-number formatting for larger ranges:
  - four-digit prices drop to one decimal place
  - larger position values reduce decimals as the number grows
  - extreme drawdown values reduce decimals to avoid unnecessary width growth
- Adjusted detail formatting for `Shares` and `P&L` as well, so larger values do not expand the table unnecessarily.
- Swapped the `P&L` display hierarchy to show return percentage on the first line and unrealized dollar amount below it.
- Simplified the trend column title to `趨勢 / Trend` while leaving the pill and tooltip to explain the 250-day moving average context.
- Reworked tooltip content delivery to build line breaks in JavaScript, so bilingual help text renders as two lines instead of showing a literal `\n`.
- Rebalanced the detail table column widths to give `Symbol` more room while tightening denser numeric columns such as `Position Value`.
- Moved help icons slightly upward to align more closely with the Chinese header line and centered body values vertically for a cleaner table rhythm.
- Updated the `P&L` tooltip copy to explain return percentage before profit/loss amount, matching the visible value order.
- Reworked sortable help headers so the `?` icon sits inline beside the Chinese label while the sort arrow stays pinned on the far right.
- Replaced the text-based theme control with a smaller icon toggle for light/dark mode.
- Moved `1Y Drawdown` to the column immediately left of `Trend` to better match the intended reading order.
- Refined the theme toggle again into a tighter two-icon capsule so it stays compact on narrower layouts instead of stretching across the header.
- Nudged the inline `?` icons slightly further toward the upper-right to tighten header rhythm without affecting sort behavior.
- Narrowed `Trailing P/E`, `Forward P/E`, and `1Y Drawdown` further and reallocated that space to the `Symbol` column.
- Rebalanced the final header widths once more by giving `Forward P/E` a bit more room and tightening `P&L`, so the help icon and sort arrow no longer feel crowded.
- Shifted `0.5%` of width from `Symbol` to `Trend` as the final table-balance adjustment before the `v1.1.2` commit.
- Added content-hash query strings to exported `styles.css` and `app.js` URLs so GitHub Pages clients do not keep rendering stale cached assets after deployment.

### Verification
- Rebuilt the static site successfully with `python portfolio.py --output docs/index.html`.
- Verified the Flask app still serves `GET /` and `GET /health` successfully.

## v1.1.1
### Documentation Links
- Replaced repo-facing absolute filesystem links with GitHub-friendly relative Markdown links.
- Updated [README.md](../README.md) and [docs/v1-implementation-log.md](./v1-implementation-log.md) so linked files no longer point to machine-specific `/Users/...` paths.
- Kept the link style compatible with both local repo browsing and GitHub rendering.

### Stock Details UI
- Tightened the `個股明細 / Stock Details` layout without changing the underlying holdings data or tab structure.
- Kept the current project color system, but made the details table denser and closer to the original reference style:
  - smaller section spacing
  - lighter, more compact table header
  - reduced row padding and pill sizing
  - added a compact ranking badge in the symbol column
- Preserved the existing columns and bilingual labeling strategy instead of reducing data scope.

### Static Output
- Regenerated [docs/index.html](./index.html) and [docs/static/styles.css](./static/styles.css) so the published static output matches the updated UI.

### Verification
- Confirmed repo-facing documents no longer contain absolute `/Users/...` links.
- Rebuilt the static site successfully with `python portfolio.py --output docs/index.html`.
- Verified `GET /` and `GET /health` still return `200` through the Flask app.

## v1.1.0
### Local Holdings Import
- Added a local holdings import path for v1.1.0 instead of integrating broker APIs directly.
- Chose the local import approach to keep broker credentials, raw exports, and future certificates out of the public site, repo history, and deployment workflow.
- Kept the public application boundary unchanged: the app still reads canonical holdings from `data/holdings.json`.
- Finalized `data/holdings.json` as the single canonical holdings source used by the app runtime.

### Data Flow
- Clarified the intended data flow as:
  - local source file
  - source normalization
  - canonical holdings validation
  - canonical JSON persistence
  - snapshot assembly
  - Flask rendering or static export
- Added [portfolio_app/holdings_import.py](../portfolio_app/holdings_import.py) as the local import boundary for supported source types.
- Kept the canonical holdings schema unchanged:
  - `symbol`
  - `shares`
  - `cost_basis`

### CLI And Safety
- Expanded [scripts/import_holdings.py](../scripts/import_holdings.py) into a general local import CLI.
- Added support for:
  - canonical CSV
  - canonical JSON
  - Firstrade Account History / Transactions CSV
  - optional static HTML rebuild after import
- Moved local manual input files out of `data/` and into `imports/`, so repo-tracked data and local source files are no longer mixed together.
- Added fail-fast protection so invalid imports do not overwrite the existing canonical JSON file.
- Switched canonical JSON persistence to an atomic write path.
- Added the first broker-specific adapter with a conservative Firstrade mapping:
  - only `RecordType=Trade`
  - only `BUY` and `SELL`
  - weighted-average cost basis reconstruction
  - non-trade funding rows ignored

### Repo And Security Boundary
- Added `.env.example` for future local-only broker integration placeholders.
- Updated `.gitignore` to exclude:
  - `.env` and `.env.*`
  - local import directories
  - certificates and common key file types
  - spreadsheet exports
- Moved the provided Firstrade export sample into `imports/firstrade/`, which is ignored by git.
- Removed the tracked `data/holdings.csv` role from the canonical runtime path and kept canonical CSV as a local import-only format under `imports/`.
- Added [docs/holdings-import.md](./holdings-import.md) to document the supported local update flow.

### Documentation Refresh
- Updated [docs/codebase-review.md](./codebase-review.md) to reflect the current modular application structure rather than the old single-file prototype.
- Updated [AGENTS.md](../AGENTS.md) with the v1.1.0 holdings-import direction, test commands, and local secrets boundary.

### Verification
- Added focused `pytest` coverage for:
  - canonical CSV import
  - canonical JSON import
  - fail-fast behavior when CSV input is invalid
  - fail-fast behavior when JSON input is invalid
- Verified that local import can still feed static export successfully without changing the public runtime interface.

## v1.0.1
### Scheduled Updates
- Updated [deploy-pages.yml](../.github/workflows/deploy-pages.yml) to run one automatic GitHub Pages refresh per day.
- The new schedule is based on Taipei time:
  - `08:00 Asia/Taipei`
- The corresponding GitHub Actions cron entry was set to:
  - `00:00 UTC`
- `push` on `main` and `workflow_dispatch` remain available.
- No UI, data model, or application behavior was changed in this version.
- For ad-hoc refreshes, the recommended manual path remains GitHub Actions `Run workflow`.
- Current workflow timing was later adjusted to:
  - `21:30 UTC`
  - `05:30 Asia/Taipei`

## What Changed
### Data and Holdings
- Added canonical holdings storage in [data/holdings.json](../data/holdings.json).
- Added a reusable local import flow in [scripts/import_holdings.py](../scripts/import_holdings.py).
- Defined the v1 holdings schema as `symbol`, `shares`, and `cost_basis`.

### Application Structure
- Reduced [portfolio.py](../portfolio.py) to a thin CLI and app entry wrapper.
- Added `portfolio_app/` to separate configuration, holdings loading, market data access, snapshot assembly, templates, static assets, and Flask routing.
- Updated [Procfile](../Procfile) to point to the new Flask app module.
- Expanded [requirements.txt](../requirements.txt) to include the packages used directly by the code.

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
- Generated the updated static site at [docs/index.html](./index.html).
- Added static assets under [docs/static](./static).

### Deployment Preparation
- Updated [deploy-pages.yml](../.github/workflows/deploy-pages.yml) to deploy from the `main` branch through GitHub Pages Actions.
- Confirmed that a separate `docs/CNAME` file is not required for this site because deployment uses a custom GitHub Actions workflow for GitHub Pages.
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
