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
    """Создать новую викторину."""

    if isinstance(payload.icon, str) and len(payload.icon) > config.IMAGE_SIZE_LIMIT:
        raise UnprocessableHTTPException("Иконка слишком большая.")

    yaml_text = schema.Quiz.to_yaml(payload.questions)

    if len(yaml_text) > config.QUIZ_SIZE_LIMIT:
        raise UnprocessableHTTPException("Размер квиза превышает лимит.")

    quiz = quizsvc.create_quiz(session, username, payload)

    if not quiz:
        raise ConflictHTTPException("Не удалось создать викторину.")
    
    return quiz

@router.get('/query', response_model=list[schema.QuizPreview])
def search_quizzes(
    session: depends.Session,
    moderator: depends.Moderator,
    query: schema.Title | None = Query(default=None, description="Поиск по названию"),
    tags: set[schema.Tag] | None = Query(default=None, description="Поиск по тегам"),
    count: schema.Count = Query(default=25),
    offset: schema.Index = Query(default=0)
) -> list[schema.QuizPreview]:
    """Поиск викторин по названию и тегам."""

    return quizsvc.search_quizzes(session, query=query, tags=tags, count=count)

@router.get('/{id}', response_model=schema.Quiz)
def get_quiz(
    session: depends.Session,
    moderator: depends.Moderator,
    id: schema.Index = Path(...)
) -> schema.Quiz:
    """Получить викторину по ID."""

    quiz = quizsvc.get_quiz(session, id)

    if not quiz:
        raise NotFoundHTTPException("Викторина не найдена.")
    
    return quiz

@router.patch('/{id}', status_code=status.HTTP_200_OK)
def update_quiz(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    role: depends.Role,
    id: schema.Index = Path(...),
    payload: schema.QuizCreate | str = Body(...)
):
    """Обновить викторину (через JSON-модель или строку текста YAML)."""

    quiz = quizsvc.get_quiz(session, id)

    if not quiz:
        raise NotFoundHTTPException("Викторина не найдена.")

    if not quizsvc.is_quiz_author(session, id, username) and role != 'administrator':
        raise ForbiddenHTTPException("Вы не являетесь автором этой викторины.")

    if isinstance(payload, str):
        if len(payload) > config.QUIZ_SIZE_LIMIT:
            raise UnprocessableHTTPException("Размер квиза превышает лимит.")
        
        try:
            payload = schema.QuizCreate(title=quiz.title, icon=quiz.icon, questions=schema.Quiz.from_yaml(payload), tags=quiz.tags)
        except schema.YAMLError:
            raise UnprocessableHTTPException("Некорректный формат YAML.")
    else:
        if isinstance(payload.icon, str) and len(payload.icon) > config.IMAGE_SIZE_LIMIT:
            raise UnprocessableHTTPException("Иконка слишком большая.")

        yaml_text = schema.Quiz.to_yaml(payload.questions)

        if len(yaml_text) > config.QUIZ_SIZE_LIMIT:
            raise UnprocessableHTTPException("Размер квиза превышает лимит.")

    if not quizsvc.update_quiz(session, username, id, payload):
        raise ConflictHTTPException("Не удалось обновить викторину.")

@router.post('/{id}/authors', status_code=status.HTTP_200_OK)
def add_author(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    role: depends.Role,
    id: schema.Index = Path(...),
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
    username: depends.Username,
    id: schema.Index = Path(...)
) -> set[schema.Username]:
    """Получить авторов викторины."""

    if not quizsvc.get_quiz(session, id):
        raise NotFoundHTTPException("Викторина не найдена.")

    return quizsvc.get_quiz_authors(session, id)

@router.delete('/{id}/authors/{author}', status_code=status.HTTP_200_OK)
def remove_author(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    role: depends.Role,
    id: schema.Index = Path(...),
    author: schema.Username = Path(...)
):
    """Удалить соавтора из викторины."""

    if not quizsvc.get_quiz(session, id):
        raise NotFoundHTTPException("Викторина не найдена.")

    if not quizsvc.is_quiz_author(session, id, username) and role != 'administrator':
        raise ForbiddenHTTPException("У вас нет прав для изменения состава авторов.")

    if not quizsvc.remove_quiz_author(session, id, author):
        raise ConflictHTTPException("Не удалось удалить автора или он не является автором.")

@router.delete('/{id}', status_code=status.HTTP_200_OK)
def delete_quiz(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    role: depends.Role,
    id: schema.Index = Path(...)
):
    """Удалить викторину."""
    if not quizsvc.get_quiz(session, id):
        raise NotFoundHTTPException("Викторина не найдена.")

    if not quizsvc.is_quiz_author(session, id, username) and role != 'administrator':
        raise ForbiddenHTTPException("У вас нет прав для удаления этой викторины.")

    if not quizsvc.delete_quiz(session, id):
        raise ConflictHTTPException("Не удалось удалить викторину.")
    
@router.get('/query', response_model=list[schema.QuizPreview])
def search_quizzes(
    session: depends.Session,
    moderator: depends.Moderator,
    query: schema.Title | None = Query(default=None),
    tags: list[schema.Tag] | None = Query(default=None),
    count: schema.Count = Query(default=25),
    offset: schema.Index = Query(default=0)
) -> list[schema.QuizPreview]:
    """Поиск викторин по названию и тегам с поддержкой постраничной пагинации."""

    tags_set = set(tags) if tags else None
    return quizsvc.search_quizzes(session, query=query, tags=tags_set, count=count, offset=offset)

@router.get('/{id}/yaml')
def download_quiz_yaml(
    session: depends.Session,
    moderator: depends.Moderator,
    id: schema.Index = Path(...)
):
    """Скачать вопросы викторины в виде .yaml файла."""

    quiz = quizsvc.get_quiz(session, id)

    if not quiz:
        raise NotFoundHTTPException("Викторина не найдена.")

    file_like = io.BytesIO(schema.Quiz.to_yaml(quiz.questions).encode('utf-8'))
    filename = f"quiz_{id}.yaml"

    return StreamingResponse(
        file_like, 
        media_type='application/x-yaml',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )
