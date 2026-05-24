from fastapi import APIRouter

import security, schema, depends
from exceptions import *

router = APIRouter(prefix='/users', tags=['Пользователи'])