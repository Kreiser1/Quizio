from fastapi import APIRouter, status, Path

import database as db
import security, schema, depends, usersvc, config
from exceptions import *

router = APIRouter(prefix='/admin', tags=['Администрирование'])

@router.get('/users', response_model=list[schema.Username])
def get_users(session: depends.Session, administrator: depends.Administrator):
    """Получить список пользователей."""

    return session.execute(db.select(db.User.username)).scalars().all()

@router.patch('/users/{username}', response_model=schema.UserProfile)
def update_profile(session: depends.Session, payload: schema.UserUpdate | schema.UserCredentialsUpdate, administrator: depends.Administrator,
       username: schema.Username = Path(...)) -> schema.UserProfile:
    """Изменить профиль пользователя по имени."""

    if isinstance(payload, schema.UserUpdate):
        if isinstance(payload.avatar, schema.Base64) and len(payload.avatar) > config.AVATAR_SIZE_LIMIT:
            raise UnprocessableHTTPException("Аватар слишком большой.")
        else:
            if int(payload.avatar) > 1048576:
                raise UnprocessableHTTPException("Неверный аватар.")

        if not usersvc.update_profile(session, username, payload):
            raise NotFoundHTTPException("Не удалось обновить данные пользователя. Проверьте имя.")
    elif isinstance(payload, schema.UserCredentialsUpdate):
        if not security.update(session, payload, force=True):
            raise NotFoundHTTPException("Не удалось обновить данные пользователя. Проверьте имя.")

    profile = usersvc.get_profile(session, username)

    if not profile:
        raise NotFoundHTTPException("Пользователь не найден.")
    
    return profile

@router.delete('/users/{username}', status_code=status.HTTP_200_OK)
def delete_profile(session: depends.Session, administrator: depends.Administrator,
       username: schema.Username = Path(...)):
    """Удалить профиль пользователя по имени."""

    if not usersvc.delete_profile(session, username):
        raise NotFoundHTTPException("Пользователь не найден.")