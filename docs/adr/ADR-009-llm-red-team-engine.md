# ADR-009: LLM-Driven Red Team Engine

- **Status**: Proposed
- **Date**: 2026-04-15 (renumbered from ADR-006 on 2026-04-27 to follow
  ADR-008's renumber)
- **Author**: @joshuakirby (with Claude design partnership)
- **Implements**: ROADMAP D5 (continuous adversarial generation)
- **Depends on**: [ADR-008](./ADR-008-adversarial-evaluation-suite.md) (Adversarial Evaluation Suite)

## Context

ADR-008 shipped AIPEA's first external adversarial corpus — 120 curated
OWASP LLM Top-10 payloads with a two-tier failure model. The corpus's
original draft (2026-04-15) flagged the canonical "ignore all previous
instructions" string as bypassing the regex; v1.6.1 (PR #50) closed
that specific gap before the corpus landed, so on rebase the corpus
*validates* the v1.6.1 fix rather than exposes a live bypass. The
underlying limitation of static corpora remains the design driver:
**static corpora age.** OWASP LLM Top 10 2026 will be partially obsolete
by 2027. Human curation scales linearly with effort, and v1.6.1 is one
data point in a longer arc — the next bypass family is unknown.

The 2026 landscape of automated red-teaming tools — Garak (NVIDIA),
Promptfoo, DeepTeam (Confident AI), AutoRedTeamer — demonstrates that
**LLM-driven adversarial generation is now a standard practice** for
continuous security evaluation. AIPEA can adopt this pattern without
embedding ML in the core library: the generator calls an LLM via httpx
(the same infrastructure AIPEA uses for Ollama and search providers).

### External References

- [Garak v0.14.0](https://github.com/NVIDIA/garak) (NVIDIA, Feb 2026):
  four-component architecture (Generators, Probes, Detectors, Buffs) for
  LLM vulnerability scanning. AIPEA's red-team engine maps to a
  simplified version: LLM provider = Generator, technique-seeded prompts
  = Probes, SecurityScanner = Detector.
- [AutoRedTeamer](https://openreview.net/forum?id=DVmn8GyjeD)
  (OpenReview): agent architecture with memory-based attack selection,
  enabling deliberate exploration of new attack vectors.
- [Promptfoo red-teaming](https://www.promptfoo.dev/docs/red-team/):
  plugin-based payload generation with CI/CD Level 3 integration
  (automated suites where high-severity findings block deployment).
- [DeepTeam](https://github.com/confident-ai/deepteam) (Confident AI):
  20+ research-backed adversarial attack methods for LLM red-teaming.
- [AI Red Teaming: Enterprise LLM Security Playbook 2026](https://www.securebydezign.com/articles/llm-red-teaming.html):
  multi-layered defense architecture (input sanitization, model-level,
  output filtering).
- NIST AI RMF 1.0 (AI 100-1), MAP function: adversarial testing as a
  core risk-identification activity.

## Decision

Introduce an optional `aipea redteam` CLI command that uses an LLM to
generate novel adversarial payloads, evaluates them against
`SecurityScanner`, and produces corpus-extension candidates and audit
reports.

### Architecture

The engine mirrors Garak's Probe/Detector pattern in a lightweight form:

1. **Generator** — an LLM (Anthropic, OpenAI, or local Ollama) called via
   httpx. Returns structured JSON payloads.
2. **Technique seeds** — the generation prompt targets one technique class
   at a time: `encoding_bypass`, `paraphrase`, `role_play`,
   `multi_language`, `indirect_injection`, `delimiter_abuse`,
   `unicode_evasion`, `instruction_smuggling`.
3. **Adversarial-against-corpus loop** — the prompt includes AIPEA's
   existing bright-line patterns and asks for novel bypasses.
4. **Iterative refinement** (up to 3 rounds) — payloads that the scanner
   caught are fed back with: *"these were detected; generate variants
   that preserve intent but evade these patterns."*
5. **Evaluation** — each payload is scanned via `SecurityScanner.scan()`.
   Results are classified as detected/missed.
6. **Output** — JSON corpus extension file + Markdown audit report.

### Provider abstraction

A `RedTeamProvider` protocol with three implementations, all using httpx
only (no SDK dependencies):

- `AnthropicProvider` — calls `/v1/messages`
- `OpenAIProvider` — calls `/v1/chat/completions`
- `OllamaProvider` — calls local `/api/generate` (existing AIPEA pattern)

Auth via env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) following the
same convention as Exa/Firecrawl.

### Output contract

Two artifacts per run:

- `tests/fixtures/adversarial/generated/<provider>-<date>.json` — raw
  payloads with detection results, reviewable by humans before merge into
  the canonical corpus.
- `docs/security/redteam-report-<date>.md` — human-readable summary with
  catch rate, novel bypasses, technique breakdown, recommended corpus
  additions.

### CLI surface

```
aipea redteam --provider claude --num 50 --output reports/
aipea redteam --ollama --num 50       # offline mode
aipea redteam --extend-corpus          # auto-append to generated/ for review
```

### Where it lives

- New package: `src/aipea/redteam/` (`generator.py`, `providers.py`).
- Registered as `aipea redteam` CLI subcommand (alongside `configure`,
  `check`, `doctor`).
- Zero new runtime dependencies — httpx is already required; typer is
  already in `[cli]` extras.

### CI integration (optional)

A scheduled GitHub Actions workflow running weekly/monthly:
- Generates 50 payloads against the latest `main`.
- Opens an auto-PR with corpus-extension candidates for human review.
- Cost-bounded at ~$2-5/run ($100-250/yr at weekly cadence).

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| Use Garak directly as dev dep | Rich probe library, NVIDIA-maintained | Heavyweight dep (~50 transitive packages); breaks offline-first; Garak probes target LLM responses, not input scanners | Architecture mismatch — Garak tests model outputs, not input filters |
| Manual corpus expansion only | Zero cost, zero deps | Doesn't scale; curator blind spots persist; ages between updates | The Wave-19/20 Unicode bypasses (Cyrillic homoglyphs #97, ZWSP #108) — caught by internal audit only — prove curator blind spots |
| Hire human red-team only | Highest quality findings | $50K-$150K per engagement; point-in-time, not continuous | Complementary, not alternative — D5 generates the budget justification for this |
| Prompt-engineer against ChatGPT manually | Quick, free | Ad-hoc; unreproducible; no CI integration; no structured output | D5 automates this with structured technique seeding |

## Consequences

### Positive

- Continuous adversarial pressure that scales with LLM capability.
- Structured corpus growth via human-reviewed auto-PRs.
- Generates the data artifact needed to justify external audit budget.
- Zero new runtime deps; offline mode via Ollama.
- Audit-ready report artifacts committed to `docs/security/`.

### Negative

- Per-run cost ($1-5 for cloud providers; free for Ollama).
- Generated payloads require human triage before merge (cannot auto-merge
  adversarial content into the test suite).
- The generator's quality depends on the frontier model's creativity;
  Ollama local models may produce lower-quality payloads.

### Neutral

- The engine tests AIPEA's *input scanner*, not an LLM's responses. This
  is architecturally different from Garak/Promptfoo/DeepTeam, which test
  model outputs. Both approaches are complementary.

---

## Implementation Status (informational; status field unchanged)

As of 2026-04-28, the **B1 foundation** is in-progress on branch
`feat/redteam-b1-providers`:

| Component | Status |
|-----------|--------|
| `RedTeamProvider` Protocol + `RedTeamResult` frozen dataclass + `Technique` StrEnum (8 OWASP categories) | ✓ landed (`src/aipea/redteam/_types.py`) |
| Long-call response polling helper extracted from `gpt_review.py:219-253` | ✓ landed (`src/aipea/redteam/_polling.py`); CI workflow refactor to import from package is B1 follow-up |
| API-key + URL resolution chain (env > config > default) | ✓ landed (`src/aipea/redteam/_resolve.py`) |
| Provider registry + import-time `_validate_provider` (async-coroutine + attribute checks) | ✓ landed (`src/aipea/redteam/providers/__init__.py`) |
| `OllamaProvider` reference impl (httpx → local Ollama, 5 error categories) | ✓ landed (`src/aipea/redteam/providers/ollama.py`) |
| 52 foundation tests (97.33% module coverage) | ✓ landed (`tests/test_redteam_b1_foundation.py`) |
| `AnthropicProvider` (streaming with adaptive thinking for Opus 4.7) | B1 follow-up |
| `OpenAIResponsesProvider` (`gpt-5.5-pro` background mode + 25-min poll cap) | B1 follow-up |
| `OpenAICodexProvider` (`gpt-5.3-codex`) | B1 follow-up |
| Generator (technique-seeded prompts + iterative refinement ≤3 rounds) | B1 follow-up |
| Evaluator (`SecurityScanner.scan()` + TF-IDF novelty score) | B1 follow-up |
| Reporter (Markdown audit report writer) | B1 follow-up |
| CLI integration (`aipea redteam run / list-techniques / list-providers`) | B1 follow-up |
| `pyproject.toml [project.optional-dependencies] redteam = []` extras | B1 follow-up |
| `.github/scripts/gpt_review.py` refactor to import shared polling helper | B1 follow-up |
| Budget ledger + circuit breaker + `aipea redteam daemon` continuous mode | B2 |
| Council Mode synthesis + AgenticRed generational archive + weekly cron | B3 |

**Status field**: `Proposed` (unchanged). The status moves to
`Accepted` only when B3 lands per the multi-PR plan; the B1 / B2
intermediate merges document themselves via this Implementation
Status table rather than promoting the formal status. This avoids
ratcheting the ADR through partial states — the design remains
proposed until the full design is realized.
