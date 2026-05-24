import secrets
from typing import Dict, List
import database as db
import schema
import quizsvc


rooms: dict[schema.RoomToken, schema.Room] = {}

def create_room(session: db.Session, payload: schema.RoomCreate) -> schema.RoomToken | None:
    quiz = quizsvc.get_quiz(session, payload.quiz_id)

    if not quiz:
        return None

    access_token = secrets.token_hex(4)
    
    if access_token in rooms:
        return None

    rooms[access_token] = schema.Room(
        title=payload.title or f"Комната {access_token}",
        users=set(),
        teams=payload.teams,
        privacy=payload.privacy,
        quiz=quiz,
        current_question=0
    )

    return access_token

def update_room(session: db.Session, access_token: schema.RoomToken, payload: schema.RoomUpdate) -> bool:
    if access_token not in rooms:
        return False

    quiz = quizsvc.get_quiz(session, payload.quiz_id)

    if not quiz:
        return False

    room = rooms[access_token]
    room.title = payload.title or f"Комната {access_token}"
    room.privacy = payload.privacy
    room.quiz = quiz
    room.teams = payload.teams
    
    room.current_question = 0

    for user in room.users:
        user.score = 0
        user.answers_streak = 0
        user.answers_total = 0
        user.answers_correct = 0

    return True

def join_room(access_token: schema.RoomToken, username: schema.Username) -> bool:
    if access_token not in rooms:
        return False

    room = rooms[access_token]
    
    if any(user.username == username for user in room.users):
        return True

    new_user = schema.RoomUser(
        username=username,
        connection_state='disconnected',
        score=0,
        answers_streak=0,
        answers_total=0,
        answers_correct=0
    )

    room.users.add(new_user)
    return True


def search_rooms(query: schema.Title | None = None, count: schema.Count = 25, offset: schema.Index = 0) -> list[dict]:
    """Ищет только PUBLIC комнаты, возвращая их метаданные с пагинацией."""
    public_list = []

    for token, room in rooms.items():
        if room.privacy != "public":
            continue

        if query and query.strip():
            q = query.strip().lower()
            room_title = (room.title or "").lower()
            quiz_title = room.quiz.title.lower()
            if q not in room_title and q not in quiz_title:
                continue

        public_list.append({
            "access_token": token,
            "title": room.title,
            "quiz_title": room.quiz.title,
            "users_count": len(room.users),
            "current_question": room.current_question
        })

    return public_list[offset : offset + count]


def submit_answer(token: schema.RoomToken, username: schema.Username, payload: schema.Answer) -> tuple[bool, int]:
    """Принимает ответ, начисляет очки и обновляет стрик пользователя."""
    if token not in rooms:
        return False, 0

    room = rooms[token]
    user = next((u for u in room.users if u.username == username), None)
    
    if not user or payload.question != room.current_question:
        return False, 0

    try:
        question: schema.Question = room.quiz.questions[room.current_question]
    except IndexError:
        return False, 0

    user_answer = payload.asnwer
    correct_answer = question.answer
    is_correct = False

    # Логика сверки типов ответов
    if question.type == 'select':
        is_correct = (int(user_answer) == int(correct_answer))
    elif question.type == 'multiselect':
        try:
            is_correct = (set(user_answer) == set(correct_answer))
        except Exception:
            is_correct = False
    elif question.type == 'input':
        is_correct = (str(user_answer).strip().lower() == str(correct_answer).strip().lower())

    user.answers_total += 1
    points_awarded = 0

    if is_correct:
        user.answers_correct += 1
        user.answers_streak += 1
        streak_bonus = min(user.answers_streak * 10, 50)
        points_awarded = question.score + streak_bonus
        user.score += points_awarded
    else:
        user.answers_streak = 0

    return is_correct, points_awarded
