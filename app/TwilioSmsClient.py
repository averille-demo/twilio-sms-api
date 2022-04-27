"""
https://www.teracodes.com/area-codes/washington/
https://www.twilio.com/console/verify/dashboard
"""
import os
import sys
import time
from datetime import datetime
import logging
import argparse
from pathlib import Path
from typing import List, Dict
import json
import pprint as pp
import uuid
import toml
import twilio.rest
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException, TwilioException

__author__ = "averille"
__status__ = "demo"
__license__ = "MIT"
__version__ = "1.2.4"

MODULE = Path(__file__).resolve().name
CWD_PATH = Path(__file__).resolve().parent
REPO_NAME = CWD_PATH.parent.name


class SingleLineExceptionFormatter(logging.Formatter):
    """https://docs.python.org/3/library/logging.html#logging.LogRecord"""

    def format(self, record: logging.LogRecord) -> str:
        if record.exc_info:
            single_line = ""
            if record.msg:
                single_line += f"{record.msg} | "
            ex_type, ex_value, ex_tb = sys.exc_info()
            ex_type = f"{ex_type}" if ex_type else ""
            ex_value = " ".join(f"{str(ex_value)}".split()) if ex_value else ""
            src_name = f"{os.path.split(ex_tb.tb_frame.f_code.co_filename)[1]}" if ex_tb else ""
            line_num = f"{ex_tb.tb_lineno}" if ex_tb else ""
            single_line += f"{ex_type} {ex_value} | {src_name}:{line_num}"
            record.msg = single_line
            record.exc_info = None
            record.exc_text = None
        return super().format(record)


