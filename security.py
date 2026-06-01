from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher 
from secrets import token_hex
from jwt import PyJWT, InvalidKeyError, InvalidTokenError
from time import time
from config import AUTH_SECRET, TOKEN_SECRET, AUTH_EXPIRATION, TOKEN_EXPIRATION
import schema, database as db
from datetime import datetime
from user_agents import parse as parse_useragent
from user_agents.parsers import UserAgent

ACCESS_COOKIE='access_token'
REFRESH_COOKIE='refresh_token'

jwt = PyJWT()
argon2 = PasswordHash([Argon2Hasher(time_cost=4, memory_cost=65536)])

def compare(secret: str, hash: str) -> bool:
    return argon2.verify(secret + AUTH_SECRET, hash)

def hash(secret: str, salted: bool = True) -> str:
    return argon2.hash(secret + AUTH_SECRET) if salted else argon2.hash(secret, salt=AUTH_SECRET.encode())

def encode(token: dict) -> schema.Jwt:
    return jwt.encode(token, TOKEN_SECRET, 'HS256')

def decode(token: schema.Jwt) -> dict | None:
    try:
        return jwt.decode(token, TOKEN_SECRET, 'HS256')
    except (InvalidKeyError, InvalidTokenError):
        return None
    
def set_role(session: db.Session, user_role_update_payload: schema.UserRoleUpdate) -> bool:
    return session.execute(db.update(db.User).where(db.User.username == user_role_update_payload.username).values(role=user_role_update_payload.role)).rowcount > 0

def register(session: db.Session, user_registration_payload: schema.UserRegistration) -> schema.UserProfile | None:
    if session.execute(db.select(db.exists().where(db.User.username == user_registration_payload.username))).scalar():
        return None

    creation_date = schema.format_datetime(datetime.now())
    email = encode({'email': user_registration_payload.email}) if user_registration_payload.email else None
    email_hash = hash(user_registration_payload.email, False) if user_registration_payload.email else None

    try:

        session.add(db.User(
            username=user_registration_payload.username,
            password_hash=hash(user_registration_payload.password),
            role='user',
            creation_date=creation_date,
            email=email,
            email_hash=email_hash
        ))

        session.flush()

        return schema.UserProfile(
            username=user_registration_payload.username,
            email=user_registration_payload.email,
            creation_date=creation_date,
            role='user'
        )
    except db.IntegrityError:
        return None

def authorize(session: db.Session, user_authorization_payload: schema.UserAuthorization, user_agent: str | None = None) -> tuple[schema.HexString, schema.Jwt] | None:
    if not session.query(db.exists().where(db.User.username == user_authorization_payload.username)).scalar():
        return None
    
    device_name = "<Неизвестное устройство>"
    
    if user_agent:
        user_agent = parse_useragent(user_agent)
        user_agent: UserAgent
        device_name = f"[{user_agent.os.family} | {user_agent.browser.family}] {user_agent.device.family}"

    password_hash = session.execute(db.select(db.User.password_hash).where(db.User.username == user_authorization_payload.username)).scalar()

    if not password_hash:
        return None
    
    if not compare(user_authorization_payload.password, password_hash):
        return None

    refresh_token = token_hex(64)

    try:
        session.add(db.Auth(
            refresh_token=refresh_token,
            username=user_authorization_payload.username,
            device_name=device_name,
            creation_date=schema.format_datetime(datetime.now()),
            expiration_time = schema.Ufloat(time() + AUTH_EXPIRATION)
        ))
        
        session.flush()

        return (refresh_token, encode({
            'username': user_authorization_payload.username,
            'refresh_token': refresh_token,
            'expiration_time': schema.Ufloat(time() + TOKEN_EXPIRATION)
        }))
    except db.IntegrityError:
        return None
    
