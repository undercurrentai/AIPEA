# ADR-006: LLM-Driven Red Team Engine

- **Status**: Proposed
- **Date**: 2026-04-15
- **Author**: @joshuakirby (with Claude design partnership)
- **Implements**: ROADMAP D5 (continuous adversarial generation)
- **Depends on**: [ADR-005](./ADR-005-adversarial-evaluation-suite.md) (Adversarial Evaluation Suite)

## Context

ADR-005 shipped AIPEA's first external adversarial corpus — 120 curated
OWASP LLM Top-10 payloads with a two-tier failure model. On day one, the
corpus found a genuine gap: the canonical "ignore all previous
instructions" string bypasses the scanner's regex. This validates the
corpus approach but surfaces its limitation: **static corpora age.**
OWASP LLM Top 10 2026 will be partially obsolete by 2027. Human curation
scales linearly with effort.

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
| Manual corpus expansion only | Zero cost, zero deps | Doesn't scale; curator blind spots persist; ages between updates | ADR-005's day-one finding proves the gap |
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
