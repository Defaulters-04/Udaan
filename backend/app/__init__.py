"""Udaan backend package."""

import sys
from pathlib import Path

# Ensure repo root is on sys.path so `import engine` resolves when running
# from inside backend/ (e.g. uvicorn app.main:app or pytest).
_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
