# Deferred Items — Phase 04 (licensing-metadata-packaging)

Out-of-scope discoveries logged during execution. NOT fixed in this phase.

| Discovered in | Item | Why deferred |
|---------------|------|--------------|
| 04-02 Task 2 | `iof3d-ax --help` raises `hydra.errors.MissingConfigException: Primary config module 'geodispbench3d_iof3d.conf' not found ... contains an __init__.py file`. Confirmed PRE-EXISTING: the original `cli.py` topology (decorator in `cli.py`) produces the identical error, so the `_sweep_cli.py` split does NOT change Hydra's `config_path="conf"` resolution (the bundled `conf/` path is unchanged — finding 12 intent satisfied). Root cause is the bundled `src/geodispbench3d_iof3d/conf/` dir lacking an `__init__.py` for Hydra's `pkg://` provider in the editable install. | Out of scope for 04-02 (SCOPE BOUNDARY: not caused by this task's changes; the split is regression-neutral). Hydra config-source packaging is its own concern; candidate for Phase 5 release hardening or a dedicated quick fix. |
