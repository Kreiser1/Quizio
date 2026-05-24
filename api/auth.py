from typing import Annotated
from fastapi import APIRouter, Depends, Response, Header, status, Cookie

import database as db
import security, schema, depends
from exceptions import *

router = APIRouter(prefix='/auth', tags=['Аккаунты'])

@router.post('/register', status_code=status.HTTP_201_CREATED)
def register(
    session: depends.Session, 
    payload: schema.UserRegistration
):
    """Регистрация нового пользователя."""

    user_profile = security.register(session, payload)
    
    if not user_profile:
        raise ConflictHTTPException("Пользователь с таким именем уже существует.")
        
    return user_profile

@router.post('/login', status_code=status.HTTP_200_OK)
def login(
    session: depends.Session,
    payload: schema.UserAuthorization,
    response: Response,
    user_agent: Annotated[str | None, Header()] = None
):
    """Вход в систему с установкой токенов авторизации в куках."""

    tokens = security.authorize(session, payload, user_agent)
    
    if not tokens:
        raise UnauthorizedHTTPException("Неверное имя пользователя или пароль.")
        
    refresh_token, access_token = tokens

    response.set_cookie(
        key=security.ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        samesite="none",
        secure=True
    )

    response.set_cookie(
        key=security.REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        samesite="none",
        secure=True
    )

@router.post('/logout', status_code=status.HTTP_200_OK)
def logout(
    session: depends.Session,
    response: Response,
    refresh_token: Annotated[schema.RefreshToken, Cookie(alias=security.REFRESH_COOKIE)]
):
    """Выход из системы, удаление сессии и очистка куков."""

    if security.logout(session, refresh_token):
        response.delete_cookie(security.ACCESS_COOKIE)
        response.delete_cookie(security.REFRESH_COOKIE)
    else:
        raise UnauthorizedHTTPException()

@router.patch('/update', status_code=status.HTTP_200_OK)
def update(
    session: depends.Session,
    username: depends.Username,
    payload: schema.UserCredentialsUpdate
):
    """Обновление пароля или E-mail авторизованного пользователя."""
    
    if not security.update(session, username, payload):
        raise ForbiddenHTTPException("Не удалось обновить данные пользователя. Проверьте пароль.")


from pydantic import BaseModel
class Me(BaseModel):
    username: schema.Username
    role: schema.Role


@router.get('/me')
def get_me(
    username: depends.Username, 
    role: depends.Role
) -> Me:
    """Получение данных текущей сессии."""
    
    return {
        "username": username,
        "role": role
    }
