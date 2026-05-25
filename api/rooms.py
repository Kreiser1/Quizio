import asyncio
from typing import Annotated
from fastapi import APIRouter, status, Path, Depends, Body, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

import schema
import depends
import roomsvc
import config
from exceptions import *


router = APIRouter(prefix='/rooms', tags=['Комнаты'])

def _check_room_owner(token: schema.RoomToken, username: schema.Username, role: schema.Role) -> None:
    if token not in roomsvc.rooms:
        raise NotFoundHTTPException("Игровая комната не найдена.")
    if roomsvc.rooms[token].owner != username and role != 'administrator':
        raise ForbiddenHTTPException("У вас нет прав для управления этой комнатой.")

def _mask_room_stream(stream: schema.RoomStream, current_username: schema.Username | None) -> schema.RoomStream:
    masked_stream = stream.model_copy(deep=True)
    
    for user in masked_stream.users:
        if user.username != current_username:
            user.answers = set()
            
    for team in masked_stream.teams:
        for user in team.users:
            if user.username != current_username:
                user.answers = set()
                
    return masked_stream

@router.post('', status_code=status.HTTP_201_CREATED)
def create_room(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    payload: schema.RoomCreate = Body(...)
) -> schema.RoomToken:
    room_token = roomsvc.create_room(session, username, payload)

    if not room_token:
        raise NotFoundHTTPException("Не удалось создать комнату. Проверьте ID викторины.")
    
    return room_token

@router.put('/{token}', status_code=status.HTTP_200_OK)
def update_room(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    role: depends.Role,
    token: schema.RoomToken = Path(...),
    payload: schema.RoomCreate = Body(...)
):
    _check_room_owner(token, username, role)
    
    if not roomsvc.update_room(session, token, payload):
        raise ConflictHTTPException("Не удалось обновить комнату.")

@router.get('/query', response_model=list[schema.RoomPreview], status_code=status.HTTP_200_OK)
def search_rooms(
    moderator: depends.Moderator,
    query: schema.Title | None = Query(default=None),
    count: schema.Count = Query(default=25),
    offset: schema.Index = Query(default=0)
) -> list[schema.RoomPreview]:
    return roomsvc.search_rooms(query=query, count=count, offset=offset)

@router.get('/{token}', status_code=status.HTTP_200_OK)
def join_room(
    username: depends.Username,
    token: schema.RoomToken = Path(...)
):
    if not roomsvc.join_room(token, username):
        raise ForbiddenHTTPException("Вы забанены или комната не существует.")

@router.post('/{token}/answer', status_code=status.HTTP_200_OK)
def post_answer(
    username: depends.Username,
    token: schema.RoomToken = Path(...),
    payload: schema.Answer = Body(...)
) -> bool:
    return roomsvc.submit_answer(token, username, payload)

@router.post('/{token}/control', status_code=status.HTTP_200_OK)
def control_room(
    moderator: depends.Moderator,
    username: depends.Username,
    role: depends.Role,
    token: schema.RoomToken = Path(...),
    payload: schema.RoomControl = Body(...)
) -> schema.RoomPreview | None:
    _check_room_owner(token, username, role)

    result = roomsvc.control_room(token, payload)
    
    if not result:
        raise UnprocessableHTTPException("Неверная команда или индекс вопроса.")
        
    if isinstance(result, schema.RoomPreview):
        return result

@router.post('/{token}/ban', status_code=status.HTTP_200_OK)
def ban_user(
    moderator: depends.Moderator, username: depends.Username, role: depends.Role,
    token: schema.RoomToken = Path(...), target_user: schema.Username = Body(embed=True)
):
    _check_room_owner(token, username, role)

    if not roomsvc.ban_user(token, target_user):
        raise NotFoundHTTPException("Пользователь не найден.")

@router.post('/{token}/unban', status_code=status.HTTP_200_OK)
def unban_user(
    moderator: depends.Moderator, username: depends.Username, role: depends.Role,
    token: schema.RoomToken = Path(...), target_user: schema.Username = Body(embed=True)
):
    _check_room_owner(token, username, role)

    if not roomsvc.unban_user(token, target_user):
        raise NotFoundHTTPException("Пользователь не найден.")

@router.post('/{token}/teams', status_code=status.HTTP_201_CREATED)
def add_team(
    moderator: depends.Moderator, username: depends.Username, role: depends.Role,
    token: schema.RoomToken = Path(...), payload: schema.RoomTeam = Body(...)
):
    _check_room_owner(token, username, role)

    if not roomsvc.add_team(token, payload):
        raise ConflictHTTPException("Команда уже существует.")

@router.delete('/{token}/teams/{title}', status_code=status.HTTP_200_OK)
def delete_team(
    moderator: depends.Moderator, username: depends.Username, role: depends.Role,
    token: schema.RoomToken = Path(...), title: schema.Title = Path(...)
):
    _check_room_owner(token, username, role)

    if not roomsvc.delete_team(token, title):
        raise NotFoundHTTPException("Команда не найдена.")

@router.post('/{token}/team', status_code=status.HTTP_200_OK)
def set_user_team(
    moderator: depends.Moderator, current_username: depends.Username, role: depends.Role,
    token: schema.RoomToken = Path(...),
    username: schema.Username = Body(...),
    team: schema.Title | None = Body(default=None)
):
    _check_room_owner(token, current_username, role)

    if not roomsvc.set_user_team(token, username, team):
        raise NotFoundHTTPException("Не удалось обновить команду пользователя.")


from security import decode


@router.websocket('/{token}/stream')
async def room_stream(
    websocket: WebSocket,
    room_token: schema.RoomToken = Path(...)
):
    await websocket.accept()

    username: schema.Username | None = None
    
    try:
        cookie_header = websocket.headers.get("cookie", "")

        if f"{config.ACCESS_COOKIE}=" in cookie_header:
            raw_token = cookie_header.split(f"{config.ACCESS_COOKIE}=")[1].split(";")[0]
            access_token = decode(raw_token)

            if access_token and isinstance(access_token, dict):
                username = access_token['username']
    except Exception:
        username = None
    
    if username:
        if not roomsvc.join_room(room_token, username):
            await websocket.close()
            return
        
        if room_token in roomsvc.rooms:
            user = next((user for user in roomsvc.rooms[room_token].users if user.username == username), None)
            if user and user.connection_state != 'banned':
                user.connection_state = 'connected'
    else:
        if room_token not in roomsvc.rooms:
            await websocket.close()
            return

    try:
        while True:
            room_stream = roomsvc.refresh_room(room_token, delta_time=config.FREQUENCY)

            if not room_stream:
                await websocket.send_json({})
                await websocket.close()
                break
                
            protected_stream = _mask_room_stream(room_stream, username)
            
            try:
                validated_stream = schema.RoomStream.model_validate(protected_stream)
                await websocket.send_json(validated_stream.model_dump(mode='json'))
            except ValidationError as e:
                await websocket.send_json({})
                
            await asyncio.sleep(config.FREQUENCY)
            
    except WebSocketDisconnect:
        if username and room_token in roomsvc.rooms:
            user = next((user for user in roomsvc.rooms[room_token].users if user.username == username), None)
            if user and user.connection_state != 'banned':
                user.connection_state = 'disconnected'