def get_user_sessions(session: db.Session, username: schema.Username) -> list[schema.UserSession]:
    user_sessions = session.execute(db.select(db.Auth.username, db.Auth.refresh_token, db.Auth.device_name, db.Auth.creation_date, db.Auth.expiration_time).where(db.Auth.username == username)).all()

    return [
        schema.UserSession(
            username=user_session[0],
            refresh_token=user_session[1],
            device_name=user_session[2],
            creation_date=user_session[3],
            expiration_time=user_session[4]
        )
        for user_session in user_sessions
    ]

def login(access_token: schema.Jwt) -> schema.Username | None:
    access_token = decode(access_token)

    if not access_token:
        return None
    
    if time() >= access_token['expiration_time']:
        return None

    return access_token['username']
    
def logout(session: db.Session, refresh_token: schema.HexString) -> bool:
    return session.execute(db.delete(db.Auth).where(db.Auth.refresh_token == refresh_token)).rowcount > 0

def unauthorize(session: db.Session, username: schema.Username) -> bool:
    return session.execute(db.delete(db.Auth).where(db.Auth.username == username)).rowcount > 0

def update_credentials(session: db.Session, username: schema.Username, user_credentials_update_payload: schema.UserCredentialsUpdate, verify_old_password: bool = True) -> bool:
    if verify_old_password:
        if not user_credentials_update_payload.old_password:
            return False

        password_hash = session.execute(db.select(db.User.password_hash).where(db.User.username == username)).scalar()

        if not password_hash:
            return False
        
        if not compare(user_credentials_update_payload.old_password, password_hash):
            return False
    
    params = {
        **({'email': encode({'email': user_credentials_update_payload.new_email})} if user_credentials_update_payload.new_email else {}),
        **({'email_hash': hash(user_credentials_update_payload.new_email, False)} if user_credentials_update_payload.new_email else {}),
        **({'password_hash': hash(user_credentials_update_payload.new_password)} if user_credentials_update_payload.new_password else {})
    }

    if not params:
        return True

    if session.execute(db.update(db.User).where(db.User.username == username).values(**params)).rowcount > 0:
        session.execute(db.delete(db.Auth).where(db.Auth.username == username))
        return True
    
def refresh(session: db.Session, refresh_token: schema.HexString) -> schema.Jwt | None:
    auth = session.execute(db.select(db.Auth.username, db.Auth.expiration_time).where(db.Auth.refresh_token == refresh_token)).first()
    
    if not auth:
        return None
    
    username, expiration_time = auth

    if time() >= expiration_time:
        session.execute(db.delete(db.Auth).where(db.Auth.refresh_token == refresh_token))
        return None

    return encode({
        'username': username,
        'expiration_time': schema.Ufloat(time() + TOKEN_EXPIRATION)
    })

def get_role(session: db.Session, username: schema.Username) -> schema.Role | None:
    return session.execute(db.select(db.User.role).where(db.User.username == username)).scalar()


def initiate_recovery(session: db.Session, user_recovery_payload: schema.UserRecovery) -> schema.Jwt | None:
    email_hash = hash(user_recovery_payload.email, False)
    email = session.execute(db.select(db.User.email).where(db.User.username == user_recovery_payload.username, db.User.email_hash == email_hash)).scalar()

    if not email or not (email := decode(email)):
        return None
    
    email = email['email']

    if email != user_recovery_payload.email:
        return None
    
    return encode({
        'username': user_recovery_payload.username,
        'new_password': token_hex(16),
        'expiration_time': schema.Ufloat(time() + TOKEN_EXPIRATION)
    })

def confirm_recovery(session: db.Session, recovery_token: schema.Jwt) -> schema.Password | None:
    if not (recovery_token := decode(recovery_token)):
        return None

    if time() >= recovery_token['expiration_time']:
        return None
    
    if session.execute(db.update(db.User).where(db.User.username == recovery_token['username']).values(password_hash=hash(recovery_token['new_password']))).rowcount > 0:
        return recovery_token['new_password']
    
    return None