import asyncio
from typing import Annotated
from fastapi import APIRouter, status, Path, Cookie, Header, Body, Query, WebSocket, WebSocketDisconnect, Depends
from pydantic import ValidationError

import schema
import depends
import roomsvc
import usersvc
import config
import security
import database as db
import achisvc
from time import perf_counter
from exceptions import *


router = APIRouter(prefix='/rooms', tags=['Комнаты'])

def _hide_room_stream_answers(room_stream: schema.RoomStream, username: schema.Username):
    for user in room_stream.users:
        if user.username != username:
            user.answers = set()
            
    for team in room_stream.teams:
        for user in team.users:
            if user.username != username:
                user.answers = set()

@router.post('', status_code=status.HTTP_201_CREATED)
def create_room(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    payload: schema.RoomCreate
) -> schema.HexString:
    """Создать комнату."""

    room_token = roomsvc.create_room(session, username, payload)

    if not room_token:
        raise NotFoundHTTPException("Не удалось создать комнату. Проверьте ID викторины.")
    
    return room_token

@router.get('/query', response_model=list[schema.RoomPreview])
def search_rooms(
    role: depends.Role,
    query: schema.Name | None = Query(default=None),
    count: schema.Uint = Query(default=25),
    offset: schema.Uint = Query(default=0)
) -> list[schema.RoomPreview]:
    """Поиск комнат по названию."""

    return roomsvc.search_rooms(query=query, count=count, offset=offset, include_private=(role in ('moderator', 'administrator')))

@router.get('/{room_token}', response_model=schema.RoomPreview)
def get_room(
    moderator: depends.Moderator,
    room_token: schema.HexString = Path(...)
) -> schema.RoomPreview:
    """Получить данные комнаты."""

    room = roomsvc.get_room(room_token)

    if not room:
        raise NotFoundHTTPException("Не удалось найти комнату.")
    
    return room.preview

@router.post('/{room_token}/answer')
def submit_answer(
    username: depends.Username,
    room_token: schema.HexString = Path(...),
    payload: schema.Answer = Body(...)
) -> bool:
    """Отправить ответ."""

    room = roomsvc.get_room(room_token)

    if not room:
        raise NotFoundHTTPException("Не удалось найти комнату.")
    
    return room.submit(username, payload)

@router.post('/{room_token}/control')
def control_room(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    room_token: schema.HexString = Path(...),
    payload: schema.RoomControl = Body(...)
):
    """Отправить команду управления комнатой."""

    room = roomsvc.get_room(room_token)

    if not room:
        raise NotFoundHTTPException("Не удалось найти комнату.")

    if payload.command == 'shutdown':
        for achievement in achisvc.get_achievements(session):
            for user in room.users:
                achisvc.test_achievement(session, achievement, room, user)

        if not roomsvc.delete_room(room_token):
            raise UnknownHTTPException("Не удалось завершить комнату.")
    elif payload.command == 'show':
        if payload.question is None:
            raise BadRequestHTTPException("Вопрос для показа не указан.")
        room.show(payload.question)
    elif payload.command == 'start':
        if payload.question is None:
            raise BadRequestHTTPException("Вопрос для запуска не указан.")

        room.start(payload.question)
    elif payload.command == 'hide':
        room.hide()
    elif payload.command == 'stop':
        room.stop()

@router.post('/{room_token}/ban')
def ban_user(
    moderator: depends.Moderator,
    room_token: schema.HexString = Path(...),
    username: schema.Username = Body(embed=True)
):
    """Забанить пользователя по имени."""

    room = roomsvc.get_room(room_token)

    if not room:
        raise NotFoundHTTPException("Не удалось найти комнату.")

    if not room.ban(username):
        raise NotFoundHTTPException("Пользователь не найден.")

@router.post('/{room_token}/unban')
def unban_user(
    moderator: depends.Moderator,
    room_token: schema.HexString = Path(...),
    username: schema.Username = Body(embed=True)
):
    """Разбанить пользователя по имени."""

    room = roomsvc.get_room(room_token)

    if not room:
        raise NotFoundHTTPException("Не удалось найти комнату.")

    if not room.unban(username):
        raise NotFoundHTTPException("Пользователь не найден.")

