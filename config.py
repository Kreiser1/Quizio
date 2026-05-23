from dotenv import dotenv_values
from secrets import token_hex
import logging, sys

_config = dotenv_values('./config.env')

DATABASE_URI = _config.get('DATABASE_URI') or 'sqlite:///./database.db'
TOKEN_SECRET = _config.get('TOKEN_SECRET')
AUTH_SECRET = _config.get('AUTH_SECRET')
ADMIN_PASSWORD =_config.get('ADMIN_PASSWORD')
TOKEN_EXPIRATION = int(_config.get('TOKEN_EXPIRATION') or 600)
AUTH_COST = int(_config.get('AUTH_COST') or 65536)
AUTH_COOLDOWN = int(_config.get('AUTH_COOLDOWN') or 10)

if not TOKEN_SECRET or not AUTH_SECRET:
    logging.error("Token or auth secret is not specified in config.env")
    sys.exit(1)