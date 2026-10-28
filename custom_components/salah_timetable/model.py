"""Compatibility import path; implementation lives in domain/model.py."""

import sys as _sys

from .domain import model as _implementation

_sys.modules[__name__] = _implementation
