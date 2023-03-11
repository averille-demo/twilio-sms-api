## twilio_sms_api_py

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Code style: isort](https://img.shields.io/badge/%20imports-isort-%231674b1)](https://pycqa.github.io/isort/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-blue?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)


Send text messages programmatically with Twilio SMS API.

![image](./img/twilio_sms.png)

### Update API Credentials:
```
# setup Twilio account
# update *_secret.toml file to include your API credentials and phone number
cp './app/config/twilio_sms_example.toml' './app/config/twilio_sms_secret.toml'

within './app/config/*_secret.toml':
[twilio.LIVE]
    account_sid = "123456789abcdefg"   # <-- UPDATE
    auth_token = "abcdefg123456789"

[twilio.digits]
  to_number = "+1222333444"    # <-- UPDATE
  from_number = "+1222333444"
```

### Dependency Setup:
* [Poetry Commands](https://python-poetry.org/docs/cli/)
```
# update poetry
poetry --version
poetry self update

# use latest python version for venv
pyenv install 3.11.0
pyenv local 3.11.0

# update poetry settings
poetry config virtualenvs.in-project true
poetry config virtualenvs.prefer-active-python true
poetry config experimental.new-installer false
poetry config --list

# create venv in project
poetry check
poetry lock

# upgrade pip within venv
poetry run python -m pip install --upgrade pip

# setup pre-commit
poetry run pre-commit autoupdate
poetry run pre-commit install
```

### Run Demo:
```
poetry run python ./app/twilio_sms_demo.py
```

### Resources:
* [Twilio](https://www.twilio.com)
* [Twilio API Documentation](https://www.twilio.com/docs/sms/api/message-resource)
