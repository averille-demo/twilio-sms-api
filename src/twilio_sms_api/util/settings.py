"""Twilio related pydantic settings for /config/*.toml and pyproject.toml.

https://docs.pydantic.dev/usage/settings/
"""

import re
import string
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic_settings import BaseSettings, validator

PROJECT_PATH = Path(__file__).resolve().parent.parent

TOML_PATH = Path(PROJECT_PATH, "config", "twilio_sms_secret.toml")
if not TOML_PATH.is_file():
    raise FileNotFoundError(f"TOML_PATH does not exist: {TOML_PATH}")


PYPROJECT_PATH = Path(PROJECT_PATH, "pyproject.toml")
if not PYPROJECT_PATH.is_file():
    raise FileNotFoundError(f"PYPROJECT_PATH does not exist: {PYPROJECT_PATH}")


VALID_ENV = frozenset(("LIVE", "TEST"))


def is_valid_environment(env: str) -> bool:
    """Check if environment is allowed."""
    if env.upper() in VALID_ENV:
        return True
    return False


# compile once, use many times
E164_PHONE_ONE_PLUS = re.compile(r"^\+1[1-9]\d{1,10}$")
E164_PHONE_ONE = re.compile(r"^1[1-9]\d{1,10}$")
E164_PHONE = re.compile(r"^[1-9]\d{1,10}$")


def ensure_e164_format(digits: str) -> Optional[str]:
    """Ensure phone number aligns with '+1##########' E.164 format."""
    # remove spaces, hyphens, and parenthesis (if present)
    digits = str(digits).replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    if E164_PHONE_ONE_PLUS.match(digits):
        # example: +13609871234, valid
        return f"{digits}"
    if E164_PHONE_ONE.match(digits):
        # example: 13609871234, add '+' suffix
        return f"+{digits}"
    if E164_PHONE.match(digits):
        # example: 3609871234, add '+1' suffix
        return f"+1{digits}"
    return None


# pylint: disable=[missing-function-docstring,too-few-public-methods,missing-class-docstring]
class TomlConfig(BaseSettings):
    """Model for Twilio API credentials.

    https://docs.pydantic.dev/usage/settings/
    """

    name: str
    environment: str
    account_sid: str
    auth_token: str
    to_number: str
    from_number: str

    class Config:
        """Pydantic configuration subclass."""

        secrets_dir = TOML_PATH.parent.as_posix()
        case_sensitive = True

    @validator("environment")
    def check_environment(cls, env: str):
        """Validate toml setting."""
        if not is_valid_environment(env):
            raise ValueError(f"environment '{env}' not in {VALID_ENV}")
        return env

    @validator("account_sid")
    def check_account_sid(cls, v):
        """Validate toml setting."""
        valid_prefix = "AC"
        if len(v) != 34:
            raise ValueError(f"invalid length: {len(v)} chars")
        if not v.startswith(valid_prefix):
            raise ValueError(f"invalid format: missing '{valid_prefix}' prefix")
        return v

    @validator("auth_token")
    def check_auth_token(cls, v):
        """Validate toml setting."""
        if len(v) != 32:
            raise ValueError(f"invalid AUTH TOKEN length: {len(v)} characters")
        if not all(c in string.hexdigits for c in v):
            raise ValueError(f"invalid AUTH TOKEN: {len(v)} not hexadecimal")
        return v

    @validator("to_number")
    def check_to_number(cls, v):
        """Validate toml setting."""
        to_number = ensure_e164_format(v)
        if not to_number:
            raise ValueError(f"invalid TO number: '{v}'")
        return to_number

    @validator("from_number")
    def check_from_number(cls, v):
        """Validate toml setting."""
        from_number = ensure_e164_format(v)
        if not from_number:
            raise ValueError(f"invalid FROM number: '{v}'")
        return from_number


def open_toml(path: Path = TOML_PATH) -> Dict[str, Any]:
    """Open TOML file, return all key/value pairs (tomllib new to python 3.11)."""
    if path.is_file():
        with open(file=path, mode="rb") as fp:
            return tomllib.load(fp)
    else:
        raise FileNotFoundError(f"TOML file not found: {path}")


def load_toml_config(
    payload: Dict = open_toml(),
    twilio_env: str = "LIVE",
) -> TomlConfig:
    """Convert TOML key/value pairs to pydantic BaseSettings object.

    optional: set environment variables
    {
        'TWILIO_ACCOUNT_SID': 'AC####...',
        'TWILIO_AUTH_TOKEN': 'SOME_HEXADECIMAL',
        'TWILIO_FROM_PHONE_NUMBER': '+13609871234',
        'TWILIO_TO_PHONE_NUMBER': '+13601239876',
    }

    Args:
        payload (Dict): contents of toml file
        twilio_env (str): environment string

    Returns:
        TomlConfig: pydantic settings object
    """
    return TomlConfig(
        name=payload["project"]["name"],
        environment=twilio_env,
        account_sid=payload["twilio"][twilio_env]["account_sid"],
        auth_token=payload["twilio"][twilio_env]["auth_token"],
        to_number=payload["twilio"]["digits"]["to_number"],
        from_number=payload["twilio"]["digits"]["from_number"],
    )


class PyProjectToolPoetry(BaseSettings):
    """Pydantic settings for poetry information.

    https://python-poetry.org/docs/pyproject/
    """

    name: Optional[str]
    version: Optional[str]
    description: Optional[str]
    license: Optional[str]
    authors: Optional[List[str]]
    readme: Optional[str]
    repository: Optional[str]
    documentation: Optional[str]
    keywords: Optional[List[str]]

    class Config:
        """Pydantic configuration subclass."""

        case_sensitive = True


def parse_pyproject() -> PyProjectToolPoetry:
    """Extract tool.poetry section from pyproject.toml."""
    tool_poetry_sections: List[str] = [
        "name",
        "version",
        "description",
        "license",
        "authors",
        "repository",
        "documentation",
        "keywords",
    ]
    # init mapping to include all available sections (regardless if actually present in TOML)
    parsed_toml = dict.fromkeys(tool_poetry_sections, None)

    # read pyproject.toml
    src_toml = open_toml(path=PYPROJECT_PATH)

    # only scan [tool.poetry] section
    src_toml = src_toml["tool"]["poetry"]
    # overwrite None with values present in TOML
    for key in parsed_toml.keys():
        # skip nested .dependencies or .group.dev dicts
        if isinstance(key, str):
            parsed_toml[key] = src_toml.get(key, None)

    # build pydantic BaseSettings object with **kwargs
    return PyProjectToolPoetry(**parsed_toml)
