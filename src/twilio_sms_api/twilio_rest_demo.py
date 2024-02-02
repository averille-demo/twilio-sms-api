"""Twilio python REST demo module for SMS messages.

Resources:
https://www.teracodes.com/area-codes/washington/
https://unicode.org/emoji/charts/full-emoji-list.html
"""

import json
import time
import uuid
from pathlib import Path
from pprint import pprint
from typing import List, Optional

import pendulum
import structlog
from pydantic import ValidationError
from twilio.base.exceptions import TwilioException, TwilioRestException
from twilio.http.http_client import TwilioHttpClient
from twilio.rest import Client
from twilio.rest.api.v2010.account.message import MessageInstance
from twilio.rest.lookups.v2.phone_number import PhoneNumberInstance
from util.data_models import MessageExtract, MessageRecord
from util.emoji_generator import get_random_emoji
from util.settings import (
    DATA_PATH,
    MAX_BODY_LEN,
    MAX_SID_LEN,
    REDACTED_BODY,
    TomlConfig,
    load_toml_config,
    parse_pyproject,
)

MODULE = Path(__file__).resolve().name


structlog.configure(
    cache_logger_on_first_use=True,
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=True),
        structlog.dev.ConsoleRenderer(colors=True),
    ],
)


class TwilioSmsClient:
    """Twilio Python SMS Client class."""

    pyproject = parse_pyproject()
    log = structlog.get_logger()

    def __init__(self, environment: str):
        """Set environment for TOML."""
        super().__init__()
        self._config = load_toml_config(environment=environment)
        self._client = self._setup_client()

        self._properties = {
            "from_number": self._config.from_number,
            "to_number": self._config.to_number,
        }

    def __repr__(self) -> str:
        """Magic method string representation of class.

        Returns:
            str: official printable string representation of class
        """
        return f"{self.pyproject.name} (v{self.pyproject.version}) {self._config.environment}"

    @property
    def from_number(self) -> str:
        """Sent from phone number in E.164 format."""
        return self._properties["from_number"]

    @property
    def to_number(self) -> str:
        """Send to phone number in E.164 format."""
        return self._properties["to_number"]

    def _setup_client(self) -> Client:
        """Utilize API credentials from TOML to create python client HTTP connection.

        Returns:
            twilio.rest.Client
            https://www.twilio.com/docs/libraries/python
            https://github.com/twilio/twilio-python/blob/main/twilio/rest/__init__.py#L20

        Raises:
            TwilioRestException: if unable to connect to client HTTP connection.
        """
        try:
            if isinstance(self._config, TomlConfig):
                # pass same logger instance to HTTP client
                http_client = TwilioHttpClient(
                    pool_connections=False,
                    timeout=1.0,
                    # logger=self.log,
                    max_retries=1,
                )
                return Client(
                    username=self._config.account_sid,
                    password=self._config.auth_token,
                    http_client=http_client,
                )
        except TwilioRestException:
            self.log.exception(f"Twilio API client failure {self._config.account_sid}")
        return None

    def verify_phone_number(self, digits: str) -> bool:
        """Query carrier information about phone number.

        https://www.twilio.com/docs/lookup/v2-api#phone-number-lookup
        https://github.com/twilio/twilio-python/blob/main/twilio/rest/lookups/v2/phone_number.py#L180

        Args:
            digits (str) phone number in E164 format

        Returns:
            bool: True if phone number is externally validated.
        """
        is_valid = False
        try:
            phone_instance = self._client.lookups.v2.phone_numbers(digits).fetch(fields="line_type_intelligence")
            if isinstance(phone_instance, PhoneNumberInstance):
                if phone_instance.line_type_intelligence:
                    carrier_name = phone_instance.line_type_intelligence.get("carrier_name")
                if phone_instance.valid:
                    self.log.info(f"valid: '{digits}' carrier: {carrier_name}")
                    is_valid = True
                else:
                    self.log.error(f"invalid number: '{digits}'")
        except (TwilioException, TwilioRestException):
            self.log.exception("Twilio client error")
        return is_valid

    @staticmethod
    def show_record(record: Optional[MessageRecord]) -> None:
        """Display all object key/value pairs for debugging.

        Args:
            record: MessageRecord pydantic model

        Returns:
            None: results printed to console
        """
        if isinstance(record, MessageRecord):
            pprint(object=record.model_dump(), indent=2, width=120, compact=True)

    def build_random_message(self) -> str:
        """Generates random 8 char string with random emoji sequence."""
        emojis = " ".join(get_random_emoji(size=6))
        uid = str(uuid.uuid4()).split("-", maxsplit=1)[0]
        return f"{self} {uid} {emojis}"

    def send_sms_text(
        self,
        to_number: str,
        payload: str,
    ) -> Optional[str]:
        """Create MessageInstance and attempt to send SMS text message with Twilio API.

        https://www.twilio.com/docs/sms/api/message-resource#create-a-message-resource
        https://github.com/twilio/twilio-python/blob/main/twilio/rest/api/v2010/account/message/__init__.py#L449
        https://www.twilio.com/docs/sms/api/message-resource#message-status-values

        Args:
            to_number (str): destination device receiving the text message
            payload (str): message body sent -> to_number (truncated if text longer than 1600 chars)

        Returns:
            str: SID of text message
        """
        if len(payload) >= MAX_BODY_LEN:
            self.log.error(f"message truncated to ({MAX_BODY_LEN}) chars")
            payload = payload[:MAX_BODY_LEN]
        try:
            if self.verify_phone_number(digits=to_number):
                # note: underscore after 'from_' parameter
                message: MessageInstance = self._client.messages.create(
                    to=to_number,
                    from_=self.from_number,
                    body=payload,
                    attempt=1,
                    validity_period=5,
                )
                self.log.info(f"sid: '{message.sid}' status: '{message.status}'")
                return message.sid
        except TwilioRestException:
            self.log.exception(f"failed to send message: '{payload}'")
        return None

    @staticmethod
    def purge_prior(path: Path) -> None:
        """Remove prior version of file if exists."""
        if not path.parent.is_dir():
            path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            if path.suffix in [".json"]:
                if path.stat().st_size > 0:
                    path.unlink(missing_ok=True)

    def save_records_to_json(
        self,
        path: Path,
        records: List[MessageInstance],
    ) -> None:
        """Save output with count and timestamp of extract to JSON.

        https://pendulum.eustace.io/docs/#string-formatting

        Args:
            path (Path): pathlib object to output file
            records (List): newline delimited rows of MessageInstance

        Returns:
            None
        """
        extract = MessageExtract(
            count=len(records),
            records=records,
        )
        try:
            self.purge_prior(path=path)
            path.write_text(data=extract.model_dump_json(indent=2), encoding="utf-8")
            if path.is_file():
                self.log.info(f"saved: '{path.name}'")
        except (ValueError, json.JSONDecodeError):
            self.log.exception(f"{type(records)} '{path.name}'")

    def parse_message(
        self,
        sms: MessageInstance,
    ) -> Optional[MessageRecord]:
        """Convert desired parts of MessageInstance to pydantic model.

        https://github.com/twilio/twilio-python/blob/main/twilio/rest/api/v2010/account/message/__init__.py#L449

        Args:
            sms (MessageInstance): from Twilio REST account API

        Returns:
            MessageRecord: extracted pydantic model
        """
        parsed = None
        try:
            if isinstance(sms, MessageInstance):
                parsed = MessageRecord(
                    sid=sms.sid,
                    from_number=sms.from_,
                    to_number=sms.to,
                    body=sms.body,
                    date_created=sms.date_created,
                    date_sent=sms.date_sent,
                    date_updated=sms.date_updated,
                    direction=sms.direction,
                    error_code=sms.error_code,
                    error_message=sms.error_message,
                    num_media=sms.num_media,
                    num_segments=sms.num_segments,
                    price=sms.price,
                    price_unit=sms.price_unit,
                    status=sms.status,
                )
        except ValidationError as ex:
            self.log.exception(ex.json())
        return parsed

    def is_valid_sms_sid(self, sid: str) -> bool:
        """Validate length and prefix of SMS sid string."""
        is_valid = isinstance(sid, str) and len(sid) == MAX_SID_LEN and sid.startswith("SM")
        if not is_valid:
            self.log.error(f"invalid message sid format: {sid=}")
        return is_valid

    def delete_message(self, sid: str) -> bool:
        """Remove the entire text message from account."""
        is_deleted = False
        try:
            if self.is_valid_sms_sid(sid):
                is_deleted = self._client.messages(sid).delete()
                self.log.info(f"message deleted: {sid=}")
        except TwilioRestException:
            self.log.exception(f"failed to delete message: {sid=}")
        return is_deleted

    def redact_message_body(self, sid: str) -> bool:
        """Remove entire message body contests.

        Check if message was in fact removed prior to returning bool

        Args:
            sid (str): unique id for SMS text message

        Returns:
            bool: if message was redacted successfully
        """
        is_redacted = False
        try:
            if self.is_valid_sms_sid(sid):
                # can only POST empty string to message body
                message = self._client.messages(sid).update(body=REDACTED_BODY)
                if message.body == REDACTED_BODY:
                    self.log.info(f"message body redacted: {sid=}")
                    is_redacted = True
                else:
                    self.log.error(f"failed redaction {sid=}")
        except TwilioRestException:
            self.log.exception(f"failed to redact message: {sid=}")
        return is_redacted

    def extract_single_message(
        self,
        sid: str,
        filename: str,
    ) -> Optional[MessageRecord]:
        """Parse relevant values from single text message.

        Args:
            sid (str): unique id for SMS text message
            filename (str): file name for output message

        Returns:
            MessageRecord: message instance
        """
        message = None
        try:
            if self.is_valid_sms_sid(sid):
                sms = self._client.messages(sid).fetch()
                message = self.parse_message(sms=sms)
                if message:
                    self.save_records_to_json(path=Path(DATA_PATH, filename), records=[message])
                    self.log.info(f"message extracted: {sid=}")
        except TwilioRestException:
            self.log.exception(f"{sid=}")
        return message

    def extract_all_text_messages(
        self,
        filename: str,
    ) -> None:
        """Retrieve all SMS/MMS message history under single account_sid.

        https://www.twilio.com/docs/sms/tutorials/how-to-retrieve-and-modify-message-history-python#

        Args:
            filename (str): output filename for JSON report output

        Returns:
            None
        """
        records = []
        try:
            messages: List[MessageInstance] = self._client.messages.list(limit=100)
            for sms in messages:
                message = self.parse_message(sms)
                if message:
                    # each row newline delimited dict
                    records.append(message)
            self.log.info(f"extracted ({len(records)}) messages in account history")
            if len(records) > 0:
                self.save_records_to_json(path=Path(DATA_PATH, filename), records=records)
            else:
                self.log.error("no messages extracted")
        except (TwilioException, TwilioRestException):
            self.log.exception("Twilio client error")


def run_demo():
    """Run project demo."""
    print(f"{MODULE} started: {pendulum.now(tz='America/Los_Angeles').to_datetime_string()}")
    start = time.perf_counter()
    tsc = TwilioSmsClient(environment="LIVE")
    if tsc:
        # step 1: send test SMS message with random text (+emoji strings) to validated 'to_number'
        sid = tsc.send_sms_text(to_number=tsc.to_number, payload=tsc.build_random_message())
        # step 2: Extract prior test message by string identifier (SID)
        tsc.extract_single_message(sid=sid, filename="before_redaction.json")
        # step 3: redact message body of test message
        tsc.redact_message_body(sid=sid)
        # step 4: validate redaction results
        tsc.extract_single_message(sid=sid, filename="after_redaction.json")
        # step 5: delete prior test message
        tsc.delete_message(sid=sid)
        # step 6: extract entire message history for account
        tsc.extract_all_text_messages(filename="text_message_history.json")

    print(f"{MODULE} finished ({time.perf_counter() - start:0.2f} seconds)")


if __name__ == "__main__":
    run_demo()
