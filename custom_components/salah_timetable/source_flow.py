"""Compatibility import path; implementation lives in sources/source_flow.py."""

import sys as _sys

from .sources import source_flow as _implementation

_sys.modules[__name__] = _implementation
