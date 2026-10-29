"""Compatibility import path; implementation lives in parsers/mosque_b_ramadan_layout.py."""

import sys as _sys

from .parsers import mosque_b_ramadan_layout as _implementation

_sys.modules[__name__] = _implementation
