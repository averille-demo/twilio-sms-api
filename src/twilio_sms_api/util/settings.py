"""Twilio related pydantic settings for /config/*.toml and pyproject.toml.

https://docs.pydantic.dev/usage/settings/
"""

import platform
import re
import string
import tomllib
from pathlib import Path
from typing import Any, Dict, Final, List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent.parent.parent

DATA_PATH: Final[Path] = Path(PROJECT_ROOT, "data")
if not DATA_PATH.is_dir():
    raise NotADirectoryError(f"{DATA_PATH=}")

TOML_PATH = Path(PROJECT_ROOT, "config", "twilio_sms_secret.toml")
if not TOML_PATH.is_file():
    print(f"ERROR: update credentials in {TOML_PATH.name}")
    TOML_PATH.write_text(Path(PROJECT_ROOT, "config", "twilio_sms_example.toml").read_text())

PYPROJECT_PATH = Path(PROJECT_ROOT, "pyproject.toml")
if not PYPROJECT_PATH.is_file():
    raise FileNotFoundError(f"{PYPROJECT_PATH=}")

VALID_ENV = frozenset(("LIVE", "TEST"))
MAX_SID_LEN = 34
MAX_TOKEN_LEN = 32
MAX_BODY_LEN = 1600
REDACTED_BODY = ""


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

    model_config = SettingsConfigDict(case_sensitive=True, secrets_dir=TOML_PATH.parent.as_posix())

    name: str
    environment: str
    account_sid: str
    auth_token: str
    to_number: str
    from_number: str

    @field_validator("environment", mode="before")
    def check_environment(cls, env: str):
        """Validate toml setting."""
        if not is_valid_environment(env):
            raise ValueError(f"environment '{env}' not in {VALID_ENV}")
        return env

    @field_validator("account_sid", mode="before")
    def check_account_sid(cls, v):
        """Validate toml setting."""
        valid_prefix = "AC"
        if len(v) != MAX_SID_LEN:
            raise ValueError(f"invalid length: {len(v)} chars")
        if not v.startswith(valid_prefix):
            raise ValueError(f"invalid format: missing '{valid_prefix}' prefix")
        return v

    @field_validator("auth_token", mode="before")
    def check_auth_token(cls, v):
        """Validate toml setting."""
        if len(v) != MAX_TOKEN_LEN:
            raise ValueError(f"invalid AUTH TOKEN length: {len(v)} characters")
        if not all(c in string.hexdigits for c in v):
            raise ValueError(f"invalid AUTH TOKEN: {len(v)} not hexadecimal")
        return v

    @field_validator("to_number", "from_number", mode="before")
    def check_number(cls, v):
        """Validate toml setting."""
        to_number = ensure_e164_format(v)
        if not to_number:
            raise ValueError(f"invalid number format: '{v}'")
        return to_number


def open_toml(path: Path = TOML_PATH) -> Dict[str, Any]:
    """Open TOML file, return all key/value pairs (tomllib new to python 3.11)."""
    if path.is_file():
        with open(file=path, mode="rb") as fp:
            return tomllib.load(fp)
    else:
        raise FileNotFoundError(f"{path=}")


def load_toml_config(
    payload: Dict = open_toml(),
    environment: str = "LIVE",
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
        environment (str): environment string

    Returns:
        TomlConfig: pydantic settings object
    """
    return TomlConfig(
        name=payload["project"]["name"],
        environment=environment,
        account_sid=payload["twilio"][environment]["account_sid"],
        auth_token=payload["twilio"][environment]["auth_token"],
        to_number=payload["twilio"]["digits"]["to_number"],
        from_number=payload["twilio"]["digits"]["from_number"],
    )


class PyProjectToolPoetry(BaseSettings):
    """Pydantic settings for poetry information.

    https://python-poetry.org/docs/pyproject/
    """

    model_config = SettingsConfigDict(case_sensitive=True)

    host: str
    name: str
    version: str
    description: str
    authors: List[str]
    license: Optional[str]
    readme: Optional[str]
    repository: Optional[str]
    documentation: Optional[str]
    keywords: Optional[List[str]]


def parse_pyproject() -> PyProjectToolPoetry:
    """Extract tool.poetry section from pyproject.toml."""
    tool_poetry_sections: List[str] = [
        "name",
        "version",
        "description",
        "license",
        "authors",
        "repository",
        "readme",
        "documentation",
        "keywords",
    ]
    # init mapping to include all available sections (regardless if actually present in TOML)
    parsed_toml = dict.fromkeys(tool_poetry_sections, None)

    # read pyproject.toml
    pyproject = open_toml(path=PYPROJECT_PATH)

    # only include [tool.poetry] section
    pyproject = pyproject["tool"]["poetry"]
    # overwrite None with values present in TOML
    for key in parsed_toml.keys():
        # skip nested .dependencies or .group.dev
        if isinstance(key, str):
            parsed_toml[key] = pyproject.get(key, None)

    # add host platform information
    host_arch = f"{platform.system()} {platform.architecture()[0]} {platform.machine()}"
    parsed_toml["host"] = f"{platform.node()} ({host_arch})"

    # build pydantic BaseSettings object with **kwargs
    return PyProjectToolPoetry.parse_obj(parsed_toml)


if __name__ == "__main__":
    print(f"{load_toml_config()=}")
    print(f"{parse_pyproject()=}")
