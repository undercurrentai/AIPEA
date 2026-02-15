# Contributing

- Run `make all` before pushing; PRs failing any gate are closed or must include an approved exception memo.
- Change classes: A (style), B (refactor), C (behavioral). Class C requires backtest delta report and risk sign-off.
- Any new service must ship with OpenAPI/Proto spec, perf SLOs, and observability fields (`request_id`, `seed_id`, `dataset_hash`).
- Deviations from standard tooling require an ADR in `docs/adr/`.
- AI-assisted contributions must include attribution (see PR template).
