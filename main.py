from database import session, exists, User
from datetime import datetime
import schema, security, config

with session() as db:
    if not db.query(exists().where(User.username == 'administrator')).scalar():
        db.add(User(
            username='administrator',
            password_hash=security.hash(config.ADMIN_PASSWORD + config.AUTH_SECRET),
            role='administrator',
            creation_time=schema.format_datetime(datetime.now())
        ))