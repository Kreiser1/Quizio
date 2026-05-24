from typing import Annotated

from fastapi import Depends, Cookie, Body, Header
from fastapi_throttle import RateLimiter
from pydantic import TypeAdapter

import database as db
import security, schema, config, usersvc
from exceptions import *


Cooldown = Annotated[None, Depends(RateLimiter(times=1, seconds=config.AUTH_COOLDOWN))]

Session = Annotated[db.Session, Depends(db.session)]

def _get_refresh_token(
    refresh_token_cookie: Annotated[str | None, Cookie(alias=security.REFRESH_COOKIE)] = None,
    refresh_token_body: Annotated[str | None, Body(embed=True, alias="refresh_token")] = None,
    x_refresh_token: Annotated[str | None, Header(alias="X-Refresh-Token")] = None
) -> schema.RefreshToken:
    
    refresh_token = refresh_token_cookie or refresh_token_body or x_refresh_token
    
    if not refresh_token:
        raise UnauthorizedHTTPException("Токен авторизации не предоставлен.")
        
    try:
        return TypeAdapter(schema.RefreshToken).validate_python(refresh_token)
    except schema.ValidationError:
        raise UnauthorizedHTTPException("Неверный формат токена авторизации.")
    
RefreshToken = Annotated[schema.RefreshToken, Depends(_get_refresh_token)]

def _get_username(
	access_token: Annotated[str| None, Cookie(alias=security.ACCESS_COOKIE)] = None,
	refresh_token_cookie: Annotated[str| None, Cookie(alias=security.REFRESH_COOKIE)] = None,
    authorization: Annotated[str | None, Header()] = None,
    x_refresh_token: Annotated[str | None, Header(alias="X-Refresh-Token")] = None
) -> schema.Username:
    if not access_token and authorization and authorization.startswith("Bearer "):
        access_token = authorization.split(" ")[1]
    
    refresh_token = refresh_token_cookie or x_refresh_token

    if not access_token or not refresh_token:
        raise UnauthorizedHTTPException("Токены авторизации не предоставлены.")
    
    try:
        access_token = TypeAdapter(schema.AccessToken).validate_python(access_token)
        refresh_token = TypeAdapter(schema.RefreshToken).validate_python(refresh_token)
    except schema.ValidationError:
        raise UnauthorizedHTTPException("Неверный формат токенов авторизации.")

    username = security.login(refresh_token, access_token)

    if not username:
        raise UnauthorizedHTTPException("Ошибка при авторизации. Попробуйте обновить токен.")
    
    return username

Username = Annotated[schema.Username, Depends(_get_username)]

def _get_role(
    session: Session,
	username: Username
) -> schema.Role:
    role = session.execute(db.select(db.User.role).where(db.User.username == username)).scalar()

    if not role:
        raise UnauthorizedHTTPException()

    return role

Role = Annotated[schema.Role, Depends(_get_role)]

def _require_administrator(role: Role):
    if role != 'administrator':
        raise ForbiddenHTTPException()

def _require_moderator(role: Role):
    if role != 'administrator' and role != 'moderator':
        raise ForbiddenHTTPException()

Administrator = Annotated[None, Depends(_require_administrator)]
Moderator = Annotated[None, Depends(_require_moderator)]

def _get_optional_username(
	access_token: Annotated[str| None, Cookie(alias=security.ACCESS_COOKIE)] = None,
	refresh_token: Annotated[str| None, Cookie(alias=security.REFRESH_COOKIE)] = None,
) -> schema.Username | None:
    if not access_token or not refresh_token:
        return None
    
    try:
        access_token = TypeAdapter(schema.AccessToken).validate_python(access_token)
        refresh_token = TypeAdapter(schema.RefreshToken).validate_python(refresh_token)
    except schema.ValidationError:
        return None

    username = security.login(refresh_token, access_token)

    if not username:
        return None
    
    return username

OptionalUsername = Annotated[schema.Username | None, Depends(_get_optional_username)]

def _get_optional_role(
    session: Session,
	username: OptionalUsername
) -> schema.Role | None:
    if not username:
        return None

    role = session.execute(db.select(db.User.role).where(db.User.username == username)).scalar()

    if not role:
        UnauthorizedHTTPException()

    return role

OptionalRole = Annotated[schema.Role | None, Depends(_get_optional_role)]

def _get_user_profile(
    session: Session,
	username: Username
) -> schema.UserProfile:
    profile = usersvc.get_profile(session, username)

    if not profile:
        raise UnauthorizedHTTPException()

    return profile

Profile = Annotated[schema.UserProfile, Depends(_get_user_profile)]