"""Tests for parsing settings."""

from pathlib import Path
from typing import Dict

import pytest
from pydantic import ValidationError

from app import settings


def test_valid_phone_numbers():
    """Any phone number with/without '+1' or '1' prefix returns valid E.164 formatted string."""
    for phone_number in ["+12223334444", "12223334444", "2223334444", "(222) 333-4444", "222-333-4444"]:
        result = settings.ensure_e164_format(phone_number)
        assert isinstance(result, str)


def test_invalid_phone_numbers():
    """Invalid phone number input should return None."""
    for phone_number in ["+2223334444", "NOT_A_NUMBER", None]:
        result = settings.ensure_e164_format(phone_number)
        assert not result


def test_open_toml_valid_path():
    """Check if able to open valid TOML file."""
    result = settings.open_toml(path=settings.TOML_PATH)
    assert isinstance(result, Dict)
    assert isinstance(result["project"]["name"], str)
    assert isinstance(result["twilio"]["digits"]["to_number"], str)


def test_open_toml_invalid_path():
    """Check if opening invalid TOML file should raise exception."""
    with pytest.raises(FileNotFoundError) as ex:
        settings.open_toml(path=Path(settings.TOML_PATH.parent, "does_not_exist.toml"))
        print(ex.message)
        assert ex


def test_load_toml_settings():
    """Check if parsing TOML to pydantic settings was successful."""
    config = settings.load_toml_config()
    assert isinstance(config, settings.TomlConfig)
    for attr in ["name", "environment", "account_sid", "auth_token", "to_number", "from_number"]:
        assert hasattr(config, attr)
        assert isinstance(getattr(config, attr), str)


def test_load_invalid_toml():
    """Check if parsing invalid TOML to pydantic settings raises exception."""
    with pytest.raises(ValidationError) as ex:
        config = settings.open_toml(path=Path(settings.TOML_PATH.parent, "twilio_sms_example.toml"))
        settings.load_toml_config(config)
        print(ex.message)
        assert ex


def test_valid_environment():
    """Check if correct environment string is valid."""
    result = settings.is_valid_environment(env="TEST")
    assert result is True


def test_invalid_environment():
    """Check if incorrect environment string is invalid."""
    result = settings.is_valid_environment(env="STG")
    assert result is False


def test_parse_pyproject_toml():
    """Check parsing pyproject TOML."""
    result = settings.parse_pyproject()
    assert isinstance(result, settings.PyProjectToolPoetry)
    assert isinstance(result.name, str)
    assert isinstance(result.version, str)
