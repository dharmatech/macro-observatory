"""Macro Observatory package."""

from macro_observatory.cli import main
from macro_observatory.data import load_dataset

__all__ = ["load_dataset", "main"]