@router.post('/{room_token}/teams', status_code=status.HTTP_201_CREATED)
def add_team(
    moderator: depends.Moderator,
    room_token: schema.HexString = Path(...),
    payload: schema.RoomTeam = Body(...)
):
    """Добавить команду."""

    room = roomsvc.get_room(room_token)

    if not room:
        raise NotFoundHTTPException("Не удалось найти комнату.")

    if not room.add_team(payload):
        raise ConflictHTTPException("Команда уже существует.")

@router.delete('/{room_token}/teams')
def delete_team(
    moderator: depends.Moderator,
    room_token: schema.HexString = Path(...),
    title: schema.Name = Body(embed=True)
):
    """Удалить команду."""

    room = roomsvc.get_room(room_token)

    if not room:
        raise NotFoundHTTPException("Не удалось найти комнату.")

    if not room.delete_team(title):
        raise NotFoundHTTPException("Команда не найдена.")

@router.post('/{room_token}/team')
def set_user_team(
    moderator: depends.Moderator, current_username: depends.Username, role: depends.Role,
    room_token: schema.HexString = Path(...),
    username: schema.Username = Body(embed=True),
    title: schema.Name | None = Body(embed=True, default=None)
):
    """Установить команду пользователя."""
    
    room = roomsvc.get_room(room_token)

    if not room:
        raise NotFoundHTTPException("Не удалось найти комнату.")

    if not room.set_user_team(username, title):
        raise NotFoundHTTPException("Не удалось обновить команду пользователя. Проверьте имя.")


from pydantic import TypeAdapter


def _authorize_room_steam(
    session: db.Session,
    access_token: str | None,
    refresh_token: str | None,
) -> schema.Username | None:
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

    if access_token:
        username = security.login(access_token)

    if not username:
        access_token = security.refresh(session, refresh_token)
        if access_token:
            username = security.login(access_token)

    return username

@router.websocket('/{room_token}/stream')
async def room_stream(
    websocket: WebSocket,
    session: depends.Session,
    room_token: schema.HexString = Path(...)
):
    """WebSocket для просмотра комнаты в реальном времени."""

    access_token_cookie = websocket.cookies.get(security.ACCESS_COOKIE)
    refresh_token_cookie = websocket.cookies.get(security.REFRESH_COOKIE)

    access_token_header = websocket.headers.get("access-token")
    refresh_token_header = websocket.headers.get("refresh-token")

    access_token = access_token_cookie or access_token_header
    refresh_token = refresh_token_cookie or refresh_token_header

    username = _authorize_room_steam(session, access_token, refresh_token)

    if not username:
        await websocket.close(code=1008, reason=UnauthorizedHTTPException().detail)
        return
    
    room = roomsvc.get_room(room_token)

    if not room:
        await websocket.close(code=1008, reason="Не удалось найти комнату.")
        return
    
    role = security.get_role(session, username) or 'user'
    profile = usersvc.get_profile(session, username)
    nickname = profile.nickname

    if not room.join(username, nickname, role in ('moderator', 'administrator')):
        await websocket.close(code=1008, reason=ForbiddenHTTPException().detail)
        return

    await websocket.accept()

    user = next((user for user in room.users if user.username == username), None)
    
    if user and user.connection != 'banned':
        user.connection = 'connected'

    try:
        while True:
            if room_token not in roomsvc.ROOMS:
                await websocket.send_json(room_stream.model_dump(mode='json'))
                await websocket.close(code=1000, reason="Комната была завершена.")
                break

            if user.connection == 'banned' and not role in ('moderator', 'administrator'):
                await websocket.close(code=1008, reason="Вы были забанены.")
                break

            room.refresh(perf_counter())

            room_stream = room.stream
                
            if role not in ('moderator', 'administrator'):
                _hide_room_stream_answers(room_stream, username)

            await websocket.send_json(room_stream.model_dump(mode='json'))
                
            await asyncio.sleep(1.0 / config.FREQUENCY)
    except WebSocketDisconnect:
        if room_token in roomsvc.ROOMS:
            if user and user.connection != 'banned':
                user.connection = 'disconnected'