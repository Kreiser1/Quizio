import sqlite3

from sqlalchemy import create_engine, exists, select, update, delete, func, and_
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session
from sqlalchemy import String, Text, UniqueConstraint, CheckConstraint, Integer, Table, Column, ForeignKey, BigInteger
from sqlalchemy.exc import IntegrityError
from typing import Optional
from config import DATABASE_URI
from collections.abc import Generator


class Base(DeclarativeBase):
	pass


engine = create_engine(DATABASE_URI)
_Session = sessionmaker(
    bind=engine,
    autocommit=False, 
    autoflush=False,
    expire_on_commit=True
)

def session() -> Generator[Session, None, None]:
    with _Session() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

from contextlib import contextmanager

@contextmanager
def connect() -> Generator[Session, None, None]:
    with _Session() as session:
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