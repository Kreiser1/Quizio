import schema, security, database as db

def get_profile(session: db.Session, username: schema.Username) -> schema.UserProfile | None:
    profile = session.execute(db.select(
        db.User.nickname,
        db.User.email,
        db.User.avatar,
        db.User.creation_date,
        db.User.role
    ).where(db.User.username == username)).first()

    if not profile:
        return None
    
    email = profile[1]

    if email and (email := security.decode(email)):
        email = email['email']

    return schema.UserProfile(
        username=username,
        nickname=profile[0],
        email=email,
        avatar=profile[2],
        creation_date=profile[3],
        role=profile[4]
    )

def update_profile(session: db.Session, username: schema.Username, user_update_payload: schema.UserUpdate) -> bool:
    params = {
        **({'full_name': user_update_payload.full_name} if user_update_payload.full_name else {}),
        **({'avatar': user_update_payload.avatar} if user_update_payload.avatar else {}),
    }

    return session.execute(db.update(db.User).where(db.User.username == username).values(**params)).rowcount > 0

def delete_profile(session: db.Session, username: schema.Username) -> bool:
    return session.execute(db.delete(db.User).where(db.User.username == username)).rowcount > 0

def get_users(session: db.Session) -> set[schema.Username]:
    return session.execute(db.select(db.User.username)).scalars().all()