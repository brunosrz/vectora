"""Tests for src/version.py"""

from __future__ import annotations

import re

from backend.version import __version__


def test_version_is_string():
    assert isinstance(__version__, str)


def test_version_semver():
    assert re.match(r"^\d+\.\d+\.\d+", __version__), f"Not semver: {__version__}"
