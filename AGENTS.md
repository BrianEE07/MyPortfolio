# Repository Guidelines

## Purpose
This file defines the default engineering rules for future Codex collaboration in this repository. Unless the user explicitly says otherwise, these rules are the default standard for planning, editing, refactoring, reviewing, and verifying work.

## Active v1.0.0 Direction
Current implementation work should align with the approved v1.0.0 plan:

- split the current single-file structure into clearer modules
- separate data logic, UI logic, and external data-fetching logic
- replace the template holdings with the owner's real holdings data
- establish one unified minimal holdings data format
- move the UI toward tab-based navigation
- use `Holdings Overview` and `Stock Details` as the default tabs
- support both light and dark themes, with light mode as the default

When making implementation decisions, prefer options that move the project toward this structure.

## Project Context
- The current project is centered on `portfolio.py`, a single-file Flask application that can both serve the site locally and generate a static HTML snapshot.
- Runtime dependencies live in `requirements.txt`.
- Deployment-related files include `Procfile` and `.github/workflows/deploy-pages.yml`.
- Generated static output should be written under `docs/`, such as `docs/index.html`.

## Development Principles
- Prioritize readability, maintainability, and extensibility over cleverness.
- Avoid flashy or overly compressed implementations unless they provide clear operational value.
- Write code in the style of a senior engineer: explicit, stable, and easy to reason about.
- Prefer clear and durable patterns over brittle abstractions.
- Unless behavior change is part of the approved task, preserve existing behavior.
- Even when visible product changes are intended, implement them through small, reviewable steps.

## Naming Conventions
- Use clear, descriptive, semantic English names for variables, functions, classes, modules, templates, and UI identifiers.
- Avoid unnecessary abbreviations. Prefer `holdings_schema` over unclear names like `hs`.
- Keep naming consistent across modules. If a concept is named `holding`, do not rename it to `position` elsewhere without a deliberate reason.
- Use `snake_case` for variables and functions, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for module-level constants.
- Data model field names should stay explicit and stable once introduced. Prefer names such as `symbol`, `shares`, and `cost_basis`.

## Comments And Documentation
- All code comments must be written in English.
- All docstrings must be written in English.
- Do not mix Chinese into comments, docstrings, variable names, function names, class names, or module names.
- Comments should explain intent, reasoning, constraints, or tradeoffs.
- Do not add comments that simply repeat what the code already says.
- When behavior is non-obvious, document why the implementation exists in its current form.

## Structure And Design Rules
- Separate data logic, UI logic, and external API access whenever practical.
- Avoid concentrating too many responsibilities in one file.
- Keep functions small and focused on one job.
- Design modules for high cohesion and low coupling.
- Prefer explicit data flow over hidden shared state.
- When adding new logic, favor extracting helpers, services, or models instead of expanding already overloaded files.
- Do not let template structure become the primary place where business rules are encoded.

## UI And Data Constraints
- Light mode is the default visual mode for v1.0.0.
- Dark mode support should be implemented through reusable theme tokens or an equivalent maintainable system, not by duplicating entire templates.
- The default top-level information architecture should center on `Holdings Overview` and `Stock Details`.
- The holdings model should be kept minimal during v1.0.0. Add fields only when they support a concrete need in calculations, rendering, or migration.
- UI restructuring should not bypass structural cleanup. Prefer aligning tabs and themes with extracted templates and clearer view models.

## Modification Strategy
- Prefer small, traceable, low-risk changes.
- Avoid large rewrite-style edits unless explicitly requested.
- Refactor incrementally, with behavior preserved where possible at each step.
- Do not perform unrelated cleanup while working on a scoped task.
- If a larger cleanup is tempting but out of scope, note it separately instead of bundling it into the same change.
- When a change spans structure, data, and UI, sequence it so the data model and boundaries are stabilized before presentation-level refinement.

## Collaboration Requirements
- Before making substantial edits, explain the plan briefly.
- After making changes, summarize what changed and why.
- State assumptions explicitly when they affect implementation choices.
- Avoid opportunistic edits unrelated to the requested task.
- If a decision has meaningful tradeoffs, surface them clearly before proceeding.
- Keep document updates and implementation work aligned. If the plan changes, update the relevant project documents before or alongside the code.

## Testing And Verification
- There is no committed automated test suite yet, so verification must be intentional.
- For syntax validation, use:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile portfolio.py
```

- For local development, use:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 portfolio.py --serve
```

- For static output validation, use:

```bash
python3 portfolio.py --output docs/index.html
```

- If a change affects rendering or data assembly, verify both `/` and `/health`, and confirm static export still works.
- If a change introduces new module seams or data transformations, add focused tests where practical rather than relying only on manual checks.

## Refactoring Guidance For This Repository
- The current codebase has significant responsibility concentration in `portfolio.py`.
- When refactoring, prioritize extracting:
  - holdings configuration and schema definitions
  - external data clients
  - portfolio and signal calculation logic
  - snapshot or view-model assembly logic
  - templates and frontend assets
  - Flask app bootstrap and routing
- Do not combine structural refactors with unrelated feature work.
- Keep refactors reversible, reviewable, and easy to validate.

## Review Standard
- Default to a code review mindset that looks for correctness issues, maintainability risks, regressions, and missing validation.
- Call out high-coupling areas, naming drift, repeated logic, hidden behavior dependencies, and schema leakage across layers.
- Prefer concrete findings and actionable recommendations over generic style feedback.

## Commit And PR Guidance
- Follow concise commit subjects in the form `<type>: <summary>`, consistent with the current history such as `init: clone portfolio template`.
- Keep pull requests focused and narrow in scope.
- Document behavior impact, UI impact, data-model impact, and deployment impact when relevant.
- Include screenshots when UI output changes.

## Git Commit Workflow
- Before creating a commit, record the implementation scope in project docs when the change is substantial.
- For milestone-sized work, add or update a version log under `docs/`, such as `docs/v1-implementation-log.md`.
- Run the minimum relevant verification before staging changes.
- At a minimum, prefer:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile portfolio.py
python3 portfolio.py --output docs/index.html
```

- Stage only files related to the requested task.
- Do not stage local-only artifacts such as `.venv/`, `.DS_Store`, temporary output, or unrelated generated files.
- Keep `.gitignore` updated when local environment noise appears during work.
- If a tracked deployment file is intentionally ignored, add it explicitly and document why.
- Check `git status --short` before commit and leave the working tree clean after commit whenever practical.
- Use concise commit messages in the form `<type>: <summary>`.
- If the change includes user-visible behavior, ensure the commit includes the related docs, generated static output, and runtime assets needed for deployment consistency.
