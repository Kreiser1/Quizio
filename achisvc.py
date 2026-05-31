from datetime import datetime
import database as db
import schema

def create_achievement(session: db.Session, payload: schema.AchievementCreate) -> schema.Achievement | None:
    try:
        compile(payload.condition, "<string>", "eval")
    except SyntaxError:
        return None
    
    new_achievement = db.Achievement(
        title=payload.title,
        icon=payload.icon,
        condition=payload.condition
    )

    session.add(new_achievement)

    try:
        session.flush()
    except db.IntegrityError:
        return None
    
    return schema.Achievement(
        id=new_achievement.id,
        title=new_achievement.title,
        icon=new_achievement.icon,
        condition=new_achievement.condition
    )

def delete_achievement(session: db.Session, id: schema.Uint) -> bool:
    return session.execute(db.delete(db.Achievement).where(db.Achievement.id == id)).rowcount > 0

def award_achievement(session: db.Session, username: schema.Username, id: schema.Uint) -> bool:
    user_exists = session.query(db.User.username).filter(db.User.username == username).scalar() is not None
    achi_exists = session.query(db.Achievement.id).filter(db.Achievement.id == id).scalar() is not None
    
    if not user_exists or not achi_exists:
        return False
    
    session.execute(db.insert(db.user_achievement).values(
        username=username,
        achievement_id=id
    ))

    try:
        session.flush()
        return True
    except db.IntegrityError:
        return False

def revoke_achievement(session: db.Session, username: schema.Username, id: schema.Uint) -> bool:
    return session.execute(db.delete(db.user_achievement).where(db.user_achievement.c.username == username, db.user_achievement.c.achievement_id == id)).rowcount > 0

def get_user_achievements(session: db.Session, username: schema.Username) -> list[schema.Achievement]:
    achievements = session.execute(db.select(
            db.Achievement.id,
            db.Achievement.title,
            db.Achievement.icon,
            db.Achievement.condition
        )
        .join(db.user_achievement, db.Achievement.id == db.user_achievement.c.achievement_id)
        .where(db.user_achievement.c.username == username)).all()
    
    return [
        schema.Achievement(
            id=achievement[0],
            title=achievement[1],
            icon=achievement[2],
            condition=achievement[3]
        )
        for achievement in achievements
    ]

def get_achievements(session: db.Session) -> list[schema.Achievement]:
    achievements = session.execute(db.select(
        db.Achievement.id,
        db.Achievement.title,
        db.Achievement.icon,
        db.Achievement.condition
    )).all()
    
    return [
        schema.Achievement(
            id=achievement[0],
            title=achievement[1],
            icon=achievement[2],
            condition=achievement[3]
        )
        for achievement in achievements
    ]

def test_achievement(session: db.Session, achievement: schema.Achievement, room: schema.Room, room_user: schema.RoomUser) -> bool:
    if session.execute(db.select(db.exists(db.user_achievement).where(
        db.user_achievement.c.achievement_id == achievement.id,
        db.user_achievement.c.username == room_user.username
    ))).scalar():
        return False
    
    try:
        grant = eval(achievement.condition, globals={"__builtins__": None}, locals={'room': room, 'user': room_user})
    except Exception:
        return False

    if not grant:
        return False
    
    return award_achievement(session, room_user.username, achievement.id)