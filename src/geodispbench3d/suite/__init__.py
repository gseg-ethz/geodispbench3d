"""Suite composition: ties tool + dataset + metrics + search settings together."""

from __future__ import annotations

from .loader import SearchConfig, SuiteConfig, load_suite

__all__ = ["SearchConfig", "SuiteConfig", "load_suite"]
