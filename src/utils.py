"""
utils.py — shared helpers for the post-detection road-litter priority pipeline.

Purpose
    Configuration loading, input-schema validation, coordinate projection,
    100 m gridding, period filtering, deterministic seeding and logging.
    Every pipeline stage (src/01..06) imports from here so that parameters,
    column names and the coordinate reference system live in exactly one place.

Inputs / outputs
    Pure utility module; no files are read or written here except config YAML.

Key parameters
    All read from the config dict (see config/default_config.yaml). Nothing in
    this module hard-codes a project-specific path, grid size or threshold.

Run order
    Imported by all stages; never run directly.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "PyYAML is required to read config files. Install with `pip install pyyaml`."
    ) from exc

try:
    from pyproj import Transformer
    _PYPROJ_AVAILABLE = True
except Exception:  # pragma: no cover
    _PYPROJ_AVAILABLE = False


# --------------------------------------------------------------------------- #
# Repo root + logging
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parents[1]


def get_logger(name: str = "pipeline") -> logging.Logger:
    """Return a configured logger that writes timestamped lines to stdout."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s",
                                                datefmt="%H:%M:%S"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


LOG = get_logger()


def log(msg: str) -> None:
    LOG.info(msg)


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def load_config(config_path: str | Path) -> dict:
    """Load a YAML config file and return it as a dict."""
    p = Path(config_path)
    if not p.is_absolute():
        # resolve relative to current working dir first, then repo root
        p = p if p.exists() else (REPO_ROOT / config_path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(p, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ValueError(f"Config {p} did not parse to a mapping.")
    cfg["_config_path"] = str(p)
    return cfg


def resolve_path(cfg: dict, path_str: str) -> Path:
    """Resolve a possibly-relative path from config against the repo root."""
    p = Path(path_str)
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    return (REPO_ROOT / path_str).resolve()


def set_seed(cfg: dict) -> int:
    """Set numpy's global RNG seed from config for reproducibility."""
    seed = int(cfg.get("random_seed", 0))
    np.random.seed(seed)
    return seed


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


# --------------------------------------------------------------------------- #
# Projection
# --------------------------------------------------------------------------- #
def get_transformers(cfg: dict):
    """Return (fwd, inv) pyproj Transformers: geographic<->projected.

    fwd: lon/lat (EPSG:4326) -> x_m/y_m (projected CRS, e.g. EPSG:6673)
    inv: x_m/y_m -> lon/lat
    """
    if not _PYPROJ_AVAILABLE:
        raise ImportError(
            "pyproj is required for coordinate projection. "
            "Install with `pip install pyproj`."
        )
    geo = cfg["crs"]["geographic"]
    proj = cfg["crs"]["projected"]
    fwd = Transformer.from_crs(geo, proj, always_xy=True)
    inv = Transformer.from_crs(proj, geo, always_xy=True)
    return fwd, inv


# --------------------------------------------------------------------------- #
# Schema validation
# --------------------------------------------------------------------------- #
def validate_columns(df: pd.DataFrame, required: Iterable[str], table_name: str) -> None:
    """Raise a clear, human-readable error if any required column is missing."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Input table '{table_name}' is missing required column(s): "
            f"{missing}. Present columns: {list(df.columns)}. "
            f"See docs/input_data_schema.md for the expected schema."
        )


def canonical_columns(cfg: dict) -> dict:
    """Return the {logical_name: actual_column_name} mapping from config."""
    return dict(cfg["columns"])


# --------------------------------------------------------------------------- #
# Gridding
# --------------------------------------------------------------------------- #
def cell_indices(x_m: np.ndarray, y_m: np.ndarray, grid_size_m: float):
    """Floor projected coordinates to integer (cell_ix, cell_iy), origin (0,0)."""
    ix = np.floor(np.asarray(x_m, dtype=float) / grid_size_m).astype(np.int64)
    iy = np.floor(np.asarray(y_m, dtype=float) / grid_size_m).astype(np.int64)
    return ix, iy


def grid_id(cell_ix, cell_iy) -> pd.Series:
    return (pd.Series(cell_ix).astype(str) + "_" + pd.Series(cell_iy).astype(str))


def cell_center_m(cell_ix, cell_iy, grid_size_m: float):
    xc = np.asarray(cell_ix, dtype=float) * grid_size_m + grid_size_m / 2.0
    yc = np.asarray(cell_iy, dtype=float) * grid_size_m + grid_size_m / 2.0
    return xc, yc


# --------------------------------------------------------------------------- #
# Periods
# --------------------------------------------------------------------------- #
def period_mask(date_ts: pd.Series, start: str, end: str) -> pd.Series:
    """Inclusive date mask [start 00:00:00, end 23:59:59]."""
    s = pd.Timestamp(start)
    e = pd.Timestamp(end) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    return (date_ts >= s) & (date_ts <= e)


def iter_periods(cfg: dict):
    """Yield (label, start, end) for full / period1 / period2 in fixed order."""
    for label in ("full", "period1", "period2"):
        spec = cfg["periods"][label]
        yield label, spec["start"], spec["end"]
