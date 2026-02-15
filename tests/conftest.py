"""AIPEA test configuration."""

from __future__ import annotations

import os

# Set test environment to prevent any production behavior
os.environ.setdefault("AIPEA_ENV", "test")
