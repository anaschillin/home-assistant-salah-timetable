"""Compatibility import path; implementation lives in imports/import_flow.py."""

import sys as _sys

from .imports import import_flow as _implementation

_sys.modules[__name__] = _implementation
