from . import Base, Mapped, exists, relationship, CheckConstraint, mapped_column, String, Integer, Text, UniqueConstraint, Table, Column, Optional, ForeignKey, session, BigInteger
import schema, security, config


author_quiz = Table(
    'user_quiz',
    Base.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('username', String(32), ForeignKey('users.username', ondelete='CASCADE', onupdate='CASCADE')),
    Column('quiz_id', Integer, ForeignKey('quizzes.id', ondelete='CASCADE')),
    UniqueConstraint('username', 'quiz_id', name='user_quiz_unique')
)

tag_quiz = Table(
    'tag_quiz',
    Base.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('tag', String(32)),
    Column('quiz_id', Integer, ForeignKey('quizzes.id', ondelete='CASCADE')),
    UniqueConstraint('tag', 'quiz_id', name='tag_quiz_unique')
)

user_achievement = Table(
    'user_achievement',
    Base.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('username', String(32), ForeignKey('users.username', ondelete='CASCADE', onupdate='CASCADE')),
    Column('achievement_id', Integer, ForeignKey('achievements.id', ondelete='CASCADE')),
    UniqueConstraint('username', 'achievement_id', name='user_achievement_unique')
)


class User(Base):
    __tablename__ = 'users'
    
    username: Mapped[str] = mapped_column(String(32), primary_key=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(64))
    avatar: Mapped[str] = mapped_column(Text(), default='0')
    password_hash: Mapped[str] = mapped_column(String(128))
    email_hash: Mapped[Optional[str]] = mapped_column(String(128))
    email: Mapped[Optional[str]] = mapped_column(String(768))
    role: Mapped[str] = mapped_column(String(64), default='user')
    creation_date: Mapped[str] = mapped_column(String(32))

    quizzes: Mapped[list['Quiz']] = relationship(
        secondary=author_quiz, 
        back_populates='authors'
    )

    achievements: Mapped[list['Achievement']] = relationship(
        secondary=user_achievement,
        back_populates='users'
    )

    __table_args__ = (
        CheckConstraint(
            '(email_hash IS NULL AND email IS NULL) OR (email_hash IS NOT NULL AND email IS NOT NULL)',
            name='check_users_email_hash_email'
        ),
    )


class Quiz(Base):
    __tablename__ = 'quizzes'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(64))
    icon: Mapped[str] = mapped_column(Text(), default='1')
    creation_date: Mapped[str] = mapped_column(String(32))
    last_edit_date: Mapped[str] = mapped_column(String(32))
    last_edit_username: Mapped[str] = mapped_column(String(32))
    yaml: Mapped[str] = mapped_column(Text)
    
    @property
    def questions(self) -> list[schema.Question]:
        return schema.Quiz.from_yaml(self.yaml)
    
    @questions.setter
    def questions(self, value: list[schema.Question]):
        self.yaml = schema.Quiz.to_yaml(value)

    authors: Mapped[list['User']] = relationship(
        secondary=author_quiz, 
        back_populates='quizzes'
    )


class Auth(Base):
    __tablename__ = 'auth'

    refresh_token: Mapped[str] = mapped_column(String(128), primary_key=True)
    username: Mapped[str] = mapped_column(String(32), ForeignKey('users.username', ondelete='CASCADE'))
    creation_date: Mapped[str] = mapped_column(String(32))
    expiration_time: Mapped[int] = mapped_column(BigInteger)
    device_name: Mapped[str] = mapped_column(String(128))


class Achievement(Base):
    __tablename__ = 'achievements'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(64))
    icon: Mapped[str] = mapped_column(Text(), default='2')
    condition: Mapped[str] = mapped_column(Text)

    users: Mapped[list['User']] = relationship(
        secondary=user_achievement,
        back_populates='achievements'
    )