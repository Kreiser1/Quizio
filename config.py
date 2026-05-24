from dotenv import dotenv_values
from secrets import token_hex
import logging, sys

_config = dotenv_values('./config.env')

DATABASE_URI = _config.get('DATABASE_URI') or 'sqlite:///./database.db'
TOKEN_SECRET = _config.get('TOKEN_SECRET')
AUTH_SECRET = _config.get('AUTH_SECRET')
ADMIN_USERNAME =_config.get('ADMIN_USERNAME')
ADMIN_PASSWORD =_config.get('ADMIN_PASSWORD')
TOKEN_EXPIRATION = int(_config.get('TOKEN_EXPIRATION') or 1209600)
AUTH_COST = int(_config.get('AUTH_COST') or 65536)
AUTH_COOLDOWN = int(_config.get('AUTH_COOLDOWN') or 10)
DEBUG = _config.get('DEBUG').lower() == 'true'

if not TOKEN_SECRET or not AUTH_SECRET:
    logging.error("Token or auth secret is not specified in config.env")
    sys.exit(1)

if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    logging.error("Initial admin username or password is not specified in config.env")
    sys.exit(1)