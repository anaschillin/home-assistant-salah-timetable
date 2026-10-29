"""Compatibility import path; implementation lives in parsers/csv_parser.py."""

import sys as _sys

from .parsers import csv_parser as _implementation

_sys.modules[__name__] = _implementation
