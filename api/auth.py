from typing import Annotated
from fastapi import APIRouter, Depends, Response, Header, status, Cookie

import security, schema, depends
from exceptions import *

router = APIRouter(prefix='/auth', tags=['Авторизация'])

@router.post('/register', status_code=status.HTTP_201_CREATED)
def register(
    session: depends.Session, 
    payload: schema.UserRegistration,
    cooldown: depends.Cooldown
):
    """Регистрация нового пользователя."""

    user_profile = security.register(session, payload)
    
    if not user_profile:
        raise ConflictHTTPException("Пользователь с таким именем уже существует.")
        
    return user_profile

@router.post('/login', response_model=schema.Tokens)
def login(
    session: depends.Session,
    payload: schema.UserAuthorization,
    response: Response,
    cooldown: depends.Cooldown,
    user_agent: Annotated[str | None, Header()] = None
) -> schema.Tokens:
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

    return schema.Tokens(access_token=access_token, refresh_token=refresh_token)

@router.post('/refresh', response_model=schema.Tokens)
def refresh(
    session: depends.Session,
    refresh_token: depends.RefreshToken,
    response: Response,
    cooldown: depends.Cooldown
) -> schema.Tokens:
    """Обновление токенов авторизации в куках."""

    access_token = security.refresh(session, refresh_token)
    
    if not access_token:
        raise UnauthorizedHTTPException("Ошибка при авторизации. Проверьте токен.")

    response.set_cookie(
        key=security.ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        samesite="none",
        secure=True
    )

    return schema.Tokens(access_token=access_token)

@router.post('/logout', status_code=status.HTTP_200_OK)
def logout(
    session: depends.Session,
    response: Response,
    refresh_token: depends.RefreshToken,
    cooldown: depends.Cooldown
):
    """Выход из системы, удаление сессии и очистка куков."""

    if security.logout(session, refresh_token):
        response.delete_cookie(security.ACCESS_COOKIE)
        response.delete_cookie(security.REFRESH_COOKIE)
    else:
        raise UnauthorizedHTTPException()

@router.patch('/register', status_code=status.HTTP_200_OK)
def update(
    session: depends.Session,
    username: depends.Username,
    payload: schema.UserCredentialsUpdate,
    cooldown: depends.Cooldown
):
    """Обновление пароля или E-mail авторизованного пользователя."""
    
    if not security.update(session, username, payload):
        raise ForbiddenHTTPException("Не удалось обновить данные пользователя. Проверьте пароль.")

@router.get('/sessions', response_model=list[schema.UserSession])
def sessions(session: depends.Session, username: depends.Username):
    return security.sessions(session, username)

from typing import Annotated
from fastapi import Body, status
from pydantic import TypeAdapter, ValidationError


@router.post('/recover', status_code=status.HTTP_200_OK)
def recover(
    session: depends.Session,
    payload: Annotated[dict | str, Body()],
    cooldown: depends.Cooldown
):
    """
    Запрос на восстановление пароля пользователя.
    1. Если передан JSON с username и email -> Инициирует сброс.
    2. Если передана строка (токен) -> Производит сброс.
    """

    raise NotImplementedHTTPException("Закрыто до внедрения почтового сервера.")
    
    try:
        user_recovery_payload = TypeAdapter(schema.UserRecovery).validate_python(payload)
        
        recovery_token = security.initiate_recover(session, user_recovery_payload)
        
        if not recovery_token:
            raise UnauthorizedHTTPException("Неверные данные пользователя.")
        
        return
    except ValidationError:
        pass

    try:
        recovery_token = TypeAdapter(schema.RecoveryToken).validate_python(payload)
        
        if not security.recover(session, recovery_token):
            raise NotFoundHTTPException("Срок действия токена истек или он не существует.")
            
        return
    except ValidationError:
        pass

    raise UnprocessableHTTPException()