"""Compatibility import path; implementation lives in runtime/coordinator.py."""

import sys as _sys

from .runtime import coordinator as _implementation

_sys.modules[__name__] = _implementation
