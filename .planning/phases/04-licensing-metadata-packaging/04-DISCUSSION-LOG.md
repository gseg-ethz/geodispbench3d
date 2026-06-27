# Phase 4: Licensing, Metadata & Packaging - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-27
**Phase:** 4-Licensing, Metadata & Packaging
**Areas discussed:** iof3d in public dist, F2S3 pchandler resolution, pchandler pinning, public metadata polish

---

## iof3D in the public distribution

First framed as exclude-vs-ship; the maintainer paused to clarify two constraints: (1) iof3D
publishes publicly in ~6 months, (2) the integration must keep working locally for ongoing
research (iof3D is a private repo they have access to). Scouting confirmed `geodispbench3d_iof3d`
eagerly imports `iof3D.*`/`pc2img`/`pchandler` at package top, so a public import hard-fails; core
`geodispbench3d` imports nothing from iof3D. The maintainer then asked whether an *extra* could
gate the `geodispbench3d_iof3d` subpackage — answered: no, extras list *distributions*, not in-wheel
subpackages; the only way is a separate plugin distribution.

| Option | Description | Selected |
|--------|-------------|----------|
| Single wheel, ship dormant (guarded imports) | Keep subpackage in `packages`; guard heavy imports so public import succeeds, use fails actionably; comment the extra | ✓ |
| Split into plugin distribution | Promote to own distribution the `[iof3d]` extra pulls in; cleanest core wheel but second build target/version + heavier change, no timeline benefit | |
| Exclude from the wheel | Drop package + script from published artifact; needs build trickery / divergent branch to keep editable install working | |

**User's choice:** Single wheel, ship dormant.
**Notes:** Decisive factor — the setuptools `packages` list governs both the wheel and editable
installs, so excluding would break the maintainer's own research env. Plugin-distribution split
was acknowledged as architecturally cleanest but deferred to iof3D go-live.

---

## F2S3 pchandler resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Add `pchandler` to the `f2s3` extra | `f2s3 = ["pchandler ~= 2.1"]`; parser unchanged; satisfies PKG-02 | ✓ |
| pchandler-free example parser | Rewrite `output_parser.py` to numpy/pandas; `[f2s3]` needs nothing heavy but more work, diverges from research parser | |
| Decide after pchandler verification | Run PKG-03 check first, then choose | |

**User's choice:** Add pchandler to the f2s3 extra.
**Notes:** F2S3 is the canonical public `CliToolAdapter` example (Phase 3 CLI-05) and must stay
fully runnable publicly — so it gets a real resolvable dependency, not the dormant treatment iof3D
received. Commenting out the `iof3d` extra removes the only thing currently dragging pchandler in,
which is exactly why it must move into the f2s3 extra.

---

## pchandler pinning

| Option | Description | Selected |
|--------|-------------|----------|
| Compatible-release `~=` | Match house style; tighten to three-component if pre-1.0 | ✓ |
| Floor pin `>=` | Allows all forward versions incl. majors; risk of silent breakage | |
| Unpinned | Lightest; no protection against incompatible future release | |

**User's choice:** Compatible-release — `pchandler ~= 2.1` (maintainer confirmed 2.1 is the live
PyPI version; post-1.0, so two-component is correct).
**Notes:** 2.x is a major line, so PKG-03 must verify the imported symbols (`PointCloudData`, `Csv`,
`SphereFilter`, `geometry.spherical.Angle`) still exist at those paths in 2.1 before the pin is
trusted.

---

## Public metadata polish (maturity)

| Option | Description | Selected |
|--------|-------------|----------|
| 4 - Beta | Honest first-public-release signal; mature in-house, new to outside users | ✓ |
| 5 - Production/Stable | Claims stable API others can depend on | |
| 3 - Alpha | Early-stage; understates a hardened codebase | |

**User's choice:** Development Status :: 4 - Beta.
**Notes:** Also adding `Intended Audience :: Science/Research`, `Topic :: Scientific/Engineering`,
and `Documentation` + `Changelog` `project.urls` by default (maintainer did not contest these).

## Claude's Discretion

- Exact guard mechanism for dormant iof3D (PEP 562 `__getattr__` vs try/except re-exports).
- Wording of the actionable "install iof3D" error message.
- Exact `Documentation`/`Changelog` URL targets.

## Deferred Ideas

- iof3D extra re-enablement at go-live (~6 months): uncomment extra, set version pins, publish.
- Plugin-distribution split for `geodispbench3d_iof3d` — revisit at iof3D go-live.
