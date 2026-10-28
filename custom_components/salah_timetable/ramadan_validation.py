"""Compatibility import path; implementation lives in domain/ramadan_validation.py."""

import sys as _sys

from .domain import ramadan_validation as _implementation

_sys.modules[__name__] = _implementation
