# Static Site Interfaces

Status: draft

This document records a design principle for Macro Observatory's browser layer: published data artifacts should be shared across multiple possible static interfaces.

The initial web presentation will probably use Plotly because it is practical, familiar from the existing Streamlit project, and easy to host from GitHub Pages. Plotly should be treated as the first interface, not as the permanent shape of the project.

## Core Principle

The static data contract and the frontend interface should stay separate.

The data pipeline owns:

- source API access,
- cache updates,
- Pandas-friendly source and derived datasets,
- formula logic,
- validation,
- published browser-facing data artifacts,
- metadata describing those artifacts.

Each frontend owns only its presentation and interaction model. A frontend may choose Plotly, another charting library, a framework, or a notebook-like browser experience, but it should consume published artifacts instead of reimplementing canonical data work.

## Shared Data Contract

The initial shared static contract is the generated `site/data/` directory.

For the Fed Net Liquidity milestone, that currently means artifacts such as:

```text
site/
  data/
    fed-net-liquidity.json
    fed-net-liquidity.csv
    fed-net-liquidity-metadata.json
```

The exact data formats can evolve, but the architectural role should remain stable: `site/data/` is the handoff point between Python data generation and browser presentation.

Frontend code should not depend on internal cache files under `data/cache/`. Source caches and derived caches are for incremental updates, Pandas inspection, and build-time transforms. Published artifacts are for static-site consumers.

## First Interface

The first interface can be a simple static Plotly page.

For the next checkpoint, a small root site is enough:

```text
site/
  index.html
  assets/
  data/
```

This keeps the implementation direct and avoids introducing a frontend build step before the first chart exists. A future checkpoint can reorganize the frontend once there is more than one interface to route between.

## Shared Browser Behaviors

Common chart interactions should live in shared static-site code when they are not specific to one dataset.

The first shared behavior is viewport-expanded chart mode. Pages should use the shared `enableChartExpansion(...)` helper instead of reimplementing expansion per dashboard. The behavior is intentionally in-app rather than operating-system fullscreen:

- a visible `Expand` button appears near the chart heading,
- the expanded chart gets a visible `Restore` button,
- `Escape` is an extra restore shortcut,
- scroll position is restored on close,
- Plotly is resized after expand and restore.

Future chart pages should use the same pattern unless a page has a clear reason to diverge.

## Future Interfaces

Future interfaces should be allowed to exist beside the first one without disrupting existing URLs or users.

Possible examples:

- a richer Plotly dashboard,
- an alternative charting-library experiment,
- a React or TypeScript application,
- an Observable-style exploratory interface,
- a notebook-like browser data explorer,
- a compact mobile-first view.

The exact directory layout should be decided when the second interface is implemented. Possible shapes include:

```text
site/
  index.html
  apps/
    plotly/
    experimental-charting/
  data/
```

or:

```text
site/
  plotly/
  experimental-charting/
  data/
```

The important constraint is not the final folder name. The important constraint is that interfaces are replaceable consumers of shared published data.

## Data Shape Changes

If a future interface needs a different data shape, the publisher should create an additional artifact or a versioned artifact instead of casually mutating an existing artifact that another interface may already consume.

For example, a future compact columnar browser format could live next to the current JSON and CSV artifacts rather than replacing them immediately.

This keeps experiments isolated and makes it possible to compare frontend approaches against the same underlying source and derived datasets.

## Non-Goals

- Choose the final frontend framework for the whole project.
- Build a multi-interface router before the first chart works.
- Move formula logic into browser JavaScript.
- Make internal source caches part of the browser contract.
- Force future chart experiments to modify the initial Plotly page.

## Design Implication For The Next Checkpoint

The next implementation should build the first Plotly interface as a small static consumer of `site/data/fed-net-liquidity.json` and `site/data/fed-net-liquidity-metadata.json`.

The page can be the default root experience for now, while the data contract remains presentation-neutral enough for future interfaces.
