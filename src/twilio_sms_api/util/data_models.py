"""Twilio SMS related pydantic models.

https://docs.pydantic.dev/usage/models/
https://docs.pydantic.dev/usage/model_config/
https://docs.python.org/3/library/datetime.html
https://github.com/twilio/twilio-python/blob/main/twilio/base/deserialize.py
https://github.com/twilio/twilio-python/blob/main/twilio/rest/api/v2010/account/message/__init__.py#L449
"""

import re
from datetime import datetime, timezone
from typing import List, Optional

import emoji
from pydantic import BaseModel, ConfigDict, computed_field, field_serializer, field_validator

from twilio_sms_api.util.settings import MAX_SID_LEN, REDACTED_BODY

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# pylint: disable=[too-few-public-methods, no-self-argument]
class MessageRecord(BaseModel):
    """Extract selected attributes of each MessageInstance object.

    All datetime objects JSON encoded in 'YYYY-MM-DD HH:MM:SS' string format (UTC timezone)
    """

    model_config = ConfigDict(check_fields=True, extra="forbid", populate_by_name=False, str_strip_whitespace=True)

    sid: str
    status: str
    from_number: str
    to_number: str
    body: str
    date_created: datetime
    date_sent: datetime
    date_updated: datetime
    direction: str
    error_code: Optional[int]
    error_message: Optional[str]
    num_media: str
    num_segments: str
    price: Optional[float] = 0.0
    price_unit: str

    @field_validator("sid", mode="before")
    def check_message_sid(cls, v):
        """Validate length and prefix of sid string."""
        valid_prefix = "SM"
        if len(v) != MAX_SID_LEN:
            raise ValueError(f"invalid length: {len(v)} chars")
        if not v.startswith(valid_prefix):
            raise ValueError(f"invalid format: missing '{valid_prefix}' prefix")
        return v

    @field_validator("body", mode="before")
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

    @field_serializer("date_created", "date_sent", "date_updated", when_used="always")
    def serialize_datetime(self, dt: datetime) -> str:
        """Convert UTC datetime object to 'YYYY-MM-DD HH:MM:SS' formatted string."""
        return dt.strftime(DATETIME_FORMAT)

    @computed_field
    def emoji_count(self) -> int:
        """Determine number of unique emoji strings present in message body."""
        return emoji.emoji_count(self.body, unique=True)

    @computed_field
    def is_redacted(self) -> bool:
        """Boolean value if message body is empty string."""
        return self.body == REDACTED_BODY


class MessageExtract(BaseModel):
    """Model to track extract date and counts.

    https://www.twilio.com/docs/sms/api/message-resource
    """

    model_config = ConfigDict(extra="forbid")

    extract_date: str = datetime.now(tz=timezone.utc).strftime(DATETIME_FORMAT)
    count: int = 0
    records: List[MessageRecord] = []
