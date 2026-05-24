from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher 
from secrets import token_hex
from jwt import PyJWT
from time import time
from config import AUTH_SECRET, TOKEN_SECRET, TOKEN_EXPIRATION, AUTH_COST
from schema import RefreshToken, Password, AccessToken

ACCESS_COOKIE='access_token'
REFRESH_COOKIE='refresh_token'

jwt = PyJWT()
argon2 = PasswordHash([Argon2Hasher(time_cost=4, memory_cost=AUTH_COST)])

def compare(secret: str, hash: str) -> bool:
    return argon2.verify(secret + AUTH_SECRET, hash)

def hash(secret: str) -> str:
    return argon2.hash(secret + AUTH_SECRET)

def encode(token: dict) -> str:
    return jwt.encode(token, TOKEN_SECRET, 'HS256')

def decode(token: str) -> dict:
    return jwt.decode(token, TOKEN_SECRET, 'HS256')