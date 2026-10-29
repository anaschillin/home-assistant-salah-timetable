"""Compatibility import path; implementation lives in domain/ramadan.py."""

import sys as _sys

from .domain import ramadan as _implementation

_sys.modules[__name__] = _implementation
