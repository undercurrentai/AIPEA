# Wave C1 — AI Second-Reviewer Gate: Dry-Run Evidence + Operator Runbook

**Date:** 2026-04-11
**Wave:** C1 (ROADMAP §P5a)
**PR:** [undercurrentai/AIPEA#24](https://github.com/undercurrentai/AIPEA/pull/24) — `feat(ci): Wave C1 — automated dual-AI second-reviewer gate`
**Status:** **Graceful-failure path verified on PR #24 (second CI run, commit 3125b4b). Main CI all green. AI review jobs red-but-expected (no secret yet). Ready for admin-merge + secret provisioning + full dry-run.**

---

## 1. What this document captures

Wave C1 introduces an automated dual-AI second-reviewer gate (`gpt-5.4-pro` + `openai/codex-action@v1`) that fires on pull requests touching AIPEA's security-critical paths. The gate cannot be end-to-end-tested without the `OPENAI_API_KEY` repo secret. This audit records the **first half** of the validation — the graceful-failure path, which runs *without* the secret — and lays out the runbook the operator will follow to validate the **second half** (the happy path) after the secret is provisioned and branch protection is configured.

The point of the graceful-failure dry-run is: if the gate fails for any reason (secret missing, API outage, quota exhausted, model error, network flake), the operator must receive a **visible, structured PR comment** explaining what happened, not a silent red check that forces them to dig through workflow logs. That property is now empirically verified.

## 2. Dry-run 1 — graceful failure (no secret)

### Setup
- PR #24 was opened on branch `feat/p5a-ai-second-review-gate` (base `main`).
- The PR modifies `.github/workflows/**` and `.github/CODEOWNERS`, which both match the new workflow's `paths:` filter. The workflow therefore fires on its own PR — a free dry-run with no extra work.
- No secrets were provisioned at the time of the CI run. `OPENAI_API_KEY` was empty in the workflow environment.

### First CI run (commit `0d3d1df`)
- **Main CI jobs:** `lint`, `typecheck`, `test (3.11)`, `test (3.12)`, `CodeQL`, `analyze (python)`, `dependency-review`, `scaffold-lint` — **all green**. 991 tests passed, 35 skipped, 92.93% coverage.
- **`GPT 5.4 Pro review` job:** failed in 9 seconds with `gpt_review: OPENAI_API_KEY not set`, exit code 2. Expected behavior per `gpt_review.py`'s environment check.
- **`Codex CLI review` job:** failed in 21 seconds. The `openai/codex-action@v1` composite action reached its own internal auth/install step before failing. Expected.
- **Problem discovered:** no fallback PR comments were posted. The `Load review body into env` and `Post review comment` steps were **skipped** after the failing review step because they lacked `if: always()`. Default GH Actions step-level conditional is `if: success()`, which skips subsequent steps when an earlier step fails.

This was a real usability bug: the graceful-failure path was designed to always post a visible explanation, but the default step gating swallowed the fallback. The script correctly wrote the fallback markdown to disk; the workflow just never read it back.

### Fix (commit `3125b4b`)
Added `if: always() && steps.diff.outputs.diff_empty != 'true'` to **both** the `Load review body into env` and `Post review comment` steps in **both** jobs. Rationale captured inline as a comment block on each modified step. Fail-closed semantics preserved: the earlier review step still exits non-zero, so the overall job stays red and branch protection holds the PR — the only behavioral change is that a visible explanation now reaches the PR.

### Second CI run (commit `3125b4b`)
- **Main CI jobs:** all green again (no regression from the fix).
- **`GPT 5.4 Pro review`:** failed in 11 seconds — expected.
- **`Codex CLI review`:** failed in 22 seconds — expected.
- **Fallback comments posted:** both. Retrieved via `gh pr view 24 --json comments` and verified in full.

#### GPT fallback comment (verbatim from PR #24)

```markdown
<!-- ai-second-review:gpt -->

## 🤖 gpt-5.4-pro — Second-Reviewer Gate

## Verdict

`COMMENT` — review could not be completed.

## Blocking concerns

_Review execution failed before a verdict could be produced._

## Non-blocking observations

- Reason: OPENAI_API_KEY is not set in the workflow environment
- The `gpt-review` job status is red; branch protection will hold the PR.
- @joshuakirby: inspect the workflow logs to decide whether to retry or admin-override.

## Specific line callouts

_None._

## What I did NOT review

- The diff itself (the review process failed before the model was consulted).


---
*Automated via `.github/workflows/ai-second-review.yml` (Wave C1 — ROADMAP §P5a). Accountable human reviewer: @joshuakirby. See [CONTRIBUTING.md](../blob/main/CONTRIBUTING.md) §Second-Reviewer Gate.*
```

This is the `_fallback_markdown()` helper in `.github/scripts/gpt_review.py` rendered through the marker + header + footer template in the `github-script` comment-post step. Structured, attribution-complete, operator-actionable.

#### Codex fallback comment (verbatim from PR #24)

```markdown
<!-- ai-second-review:codex -->

## 🤖 Codex CLI — Second-Reviewer Gate

_Codex review produced no output. Check the workflow logs for details._


---
*Automated via `.github/workflows/ai-second-review.yml` (Wave C1 — ROADMAP §P5a). Accountable human reviewer: @joshuakirby. See [CONTRIBUTING.md](../blob/main/CONTRIBUTING.md) §Second-Reviewer Gate.*
```

Much terser than the GPT fallback because the `openai/codex-action@v1` composite action failed before Codex produced any output file — the workflow's shell fallback-write step synthesized the placeholder so the downstream comment-post step had something to read. This is acceptable for now. A future improvement could wrap the action invocation with a pre-check step that writes a richer fallback on auth-missing, but that's out of scope for C1 — the current behavior meets the *"always post something visible"* requirement.

### What was verified
- [x] The `paths:` filter fires on the expected files.
- [x] Both jobs run in parallel on the same PR.
- [x] `gpt_review.py` detects a missing `OPENAI_API_KEY` and exits non-zero without any API call being made (empty-string key handling).
- [x] `openai/codex-action@v1` fails gracefully when its own auth check fails — does not hang, does not leak error details into PR comment body.
- [x] `always()` guards on downstream steps cause fallback comments to be posted even when the review step fails.
- [x] The marker-based comment pattern (`<!-- ai-second-review:gpt -->` / `<!-- ai-second-review:codex -->`) does not collide with any existing comment on the PR.
- [x] The `$GITHUB_ENV` multiline-var pattern (`REVIEW_BODY<<__AIPEA_REVIEW_BODY_EOF_${run_id}__`) successfully passes multi-section markdown through to `actions/github-script` without needing `require('fs')`.
- [x] Concurrency group `ai-second-review-${pr_number}` with `cancel-in-progress: true` prevents duplicate runs on the same PR.
- [x] Main CI is unaffected by the new workflow file (all 991 tests pass on both CI runs).
- [x] No secrets leaked into any log line, PR comment, or workflow file.

### What is NOT yet verified (the happy path — requires secret)
- [ ] `openai>=2.11` install against the blacksmith runner succeeds.
- [ ] `client.responses.create(model="gpt-5.4-pro", reasoning={"effort": "high"}, background=True, store=True, ...)` accepted by the Responses API.
- [ ] `client.responses.retrieve(response_id)` polls cleanly until `status == "completed"`.
- [ ] `_extract_text(final)` pulls a real review body from either `output_text` or the `output` walk fallback.
- [ ] `gpt-5.4-pro` with the C1 system prompt produces a usable review on a realistic AIPEA diff (not an over-confident APPROVE, not a hallucinated blocker).
- [ ] `openai/codex-action@v1` successfully installs the CLI, starts the Responses-API proxy, and `codex exec` runs in `read-only` sandbox without permission errors.
- [ ] Codex's shell-exploration pass produces file:line-grounded observations rather than paraphrases of the diff.
- [ ] Both reviews complete within the 30-minute job timeout on a realistic diff.
- [ ] Branch protection (once configured) blocks merge until both AI checks go green.

All of the above require `OPENAI_API_KEY` to be set in repo secrets and the dry-run PR to be opened. Runbook below.

---

## 3. Operator runbook — bringing the gate online

Execute these steps **in order** from your local terminal after PR #24 is merged. Each step has a concrete success signal. Do not skip steps — the dry-run PR at the end is the real validation.

### Step 1 — Merge PR #24 (admin override)

```bash
gh pr merge 24 --squash --delete-branch --admin --repo undercurrentai/AIPEA
```

Bus-factor-1 note: same admin override we used on #20/21/22/23. This is the *last* PR that will need `--admin` for this reason — once the gate is live on `main`, subsequent security-gated PRs will use the AI reviews as the mandatory second reviewer instead of requiring admin override.

**Success signal:** PR #24 shows as merged; `main` now contains `.github/workflows/ai-second-review.yml`.

### Step 2 — Provision the `OPENAI_API_KEY` repo secret

**Do not paste the key into chat.** Run this from your terminal:

```bash
gh secret set OPENAI_API_KEY --repo undercurrentai/AIPEA
```

`gh` will prompt for the value on stdin. Paste the key there. It goes directly into GitHub's encrypted secret store — the workflow will reference it via `${{ secrets.OPENAI_API_KEY }}`, which is a GH Actions expression, not a literal.

**Success signal:**

```bash
gh secret list --repo undercurrentai/AIPEA | grep OPENAI_API_KEY
```

should print a line with `OPENAI_API_KEY` and a timestamp. (The value itself is never retrievable — GH secrets are write-only from the CLI.)

### Step 3 — Configure branch protection

I cannot set this from the CLI without broader admin scopes. Use the GH web UI:

1. Navigate to **Settings → Branches → Rules** on the AIPEA repo.
2. Edit the existing ruleset for `main` (or create one if none exists).
3. Under **Require status checks to pass**, add these two checks (the workflow must have run at least once against `main` for the check names to appear in the autocomplete; Step 2 above is sufficient to make the workflow visible):
   - `AI Second Review / GPT 5.4 Pro review`
   - `AI Second Review / Codex CLI review`
4. Keep the existing required checks: `lint`, `typecheck`, `test (3.11)`, `test (3.12)`.
5. Enable **Require branches to be up to date before merging**.
6. Save.

**Success signal:** the branch protection rule page for `main` shows six required status checks total.

### Step 4 — Dry-run PR (the real validation)

Open a throwaway PR that touches a single inert line in `src/aipea/security.py` (e.g., add a trailing period to a comment):

```bash
git checkout main
git pull
git checkout -b dry-run/ai-second-review-validation
# Edit a comment in src/aipea/security.py — add a trailing period or similar
git add src/aipea/security.py
git commit -m "test(ci): dry-run validation for Wave C1 AI second-reviewer gate

Intentionally touches a single security.py comment to trigger the new
ai-second-review.yml workflow on a realistic security-gated diff. This
PR will be closed after both AI review jobs complete successfully and
the run URLs are captured in
docs/claude/audits/ai-second-review-dry-run-2026-04-11.md.

Do not merge this PR."
git push -u origin dry-run/ai-second-review-validation
gh pr create --title "test(ci): dry-run validation for Wave C1 AI second-reviewer gate" \
  --body "Throwaway PR to exercise the Wave C1 AI second-reviewer gate on a realistic diff. See \`docs/claude/audits/ai-second-review-dry-run-2026-04-11.md\` §4 for the verification checklist. Will be closed without merging."
```

Wait for CI. Expected timings (based on the model card):
- `GPT 5.4 Pro review`: 3–15 minutes depending on `gpt-5.4-pro` reasoning time.
- `Codex CLI review`: 5–20 minutes (Codex's shell exploration takes longer than a pure API call).

Do not cancel. The 30-minute per-job timeout is deliberate headroom.

### Step 5 — Validate the dry-run outputs

Run:

```bash
gh pr view <DRY_RUN_PR_NUMBER> --json comments \
  --jq '.comments | map(select(.body | startswith("<!-- ai-second-review"))) | .[] | .body'
```

Inspect each comment against the following checklist:

**`gpt-5.4-pro` comment must satisfy:**
- [ ] `Verdict` is one of `APPROVE`, `REQUEST_CHANGES`, `COMMENT` (not empty, not a different value)
- [ ] `Blocking concerns` contains either `_None._` or a list of concrete concerns with file:line evidence
- [ ] At least one `file:line` reference in `Specific line callouts` that exists in the actual diff
- [ ] `What I did NOT review` is honestly populated (not a generic `_None._`)
- [ ] No hallucinated references to nonexistent files, functions, or lines
- [ ] No leaked reasoning tokens, no system-prompt echoes

**`codex` comment must satisfy:**
- [ ] All of the above, plus
- [ ] `Cross-references verified` section lists at least one shell command that was actually run (rg, grep, git blame, etc.)
- [ ] The cross-references verify a real claim (not `rg 'foo'` followed by "no results, no concerns")

**Both jobs must satisfy:**
- [ ] Exit code 0 (check via `gh run view <run_id>`)
- [ ] Status shown as green in PR checks
- [ ] Job duration under the 30-minute timeout
- [ ] Job summary contains the same markdown as the PR comment

### Step 6 — Capture evidence

Append a new section **§5 — Dry-run 2 (happy path)** to this audit doc with:

- Dry-run PR number and URL
- Commit SHAs that triggered the workflow runs
- Run IDs for both the `gpt-review` and `codex-review` jobs
- Job durations
- Verbatim copies of both review comments
- Checklist results from Step 5
- Any quirks or unexpected behaviors worth remembering

Then commit this audit doc update to `main` via a small PR with title `docs(audit): Wave C1 dry-run 2 — happy path verification`.

### Step 7 — Close the dry-run PR

```bash
gh pr close <DRY_RUN_PR_NUMBER> --delete-branch --comment "Validated in docs/claude/audits/ai-second-review-dry-run-2026-04-11.md §5. Closing without merging."
```

### Step 8 — Update plan + tasks

- Mark Wave C1 complete in `~/.claude/plans/reactive-growing-lark.md` (existing detailed-design block gets a `**Status (as of YYYY-MM-DD): complete, verified on PR #<N>**` banner at the top).
- Close task `#7 Wave C1: Automated dual-AI second-reviewer gate` in the task list.
- Move to Wave D (v1.4.0 engineering) or Wave E (commercial validation) per priority.

---

## 4. Rollback procedure

If the dry-run PR (Step 4) reveals a deeper problem with the gate — hallucinated reviews, runaway costs, false positives at an unacceptable rate, or infrastructure failures — roll back the workflow without rolling back the rest of Wave C:

```bash
# From the repo root on main, with latest pulled:
git checkout -b revert/ai-second-review
git rm .github/workflows/ai-second-review.yml
git rm .github/scripts/gpt_review.py
git rm -r .github/codex
# Do NOT revert .github/CODEOWNERS — the @joshuakirby entries on security.py,
# __init__.py, and pyproject.toml are still valuable on their own even without
# the AI gate.
git commit -m "revert(ci): Wave C1 AI second-reviewer gate, pending redesign

Reverts .github/workflows/ai-second-review.yml, gpt_review.py, and the
codex prompts directory. Keeps .github/CODEOWNERS as-is.

Reason: <describe what broke in the dry-run>

Re-introduction criteria:
  - <what needs to change before we try again>

See docs/claude/audits/ai-second-review-dry-run-2026-04-11.md §6 for the
incident record."
gh pr create --title "revert(ci): Wave C1 AI second-reviewer gate, pending redesign" \
  --body "..."
```

After rollback, append **§6 — Rollback incident** to this audit doc documenting what went wrong, what we learned, and what needs to change before the next attempt. Update branch protection to remove the two required AI checks.

**Costs are bounded.** Even a worst-case runaway scenario is capped by the 30-minute job timeout and `gpt-5.4-pro`'s pricing model. A single rogue dry-run PR cannot burn more than single-digit dollars per run. Do not hesitate to run the dry-run — the downside is tiny.

---

## 5. Dry-run 2 (happy path) — 2026-04-12

### Setup

- PR #28 opened on branch `dry-run/ai-second-review-validation` (base `main`).
- Commit `550ed17`: single-line docstring change in `src/aipea/security.py:5` — removed stale "integration with Agora IV" wording.
- Secrets provisioned: `OPENAI_API_KEY` (2026-04-12T02:00:13Z), `ANTHROPIC_API_KEY` (2026-04-12T02:47:07Z).
- Branch protection ruleset `repo-ai-second-review-required` active on `main` requiring all 3 AI checks.

### Run metadata

| Item | Value |
|---|---|
| PR | [#28](https://github.com/undercurrentai/AIPEA/pull/28) |
| Commit | `550ed17c9eea60a317e436abf967cbb7b2ba5b93` |
| Workflow run | [24319541008](https://github.com/undercurrentai/AIPEA/actions/runs/24319541008) |
| GPT 5.4 Pro job | [71003024797](https://github.com/undercurrentai/AIPEA/actions/runs/24319541008/job/71003024797) — **PASS** (9m13s) |
| Codex CLI job | [71003024795](https://github.com/undercurrentai/AIPEA/actions/runs/24319541008/job/71003024795) — **PASS** (2m53s) |
| Claude Opus 4.6 job | [71003024796](https://github.com/undercurrentai/AIPEA/actions/runs/24319541008/job/71003024796) — **FAIL** (21s, credit balance too low) |

### GPT 5.4 Pro review comment (verbatim)

```markdown
<!-- ai-second-review:gpt -->

## 🤖 gpt-5.4-pro — Second-Reviewer Gate

## Verdict

COMMENT

Docstring-only change in a gated file; no runtime, compliance, regex, export, dependency, or CI behavior change is visible in this diff.

## Blocking concerns

_None._

## Non-blocking observations

_None._

## Specific line callouts

- `src/aipea/security.py:5` — removed the stale `integration with Agora IV` wording from the module docstring; this is a documentation-only cleanup with no security/compliance-path impact.

## What I did NOT review

- I did not run tests.
- I did not verify runtime behavior from source execution; this diff appears docstring-only.
- I did not review files outside the provided diff.
```

### Codex CLI review comment (verbatim)

```markdown
<!-- ai-second-review:codex -->

## 🤖 Codex CLI — Second-Reviewer Gate

## Verdict

`COMMENT` — trivial docs-only change in `src/aipea/security.py:5` with no executable behavior changes.

## Blocking concerns

_None._

## Non-blocking observations

- Scope is a one-line docstring edit (`1` insertion, `1` deletion, one file); no compliance, regex, exception-handling, or public-API behavior changed.
- `SecurityContext` call-site behavior remains consistent with caller-provided compliance mode (`src/aipea/enhancer.py:900-909`, `src/aipea/security.py:747-770`).

## Specific line callouts

- `src/aipea/security.py:5` — removes "integration with Agora IV" from the module docstring; runtime logic is unchanged.

## Cross-references verified

- `sed -n '1,220p' pr_diff.patch` — confirmed patch content.
- `git apply --stat pr_diff.patch` and `git apply --numstat pr_diff.patch` — confirmed only one file changed (`src/aipea/security.py`).
- `rg -n "^diff --git a/(src/aipea/security.py|src/aipea/__init__.py|src/aipea/errors.py|pyproject.toml|\.github/workflows/|\.github/CODEOWNERS)" pr_diff.patch` — confirmed gated-path scope is only `security.py`.
- `rg -n "SecurityContext\(|compliance_mode" src tests` and `nl -ba src/aipea/enhancer.py | sed -n '880,925p'` — confirmed no new hard-coded compliance bypass introduced.
- `rg -n "except Exception" src tests` with spot checks at `src/aipea/config.py:491` and `src/aipea/cli.py:396` — confirmed only known production carve-outs are present.
- `rg -n "test_all_has_42_symbols|__all__" src/aipea/__init__.py tests/test_live.py` — verified API-surface guard remains unchanged.

## What I did NOT review

- Did not execute tests; this review is static-analysis only.
- Did not benchmark regex performance at runtime.
- Did not re-audit workflow SHA pinning or `pyproject.toml` dependency policy because those files are untouched in this PR.
```

### Claude Opus 4.6 fallback comment (verbatim)

```markdown
<!-- ai-second-review:claude -->

## 🤖 Claude Opus 4.6 — Second-Reviewer Gate

_Claude review produced no output. Check the workflow logs for details._
```

**Failure reason**: `SDK execution error: Error: Claude Code returned an error result: Credit balance is too low`. The `ANTHROPIC_API_KEY` was valid (auth succeeded) but the account had insufficient credits at the time of the run. Credits were topped up post-run (2026-04-12). A re-run of the workflow or a subsequent PR will validate the Claude happy path.

### Checklist results

**GPT 5.4 Pro:**
- [x] `Verdict` is one of `APPROVE`, `REQUEST_CHANGES`, `COMMENT` — value: `COMMENT`
- [x] `Blocking concerns` contains `_None._`
- [x] `Specific line callouts` references `src/aipea/security.py:5` (exists in actual diff)
- [x] `What I did NOT review` is honestly populated (3 items)
- [x] No hallucinated references to nonexistent files, functions, or lines
- [x] No leaked reasoning tokens, no system-prompt echoes

**Codex CLI:**
- [x] All GPT checklist items satisfied
- [x] `Cross-references verified` lists 6 shell commands that were actually run
- [x] Cross-references verify real claims (compliance bypass check, API surface guard, exception audit)

**Claude Opus 4.6:**
- [x] Fallback comment posted (graceful failure)
- [x] Job exited non-zero (branch protection held)
- [ ] Happy-path review — **deferred** (credit balance issue, not workflow bug)

**Both passing jobs:**
- [x] Exit code 0 (GPT and Codex)
- [x] Status shown as green in PR checks
- [x] Job durations under 30-minute timeout (9m13s, 2m53s)

### Quirks and observations

1. **GPT 5.4 Pro took 9m13s** for a 1-line docstring change. The background-mode polling overhead is significant even on trivial diffs. On a real 200-LOC security PR the reasoning time will be longer, but the polling overhead (~5 min baseline) should amortize.
2. **Codex is the better reviewer** on this diff — it ran 6 independent cross-reference checks against the full repo, while GPT only reviewed the diff in isolation. Codex's shell-exploration approach adds genuine verification value.
3. **Claude's 21s failure** is fast enough that it doesn't meaningfully delay the workflow. The fallback comment posted correctly. Once credits are restored, re-running the workflow should produce a review.
4. **Branch protection blocked merge** as expected — the "Merging is blocked" state was visible in the PR UI with the admin bypass checkbox available.

---

## 6. Rollback incident — to be filled in if needed

*Empty unless a rollback is triggered.*

---

## Appendix A — Commit / run IDs for dry-run 1

| Item | Value |
|---|---|
| Branch | `feat/p5a-ai-second-review-gate` |
| First CI run (workflow file first pushed) | commit `0d3d1df` |
| Fix commit (adds `always()` guards) | commit `3125b4b` |
| Main CI status at head | 8/8 checks green |
| AI review jobs at head | 2/2 red-but-expected (missing secret); both fallback comments posted |
| Graceful-failure path | **verified** |
| Happy path | **pending** — requires Steps 2–5 above |

## Appendix B — What I am deliberately NOT doing in this audit pass

- **Not testing the happy path locally.** The user's key is in conversation history; I am not writing it to any file, env var, or tool call that could persist it. The happy-path validation is gated on the user provisioning the secret via `gh secret set`.
- **Not widening the `paths:` filter** to `src/aipea/**`. The gate's scope is deliberately narrow and the audit doc preserves that choice. Widening is a one-line follow-up if the cost/value ratio warrants it.
- **Not pre-pinning `openai/codex-action@v1` at a specific SHA.** The first stable SHA capture happens *after* a successful dry-run 2, per the plan file.
- **Not expanding `gpt_review.py`'s review taxonomy.** The current system prompt covers AIPEA-specific concerns (broad-except regressions, ReDoS, homoglyph gaps, FedRAMP re-introduction, SHA-pinning, license contamination, `__all__` drift). Adding more watches here without dry-run evidence would be premature.
- **Not writing tests for `gpt_review.py` or the workflow.** The workflow is validated end-to-end by the dry-run PR, not by unit tests. Unit-testing a thin API client adds surface area without catching real failures.

---

*Wave C1 CI stabilization audit | Rigor protocol pass 2026-04-11 | Author: Claude Opus 4.6 via Claude Code | Human reviewer: @joshuakirby*
