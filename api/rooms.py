import asyncio
from typing import Annotated
from fastapi import APIRouter, status, Path, Depends, Body, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

import schema
import depends
import roomsvc
import usersvc
import config
import security
from exceptions import *


router = APIRouter(prefix='/rooms', tags=['Комнаты'])

def _check_room_owner(room_token: schema.RoomToken, username: schema.Username, role: schema.Role) -> None:
    if room_token not in roomsvc.rooms:
        raise NotFoundHTTPException("Игровая комната не найдена.")
    if roomsvc.rooms[room_token].owner != username and role != 'administrator':
        raise ForbiddenHTTPException("У вас нет прав для управления этой комнатой.")

def _mask_room_stream(stream: schema.RoomStream, username: schema.Username) -> schema.RoomStream:
    masked_stream = stream.model_copy(deep=True)
    
    for user in masked_stream.users:
        if user.username != username:
            user.answers = set()
            
    for team in masked_stream.teams:
        for user in team.users:
            if user.username != username:
                user.answers = set()
                
    return masked_stream

@router.post('', status_code=status.HTTP_201_CREATED)
def create_room(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    payload: schema.RoomCreate = Body(...)
) -> schema.RoomToken:
    """Создать комнату."""

    room_token = roomsvc.create_room(session, username, payload)

    if not room_token:
        raise NotFoundHTTPException("Не удалось создать комнату. Проверьте ID викторины.")
    
    return room_token

@router.put('/{room_token}', status_code=status.HTTP_200_OK)
def update_room(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    role: depends.Role,
    room_token: schema.RoomToken = Path(...),
    payload: schema.RoomCreate = Body(...)
):
    """Обновить комнату."""

    _check_room_owner(room_token, username, role)
    
    if not roomsvc.update_room(session, room_token, payload):
        raise ConflictHTTPException("Не удалось обновить комнату.")

@router.get('/query', response_model=list[schema.RoomPreview], status_code=status.HTTP_200_OK)
def search_rooms(
    role: depends.Role,
    query: schema.Title | None = Query(default=None),
    count: schema.Count = Query(default=25),
    offset: schema.Index = Query(default=0)
) -> list[schema.RoomPreview]:
    """Поиск комнат."""

    return roomsvc.search_rooms(query=query, count=count, offset=offset, force=(role == 'administrator' or role=='moderator'))

@router.get('/{room_token}', response_model=schema.Room)
def get_room(
    moderator: depends.Moderator,
    room_token: schema.RoomToken = Path(...)
) -> schema.Room:
    """Получить данные комнаты."""

    room = roomsvc.get_room(room_token)

    if not room:
        raise NotFoundHTTPException("Не удалось найти комнату.")
    
    return room

@router.post('/{room_token}/answer', status_code=status.HTTP_200_OK)
def submit_answer(
    username: depends.Username,
    role: depends.Role,
    room_token: schema.RoomToken = Path(...),
    payload: schema.Answer = Body(...)
) -> bool:
    """Отправить ответ."""

    return roomsvc.submit_answer(room_token, username, payload, (role == 'moderator' or role == 'administrator'))

@router.post('/{room_token}/control', status_code=status.HTTP_200_OK)
def control_room(
    moderator: depends.Moderator,
    username: depends.Username,
    role: depends.Role,
    room_token: schema.RoomToken = Path(...),
    payload: schema.RoomControl = Body(...)
):
    """Отправить команду управления комнатой."""

    _check_room_owner(room_token, username, role)

    result = roomsvc.control_room(room_token, payload)
    
    if not result:
        raise UnprocessableHTTPException("Неверная команда или индекс вопроса.")

@router.post('/{room_token}/ban', status_code=status.HTTP_200_OK)
def ban_user(
    moderator: depends.Moderator, username: depends.Username, role: depends.Role,
    room_token: schema.RoomToken = Path(...), ban_username: schema.Username = Body(embed=True)
):
    """Забанить пользователя."""

    _check_room_owner(room_token, username, role)

    if not roomsvc.ban_user(room_token, ban_username):
        raise NotFoundHTTPException("Пользователь не найден.")

