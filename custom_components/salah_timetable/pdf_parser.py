"""Compatibility import path; implementation lives in parsers/pdf_parser.py."""

import sys as _sys

from .parsers import pdf_parser as _implementation

_sys.modules[__name__] = _implementation
