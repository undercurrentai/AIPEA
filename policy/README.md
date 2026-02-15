# OPA Policy Directory

Deny-by-default egress policies for AI agents and services, enforced via [Open Policy Agent](https://www.openpolicyagent.org/) (OPA) / [Conftest](https://www.conftest.dev/).

## Setup

1. Install Conftest:
   ```bash
   # macOS
   brew install conftest

   # Linux
   curl -L -o conftest.tar.gz \
     https://github.com/open-policy-agent/conftest/releases/latest/download/conftest_Linux_x86_64.tar.gz
   tar xzf conftest.tar.gz && sudo mv conftest /usr/local/bin/
   ```

2. Run policy checks:
   ```bash
   conftest test --policy policy --no-color .
   ```

## Writing Policies

- Policies use [Rego](https://www.openpolicyagent.org/docs/latest/policy-language/) syntax.
- `agent-egress.rego` — deny-by-default egress allowlist per agent (S4.7 in Engineering Standards).
- Add new `.rego` files to this directory for additional policy domains.
- CI (`ci.yml`) runs `conftest test` automatically when this directory exists.

## How It Works

Each policy file defines `deny` rules. If any `deny` rule matches, the check fails. The `allow` rule is a whitelist — only explicitly listed agent/destination pairs are permitted.

Input format expected by `agent-egress.rego`:
```json
{
  "agent_id": "pricing-agent",
  "dst_host": "api.pricing.internal"
}
```