@router.post('/{room_token}/unban', status_code=status.HTTP_200_OK)
def unban_user(
    moderator: depends.Moderator, username: depends.Username, role: depends.Role,
    room_token: schema.RoomToken = Path(...), unban_username: schema.Username = Body(embed=True)
):
    """Разбанить пользователя."""

    _check_room_owner(room_token, username, role)

    if not roomsvc.unban_user(room_token, unban_username):
        raise NotFoundHTTPException("Пользователь не найден.")

@router.post('/{room_token}/teams', status_code=status.HTTP_201_CREATED)
def add_team(
    moderator: depends.Moderator, username: depends.Username, role: depends.Role,
    room_token: schema.RoomToken = Path(...), payload: schema.RoomTeam = Body(...)
):
    """Добавить команду."""

    _check_room_owner(room_token, username, role)

    if not roomsvc.add_team(room_token, payload):
        raise ConflictHTTPException("Команда уже существует.")

@router.delete('/{room_token}/teams/{title}', status_code=status.HTTP_200_OK)
def delete_team(
    moderator: depends.Moderator, username: depends.Username, role: depends.Role,
    room_token: schema.RoomToken = Path(...), title: schema.Title = Path(...)
):
    """Удалить команду."""
    
    _check_room_owner(room_token, username, role)

    if not roomsvc.delete_team(room_token, title):
        raise NotFoundHTTPException("Команда не найдена.")

@router.post('/{room_token}/team', status_code=status.HTTP_200_OK)
def set_user_team(
    moderator: depends.Moderator, current_username: depends.Username, role: depends.Role,
    room_token: schema.RoomToken = Path(...),
    username: schema.Username = Body(...),
    team: schema.Title | None = Body(default=None)
):
    """Установить команду пользователя."""
    
    _check_room_owner(room_token, current_username, role)

    if not roomsvc.set_user_team(room_token, username, team):
        raise NotFoundHTTPException("Не удалось обновить команду пользователя.")


from pydantic import TypeAdapter


def _authorize_room_steam(
    session: Session,
    access_token: str | None,
    refresh_token: str | None
) -> schema.Username | None:
    if not refresh_token:
        return None

    try:
        refresh_token = TypeAdapter(schema.RefreshToken).validate_python(refresh_token)
    except schema.ValidationError:
        return None
    
    try:
        access_token = TypeAdapter(schema.AccessToken).validate_python(access_token)
    except schema.ValidationError:
        access_token = None
    
    username: schema.Username | None = None

    if access_token:
        username = security.login(refresh_token, access_token)

    if not username:
        access_token = security.refresh(session, refresh_token)
        if access_token:
            username = security.login(refresh_token, access_token)

    return username

@router.websocket('/{room_token}/stream')
async def room_stream(
    websocket: WebSocket,
    session: depends.Session,
    room_token: schema.RoomToken = Path(...)
):
    """WebSocket для просмотра комнаты в реальном времени."""

    username = _authorize_room_steam(session, websocket.cookies.get(security.ACCESS_COOKIE), websocket.cookies.get(security.REFRESH_COOKIE))

    if not username:
        await websocket.close(code=1008, reason=UnauthorizedHTTPException().detail)
        return
    
    role = security.get_role(session, username) or 'user'
    full_name = None

    profile = usersvc.get_profile(session, username)
    
    if profile and profile.full_name:
        full_name = profile.full_name

    if not roomsvc.join_room(room_token, username, full_name, (role == 'moderator' or role == 'administrator')):
        await websocket.close(code=1008, reason=ForbiddenHTTPException().detail)
        return

    await websocket.accept()

    role = security.get_role(session, username) or 'user'

    if room_token in roomsvc.rooms:
        user = next((user for user in roomsvc.rooms[room_token].users if user.username == username), None)
        if user and user.connection_state != 'banned':
            user.connection_state = 'connected'

    try:
        while True:
            room_stream = roomsvc.refresh_room(room_token, delta_time=1.0 / config.FREQUENCY)

            if not room_stream:
                await websocket.send_json({})
                await websocket.close()
                break
                
            room_stream = room_stream if role in ('moderator', 'administrator') else _mask_room_stream(room_stream, username)
            await websocket.send_json(room_stream.model_dump(mode='json'))
                
            await asyncio.sleep(1.0 / config.FREQUENCY)
    except WebSocketDisconnect:
        if username and room_token in roomsvc.rooms:
            user = next((user for user in roomsvc.rooms[room_token].users if user.username == username), None)
            if user and user.connection_state != 'banned':
                user.connection_state = 'disconnected'