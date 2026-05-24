from typing import Annotated
from fastapi import APIRouter, status, Path, Depends, Body, Query
from fastapi.responses import StreamingResponse
import io

import schema
import depends
import quizsvc
import gamesvc
import config
from exceptions import *


router = APIRouter(prefix='/games', tags=['Игры'])