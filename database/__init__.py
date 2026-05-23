import sqlite3

from sqlalchemy import create_engine, exists
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session as _Session
from sqlalchemy import String, Text, UniqueConstraint, CheckConstraint, Integer, Table, Column, ForeignKey
from sqlalchemy.exc import IntegrityError
from typing import Optional
from config import DATABASE_URI
from collections.abc import Generator
from contextlib import contextmanager


class Base(DeclarativeBase):
	pass


engine = create_engine(DATABASE_URI)
Session = sessionmaker(
    bind=engine,
    autocommit=False, 
    autoflush=False,
    expire_on_commit=True
)

@contextmanager
def session() -> Generator[_Session, None, None]:
    with Session() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


from .models import *
Base.metadata.create_all(bind=engine)