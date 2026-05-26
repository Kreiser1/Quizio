from typing import Annotated
from fastapi import APIRouter, status, Path, Depends, Body
from fastapi.responses import StreamingResponse
import io

import schema
import depends
import achisvc
import config
from exceptions import *


router = APIRouter(prefix='/achievements', tags=['Достижения'])

@router.post('', response_model=schema.Achievement, status_code=status.HTTP_201_CREATED)
def create_achievement(
    session: depends.Session,
    moderator: depends.Moderator,
    payload: schema.AchievementCreate = Body(...)
) -> schema.Achievement:
    """Создать новое достижение."""
    
    if isinstance(payload.icon, str):
        if len(payload.icon) > config.IMAGE_SIZE_LIMIT:
            raise UnprocessableHTTPException("Иконка слишком большая.")
    elif payload.icon > 1048576:
        raise UnprocessableHTTPException("Неверная иконка.")

    try:
        compile(payload.condition, "<string>", "eval")
    except SyntaxError:
        raise UnprocessableHTTPException("Некорректный синтаксис в условии достижения.")
    

    achievement = achisvc.create_achievement(session, payload)

    if not achievement:
        raise ConflictHTTPException("Не удалось создать достижение.")
        
    return achievement

@router.delete('/{id}', status_code=status.HTTP_200_OK)
def delete_achievement(
    session: depends.Session,
    moderator: depends.Moderator,
    id: schema.Index = Path(...)
):
    """Удалить достижение."""

    success = achisvc.delete_achievement(session, id)

    if not success:
        raise NotFoundHTTPException("Достижение не найдено.")

@router.get('/yaml', status_code=status.HTTP_200_OK)
def download_achievements_yaml(
    session: depends.Session,
    moderator: depends.Moderator
):
    """Скачать .yaml всех достижений."""

    achievements = achisvc.get_achievements(session)
    
    if not achievements:
        raise NotFoundHTTPException("Список достижений пуст.")

    file_like = io.BytesIO(schema.Achievement.to_yaml(achievements).encode('utf-8'))
    filename = "achievements.yaml"

    return StreamingResponse(
        schema.Achievement.to_yaml(achievements), 
        media_type='application/x-yaml',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )

@router.get('', response_model=list[schema.AchievementCreate], status_code=status.HTTP_200_OK)
def get_my_achievements(
    session: depends.Session,
    username: depends.Username
) -> list[schema.AchievementCreate]:
    """Получить список всех достижений текущего пользователя."""
    
    user_achievements = achisvc.get_user_achievements(session, username)
        
    return [
        schema.AchievementCreate(
            title=achievement.title,
            icon=achievement.icon,
            condition='<secret>'
        )
        for achievement in user_achievements
    ]