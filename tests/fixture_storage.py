"""Portable, ignored storage for bounded owned test fixtures."""
from pathlib import Path
import tempfile


def temporary_directory(root):
    parent = Path(root) / 'build' / 'test-fixtures'
    parent.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=parent)
