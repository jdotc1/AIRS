"""Owned ephemeral fixtures work in a clean checkout without private evidence."""
from pathlib import Path
import tempfile

def owned_temporary_directory(root=None):
    destination=Path(root) if root is not None else Path(__file__).resolve().parents[1]/'local-evidence/security-delta-owned-tests'
    destination.mkdir(parents=True,exist_ok=True)
    return tempfile.TemporaryDirectory(dir=destination)
