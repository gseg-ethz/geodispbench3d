"""Unit tests for :meth:`SweepParameter.from_mapping` (F-02 single-sourcing).

``from_mapping`` is the single coercion source that replaces the three
byte-identical inline construction blocks previously duplicated across
``load_sweep_config`` (parameters.py), ``_load_hyperparameters``
(tool/loader.py), and ``_coerce_hparam`` (iof3d/factory.py). These tests pin
the 11-field mapping and its edge cases so the three sites cannot drift.
"""

from __future__ import annotations

from typing import Any

import pytest

from geodispbench3d.sweep.parameters import SweepParameter


def test_from_mapping_all_eleven_fields() -> None:
    """Every one of the 11 fields is populated and field-identical to the
    direct constructor for the same input (the invariant the three inline
    blocks all shared)."""

    entry = {
        "name": "alpha",
        "type": "range",
        "value_type": "float",
        "values": [0.0, 0.5, 1.0],
        "lower": 0.0,
        "upper": 1.0,
        "log_scale": True,
        "step": 0.25,
        "activates_on": {"mode": ["fast"]},
        "is_ordered": True,
        "sort_values": False,
    }

    assert SweepParameter.from_mapping(entry) == SweepParameter(
        name="alpha",
        kind="range",
        value_type="float",
        values=[0.0, 0.5, 1.0],
        lower=0.0,
        upper=1.0,
        log_scale=True,
        step=0.25,
        activates_on={"mode": ["fast"]},
        is_ordered=True,
        sort_values=False,
    )


def test_from_mapping_defaults_for_omitted_fields() -> None:
    """Omitted optional fields fall back to the same defaults the inline
    blocks produced (type->choice, value_type->str, log_scale->False, rest
    None)."""

    param = SweepParameter.from_mapping({"name": "beta"})

    assert param == SweepParameter(name="beta", kind="choice", value_type="str")
    assert param.values is None
    assert param.lower is None
    assert param.upper is None
    assert param.log_scale is False
    assert param.step is None
    assert param.activates_on is None
    assert param.is_ordered is None
    assert param.sort_values is None


def test_from_mapping_values_none_stays_none() -> None:
    """An explicit ``values: None`` is preserved as None, not coerced to []."""

    param = SweepParameter.from_mapping({"name": "gamma", "values": None})

    assert param.values is None


@pytest.mark.parametrize("values_input", [[1, 2, 3], (1, 2, 3)])
def test_from_mapping_normalizes_values_to_list(values_input: Any) -> None:
    """``values`` given as a tuple OR a list both produce the same normalized
    list (the ``list(...)`` copy the inline blocks performed)."""

    param = SweepParameter.from_mapping({"name": "delta", "values": values_input})

    assert param.values == [1, 2, 3]
    assert isinstance(param.values, list)


def test_from_mapping_missing_name_raises() -> None:
    """A mapping missing the required ``name`` raises KeyError — the exact
    behavior the inline ``entry["name"]`` access produced."""

    with pytest.raises(KeyError):
        SweepParameter.from_mapping({"type": "choice"})
