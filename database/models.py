from . import Base, Mapped, exists, relationship, CheckConstraint, mapped_column, String, Integer, Text, UniqueConstraint, Table, Column, Optional, ForeignKey, session, BigInteger
import schema, security, config


user_quiz = Table(
    'user_quiz',
    Base.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('username', String(32), ForeignKey('users.username', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
    Column('quiz_id', Integer, ForeignKey('quizzes.id', ondelete='CASCADE')),
    UniqueConstraint('username', 'quiz_id', name='user_quiz_unique')
)

tag_quiz = Table(
    'tag_quiz',
    Base.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('tag', String(32), nullable=False),
    Column('quiz_id', Integer, ForeignKey('quizzes.id', ondelete='CASCADE')),
    UniqueConstraint('tag', 'quiz_id', name='tag_quiz_unique')
)


class User(Base):
    __tablename__ = 'users'
    
    username: Mapped[str] = mapped_column(String(32), primary_key=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    avatar: Mapped[str] = mapped_column(Text(), default='0', nullable=False)
    password_hash: Mapped[str] = mapped_column(String(384), nullable=False)
    email_hash: Mapped[Optional[str]] = mapped_column(String(384), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default='user', nullable=False)
    creation_time: Mapped[str] = mapped_column(String(32), nullable=False)

    quizzes: Mapped[list["Quiz"]] = relationship(
        secondary=user_quiz, 
        back_populates="users"
    )

    __table_args__ = (
        CheckConstraint(
            "(email_hash IS NULL AND email IS NULL) OR (email_hash IS NOT NULL AND email IS NOT NULL)",
            name="check_users_email_hash_email"
        ),
    )


class Quiz(Base):
    __tablename__ = 'quizzes'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    icon: Mapped[str] = mapped_column(Text(), default='0')
    creation_time: Mapped[str] = mapped_column(String(32), nullable=False)
    edit_time: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    last_edit_username: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    yaml: Mapped[str] = mapped_column(Text, nullable=False)
    
    @property
    def questions(self) -> list[schema.Question]:
        return schema.Quiz.from_yaml(self.yaml)
    
    @questions.setter
    def questions(self, value: list[schema.Question]):
        self.yaml = schema.Quiz.to_yaml(value)

    authors: Mapped[list["User"]] = relationship(
        secondary=user_quiz, 
        back_populates="quizzes"
    )


class Auth(Base):
    __tablename__ = 'auth'

    refresh_token: Mapped[str] = mapped_column(String(128), primary_key=True)
    username: Mapped[str] = mapped_column(String(32), ForeignKey('users.username', ondelete='CASCADE'), nullable=False)
    creation_time: Mapped[str] = mapped_column(String(32), nullable=False)
    expiration_time: Mapped[int] = mapped_column(BigInteger, nullable=False)
    device: Mapped[str] = mapped_column(String(128), nullable=True)