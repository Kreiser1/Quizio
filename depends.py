from typing import Annotated

from fastapi import Depends, Cookie
from pydantic import TypeAdapter

import database as db
import security, schema
from exceptions import *


Session = Annotated[db.Session, Depends(db.session)]

def _get_username(
	access_token: Annotated[str| None, Cookie(alias=security.ACCESS_COOKIE)] = None,
	refresh_token: Annotated[str| None, Cookie(alias=security.REFRESH_COOKIE)] = None,
) -> schema.Username:
    if not access_token or not refresh_token:
        raise UnauthorizedHTTPException()
    
    try:
        access_token = TypeAdapter(schema.AccessToken).validate_python(access_token)
        refresh_token = TypeAdapter(schema.RefreshToken).validate_python(refresh_token)
    except schema.ValidationError:
        raise UnauthorizedHTTPException('Неверный формат токенов авторизации')

    username = security.login(refresh_token, access_token)

    if not username:
        raise UnauthorizedHTTPException()
    
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

def _get_user_profile(
    session: Session,
	username: Username
) -> schema.UserProfile:
    profile = session.execute(db.select(db.User.full_name, db.User.email, db.User.avatar, db.User.creation_time, db.User.role).where(db.User.username == username)).first()

    if not profile:
        raise UnauthorizedHTTPException()

    email = security.decode(profile[1]) if profile[1] else None

    return schema.UserProfile(
        username=username,
        full_name=profile[0],
        email=email,
        avatar=profile[2],
        creation_time=profile[3],
        role=profile[4]
    )

Profile = Annotated[schema.UserProfile, Depends(_get_user_profile)]