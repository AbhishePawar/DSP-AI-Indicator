"""Supervisor entry point for the existing DSP API; no alternative pipeline."""
from pathlib import Path
import sys
import tomllib

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(Path(__file__).with_name(".env"))
# Prefer this monorepo's packages over unrelated packages with generic names.
project = tomllib.loads((ROOT / "pyproject.toml").read_text())
sys.path[:0] = [str(ROOT / p) for p in project["tool"]["setuptools"]["packages"]["find"]["where"]]

from api_platform.api.app import app

__all__ = ["app"]
