"""Compatibility import path; implementation lives in sources/source_updates.py."""

import sys as _sys

from .sources import source_updates as _implementation

_sys.modules[__name__] = _implementation
