from fastapi import APIRouter, status, Path

import security, schema, depends, usersvc, config
from exceptions import *

router = APIRouter(prefix='/quizzez', tags=['Викторины'])

@router.get('/{id}', response_model=schema.UserProfile)
def get_quiz(session: depends.Session, moderator: depends.Moderator) -> schema.Quiz:
    """Получить викторину по ID."""

    raise NotImplementedHTTPException()