from typing import Annotated
from fastapi import APIRouter, Depends, Response, Header, status, Cookie, Body

import security, schema, depends, config
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

@router.post('/login', response_model=schema.Authorization)
def login(
    session: depends.Session,
    payload: schema.UserAuthorization,
    response: Response,
    cooldown: depends.Cooldown,
    user_agent: Annotated[str | None, Header()] = None
) -> schema.Authorization:
    """Вход в систему с установкой токенов авторизации в куках."""

    tokens = security.authorize(session, payload, user_agent)
    
    if not tokens:
        raise UnauthorizedHTTPException("Неверное имя пользователя или пароль.")
        
    refresh_token, access_token = tokens

    response.set_cookie(
        key=security.ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        samesite='lax',
        secure=False
    )

    response.set_cookie(
        key=security.REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        samesite='lax',
        secure=False
    )

    return schema.Authorization(access_token=access_token, refresh_token=refresh_token)

@router.post('/logout')
def logout(
    session: depends.Session,
    username: depends.Username,
    response: Response,
    cooldown: depends.Cooldown,
    refresh_token_body: Annotated[schema.HexString | None, Body(embed=True, alias='refresh_token')] = None,
    refresh_token_cookie: Annotated[str | None, Cookie(alias=security.REFRESH_COOKIE)] = None,
    refresh_token: Annotated[str | None, Header()] = None
):
    """Выход из системы, удаление сессии и очистка куков."""

    refresh_token = refresh_token_body or refresh_token_cookie or refresh_token

    if not refresh_token:
        return BadRequestHTTPException("Токен авторизации не предоставлен.")

    try:
        refresh_token = TypeAdapter(schema.HexString).validate_python(refresh_token)
    except schema.ValidationError:
        return UnprocessableHTTPException("Неверный формат токена авторизации.")

    if refresh_token not in tuple(map(lambda user_session: user_session.refresh_token, security.get_user_sessions(session, username))):
        raise ForbiddenHTTPException("Вы не являетесь владельцем этого токена авторизации.")

    if security.logout(session, refresh_token):
        if refresh_token_cookie == refresh_token:
            response.delete_cookie(security.ACCESS_COOKIE)
            response.delete_cookie(security.REFRESH_COOKIE)
    else:
        raise UnknownHTTPException()

@router.patch('/register')
def update(
    session: depends.Session,
    username: depends.Username,
    payload: schema.UserCredentialsUpdate
):
    """Обновление данных для входа авторизованного пользователя."""

    if not payload.new_password and not payload.new_email:
        return
    
    if not security.update_credentials(session, username, payload):
        raise ForbiddenHTTPException("Не удалось обновить данные пользователя. Проверьте пароль.")

@router.get('/sessions', response_model=list[schema.UserSession])
def sessions(session: depends.Session, username: depends.Username):
    return security.get_user_sessions(session, username)


from typing import Annotated
from fastapi import Body, status
from pydantic import TypeAdapter, ValidationError


@router.post('/recover')
def recover(
    session: depends.Session,
    # payload: Annotated[dict | str, Body()],
    cooldown: depends.Cooldown
):
    """
    Запрос на восстановление пароля пользователя (закрыто до внедрения почтового сервера).
    """

    # 1. Если передан JSON с username и email -> Инициирует сброс.
    # 2. Если передана строка (токен) -> Производит сброс.

    raise NotImplementedHTTPException("Закрыто до внедрения почтового сервера.")
    
    try:
        user_recovery_payload = TypeAdapter(schema.UserRecovery).validate_python(payload)
        
        recovery_token = security.initiate_recovery(session, user_recovery_payload)
        
        if not recovery_token:
            raise UnauthorizedHTTPException("Неверные данные пользователя.")
        
        return
    except ValidationError:
        pass

    try:
        recovery_token = TypeAdapter(schema.Jwt).validate_python(payload)
        
        if not security.confirm_recovery(session, recovery_token):
            raise NotFoundHTTPException("Срок действия токена истек или он не существует.")
            
        return
    except ValidationError:
        pass

    raise UnprocessableHTTPException()