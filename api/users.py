from fastapi import APIRouter, status, Path

import security, schema, depends, usersvc, config
from exceptions import *

router = APIRouter(prefix='/users', tags=['Пользователи'])

@router.get('/me', response_model=schema.UserProfile)
def me(session: depends.Session, username: depends.Username):
    """Получить профиль текущего пользователя."""

    profile = usersvc.get_profile(session, username)

    if not profile:
        raise NotFoundHTTPException("Профиль не найден.")

    return profile

@router.patch('/me', response_model=schema.UserProfile)
def update_profile(session: depends.Session, username: depends.Username, payload: schema.UserUpdate) -> schema.UserProfile:
    """Изменить профиль текущего пользователя."""

    if isinstance(payload.avatar, str) and len(payload.avatar) > config.IMAGE_SIZE_LIMIT:
        raise UnprocessableHTTPException("Аватар слишком большой.")

    if not usersvc.update_profile(session, username, payload):
        raise NotFoundHTTPException("Не удалось обновить данные пользователя.")

    profile = usersvc.get_profile(session, username)
    
    if not profile:
        raise NotFoundHTTPException("Профиль не найден.")
    
    return profile

@router.get('/{username}', response_model=schema.UserProfile)
def get_profile(session: depends.Session, current_username: depends.Username, role: depends.Role,
       username: schema.Username = Path(...)) -> schema.UserProfile:
    """Получить профиль пользователя по имени."""

    profile = usersvc.get_profile(session, username)

    if not profile:
        raise NotFoundHTTPException("Пользователь не найден.")
    
    if username != current_username and role != 'administrator':
        profile.email = None
        profile.creation_date = None

    return profile