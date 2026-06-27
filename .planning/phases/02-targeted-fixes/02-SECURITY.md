---
phase: 02
slug: targeted-fixes
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-06-27
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
>
> Register origin: authored at plan time (all 7 PLAN files carry a `<threat_model>`
> block). ASVS L1, block-on `high`. All threats are severity `low`, mitigated or
> accepted, so `threats_open: 0` — the L1 short-circuit applies (no auditor pass
> required; mitigations are grep-verifiable and corroborated by the passing UAT).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| trusted-local YAML → loaders | Operator-authored local suite/dataset/tool/param config; no untrusted or network input. Phase 2 is tests + typing + dead-code removal + observability — no new boundary added. | Local config (non-sensitive) |
| on-disk summary/cache JSON → readers (`load_trial_record`, `read_prediction`, `_tool_from_record`) | Readers deserialize on-disk JSON the framework itself wrote. F-08 narrowed catches + added an observe-only `on_non_fatal` callback; F-30 removed the `yaml_hash` reconstructed field. No new untrusted parsing; corrupt-file → miss/empty fallback preserved. | Framework-written provenance/prediction JSON |
| runner → on-disk trial-level summary artifact | New trial-level summary JSON is written (not read back) by the runner; the write is fail-soft and cannot break a trial. | Framework-written observability JSON |
| plugin callables → evaluation glue | Trusted-local plugin callables (parser/metric). The 4 arbitrary-callable boundaries stay broad so a plugin `ValueError`/`KeyError` cannot crash a pass. F-08 did not change the plugin-trust boundary. | In-process call results |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-01 | Information Disclosure | silent fail-soft degradation across sweep/runner/rescore/cache/eval/analyze | low | mitigate | F-05 surfaces `objective_cases_finite/total`; F-08 adds typed `PassDiagnostics` counter, promotes debug→warning, and emits a CLI "N non-fatal failures" line. Verified UAT #9 (02-03-D3), #11–13 (02-05-D1/2/3). | closed |
| T-02-02 | Tampering | predictions-cache / trial-record corrupt-file fallback | low | mitigate | `read_prediction` + `load_trial_record` narrowed to `(OSError, json.JSONDecodeError)`; corrupt→miss/empty fallback preserved, `on_non_fatal` observes only. Verified UAT #12 (02-05-D2). | closed |
| T-02-03 | Tampering | duplicated param coercion drifting across sites | low | mitigate | `SweepParameter.from_mapping` single-sources the 11-field coercion across all 3 sites; parameterized tests pin the field mapping. Verified UAT #10 (02-04-D1). | closed |
| T-02-04 | Denial of Service | over-narrowing a plugin-callable boundary | low | mitigate | The 4 arbitrary-callable sites (evaluation parser/metric, rescore outer, analysis) stay `except Exception` with documented reason so a plugin exception cannot crash the sweep. Verified UAT #11 (02-05-D1) + 02-05 Threat Surface note. | closed |
| T-02-05 | Tampering | lazy-import gating broken by an over-eager hoist | low | mitigate | F-10 hoists only internal/stdlib imports; `tests/core/test_imports.py` guard confirms no iof3D/pchandler/Ax reaches module level. Verified UAT #15 (02-06-D2). | closed |
| T-02-06 | Tampering | provenance/cache key drift between sweep and rescore | low | mitigate | F-03 single-sources `parser_fn_repr`; byte-identity assertions (incl. nested `<locals>` callable) lock the `module:qualname` key. Verified UAT #17 (02-07-D1). | closed |
| T-02-07 | Denial of Service | silent no-op of declared-but-unsupported `parallel_trials` | low | mitigate | Shared `ExecutionConfig.ensure_supported()` raises deterministically (not warn-only) from both `_cmd_sweep` and `run_with_suite` — bypass-proof. Verified UAT #19 (02-07-D3). | closed |
| T-02-08 | Tampering | dead-field deletion breaking in-repo YAML / old records | low | mitigate | Loaders use `.get()`-based extraction; `yaml_hash` old-record compat test + loading every shipped suite confirm nothing breaks. Verified UAT #18, #20 (02-07-D2/D4). | closed |
| T-02-09 | Tampering | `pyright_gate.py` runs pyright via subprocess | low | accept | Stdlib-only script, no `shell=True`, no untrusted input; reads only a sibling baseline JSON the same plan wrote. Accepted risk (see log). | closed |
| T-02-10 | Tampering | trial-level summary artifact write failure | low | mitigate | The write is wrapped fail-soft (logs at warning, never fails a trial); 02-05 adds the non-fatal counter to this site. Verified UAT #9 (02-03-D3). | closed |
| T-02-11 | Information Disclosure | timestamp format change breaks a Z-only consumer | low | mitigate | `datetime.fromisoformat` parse assertions prove the new offset-aware `+00:00` format is machine-parseable; no Z-only consumer exists in-repo. Verified UAT #14 (02-06-D1). | closed |
| T-02-SC | Tampering | package installs (supply chain) | low | accept | No external runtime packages installed by the phase; the optional D-12 CI env installs only CI-pinned `pyright==1.1.392` + already-declared `.[dev]` deps. Accepted risk (see log). | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-09 | `pyright_gate.py` is a stdlib-only dev gate: no `shell=True`, no untrusted input, reads only a sibling baseline JSON it wrote. Not shipped in the runtime package. | Nicholas Meyer | 2026-06-27 |
| AR-02-02 | T-02-SC | Phase 2 installs no external runtime dependencies; only optional CI-pinned dev tooling (`pyright==1.1.392`, already-declared `.[dev]`). No new registry/runtime surface in the shipped project. | Nicholas Meyer | 2026-06-27 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-27 | 12 | 12 | 0 | gsd-secure-phase (L1 short-circuit, plan-time register) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-27
