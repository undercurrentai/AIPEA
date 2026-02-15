Audit AIPEA dependencies for security vulnerabilities and license compliance.

Steps:
1. Read `pyproject.toml` to list all dependencies (core + dev)
2. For each dependency, verify:
   - License is MIT-compatible (MIT, BSD, Apache 2.0, ISC) — REFUSE GPL/LGPL/AGPL
   - No known CVEs (check via `pip audit` if available, or web search)
3. Verify core modules (`security.py`, `knowledge.py`, `search.py`) import only stdlib + httpx
   - Run: `grep "^import\|^from" src/aipea/security.py src/aipea/knowledge.py src/aipea/search.py`
4. Check for outdated packages: `pip list --outdated` (if in venv)
5. Report findings as a table: Package | Version | License | Status | Notes