class TwilioSmsClient:
    """Twilio Python SMS Client class"""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.cls_name = f"{type(self).__name__}"
        self.logger = self.__setup_logger()
        self.cmd_args = self.__parse_cmd_args()
        self.__config_path = Path(CWD_PATH, "config", "twilio_sms_private.toml")
        self.__config = self.__parse_toml()
        self.__client = self.__prepare_credentials()

    def show_state(self):
        """displays all class variables (types and values)"""
        for key, val in self.__dict__.items():
            print(f"self.{key:36} {str(type(val)):36}\t '{val}'")

    def show_data(self, title: str, data):
        """displays all data values"""
        print(f"\n{self.cls_name} {title}")
        pp.pprint(data, indent=2, width=120, compact=True, sort_dicts=False)

    def __parse_cmd_args(self) -> Dict:
        """ parse command line arguments"""
        parser = argparse.ArgumentParser(description=MODULE)
        parser.add_argument(
            "-e",
            "--environment",
            action="store",
            type=str,
            required=False,
            default="LIVE",
            help="Enter Twilio environment, choose from either 'LIVE' or 'TEST'",
        )
        parser.add_argument(
            "-f",
            "--from_number",
            action="store",
            type=str,
            required=False,
            default="3035551000",
            help="Enter Twilio sending number (example: '3035551000')",
        )
        parser.add_argument(
            "-t",
            "--to_number",
            action="store",
            type=str,
            required=False,
            default="3604442000",
            help="Enter validated recipient phone number (example: '3035551000')",
        )
        cmd_args = vars(parser.parse_args())
        # user input validation
        valid_env = ["LIVE", "TEST"]
        if cmd_args['environment'] not in valid_env:
            parser.error(f"{cmd_args['environment']} not in {valid_env}")
        for digits in ['from_number', 'to_number']:
            # remove spaces and hyphens if present
            cmd_args[digits] = cmd_args[digits].replace("-", "").replace(" ", "")
            # remove leading 1 if present
            if len(cmd_args[digits]) == 11 and cmd_args[digits][0] == '1':
                cmd_args[digits] = cmd_args[digits][1:]
            elif len(cmd_args[digits]) != 10:
                parser.error(
                    f"{digits}: '{cmd_args[digits]}' !=10 characters (area code, prefix, and line number only)")
            # prepend '+1' to number if not present (E.164 format)
            if not str(cmd_args[digits]).startswith("+1"):
                cmd_args[digits] = '+1' + cmd_args[digits]
        self.logger.info(f"cmd_args: {cmd_args}")
        return cmd_args

    def __parse_toml(self) -> Dict:
        """set configuration data from .toml file"""
        config = None
        try:
            if self.__config_path.is_file() and self.__config_path.stat().st_size > 0:
                config = toml.load(self.__config_path)
            else:
                raise FileNotFoundError
        except (KeyError, ValueError, FileNotFoundError):
            self.logger.exception(msg=f"{self.__config_path}")
        return config

    def __prepare_credentials(self) -> twilio.rest.Client:
        """prepare and parse client API credentials from toml"""
        try:
            if isinstance(self.cmd_args, Dict) and isinstance(self.__config, Dict):
                environment = self.cmd_args.get('environment')
                account_sid = self.__config["twilio"][environment]["account_sid"]
                auth_token = self.__config["twilio"][environment]["api_token"]
                return Client(account_sid, auth_token)
        except TwilioRestException:
            self.logger.exception(msg=f"Twilio API client failure {account_sid}")
        return None

    @staticmethod
    def __setup_logger(log_file=Path(CWD_PATH, "logs", f"{REPO_NAME}.log"), purge_log=False):
        """formatted logging with both file and console output"""
        # create empty log file if missing
        if purge_log:
            if log_file.is_file() and log_file.stat().st_size > 0:
                log_file.unlink(missing_ok=True)
        if not log_file.parent.exists():
            log_file.parent.mkdir(parents=True, exist_ok=True)
        if not log_file.is_file():
            log_file.touch(mode=0o777, exist_ok=True)
        # set name to caller module
        logger = logging.getLogger(name=MODULE)
        logger.setLevel(logging.INFO)
        log_format = u"{asctime} [{levelname}]\t{name} | {funcName}() line:{lineno} | {message}"
        datefmt = "%Y-%m-%d %H:%M:%S"
        log_fmt = SingleLineExceptionFormatter(fmt=log_format, datefmt=datefmt, style="{", validate=True)
        # save to file
        file_hdlr = logging.FileHandler(log_file)
        file_hdlr.setLevel(logging.INFO)
        file_hdlr.setFormatter(fmt=log_fmt)
        logger.addHandler(file_hdlr)
        # display log in console
        stdout_hdlr = logging.StreamHandler(sys.stdout)
        stdout_hdlr.setLevel(logging.DEBUG)
        stdout_hdlr.setFormatter(fmt=log_fmt)
        logger.addHandler(stdout_hdlr)
        return logger

    @staticmethod
    def is_valid_file(path: Path) -> bool:
        """checks: file exists, is not directory, has correct extension and file_size > 1 bytes"""
        is_valid = False
        if path.is_file():
            if path.suffix in [".json"]:
                if path.stat().st_size > 1:
                    is_valid = True
        return is_valid

    def write_json(self, path: Path, data: Dict) -> None:
        """exports request data to '.json' formatted file."""
        try:
            # create parent path if needed
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
            # remove prior version
            if self.is_valid_file(path=path):
                path.unlink(missing_ok=True)
            if isinstance(data, Dict):
                with open(path, "w", encoding="utf-8") as fp:
                    fp.write(json.dumps(data, indent=2, sort_keys=False))
            # check if new file exists
            if self.is_valid_file(path=path):
                self.logger.info(f"SUCCESS '{path.name}'")
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            self.logger.exception(msg=f"{type(data)} '{path.name}'")

    @staticmethod
    def create_random_uid(truncate=False) -> str:
        """returns: 8-char string (first part of globally unique UUID)"""
        uuid_str = f"{uuid.uuid4()}"
        if truncate:
            return uuid_str.split("-")[0]
        return uuid_str

    def is_connected(self):
        """valid client with parsed credentials"""
        return isinstance(self.__client, twilio.rest.Client)

    def send_sms_text(self, content: str) -> bool:
        """send text message from Twilio API"""
        try:
            if self.is_connected() and isinstance(content, str):
                # truncate as needed
                if len(content) >= 1600:
                    content = content[:1600]
                # note: underscore after 'from_' parameter
                message = self.__client.messages.create(
                    to=self.cmd_args.get("to_number"),
                    from_=self.__config["twilio"]["sender"]["from_number"],
                    body=content,
                )
                self.logger.info(msg=f"SUCCESS sid: '{message.sid}'")
            else:
                self.logger.error(msg=f"not connected with content: {content}")
        except TwilioRestException:
            self.logger.exception(msg="")
        except KeyError:
            self.logger.exception(msg=f"key not in {self.__config_path.name}")

    @staticmethod
    def parse_usage_record(record: object) -> Dict:
        """convert Twilio.Api.V2010.RecordInstance object to key/value pairs
        https://www.rubydoc.info/gems/twilio-ruby/5.29.0/Twilio/REST/Api/V2010/AccountContext/UsageList/RecordInstance
        """
        return {
            "category": record.category,
            "description": record.description,
            "start_date": record.start_date.strftime("%Y-%m-%d"),
            "end_date": record.end_date.strftime("%Y-%m-%d"),
            "count": record.count,
            "count_unit": record.count_unit,
            "account_sid": record.account_sid,
            "subresource_uris": record.subresource_uris,
            "uri": record.uri,
            "as_of": record.as_of,
            "price": int(record.price),
            "price_unit": record.price_unit,
            "usage": record.usage,
            "usage_unit": record.usage_unit,
        }

    def extract_usage_records(self, path=Path(CWD_PATH, "data", "usage_records.json")) -> List:
        """extract list of usage records from RecordInstance to json
        https://www.twilio.com/docs/usage/api/usage-record
        """
        data = []
        try:
            if self.is_connected():
                records = self.__client.usage.records.list()
                for record in records:
                    data.append(self.parse_usage_record(record=record))
                self.write_json(path=path, data={"records": data})
        except TwilioRestException:
            self.logger.exception(msg=f"{path.name}")
        return data

    @staticmethod
    def parse_message_record(record: object) -> Dict:
        """convert relevant parts of Twilio.Api.V2010.MessageInstance to key/value pairs"""
        date_format = "%Y-%m-%d %H:%M:%S %p"
        return {
            "account_sid": record.account_sid,
            "api_version": record.api_version,
            "body": record.body,
            "date_created": record.date_created.strftime(date_format),
            "date_sent": record.date_sent.strftime(date_format),
            "date_updated": record.date_updated.strftime(date_format),
            "direction": record.direction,
            "error_code": record.error_code,
            "error_message": record.error_message,
            "from": record.from_,
            "to": record.to,
            "num_media": record.num_media,
            "num_segments": record.num_segments,
            "price": record.price,
            "price_unit": record.price_unit,
            "status": record.status,
        }

    def get_messages(self, path=Path(CWD_PATH, "data", "messages.json")) -> list:
        """
        returns list of messages pushed from account
        https://www.twilio.com/docs/sms/tutorials/how-to-retrieve-and-modify-message-history-python#
        """
        messages = []
        try:
            if self.is_connected():
                records = self.__client.messages.list()
                for record in records:
                    messages.append(self.parse_message_record(record=record))
                self.write_json(path=path, data={"messages": messages})
        except (TwilioException, TwilioRestException):
            self.logger.exception(msg=f"{path.name}")
        return messages


if __name__ == "__main__":
    print(f"{MODULE} started {datetime.now().strftime('%Y-%m-%d %H:%M:%S %p')}")
    start = time.perf_counter()
    tc = TwilioSmsClient()
    tc.send_sms_text(f"{MODULE} guid: {tc.create_random_uid()}")
    tc.get_messages()
    print(f"{MODULE} finished in {time.perf_counter() - start:0.2f} seconds")
