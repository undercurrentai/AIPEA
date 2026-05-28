# AEGIS Adapter for AIPEA

## Purpose & scope

AEGIS (AI Ethics Governance & Integrity System) uses AIPEA to
preprocess claims before gate evaluation. The adapter lives in the
`aegis-governance` repo at `src/integration/aipea_bridge.py` and is
maintained there; this document is the **AIPEA-side contract** it
consumes. The audience is aegis-governance maintainers and any future
adapter author modeled on the aegis bridge.

Every claim in this doc has a corresponding assertion in
[`tests/test_aegis_integration.py`](../../tests/test_aegis_integration.py)
and vice versa — the doc + test together ARE the contract. AIPEA's CI
runs the contract test on every PR, so surface-breaking changes fail
`make ci` BEFORE shipping to PyPI.

## Quick start

```python
from aipea import enhance_prompt, ComplianceMode

result = await enhance_prompt(
    query=claim_text,
    model_id="claude-opus-4-7",
    compliance_mode=ComplianceMode.GENERAL,
)

# Read these:
result.enhanced_prompt                # str — the enriched claim text
result.query_analysis.query_type      # QueryType enum — use .value for the string
result.query_analysis.complexity      # float, 0.0-1.0
result.query_analysis.needs_current_info  # bool — hint that fresh data would help
result.processing_tier.value          # str — "offline" | "tactical" | "strategic"
result.enhancement_time_ms            # float — wall-clock processing time
result.search_context                 # SearchContext | None — when include_search=True
result.scan_result                    # ScanResult | None — security flags live HERE
result.scan_result.flags              # list[str] — the prefix-tagged security flags
result.scan_result.is_blocked         # bool — refuse-processing signal
result.scan_result.force_offline      # bool — route-to-local-model signal
```

AIPEA is an optional dependency on the aegis-governance side. When
not installed, the adapter returns passthrough results (original
claim text, `query_type="unknown"`, `complexity=0.5`,
`processing_tier="offline"`, `security_flags=[]`).

## The contract

Each row below is pinned by a test in
`tests/test_aegis_integration.py`. Renaming or removing any of these
is a breaking change.

### Flag-name constants

Exported from `aipea`; pinned by
`TestAEGISContractFlagConstants`.

| Constant | String literal | Format / example |
|---|---|---|
| `FLAG_PII_DETECTED` | `"pii_detected:"` | prefix + type, e.g. `pii_detected:ssn` |
| `FLAG_PHI_DETECTED` | `"phi_detected:"` | prefix + type, e.g. `phi_detected:mrn` |
| `FLAG_CLASSIFIED_MARKER` | `"classified_marker:"` | prefix + marker, e.g. `classified_marker:TOP SECRET` |
| `FLAG_INJECTION_ATTEMPT` | `"injection_attempt"` | exact literal — NO colon, no suffix |
| `FLAG_CUSTOM_BLOCKED` | `"custom_blocked:"` | prefix + truncated pattern, e.g. `custom_blocked:foo` |

### Enum values

Enum `.value` strings the adapter passes into `enhance_prompt()` or
reads off the response; pinned by `TestAEGISContractEnumValues`.

| Enum | Members | `.value` strings |
|---|---|---|
| `ComplianceMode` | `GENERAL`, `HIPAA`, `TACTICAL`, `FEDRAMP` (deprecated v1.3.4; removal v2.0.0 per ADR-002) | `"general"`, `"hipaa"`, `"tactical"`, `"fedramp"` |
| `ProcessingTier` | `OFFLINE`, `TACTICAL`, `STRATEGIC` | `"offline"`, `"tactical"`, `"strategic"` |
| `QueryType` | `TECHNICAL`, `RESEARCH`, `CREATIVE`, `ANALYTICAL`, `OPERATIONAL`, `STRATEGIC`, `UNKNOWN` | the lowercase string of each name |

### Dataclass fields

Pinned by `TestAEGISContractDataclassFields`. Field NAMES are
pinned; type-widening (e.g., `list[str]` → `Sequence[str]`) is
intentionally allowed.

| Dataclass | Required field names |
|---|---|
| `ScanResult` | `flags`, `is_blocked`, `force_offline` |
| `EnhancementResult` | `enhanced_prompt`, `processing_tier`, `security_context`, `query_analysis`, `search_context`, `enhancement_time_ms`, `scan_result` |
| `QueryAnalysis` | `query_type`, `complexity`, `needs_current_info` |

