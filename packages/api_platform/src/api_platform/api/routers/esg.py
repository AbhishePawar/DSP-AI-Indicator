"""Bytecode-backed recovery shim — loads frozen RC1 connector bytecode."""
from __future__ import annotations

from importlib.machinery import SourcelessFileLoader
from pathlib import Path
import sys

_REPO = Path(__file__).resolve()
# Walk up to repo root (contains .bytecode_backup)
_root = _REPO
while _root.parent != _root and not (_root / '.bytecode_backup').exists():
    _root = _root.parent
_BACKUP = _root / '.bytecode_backup' / 'packages__api_platform__src__api_platform__api__routers' / 'esg.cpython-313.pyc'
_loader = SourcelessFileLoader(__name__, str(_BACKUP))
_code = _loader.get_code(__name__)
if _code is None:
    raise ImportError(f'Unable to load bytecode from {_BACKUP}')
exec(_code, globals())
