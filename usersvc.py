import schema, security, database as db

def get_profile(session: db.Session, username: schema.Username) -> schema.UserProfile | None:
    profile = session.execute(db.select(
        db.User.full_name,
        db.User.email,
        db.User.avatar,
        db.User.creation_time,
        db.User.role
    ).where(db.User.username == username)).mappings().first()

    if not profile:
        return None
    
    email = security.decode(profile['email'])['email'] if profile['email'] else None
    
    return schema.UserProfile(
        username=username,
        full_name=profile['full_name'],
        email=email,
        avatar=profile['avatar'],
        creation_time=profile['creation_time'],
        role=profile['role']
    )

def update_profile(session: db.Session, username: schema.Username, user_update_payload: schema.UserUpdate) -> bool:
    params = {
        **({'full_name': user_update_payload.full_name} if user_update_payload.full_name else {}),
        **({'avatar': user_update_payload.avatar} if user_update_payload.avatar else {}),
    }

    return session.execute(db.update(db.User).where(db.User.username == username).values(**params)).rowcount > 0

def update_role(session: db.Session, user_role_update_payload: schema.UserRoleUpdate) -> bool:
    return session.execute(db.update(db.User).where(db.User.username == user_role_update_payload.username).values(role=user_role_update_payload.role)).rowcount > 0

def delete_profile(session: db.Session, username: schema.Username) -> bool:
    return session.execute(db.delete(db.User).where(db.User.username == username)).rowcount > 0

def get_users(session: db.Session) -> set[schema.Username]:
    return session.execute(db.select(db.User.username)).scalars().all()