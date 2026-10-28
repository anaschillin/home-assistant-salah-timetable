"""Compatibility import path; implementation lives in imports/import_comparison.py."""

import sys as _sys

from .imports import import_comparison as _implementation

_sys.modules[__name__] = _implementation
