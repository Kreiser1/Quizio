from fastapi import APIRouter, status, Path, Query

import database as db
import security, schema, depends, usersvc, config
from exceptions import *

router = APIRouter(prefix='/admin', tags=['Администрирование'])

@router.get('/users', response_model=set[schema.Username])
def get_users(session: depends.Session, administrator: depends.Administrator) -> set[schema.Username]:
    """Получить список пользователей."""

    return usersvc.get_users(session)

@router.patch('/users/{username}/role', response_model=schema.UserProfile)
def update_role(session: depends.Session, payload: schema.UserRoleUpdate, administrator: depends.Administrator) -> schema.UserProfile:
    """Изменить роль пользователя по имени."""

    if not security.set_role(session, payload):
        raise NotFoundHTTPException("Не удалось обновить роль пользователя. Проверьте имя.")

    profile = usersvc.get_profile(session, payload.username)

    if not profile:
        raise NotFoundHTTPException("Профиль не найден.")
    
    return profile

@router.patch('/users/{username}/credentials')
def update_credentials(session: depends.Session, payload: schema.UserCredentialsUpdate, administrator: depends.Administrator,
       username: schema.Username = Path(...)):
    """Изменить данные для входа пользователя по имени."""

    if not security.update_credentials(session, username, payload, verify_old_password=False):
        raise NotFoundHTTPException("Не удалось обновить данные для входа пользователя. Проверьте имя.")

@router.patch('/users/{username}', response_model=schema.UserProfile)
def update_profile(session: depends.Session, payload: schema.UserUpdate, administrator: depends.Administrator,
       username: schema.Username = Path(...)) -> schema.UserProfile:
    """Изменить профиль пользователя по имени."""

    if isinstance(payload.avatar, str) and len(payload.avatar) > config.IMAGE_SIZE_LIMIT:
        raise UnprocessableHTTPException("Аватар слишком большой.")

    if not usersvc.update_profile(session, username, payload):
        raise NotFoundHTTPException("Не изменить профиль пользователя. Проверьте имя.")

    profile = usersvc.get_profile(session, username)

    if not profile:
        raise UnknownHTTPException("Профиль не найден.")
    
    return profile

@router.delete('/users/{username}')
def delete_profile(session: depends.Session, administrator: depends.Administrator,
       username: schema.Username = Path(...)):
    """Удалить профиль пользователя по имени."""

    if not usersvc.delete_profile(session, username):
        raise NotFoundHTTPException("Профиль не найден.")
    
@router.get('/query', response_model=list[schema.UserProfile])
def search_users(
    session: depends.Session,
    administrator: depends.Administrator,
    query: schema.Name | None = Query(default=None),
    count: schema.Uint = Query(default=25),
    offset: schema.Uint = Query(default=0)
) -> list[schema.QuizPreview]:
    """Поиск пользователей по имени."""

    return usersvc.search_users(session, query=query, count=count, offset=offset)