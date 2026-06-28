# Future Feature-Module Architecture

Status: future direction

Macro Observatory currently uses explicit central modules for source adapters, derived builders, registry entries, publishers, and static pages. That is straightforward while the project is small, but each new page can require coordinated edits across several files.

A future refactor could move toward feature modules. A feature module would keep the pieces for one analytical area near each other while still registering them explicitly with the application.

Example shape:

```text
src/macro_observatory/features/
  fed_net_liquidity/
    sources.py
    derived.py
    publish.py
    registry.py
    site/
  tga_explorer/
    derived.py
    publish.py
    registry.py
    site/
  treasury_securities/
    sources.py
    derived.py
    publish.py
    registry.py
    site/
```

The first version should not become a dynamic plugin system. The safer intermediate step is modular but explicit: each feature exports dataset specs, derived builders, and publish/page configuration, and the central registry imports those exports.

Goals:

- reduce unrelated growth in files such as `derived.py`,
- make page plus dataset ownership easier to inspect,
- make it easier to add or remove an analytical page without touching many unrelated sections,
- keep commands, tests, and GitHub Actions behavior explicit and predictable.

Non-goals for now:

- runtime plugin loading,
- auto-discovery with hidden import side effects,
- per-feature dependency isolation,
- moving current implementation before the static-site pipeline is proven with several pages.

A practical first refactor would be to split `derived.py` into a package with one module per derived dataset family, while keeping the central registry and `build_derived_dataset(...)` dispatcher explicit.
