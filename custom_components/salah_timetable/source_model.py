"""Compatibility import path; implementation lives in sources/source_model.py."""

import sys as _sys

from .sources import source_model as _implementation

_sys.modules[__name__] = _implementation
