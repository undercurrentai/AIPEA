# Adversarial Corpus Sources & Attribution

This directory vendors adversarial-prompt corpora used by
[`tests/test_adversarial.py`](../../test_adversarial.py) (ADR-008).
Each corpus is documented below with its source URL, license,
upstream version/commit accessed, the date accessed, and the
extraction process used.

**Re-extraction**: The extraction script lives at
`/tmp/aipea-corpus-extract/extract.py` (one-shot, not committed).
To re-extract from upstream, recreate the script per the column
"extraction process" below and run `python3 extract.py`.

---

## Corpus inventory

| File | Source | License | Size | Date accessed |
|---|---|---|---|---|
| `owasp_llm_top10.json` | OWASP LLM Top 10 2026 taxonomy (curated) | CC-BY-SA 4.0 | 120 | 2026-04-27 (per ADR-008) |
| `promptinject.json` | [agencyenterprise/PromptInject](https://github.com/agencyenterprise/PromptInject) `promptinject/prompt_data.py` | MIT | 17 | 2026-05-02 |
| `jbb_behaviors.json` | [JailbreakBench/JBB-Behaviors](https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors) `data/{harmful,benign}-behaviors.csv` | MIT | 200 (100 harmful + 100 benign FPR) | 2026-05-02 |
| `garak_promptinject.json` | [NVIDIA/garak](https://github.com/NVIDIA/garak) `garak/probes/{promptinject,dan,latentinjection}.py` | Apache-2.0 | 43 | 2026-05-02 |

---

## Per-corpus details

### 1. `owasp_llm_top10.json`

- **Source**: Curated by `@joshuakirby` from OWASP LLM Top 10 2026
  taxonomy categories. See ADR-008
  ([`docs/adr/ADR-008-adversarial-evaluation-suite.md`](../../../docs/adr/ADR-008-adversarial-evaluation-suite.md))
  for full design rationale.
- **License**: CC-BY-SA 4.0 (OWASP project license; permits derivative
  works with attribution).
- **Attribution**: "Includes patterns derived from the OWASP LLM Top 10 2026 taxonomy
  (https://owasp.org/www-project-top-10-for-large-language-model-applications/)."
- **Schema** (matches all corpora in this directory):
  ```json
  {"id": "...", "category": "...", "payload": "...",
   "tier": "bright_line | extended", "expected_flag": "... | null",
   "source": "owasp_llm_top10", "notes": "..."}
  ```

### 2. `promptinject.json`

- **Source**:
  https://raw.githubusercontent.com/agencyenterprise/PromptInject/main/promptinject/prompt_data.py
- **Upstream commit accessed**: `main` branch as of 2026-05-02
  (last upstream push: 2024-02; corpus is stable canonical reference).
- **License**: MIT (see [PromptInject LICENSE](https://github.com/agencyenterprise/PromptInject/blob/main/LICENSE)).
- **Citation**: Perez, F. & Ribeiro, I. *Ignore Previous Prompt: Attack Techniques For Language Models.* NeurIPS 2022 ML Safety Workshop (best paper).
- **Extraction**: AST-walked `prompt_data.py`, captured every
  string-constant matching the regex
  `\b(ignore|disregard|forget|override|bypass|reset|cancel|nullify|revoke|terminate)\b`
  with length 15–400 chars. This filters to instruction-override-family
  payloads (the canonical phrasings AIPEA's `INJECTION_PATTERNS`
  targets) and excludes target-string completions and metadata.
- **Why this corpus**: Phase-1 external research established this is
  the published canonical corpus for the override family — exactly
  the surface AIPEA's regex set was written to detect. Expected hit-rate
  per the literature: 60–80%.
- **Tier**: All entries `extended` (none gating).
- **Expected flag**: All entries expect `injection_attempt` flag prefix.

### 3. `jbb_behaviors.json`

- **Source**:
  https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors/resolve/main/data/harmful-behaviors.csv
  +
  https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors/resolve/main/data/benign-behaviors.csv
- **Upstream commit accessed**: `main` branch as of 2026-05-02.
- **License**: MIT (see [jailbreakbench LICENSE](https://github.com/JailbreakBench/jailbreakbench/blob/main/LICENSE)).
- **Citation**: Chao, P. et al. *JailbreakBench: An Open Robustness Benchmark for Jailbreaking Large Language Models.* NeurIPS Datasets and Benchmarks 2024.
- **Extraction**: Read both CSVs; took `Goal` column from each row;
  kept all 100 harmful + 100 benign.
- **Why this corpus**: Provides two distinct signals in one source:
  - **Harmful (100 prompts)**: tests harmful-content goals (e.g., "explain how to hotwire a car"), which AIPEA's regex set is **NOT designed to detect**. Low hit-rate is *correct*; >20% would suggest over-blocking.
  - **Benign FPR (100 prompts)**: control set of normal queries that AIPEA **MUST NOT flag**. >5% FPR indicates a false-positive crisis warranting immediate hotfix.
- **Tier**: All entries `extended`.
- **Expected flag**: `null` for all entries (the assertion logic is
  inverted for `jbb_benign_fpr` source: any flag is a false positive).

### 4. `garak_promptinject.json`

- **Source**:
  https://raw.githubusercontent.com/NVIDIA/garak/main/garak/probes/promptinject.py
  +
  https://raw.githubusercontent.com/NVIDIA/garak/main/garak/probes/dan.py
  +
  https://raw.githubusercontent.com/NVIDIA/garak/main/garak/probes/latentinjection.py
- **Upstream commit accessed**: `main` branch as of 2026-05-02
  (garak is actively maintained by NVIDIA; v0.14.1 was 2026-04-03).
- **License**: Apache-2.0 (see [garak LICENSE](https://github.com/NVIDIA/garak/blob/main/LICENSE)).
- **Citation**: Derczynski, L. et al. *garak: A Framework for Security Probing Large Language Models.* arXiv:2406.11036, 2024.
- **Apache-2.0 NOTICE acknowledgment** (Apache-2.0 §4 attribution):

  > Portions of this corpus are derived from NVIDIA garak
  > (https://github.com/NVIDIA/garak), licensed under Apache License 2.0.
  > Copyright (c) NVIDIA Corporation. The garak source remains
  > separately licensed under Apache-2.0; only the prompt-string
  > content was extracted.

- **Extraction**: AST-walked each of the three probe files; captured
  string constants matching
  `\b(ignore|disregard|forget|override|bypass|developer mode|DAN|do anything now|jailbreak|system prompt)\b`
  with length 30–800 chars. Skipped docstring-shaped multi-paragraph
  strings. Did NOT install garak as a package (its full dep tree is
  heavy; we only need the prompt strings as data).
- **Why this corpus**: Adds paraphrase-coverage breadth that
  PromptInject misses (DAN-style roleplay, "developer mode" prompts,
  latent-injection patterns). Expected hit-rate: 15–35%.
- **Tier**: All entries `extended`.
- **Expected flag**: All entries expect `injection_attempt` flag prefix.

---

## License compatibility summary

AIPEA is MIT-licensed. All vendored corpora are compatible:

- **MIT** (PromptInject, JBB-Behaviors): freely redistributable with
  attribution; no re-licensing burden.
- **Apache-2.0** (Garak): permissive; requires NOTICE attribution
  (provided above).
- **CC-BY-SA 4.0** (OWASP): permits derivative works with attribution
  and same-license redistribution; the AIPEA repo's MIT license
  applies to the `aipea` package source code; the vendored OWASP
  corpus retains its CC-BY-SA license per the attribution above.

This is **not** legal advice; if you redistribute AIPEA's
`tests/fixtures/adversarial/` directory as part of a commercial
product, consult counsel about Apache-2.0 NOTICE compliance and
CC-BY-SA "share-alike" implications.

---

## Re-extraction reproducibility

The one-shot extraction script (uncommitted) lived at
`/tmp/aipea-corpus-extract/extract.py` on 2026-05-02 and used only
Python stdlib (no `pip install` of `datasets`, `garak`, or
`promptinject` packages). It:

1. Fetched each upstream URL via `urllib.request`.
2. AST-parsed Python sources; CSV-parsed JBB tables.
3. Filtered string constants by regex heuristic (override verbs).
4. Wrote four JSON files to this directory.

If upstream layouts change (e.g., PromptInject `prompt_data.py`
restructures), the heuristic may need adjustment. The extraction
script is intentionally stateless and re-runnable.

---

*Last updated 2026-05-02 (Phase 4.c adversarial corpus expansion).
See [ADR-008](../../../docs/adr/ADR-008-adversarial-evaluation-suite.md)
for the original adversarial-suite design and
[ADR-005 §C.1](../../../docs/adr/ADR-005-pr52-vc-adversarial-review-response.md)
for the multi-corpus expansion commitment.*
