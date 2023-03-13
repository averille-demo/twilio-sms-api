"""Twilio SMS related pydantic models.

https://docs.pydantic.dev/usage/models/
https://docs.pydantic.dev/usage/model_config/
https://docs.python.org/3/library/datetime.html
"""
import re
from datetime import datetime
from typing import List, Optional

import emoji
from pydantic import BaseModel, validator

REDACTED_BODY = ""


# pylint: disable=[too-few-public-methods]
class MessageRecord(BaseModel):
    """Extract selected attributes of each MessageInstance object.

    All datetime objects JSON encoded as ISO 8601 strings (UTC timezone)

    https://github.com/twilio/twilio-python/blob/main/twilio/base/deserialize.py
    https://github.com/twilio/twilio-python/blob/main/twilio/rest/api/v2010/account/message/__init__.py#L449
    """

    sid: str
    status: str
    from_: str
    to: str
    body: str
    date_created: datetime
    date_sent: datetime
    date_updated: datetime
    direction: str
    error_code: Optional[str]
    error_message: Optional[str]
    num_media: str
    num_segments: str
    price: Optional[float]
    price_unit: str
    emoji_count: int
    is_redacted: bool

    class Config:
        """Model configuration options.

        https://docs.pydantic.dev/usage/model_config/#options
        """

        json_encoders = {datetime: lambda dt: dt.isoformat()}

    @validator("sid")
    def check_message_sid(cls, v):
        """Validate length and prefix of sid string."""
        valid_prefix = "SM"
        if len(v) != 34:
            raise ValueError(f"invalid length: {len(v)} chars")
        if not v.startswith(valid_prefix):
            raise ValueError(f"invalid format: missing '{valid_prefix}' prefix")
        return v

    @validator("body")
    def sanitize_message_body(cls, text):
        """Sanitize SMS message body text.

        replace unicode emoji string(s) with readable text
        example: 👍 -> '{thumbs_up}'
        remove/replace whitespace chars

        Args:
            text: raw SMS body string

        Returns:
            sanitized text string
        """
        # convert unicode emoji to readable delimited text
        text = emoji.demojize(text, delimiters=("{", "}"))
        # drop tab and newline chars
        text = text.replace("\t", " ").replace("\n", " ")
        # replace consecutive whitespace with single space
        text = re.sub(r" +", " ", text)
        # remove leading/trailing whitespace
        text = text.strip()
        return text


class MessageExtract(BaseModel):
    """Model to track extract date and count.

    https://www.twilio.com/docs/sms/api/message-resource
    """

    extract_date: datetime
    count: int = 0
    records: List[MessageRecord] = []

    class Config:
        """Model configuration options.

        https://docs.pydantic.dev/usage/model_config/#options
        """

        json_encoders = {datetime: lambda dt: dt.isoformat()}
