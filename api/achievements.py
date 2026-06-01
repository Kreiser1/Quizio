from typing import Annotated
from fastapi import APIRouter, status, Path, Depends, Body
from fastapi.responses import StreamingResponse
import re

import schema
import depends
import achisvc
import config
from exceptions import *


router = APIRouter(prefix='/achievements', tags=['Достижения'])

SAFE_PATTERN = re.compile(r'^(?!.*__)(?!.*\bpow\b)(?!.*<<)(?!.*setattr)(?!.*lambda)(?!.*def)(?!.*format)(?!.*getattr)(?!.*local)(?!.*global)(?!.*>>)(?!.*\*\*)(?!.*%)(?!.*\bclass\b)(?!.*\\x[0-9a-fA-F]{2})[a-zA-Z0-9\s\.&|!=<>()[\]\'"]+$')

@router.post('', response_model=schema.Achievement, status_code=status.HTTP_201_CREATED)
def create_achievement(
    session: depends.Session,
    moderator: depends.Moderator,
    role: depends.Role,
    payload: schema.AchievementCreate
) -> schema.Achievement:
    """Создать новое достижение."""
    
    if isinstance(payload.icon, str) and len(payload.icon) > config.IMAGE_SIZE_LIMIT:
        raise UnprocessableHTTPException("Иконка слишком большая.")

    if role != 'administrator' and (not SAFE_PATTERN.match(payload.condition) or len(payload.condition) > 128):
        raise ForbiddenHTTPException("Условие слишком длинное или содержит запрещённые конструкции. Обратитесь к администратору.")        

    try:
        compile(payload.condition, "<string>", "eval")
    except SyntaxError:
        raise UnprocessableHTTPException("Некорректный синтаксис в условии достижения.")

    achievement = achisvc.create_achievement(session, payload)

    if not achievement:
        raise ConflictHTTPException("Не удалось создать достижение.")
        
    return achievement

@router.delete('/{id}')
def delete_achievement(
    session: depends.Session,
    moderator: depends.Moderator,
    id: schema.Uint = Path(...)
):
    """Удалить достижение."""

    if not achisvc.delete_achievement(session, id):
        raise NotFoundHTTPException("Достижение не найдено.")

@router.get('', response_model=list[schema.Achievement])
def get_my_achievements(
    session: depends.Session,
    username: depends.Username,
    role: depends.Role
) -> list[schema.AchievementCreate]:
    """Получить список достижений текущего пользователя."""
    
    achievements = achisvc.get_user_achievements(session, username)

    if role != 'administrator' and role != 'moderator':
        for achievement in achievements:
            achievement.condition = '<secret>'
        
    return achievements

@router.get('/all', response_model=list[schema.Achievement])
def get_achievements(
    session: depends.Session,
    role: depends.Role
) -> list[schema.Achievement]:
    """Получить список всех достижений."""

    achievements = achisvc.get_achievements(session)

    if role != 'administrator' and role != 'moderator':
        for achievement in achievements:
            achievement.condition = '<secret>'
        
    return achievements