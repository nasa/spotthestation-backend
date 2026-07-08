"""Tests for ``rest.config.calculate_data_on_boot`` env-var parsing."""

import pytest

from rest.config import calculate_data_on_boot


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "Yes", "on", "  on  "])
def test_truthy_values_enable_boot_calculation(monkeypatch, value):
    monkeypatch.setenv("CALCULATE_DATA_ON_BOOT", value)
    assert calculate_data_on_boot() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "", "maybe"])
def test_other_values_disable_boot_calculation(monkeypatch, value):
    monkeypatch.setenv("CALCULATE_DATA_ON_BOOT", value)
    assert calculate_data_on_boot() is False


def test_unset_variable_disables_boot_calculation(monkeypatch):
    monkeypatch.delenv("CALCULATE_DATA_ON_BOOT", raising=False)
    assert calculate_data_on_boot() is False