### Function signature

Pinned by `TestAEGISContractFunctionSignatures`.

```python
async def enhance_prompt(
    query: str,
    model_id: str,
    security_level: SecurityLevel = SecurityLevel.UNCLASSIFIED,
    compliance_mode: ComplianceMode | None = None,
    force_offline: bool = False,
    include_search: bool = True,
    format_for_model: bool = True,
    strategy: str | None = None,
) -> EnhancementResult: ...
```

Required kwargs the adapter may pass (test pins these):
`query`, `model_id`, `compliance_mode`, `force_offline`,
`include_search`. Other kwargs may be added (backwards-compatible)
in future minor releases.

### Flag-name conventions

The 5 `FLAG_*` constants document the canonical prefix that flag
strings use. Worked examples (every example below is a real string
that appears in `ScanResult.flags`):

| Detection | Flag string | Source |
|---|---|---|
| Social-security-number PII | `"pii_detected:ssn"` | `security.py` PII patterns |
| Medical-record-number PHI | `"phi_detected:mrn"` | `security.py` HIPAA-mode PHI patterns |
| TOP SECRET banner | `"classified_marker:TOP SECRET"` | `security.py` TACTICAL-mode classified-marker scan |
| Instruction-override injection | `"injection_attempt"` | `security.py` injection detection (always-on) |
| Custom blocked pattern | `"custom_blocked:<truncated to 20 chars>"` | `SecurityContext.blocked_patterns` |

`ScanResult` also carries convenience helpers (`has_pii()`,
`has_phi()`, `has_classified_content()`, `has_injection_attempt()`,
`has_compliance_taint()`) for adapters that prefer
typed-helper access over string-prefix matching.

## Behavioral invariants

Prose mirror of `TestAEGISContractBehavioralInvariants`. The AEGIS
gate evaluator can rely on these holding across the v1.x line.

1. **Injection is ALWAYS blocked**. An injection-detection match
   (e.g., the canonical "ignore all previous instructions" family)
   sets `scan_result.is_blocked is True` AND appends
   `"injection_attempt"` to `scan_result.flags`, in every compliance
   mode (GENERAL / HIPAA / TACTICAL). Injection-blocking is not
   mode-gated.

2. **HIPAA mode flags PHI**. In `ComplianceMode.HIPAA`, the scanner
   runs PHI-pattern detection (MRN, DOB, etc.) and appends one or
   more `phi_detected:<type>` flags to `scan_result.flags`. GENERAL
   mode does NOT run PHI detection — flagging is HIPAA-scoped.

3. **TACTICAL mode forces offline on classified markers**. In
   `ComplianceMode.TACTICAL`, the scanner runs classified-marker
   detection (TOP SECRET, SCI, NOFORN, etc.) and on any match sets
   `scan_result.force_offline is True` AND appends one or more
   `classified_marker:<marker>` flags to `scan_result.flags`. The
   adapter (or downstream router) is responsible for honoring
   `force_offline` by routing to a local model — AIPEA does NOT
   enforce network egress.

4. **`scan_result` is populated on a successful enhance**. After
   `await enhance_prompt(...)` returns a non-blocked result,
   `result.scan_result` is a non-`None` `ScanResult` instance. The
   security findings are NOT exclusively a side channel — they ride
   on the same result object the adapter reads other fields from.

## AIPEA → AEGIS field mapping

The adapter maps AIPEA's `EnhancementResult` onto AEGIS's
`PreprocessedClaim` dataclass. Field-name pairs (AIPEA → AEGIS):

| AIPEA field | AEGIS field | Usage |
|---|---|---|
| `enhanced_prompt` | `enhanced_claim` | Enriched text for gate evaluation |
| `query_analysis.complexity` | `claim_complexity` | Route to appropriate gate depth |
| `query_analysis.needs_current_info` | `requires_live_search` | Trigger evidence gathering |
| `search_context.results` | `background_evidence` | Pre-gathered context |
| `scan_result.flags` | `security_flags` | Block / route unsafe claims |
| `processing_tier` | `preprocessing_tier` | Audit trail |

**Drift fix (2026-05-28)**: the previous version of this doc listed
`security_context.flags` as the source for `security_flags`. That
attribute does not exist — `EnhancementResult.security_context` is a
`SecurityContext`, which has no `.flags` field. The correct source
is `scan_result.flags`, added to `EnhancementResult` in v1.6.0
([ADR-004](../adr/ADR-004-taint-aware-feedback-averaging.md)).
Adapters that previously read `security_context.flags` got an
`AttributeError`; adapters that hardcoded an empty list (see §Known
integration gaps Gap 1 below) silently dropped all security findings.

## Known integration gaps

The following findings come from the F-audit's cross-repo review.
This AIPEA-side audit cannot independently verify aegis-side code
state (this session has scope over `undercurrentai/aipea` only); the
recommended fixes are scoped to the aegis-governance repo and should
land as a separate PR there.

### Gap 1 — Security flags discarded by the adapter

If `aegis-governance/src/integration/aipea_bridge.py` hardcodes
`security_flags=[]` in its `_map_result` (or equivalent), the AEGIS
gate evaluator receives zero security findings even when AIPEA
flagged PII / PHI / injection / classified content. The recommended
fix is a one-liner that forwards `scan_result.flags`:

```python
# In AIPEAGateAdapter._map_result(...):
security_flags=list(result.scan_result.flags) if result.scan_result else [],
```

The AIPEA-side contract test
(`tests/test_aegis_integration.py::TestAEGISContractDataclassFields::test_enhancement_result_has_required_fields`)
pins that `scan_result` is a stable field on `EnhancementResult`, so
the fix is safe to land without further AIPEA-side coordination.

### Gap 2 — Adapter exported but not wired into a call site

If `AIPEAGateAdapter` is exported from `aegis-governance/src/integration/__init__.py`
but no call site invokes `await adapter.preprocess_claim(...)` in
`pcw_decide.py` / `consensus.py` / `proposal.py` / `gates.py`, the
adapter is specification-only / ready-to-integrate. The natural
wire-in point is `pcw_decide()` before submitting the claim to
guardrails — preprocess the claim once, then feed the enriched
`PreprocessedClaim` (with `security_flags` populated per Gap 1)
into the existing gate-evaluation flow.

Both gaps are explicitly out-of-scope for the AIPEA-side F audit;
they are recorded here so a future aegis-governance PR has the
contract context. AIPEA's CI will keep the consumed surface stable
while the aegis side closes the gaps.

## Why this is not an ADR

The doc + `tests/test_aegis_integration.py` together constitute the
contract — an ADR would be redundant (the contract IS the
architecture for this integration, not a decision about it).
Revisit if a real architectural decision arises: a new transport
(e.g., gRPC or HTTP instead of in-process), a versioned API endpoint
(`/v1/enhance`), or a typed `Protocol` class hoisted into a shared
package. At that point an ADR is the right vehicle.

## Versioning + compatibility

The surface above is considered stable across the v1.x line.
Breaking changes ship in v2.0.0 per [`docs/MIGRATION.md`](../MIGRATION.md).
The one in-flight deprecation through v1.x is `ComplianceMode.FEDRAMP`
(deprecated in v1.3.4 per
[ADR-002](../adr/ADR-002-fedramp-removal.md); removal scheduled
v2.0.0). The `.value` string `"fedramp"` remains decodable through
the deprecation window so adapters that received it during v1.x
continue to parse.

## When to use

- **Gate evaluation**: preprocess claims before research verification
- **Batch processing**: enrich multiple claims with context before scoring
- **Security screening**: screen user inputs for PII / PHI / injection / classified content before processing

## Installation

```bash
# In aegis-governance repo
pip install aipea
```

## Status

- **AIPEA-side contract**: pinned by
  [`tests/test_aegis_integration.py`](../../tests/test_aegis_integration.py)
  (16 test cases across 5 classes; runs in `make ci`).
- **aegis-governance-side adapter**: `AIPEAGateAdapter` and
  `PreprocessedClaim` live in
  `aegis-governance/src/integration/aipea_bridge.py`. The aegis-side
  unit-test count quoted in earlier versions of this doc ("9 unit
  tests") is not verified by this session — refer to
  aegis-governance HEAD for the current figure, and see §Known
  integration gaps for the two adapter-side findings that should be
  addressed in a sibling-repo PR.
