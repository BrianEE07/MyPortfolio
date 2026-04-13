# Refactor Plan v1

## v1.0.0 Goal
v1.0.0 is no longer a pure internal cleanup milestone. It is the first intentional productization pass for this portfolio site. The goal is to turn the current single-file prototype into a maintainable codebase while also aligning the product with the new desired experience:

- split the codebase into clearer modules
- replace the template portfolio data with the owner's real holdings
- define one minimal, stable holdings data format
- introduce a new visual theme with light mode as the default and dark mode support
- change the information architecture from one long page into tab-based navigation
- make the default tabs `Holdings Overview` and `Stock Details`

## Scope For v1.0.0
### In Scope
- Project structure cleanup and module extraction
- Holdings data model definition and data migration
- UI theme refresh, including light and dark modes
- Tab-based layout for core views
- Incremental verification to preserve working behavior during refactor

### Out Of Scope
- Major feature expansion beyond the approved tabs and theme work
- Large changes to investment logic unless required by the new data model
- Broad backend or API redesign beyond what is needed to separate responsibilities

## Priority Tasks
### 1. Define The Minimal Holdings Schema
Create a single canonical holdings format before broader refactoring starts. This schema should be simple enough to edit manually, but stable enough to support calculation, rendering, and future extension.

Suggested minimum fields:

- `symbol`
- `shares`
- `cost_basis`

Optional fields can be added later only if they support a real use case.

### 2. Replace Template Holdings With Real Portfolio Data
Move portfolio inventory out of hard-coded prototype data and into the new holdings structure. This should happen early so that later refactoring and UI work target the real dataset instead of placeholder content.

### 3. Split Responsibilities Across Modules
Break the current `portfolio.py` into clearer layers. The initial target should separate:

- holdings and app configuration
- external market data clients
- portfolio and signal calculation logic
- snapshot assembly or view-model construction
- Flask routing and application bootstrap
- templates and frontend assets

### 4. Introduce A Theme System
Replace the current single-theme approach with design tokens that support:

- light mode by default
- dark mode as an available alternative
- a clearer path for future branding updates

This work should avoid scattering color decisions directly across templates and scripts.

### 5. Convert The Page Into Tabs
Restructure the current one-page information dump into tabbed navigation. The default tabs for v1.0.0 are:

- `Holdings Overview`
- `Stock Details`

The tab system should improve information hierarchy without requiring a full SPA rewrite.

### 6. Add Verification Around The New Structure
As modules and UI boundaries are introduced, add lightweight verification around:

- holdings schema validity
- snapshot generation
- route health
- critical rendering paths

## Recommended Implementation Order
### Phase 1: Data Foundation
- Define the minimal holdings schema
- Migrate the portfolio data into that schema
- Remove assumptions tied to the old hard-coded inventory structure

### Phase 2: Structural Refactor
- Split `portfolio.py` into focused modules
- Isolate external data access from rendering logic
- Introduce clearer boundaries between data assembly and UI rendering

### Phase 3: UI Foundation
- Extract templates and shared styling structure
- Introduce theme tokens and implement light mode as default
- Add dark mode support in a maintainable way

### Phase 4: Information Architecture
- Convert the single-page layout into tab-based sections
- Establish `Holdings Overview` and `Stock Details` as the default entry points
- Ensure tab content maps cleanly to the new view-model structure

### Phase 5: Verification And Cleanup
- Validate static export and local server flows
- Add focused tests where the refactor introduces stable module seams
- Reconcile deployment and configuration details with the new structure

## Expected Result
After v1.0.0, the project should:

- use a stable, explicit holdings schema
- reflect the owner's actual portfolio data
- have clear separation between data, UI, and external integrations
- support both light and dark themes with light mode as the default
- present information through tabs instead of a single overloaded page
- be significantly easier to maintain, extend, and review

## Delivery Principle
The refactor should still be incremental. Even though v1.0.0 includes visible product changes, implementation should proceed in small, reviewable steps rather than one risky rewrite.
