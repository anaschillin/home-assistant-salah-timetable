"""Compatibility import path; implementation lives in domain/events.py."""

import sys as _sys

from .domain import events as _implementation

_sys.modules[__name__] = _implementation
