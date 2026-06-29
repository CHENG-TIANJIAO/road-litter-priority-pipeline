"""Shared test helpers: load the numbered src/ stage modules by file path."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))   # so stage modules can `import utils`


def load_module(name: str):
    """Import e.g. '03_exposure' (digits-first filename) and return the module."""
    spec = importlib.util.spec_from_file_location(f"_test_{name}", SRC / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class IdentityTransformer:
    """Stand-in for a pyproj inverse transformer (returns inputs unchanged)."""
    @staticmethod
    def transform(x, y):
        return x, y
