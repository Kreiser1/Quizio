from fastapi import Depends, Request
from database import session, Session
from schema import UserSession
from typing import Annotated
from security import ACCESS_COOKIE, REFRESH_COOKIE

DatabaseSession = Annotated[Session, Depends(session)]

def _get_user_session(request: Request) -> UserSession:
    access_token = request.cookies.get(ACCESS_COOKIE)

    

Authorization = Annotated[UserSession, Depends(_get_user_session)]