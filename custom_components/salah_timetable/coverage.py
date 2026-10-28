"""Compatibility import path; implementation lives in domain/coverage.py."""

import sys as _sys

from .domain import coverage as _implementation

_sys.modules[__name__] = _implementation
