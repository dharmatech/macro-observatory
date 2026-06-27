"""Public data loading helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from macro_observatory.cache import load_cache
from macro_observatory.registry import DEFAULT_DATA_DIR, get_dataset_spec


def load_dataset(dataset_id: str, *, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Load a cached dataset by stable dataset ID."""
    spec = get_dataset_spec(dataset_id, data_dir)
    return load_cache(spec)
