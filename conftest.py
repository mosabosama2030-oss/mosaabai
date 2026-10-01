"""Pytest configuration: ensure project root is on sys.path."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
