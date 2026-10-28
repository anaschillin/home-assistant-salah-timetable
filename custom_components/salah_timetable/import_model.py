"""Compatibility import path; implementation lives in parsers/import_model.py."""

import sys as _sys

from .parsers import import_model as _implementation

_sys.modules[__name__] = _implementation
