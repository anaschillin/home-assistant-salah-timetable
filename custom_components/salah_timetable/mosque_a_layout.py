"""Compatibility import path; implementation lives in parsers/mosque_a_layout.py."""

import sys as _sys

from .parsers import mosque_a_layout as _implementation

_sys.modules[__name__] = _implementation
