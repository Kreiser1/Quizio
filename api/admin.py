from fastapi import APIRouter, status

import database as db
import security, schema, depends
from exceptions import *

router = APIRouter(prefix='/admin', tags=['Администрирование'])

@router.get('/test', response_model=list[schema.Username])
def test(administrator: depends.Administrator, session: depends.Session):
    return session.execute(db.select(db.User.username)).scalars().all()