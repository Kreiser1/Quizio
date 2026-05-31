import asyncio
import secrets
from typing import Dict, List
import database as db
import schema
import config
import quizsvc
import achisvc


ROOMS: dict[schema.HexString, schema.Room] = {}

def create_room(session: db.Session, username: schema.Username, payload: schema.RoomCreate) -> schema.HexString | None:
    quiz = quizsvc.get_quiz(session, payload.quiz_id)

    if not quiz:
        return None

    room_token = secrets.token_hex(3)

    if room_token in ROOMS:
        return None

    ROOMS[room_token] = schema.Room(
        title=payload.title,
        owner=username,
        users=set(),
        teams=set(),
        privacy=payload.privacy,
        quiz=quiz
    )

    return room_token

def get_room(room_token: schema.HexString) -> schema.Room | None:
    if room_token not in ROOMS:
        return None
    
    return ROOMS[room_token]

def delete_room(room_token: schema.HexString) -> bool:
    if room_token not in ROOMS:
        return False
    
    del ROOMS[room_token]
    return True

def search_rooms(query: schema.Name | None = None, count: schema.Uint = 25, offset: schema.Uint = 0, include_private: bool = False) -> list[schema.RoomPreview]:
    rooms_found = []

    if query:
        query = query.strip().lower()

    for room_token, room in ROOMS.items():
        if not include_private and room.privacy != "public":
            continue

        if query:
            room_title = room.title.lower()
            quiz_title = room.quiz.title.lower()

            if query not in room_title and query not in quiz_title:
                continue

        preview = room.preview
        preview.room_token = room_token

        rooms_found.append(preview)

    return rooms_found[offset : offset + count]