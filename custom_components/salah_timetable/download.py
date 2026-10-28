"""Compatibility import path; implementation lives in sources/download.py."""

import sys as _sys

from .sources import download as _implementation

_sys.modules[__name__] = _implementation
