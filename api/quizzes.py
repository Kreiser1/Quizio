from typing import Annotated
from fastapi import APIRouter, status, Path, Depends, Body, UploadFile, File
import schema, depends, quizsvc, config
from exceptions import *

router = APIRouter(prefix='/quizzes', tags=['Викторины'])

@router.post('', response_model=schema.Quiz, status_code=status.HTTP_201_CREATED)
def create_quiz(
    session: depends.Session,
    moderator: depends.Moderator,
    username: depends.Username,
    payload: schema.QuizCreate
) -> schema.Quiz:
    """Создать викторину."""
    
    yaml_text = schema.Quiz.to_yaml(payload.questions)

    if len(yaml_text) > config.QUIZ_SIZE_LIMIT:
        raise UnprocessableHTTPException("Превышен лимит размера квиза.")

    quiz = quizsvc.create_quiz(session, username, payload)

    if not quiz:
        raise ConflictHTTPException("Не удалось создать викторину.")
    
    return quiz


@router.get('/{id}', response_model=schema.Quiz)
def get_quiz(
    session: depends.Session,
    moderator: depends.Moderator,
    id: schema.Index = Path(...)
) -> schema.Quiz:
    """Получить викторину."""
    
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
    payload: schema.Quiz | str = Body(...)
):
    """Обновить викторину (через JSON-модель или строку текста YAML)."""
        
    quiz = quizsvc.get_quiz(session, id)

    if not quiz:
        raise NotFoundHTTPException("Викторина не найдена.")

    if not quizsvc.is_quiz_author(session, id, username) and role == 'administrator':
        raise ForbiddenHTTPException("Вы не являетесь автором этой викторины.")

    if isinstance(payload, str):
        if len(payload) > config.QUIZ_SIZE_LIMIT:
            raise UnprocessableHTTPException("Размер квиза превышает лимит.")

        quiz.questions = schema.Quiz.from_yaml(payload)
    else:
        if isinstance(payload.icon, schema.Base64):
            if len(payload.icon) > config.IMAGE_SIZE_LIMIT:
                raise UnprocessableHTTPException("Иконка слишком большая.")
        yaml_text = schema.Quiz.to_yaml(payload.questions)
        if len(yaml_text) > config.QUIZ_SIZE_LIMIT:
            raise UnprocessableHTTPException("Размер квиза превышает лимит.")

    if not quizsvc.update_quiz(session, username, quiz):
        raise ConflictHTTPException("Не удалось обновить викторину.")