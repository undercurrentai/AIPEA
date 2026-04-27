# ADR-008: Adversarial Evaluation Suite

- **Status**: Accepted (2026-04-27 — implemented in [PR #59](https://github.com/undercurrentai/AIPEA/pull/59), squashed at `7be9c99`)
- **Date**: 2026-04-15 (renumbered from ADR-005 on 2026-04-27 to avoid
  collision with [ADR-005 — PR #52 VC adversarial review response](./ADR-005-pr52-vc-adversarial-review-response.md), merged 2026-04-24)
- **Author**: @joshuakirby (with Claude design partnership)
- **Implements**: ROADMAP D4 (adversarial red-team corpus)
- **Implemented in**: [PR #59](https://github.com/undercurrentai/AIPEA/pull/59) — corpus (120 payloads), `tests/test_adversarial.py` harness, `make adversarial` + `make adversarial-update-baseline` targets, `adversarial` pytest marker. Initial baseline against v1.6.2 (post-merge): bright_line 62/62 (100%), extended 10/58 (17.2%).
- **Fulfills**: [ADR-005](./ADR-005-pr52-vc-adversarial-review-response.md)
  Accept-track item — reviewer's §10 finding "tests verify author's
  regexes match author's payloads; not tested against published
  jailbreak corpora."

## Context

Every adversarial review of AIPEA (2026-04-11, 2026-04-14, 2026-04-15)
identified the same top-ranked residual concern: the injection layer has
never been tested against an external adversarial corpus. Tests in
`test_security.py` (~1230 LOC, 23 classes) are ~73% bug-hunt regressions
and ~27% generic pattern tests — all using author-written payloads. Two
consecutive Unicode-class bypasses were found by internal audit (wave 19
\#97 uppercase Cyrillic, wave 20 #108 zero-width chars), confirming the
surface has real exploitable gaps that internal audit catches but external
adversarial testing would catch sooner.

The committed adversarial investor review says explicitly: *"tests verify
that the author's regexes match the author's payloads. It does not test
the module against published jailbreak corpora."*

### External References

- OWASP LLM Top 10 2026 — taxonomy of LLM-specific vulnerabilities with
  representative attack patterns per category.
- NIST AI RMF 1.0 (AI 100-1), MAP function — identify and evaluate AI
  risks through adversarial testing.
- MITRE ATLAS — adversarial threat landscape for AI systems.

## Decision

Introduce a vendored adversarial evaluation suite with a two-tier failure
model, integrated into the existing pytest and CI infrastructure.

### Corpus

A curated JSON file at `tests/fixtures/adversarial/owasp_llm_top10.json`
containing ~100-400 payloads sourced from the OWASP LLM Top 10 2026
taxonomy. Each entry carries an `id`, `category`, `payload`, `tier`
(bright\_line or extended), `expected_flag`, `source`, and `notes`.

The corpus is **vendored** (checked into the repository), not fetched at
test time. This preserves the project's offline-first test stance.

### Failure model

**Bright-line tier** (~40-80 payloads): payloads that exercise patterns
AIPEA already implements (`INJECTION_PATTERNS`, homoglyph normalization,
zero-width normalization). These **must pass**. A single failure blocks CI.
Includes false-positive controls (benign queries that must NOT flag).

**Extended tier** (~50-300 payloads): real adversarial techniques
(paraphrases, encoding bypass, multi-language, role-play escape, indirect
injection) that regex-only defense may not yet handle. These are
**measured against a baseline snapshot** committed at
`tests/fixtures/adversarial/baseline.json`. CI fails only if the
pass rate regresses from the snapshot.

### Integration

- New pytest marker: `@pytest.mark.adversarial`.
- New Makefile targets: `make adversarial`, `make adversarial-update-baseline`.
- Runs in the existing CI `test` job (no new workflow needed).
- Adding `tests/test_adversarial.py` does not trigger the AI
  second-reviewer gate (test files are not in the `paths:` filter).

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| Third-party library (Garak/Giskard) as dev dep | Richer coverage, professional tooling | Breaks offline-first stance; heavyweight dep; network at test time | Offline-first is a core design principle |
| Strict: all tests must pass | Strongest signal | ~50%+ of realistic payloads will fail immediately against regex-only; forces corpus downsizing or blocks the wave | Unrealistic for v1 |
| Measurement-only (report, never fail) | Zero merge friction | No mechanical regression protection; degradation is silent | Loses the core value proposition of the suite |
| Fetch corpus at test time | Always fresh | Network dependency; flaky CI; offline-first violation | Same as third-party lib concerns |

## Consequences

### Positive

- First external adversarial corpus in the project's history.
- Measured, honest security posture: bright-line coverage is strict;
  extended coverage is tracked and can only improve.
- Baseline snapshot makes regressions mechanically detectable.
- False-positive controls prevent corpus rot from over-aggressive tuning.
- Zero new runtime dependencies.

### Negative

- Establishes `tests/fixtures/` directory convention (new precedent).
- Corpus curation requires periodic updates as OWASP taxonomy evolves.
- Extended-tier pass rate will be low initially (~30-50%), which is honest
  but may surprise readers who conflate "measured" with "passing."

### Neutral

- The baseline snapshot is an explicit record of current capability. When
  `security.py` improvements land, `make adversarial-update-baseline`
  regenerates it — the ratchet only moves forward.
