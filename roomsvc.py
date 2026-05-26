import asyncio
import secrets
from typing import Dict, List
import database as db
import schema
import config
import quizsvc
import achisvc


rooms: dict[schema.RoomToken, schema.Room] = {}

def create_room(session: db.Session, username: schema.Username, payload: schema.RoomCreate) -> schema.RoomToken | None:
    quiz = quizsvc.get_quiz(session, payload.quiz_id)

    if not quiz:
        return None

    room_token = secrets.token_hex(4)

    if room_token in rooms:
        return None

    rooms[room_token] = schema.Room(
        title=payload.title,
        owner=username,
        users=set(),
        teams=set(),
        privacy=payload.privacy,
        quiz=quiz,
        current_question=None
    )
    return room_token

def update_room(session: db.Session, room_token: schema.RoomToken, payload: schema.RoomCreate) -> bool:
    if room_token not in rooms:
        return False

    quiz = quizsvc.get_quiz(session, payload.quiz_id)

    if not quiz:
        return False

    room = rooms[room_token]
    room.title = payload.title
    room.privacy = payload.privacy
    room.quiz = quiz
    room.time = None
    room.current_question = None

    for user in room.users:
        user.score = 0
        user.answers.clear()
        user.answers_streak = 0
    
    return True

def join_room(room_token: schema.RoomToken, username: schema.Username) -> bool:
    if room_token not in rooms:
        return False

    room = rooms[room_token]
    user = next((user for user in room.users if user.username == username), None)

    if user:
        return not user.connection_state == 'banned'

    new_user = schema.RoomUser(
        username=username,
        connection_state='disconnected',
        score=0,
        answers_streak=0,
        answers=set()
    )

    room.users.add(new_user)
    return True

def search_rooms(query: schema.Title | None = None, count: schema.Count = 25, offset: schema.Index = 0) -> list[schema.RoomPreview]:
    rooms_found = []

    if query:
        query = query.strip().lower()

    for token, room in rooms.items():
        if room.privacy != "public":
            continue

        if query:
            room_title = room.title.lower()
            quiz_title = room.quiz.title.lower()

            if query not in room_title and query not in quiz_title:
                continue

        rooms_found.append(schema.RoomPreview(
            title=room.title,
            owner=room.owner,
            users_count=room.users_count,
            room_token=token,
            privacy=room.privacy,
            state='active' if room.current_question is not None else 'waiting',
            quiz=schema.QuizPreview(
                id=room.quiz.id,
                title=room.quiz.title,
                icon=room.quiz.icon,
                creation_time=room.quiz.creation_time,
                tags=room.quiz.tags,
                authors=set()
            )
        ))

    return rooms_found[offset : offset + count]

def submit_answer(token: schema.RoomToken, username: schema.Username, payload: schema.Answer) -> bool:
    if token not in rooms:
        return False

    room = rooms[token]
    user = next((user for user in room.users if user.username == username), None)
    
    if not user or user.connection_state == 'banned' or payload.question != room.current_question:
        return False

    try:
        question: schema.Question = room.quiz.questions[room.current_question]
    except IndexError:
        return False
    
    if any(answer[0] == payload.question for answer in user.answers):
        return False

    user_answer = payload.answer
    correct_answer = question.answer
    is_correct = False

    try:
        if question.type == 'select':
            is_correct = schema.Index(user_answer) == schema.Index(correct_answer)
        elif question.type == 'multiselect':
            
            is_correct = set(user_answer) == set(correct_answer)
        elif question.type == 'input':
            is_correct = str(user_answer).lower() == str(correct_answer).lower()
    except (schema.ValidationError, TypeError, ValueError):
        is_correct = False

    if is_correct:
        streak_bonus = min(1 + user.answers_streak * 0.2, 2.0)
        user.score += question.score * streak_bonus
        user.answers_streak += 1
        user.answers.add((payload.question, is_correct))
    else:
        user.answers_streak = 0
        user.answers.add((payload.question, is_correct))

    return is_correct

def control_room(room_token: schema.RoomToken, payload: schema.RoomControl) -> bool:
    if room_token not in rooms:
        return False

    room = rooms[room_token]
    command = payload.command
    question = payload.question

    if question is not None:
        if question < 0 or question >= len(room.quiz.questions):
            return False

    if command == 'show':
        room.current_question = question
        room.time = None
    elif command == 'start':
        room.current_question = question
        if question is not None:
            room.time = room.quiz.questions[question].time
        else:
            room.time = None
    elif command == 'stop':
        room.current_question = question
        room.time = None
    elif command == 'end':
        with db.connect() as session:
            achievements = achisvc.get_achievements(session)
            for user in room.users:
                for achievement in achievements:
                    achisvc.test_achievement(session, achievement, room, user)

        if room_token in rooms:
            del rooms[room_token]

    return True

def ban_user(token: schema.RoomToken, username: schema.Username) -> bool:
    if token not in rooms:
        return False
    
    room = rooms[token]
    user = next((user for user in room.users if user.username == username), None)

    if not user:
        return False
    
    user.connection_state = 'banned'
    return True

def unban_user(token: schema.RoomToken, username: schema.Username) -> bool:
    if token not in rooms:
        return False
    
    room = rooms[token]
    user = next((user for user in room.users if user.username == username), None)

    if not user:
        return False
    
    user.connection_state = 'disconnected'
    return True

def add_team(token: schema.RoomToken, payload: schema.RoomTeam) -> bool:
    if token not in rooms:
        return False
    
    room = rooms[token]
    team = next((team for team in room.teams if team.title == payload.title), None)

    if team:
        return False
    
    room.teams.add(payload)
    return True

def delete_team(token: schema.RoomToken, title: schema.Title) -> bool:
    if token not in rooms:
        return False
    
    room = rooms[token]
    team = next((team for team in room.teams if team.title == title), None)

    if not team:
        return False
    
    room.teams.remove(team)
    return True

def set_user_team(token: schema.RoomToken, username: schema.Username, title: schema.Title | None) -> bool:
    if token not in rooms:
        return False
    
    room = rooms[token]
    user = next((user for user in room.users if user.username == username), None)

    if not user:
        return False

    for team in room.teams:
        user_team = next((user for user in team.users if user.username == username), None)

        if user_team:
            team.users.remove(user_team)

    if title is not None:
        team = next((team for team in room.teams if team.title == title), None)

        if not team:
            return False
        
        team.users.add(user)

    return True

def refresh_room(token: schema.RoomToken, delta_time: schema.Time = config.FREQUENCY) -> schema.RoomStream | None:
    if token not in rooms:
        return None

    room = rooms[token]

    if room.time is not None:
        room.time -= delta_time
        
        if room.time <= 0:
            room.time = None
            room.current_question = None

    q_score, q_text, q_title, q_image, q_code, q_type, q_time = [None] * 7

    if room.current_question is not None:
        try:
            q: schema.Question = room.quiz.questions[room.current_question]
            q_score = q.score
            q_text = q.text
            q_title = q.title
            q_image = q.image
            q_code = q.code
            q_type = q.type
            q_time = room.time
        except IndexError:
            pass

    return schema.RoomStream(
        title=room.title,
        users=room.users,
        teams=room.teams,
        privacy=room.privacy,
        current_question=room.current_question,
        question_score=q_score,
        question_text=q_text,
        question_title=q_title,
        question_image=q_image,
        question_code=q_code,
        question_type=q_type,
        question_time=q_time
    )
