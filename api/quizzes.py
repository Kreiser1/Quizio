from typing import Annotated
from fastapi import APIRouter, status, Path, Depends, Body, Query
from fastapi.responses import StreamingResponse
import io

import schema
import depends
import quizsvc
import config
from exceptions import *


router = APIRouter(prefix='/quizzes', tags=['Викторины'])

@router.post('', response_model=schema.Quiz, status_code=status.HTTP_201_CREATED)
def create_quiz(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    payload: schema.QuizCreate
) -> schema.Quiz:
    """Создать новую викторину (поддерживает YAML)."""

    if isinstance(payload.icon, str) and len(payload.icon) > config.IMAGE_SIZE_LIMIT:
        raise UnprocessableHTTPException("Иконка слишком большая.")

    if isinstance(payload.questions, str):
        if len(payload.questions) > config.QUIZ_SIZE_LIMIT:
            raise UnprocessableHTTPException("Размер викторины превышает лимит.")

        try:
            payload.questions = schema.Quiz.from_yaml(payload.questions)
        except (schema.YAMLError, schema.ValidationError):
            raise UnprocessableHTTPException("Некорректный формат YAML.")
    else:
        yaml_text = schema.Quiz.to_yaml(payload.questions)

        if len(yaml_text) > config.QUIZ_SIZE_LIMIT:
            raise UnprocessableHTTPException("Размер викторины превышает лимит.")

    quiz = quizsvc.create_quiz(session, username, payload)

    if not quiz:
        raise UnknownHTTPException("Не удалось создать викторину.")
    
    return quiz

@router.get('/query', response_model=list[schema.QuizPreview])
def search_quizzes(
    session: depends.Session,
    moderator: depends.Moderator,
    query: schema.Name | None = Query(default=None),
    tags: set[schema.Tag] | None = Query(default=None),
    count: schema.Uint = Query(default=25),
    offset: schema.Uint = Query(default=0)
) -> list[schema.QuizPreview]:
    """Поиск викторин по названию и тегам."""

    return quizsvc.search_quizzes(session, query=query, tags=tags, count=count, offset=offset)

@router.get('/{id}', response_model=schema.Quiz)
def get_quiz(
    session: depends.Session,
    moderator: depends.Moderator,
    id: schema.Uint = Path(...)
) -> schema.Quiz:
    """Получить викторину по ID."""

    quiz = quizsvc.get_quiz(session, id)

    if not quiz:
        raise NotFoundHTTPException("Викторина не найдена.")
    
    return quiz

@router.patch('/{id}')
def update_quiz(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    role: depends.Role,
    id: schema.Uint = Path(...),
    payload: schema.QuizCreate = Body(...)
):
    """Обновить викторину (поддерживает YAML)."""

    quiz = quizsvc.get_quiz(session, id)

    if not quiz:
        raise NotFoundHTTPException("Викторина не найдена.")

    if not quizsvc.is_quiz_author(session, id, username) and role != 'administrator':
        raise ForbiddenHTTPException("Вы не являетесь автором этой викторины.")
    
    if isinstance(payload.icon, str) and len(payload.icon) > config.IMAGE_SIZE_LIMIT:
            raise UnprocessableHTTPException("Иконка слишком большая.")

    if isinstance(payload.questions, str):
        if len(payload.questions) > config.QUIZ_SIZE_LIMIT:
            raise UnprocessableHTTPException("Размер викторины превышает лимит.")
        
        try:
            payload.questions = schema.Quiz.from_yaml(payload.questions)
        except (schema.YAMLError, schema.ValidationError):
            raise UnprocessableHTTPException("Некорректный формат YAML.")
    else:
        yaml_text = schema.Quiz.to_yaml(payload.questions)

        if len(yaml_text) > config.QUIZ_SIZE_LIMIT:
            raise UnprocessableHTTPException("Размер викторины превышает лимит.")

    if not quizsvc.update_quiz(session, username, id, payload):
        raise UnknownHTTPException("Не удалось обновить викторину.")

@router.post('/{id}/authors')
def add_author(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    role: depends.Role,
    id: schema.Uint = Path(...),
    author: schema.Username = Body(embed=True)
):
    """Добавить соавтора к викторине."""

    if not quizsvc.get_quiz(session, id):
        raise NotFoundHTTPException("Викторина не найдена.")

    if not quizsvc.is_quiz_author(session, id, username) and role != 'administrator':
        raise ForbiddenHTTPException("У вас нет прав для изменения состава авторов.")

    if not quizsvc.add_quiz_author(session, id, author):
        raise ConflictHTTPException("Не удалось добавить автора. Возможно, он уже добавлен.")

@router.get('/{id}/authors', response_model=set[schema.Username])
def get_authors(
    session: depends.Session,
    moderator: depends.Moderator,
    id: schema.Uint = Path(...)
) -> set[schema.Username]:
    """Получить список авторов викторины."""

    if not quizsvc.get_quiz(session, id):
        raise NotFoundHTTPException("Викторина не найдена.")

    return quizsvc.get_quiz_authors(session, id)

@router.delete('/{id}/authors/{author}')
def remove_author(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    role: depends.Role,
    id: schema.Uint = Path(...),
    author: schema.Username = Path(...)
):
    """Удалить соавтора из викторины."""

    if not quizsvc.get_quiz(session, id):
        raise NotFoundHTTPException("Викторина не найдена.")

    if not quizsvc.is_quiz_author(session, id, username) and role != 'administrator':
        raise ForbiddenHTTPException("У вас нет прав для изменения состава авторов.")

    if not quizsvc.remove_quiz_author(session, id, author):
        raise ConflictHTTPException("Не удалось удалить автора или он не является автором.")

@router.delete('/{id}')
def delete_quiz(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    role: depends.Role,
    id: schema.Uint = Path(...)
):
    """Удалить викторину."""

    if not quizsvc.get_quiz(session, id):
        raise NotFoundHTTPException("Викторина не найдена.")

    if not quizsvc.is_quiz_author(session, id, username) and role != 'administrator':
        raise ForbiddenHTTPException("У вас нет прав для удаления этой викторины.")

    if not quizsvc.delete_quiz(session, id):
        raise UnknownHTTPException("Не удалось удалить викторину.")

@router.get('/{id}/yaml')
def download_quiz_yaml(
    session: depends.Session,
    moderator: depends.Moderator,
    id: schema.Uint = Path(...)
):
    """Скачать вопросы викторины в виде .yaml-файла."""

    quiz = quizsvc.get_quiz(session, id)

    if not quiz:
        raise NotFoundHTTPException("Викторина не найдена.")

    return StreamingResponse(
        io.BytesIO(schema.Quiz.to_yaml(quiz.questions).encode('utf-8')), 
        media_type='application/x-yaml',
        headers={
            'Content-Disposition': f'attachment; filename="{f"quiz_{id}.yaml"}"'
        }
    )
