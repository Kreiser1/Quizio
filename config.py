from dotenv import dotenv_values
from secrets import token_hex
import logging, sys

_config = dotenv_values('./config.env')

DATABASE_URI = _config.get('DATABASE_URI') or 'sqlite:///./database.db'
TOKEN_SECRET = _config.get('TOKEN_SECRET')
AUTH_SECRET = _config.get('AUTH_SECRET')
ADMIN_USERNAME =_config.get('ADMIN_USERNAME')
ADMIN_PASSWORD =_config.get('ADMIN_PASSWORD')
AUTH_EXPIRATION = float(_config.get('AUTH_EXPIRATION') or 1209600)
TOKEN_EXPIRATION = float(_config.get('TOKEN_EXPIRATION') or 600)
AUTH_COOLDOWN = float(_config.get('AUTH_COOLDOWN') or 2.5)
IMAGE_SIZE_LIMIT = int(_config.get('IMAGE_SIZE_LIMIT') or 2097152)
QUIZ_SIZE_LIMIT = int(_config.get('QUIZ_SIZE_LIMIT') or 8388608)
FREQUENCY = float(_config.get('FREQUENCY') or 4.0)

if not TOKEN_SECRET or not AUTH_SECRET:
    logging.error("Token or auth secret is not specified in config.env")
    sys.exit(1)

if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    logging.error("Initial admin username or password is not specified in config.env")
    sys.exit(1)

if IMAGE_SIZE_LIMIT <= 0 or QUIZ_SIZE_LIMIT <= 0 or FREQUENCY <= 0:
    logging.error("Invalid size limits or frequency in config.env")
    sys.exit(1)

if AUTH_EXPIRATION <= 0 or TOKEN_EXPIRATION <= 0 or AUTH_COOLDOWN <= 0:
    logging.error("Invalid expiration times or cooldown in config.env")
    sys.exit(1)