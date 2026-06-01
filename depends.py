from typing import Annotated

from fastapi import Depends, Cookie, Header, Response, Request
from fastapi_throttle import RateLimiter
from pydantic import TypeAdapter

from collections import defaultdict
import database as db
import security, schema, config, usersvc
from time import time
from exceptions import *


Cooldown = Annotated[None, Depends(RateLimiter(times=1, seconds=config.AUTH_COOLDOWN))]

_COOLDOWN = defaultdict(list)

def _check_cooldown(request: Request):
    client_ip = request.client.host if request.client else "Unknown"
    now = time()
    
    _COOLDOWN[client_ip] = [
        time for time in _COOLDOWN[client_ip] 
        if now - time < config.AUTH_COOLDOWN
    ]
    
    if len(_COOLDOWN[client_ip]) >= 1:
        raise TooManyRequestsHTTPException()
        
    _COOLDOWN[client_ip].append(now)

Session = Annotated[db.Session, Depends(db.session)]

def _authorize(
    session: Session,
    request: Request,
    response: Response,
    access_token_cookie: Annotated[str | None, Cookie(alias=security.ACCESS_COOKIE)] = None,
    refresh_token_cookie: Annotated[str | None, Cookie(alias=security.REFRESH_COOKIE)] = None,
    access_token: Annotated[str | None, Header()] = None,
    refresh_token: Annotated[str | None, Header()] = None,
) -> schema.Username | None:
    access_token = access_token_cookie or access_token
    refresh_token = refresh_token_cookie or refresh_token

    if not refresh_token:
        return None

    try:
        refresh_token = TypeAdapter(schema.HexString).validate_python(refresh_token)
    except schema.ValidationError:
        return None
    
    try:
        access_token = TypeAdapter(schema.Jwt).validate_python(access_token)
    except schema.ValidationError:
        access_token = None
    
    username: schema.Username | None = None
    new_access_token = False

    if not access_token:
        _check_cooldown(request)

        if not ((access_token := security.refresh(session, refresh_token)) and (new_access_token := True)):
            return None
    elif not (username := security.login(access_token)):
        _check_cooldown(request)

        if not ((access_token := security.refresh(session, refresh_token)) and (new_access_token := True)):
            return None

    if not username and not (username := security.login(access_token)):
        return None

    if new_access_token:
        response.set_cookie(
            key=security.ACCESS_COOKIE,
            value=access_token,
            httponly=True,
            samesite='lax',
            secure=not config.DEBUG
        )
    
    return username

Authorize = Annotated[schema.Username | None, Depends(_authorize)]

def _get_username(
	username: Authorize,
) -> schema.Username:
    if not username:
        raise UnauthorizedHTTPException()
    
    return username

Username = Annotated[schema.Username, Depends(_get_username)]

def _get_role(
    session: Session,
	username: Username
) -> schema.Role:
    return security.get_role(session, username) or 'user'

Role = Annotated[schema.Role, Depends(_get_role)]

def _require_administrator(role: Role):
    if role != 'administrator':
        raise ForbiddenHTTPException()

def _require_moderator(role: Role):
    if role not in ('moderator', 'administrator'):
        raise ForbiddenHTTPException()

Administrator = Annotated[None, Depends(_require_administrator)]
Moderator = Annotated[None, Depends(_require_moderator)]