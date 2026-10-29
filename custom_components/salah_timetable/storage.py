"""Compatibility import path; implementation lives in persistence/storage.py."""

import sys as _sys

from .persistence import storage as _implementation

_sys.modules[__name__] = _implementation
