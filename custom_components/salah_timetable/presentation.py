"""Compatibility import path; implementation lives in domain/presentation.py."""

import sys as _sys

from .domain import presentation as _implementation

_sys.modules[__name__] = _implementation
