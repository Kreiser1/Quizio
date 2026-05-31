from datetime import datetime
from typing import Annotated, Literal
import yaml
from yaml import YAMLError

from pydantic import (
    BaseModel,
    StringConstraints,
    Field,
    computed_field,
    ValidationError
)


Username = Annotated[str, StringConstraints(min_length=3, max_length=32, strip_whitespace=True, to_lower=True, pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$')]
Password = Annotated[str, StringConstraints(min_length=5, max_length=128, pattern=r'^\S+$')]
Text = Annotated[str, StringConstraints(min_length=3, strip_whitespace=True, pattern=r'^[^\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]+$')]
Name = Annotated[str, StringConstraints(min_length=3, max_length=64, strip_whitespace=True, pattern=r'^[^\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]+$')]
Color = Annotated[str, StringConstraints(pattern=r'^#[a-fA-F0-9]{6}$')]
Base64 = Annotated[str, StringConstraints(min_length=3, strip_whitespace=True, pattern=r'^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$')]
Email = Annotated[str, StringConstraints(min_length=5, max_length=254, strip_whitespace=True, to_lower=True, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')]
Uint = Annotated[int, Field(ge=0)]
Ufloat = Annotated[float, Field(ge=0)]
Jwt = Annotated[str, StringConstraints(pattern=r'^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$')]
HexString = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r'^(?:[0-9a-fA-F]{2})+$')]
Role = Literal['user', 'moderator', 'administrator']
Privacy = Literal['public', 'private']
QuestionType = Literal['select', 'multiselect', 'input']
DateTime = Annotated[str, StringConstraints(pattern=r'^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]) (?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$')]
Tag = Annotated[str, StringConstraints(strip_whitespace=True, max_length=32, pattern=r'^#\w+(?:_\w+)*$')]

def format_datetime(datetime: datetime) -> DateTime:
    return datetime.strftime('%Y-%m-%d %H:%M:%S')

def parse_datetime(datetime_: DateTime) -> datetime:
    return datetime.strptime(datetime_, '%Y-%m-%d %H:%M:%S')


class Configuration(BaseModel):
    auth_cooldown: Ufloat
    auth_expiration: Ufloat
    token_expiration: Ufloat
    image_size_limit: Uint
    quiz_size_limit: Uint
    frequency: Ufloat


class Authorization(BaseModel):
    access_token: Jwt
    refresh_token: HexString


class UserSession(BaseModel):
    username: Username
    refresh_token: HexString
    device_name: Name
    creation_date: DateTime
    expiration_time: Ufloat


class UserProfile(BaseModel):
    username: Username
    nickname: Name | None = None
    email: Email | None = None
    avatar: Uint | Base64 = 0
    creation_date: DateTime | None = None
    role: Role


class UserRoleUpdate(BaseModel):
    username: Username
    role: Role


class UserAuthorization(BaseModel):
    username: Username
    password: Password


class UserRegistration(BaseModel):
    username: Username
    password: Password
    email: Email | None = None


class UserUpdate(BaseModel):
    full_name: Name | None = None
    avatar: Uint | Base64 | None = None


class UserRecovery(BaseModel):
    username: Username
    email: Email


class UserCredentialsUpdate(BaseModel):
    old_password: Password
    new_password: Password | None = None
    new_email: Email | None = None


class Question(BaseModel):
    score: Uint
    text: Text
    title: Name
    image: Base64 | None = None
    code: Text | None = None
    type: QuestionType | None
    answer: set[Uint] | Uint | Text | None
    hint: set[Uint] | Text | None
    time: Ufloat | None = None


class Answer(BaseModel):
    question: Uint
    answer: set[Uint] | Uint | Text

    def __hash__(self):
        return hash(self.answer)

    def __eq__(self, other):
        if not isinstance(other, Answer):
            return False
        
        return self.answer == other.answer


class QuizPreview(BaseModel):
    id: Uint
    title: Name
    icon: Uint | Base64 = 1
    creation_date: DateTime
    score: Uint
    questions: Uint
    tags: set[Tag] | None = None
    authors: set[Username]


class QuizCreate(BaseModel):
    title: Name
    icon: Uint | Base64 = 1
    questions: list[Question] | Text
    tags: set[Tag] | None = None

class Quiz(BaseModel):
    id: Uint
    title: Name
    icon: Uint | Base64 = 1
    questions: list[Question]
    creation_date: DateTime
    last_edit_date: DateTime
    last_edit_username: Username
    tags: set[Tag] | None = None
    authors: set[Username]
    
    @computed_field
    @property
    def score(self) -> Uint:
        return sum(map(lambda question: question.score, self.questions))


    class QuestionsYaml(BaseModel):
        questions: list[Question]


    @classmethod
    def from_yaml(cls, text: str) -> list[Question]:
        return cls.QuestionsYaml.model_validate(yaml.safe_load(text)).questions

    @classmethod
    def to_yaml(cls, questions: list[Question]) -> str:
        return yaml.safe_dump(cls.QuestionsYaml(questions=questions).model_dump(mode='json'), sort_keys=False, allow_unicode=True)

    @property
    def preview(self) -> QuizPreview:
        return QuizPreview(id=self.id, title=self.title, icon=self.icon, creation_date=self.creation_date,
                           score=self.score, questions=len(self.questions), tags=self.tags, authors=self.authors)


class RoomUser(BaseModel):
    username: Username
    nickname: Name
    connection: Literal['connected', 'disconnected', 'banned']
    score: Uint
    answers_streak: Uint
    answers: set[Answer]
    
    def __hash__(self):
        return hash(self.username)

    def __eq__(self, other):
        if not isinstance(other, RoomUser):
            return False
        return self.username == other.username


class RoomTeam(BaseModel):
    title: Name
    color: Color
    users: set[Username] = set()
    
    def __hash__(self):
        return hash(self.title)

    def __eq__(self, other):
        if not isinstance(other, RoomTeam):
            return False
        
        return self.title == other.title

class RoomCreate(BaseModel):
    title: Name
    privacy: Privacy
    quiz_id: Uint


class RoomPreview(BaseModel):
    title: Name
    owner: Username
    users: Uint
    privacy: Privacy
    quiz: QuizPreview
    room_token: HexString
    state: Literal['waiting', 'active'] = 'waiting'


class RoomStream(BaseModel):
    title: Name
    users: set[RoomUser]
    teams: set[RoomTeam]
    privacy: Privacy
    question: Uint | None
    score: Uint | None
    text: Text
    question_title: Name
    image: Base64 | None
    code: Text | None
    question_type: QuestionType | None
    hint: set[Uint] | Text | None
    time: Ufloat | None = None


class Room(BaseModel):
    title: Name
    owner: Username
    users: set[RoomUser]
    teams: set[RoomTeam]
    privacy: Privacy
    quiz: Quiz
    question: Uint | None = None
    time: Ufloat | None = None
    _last_refresh_time: Ufloat | None = None

    @property
    def preview(self) -> RoomPreview:
        return RoomPreview(title=self.title, owner=self.owner, users=len(self.users), privacy=self.privacy,
                           room_token='000000', state=('active' if self.question else 'waiting'))

    @property
    def stream(self) -> RoomStream:
        question = self.quiz.questions[self.question] if (self.question and self.question < len(self.quiz.questions)) else Question(
            score=0,
            text='<default>',
            title='<default>',
            image=None,
            code=None,
            type=None,
            answer=None,
            hint=None,
            time=None
        )
        
        return RoomStream(
            title=self.title,
            users=self.users,
            teams=self.teams,
            privacy=self.privacy,
            question=self.question if self.question and self.question < len(self.quiz.questions) else None,
            score=question.score,
            text=question.text,
            question_title=question.title,
            image=question.image,
            code=question.code,
            question_type=question.type,
            hint=question.hint,
            time=self.time if self.question and self.question < len(self.quiz.questions) else None
        )
    
    def start(self, question: Uint):
        self.question = question if question < len(self.quiz.questions) else None
        self.time = self.quiz.questions[question].time if question < len(self.quiz.questions) else None

    def show(self, question: Uint):
        self.question = question if question < len(self.quiz.questions) else None
        self.time = None

    def stop(self):
        self.time = None

    def refresh(self, current_time: Ufloat):
        if self._last_refresh_time is None:
            self._last_refresh_time = current_time

        delta_time = current_time - self._last_refresh_time

        if delta_time <= 0:
            return

        if self.time is not None:
            self.time -= delta_time
        
            if self.time <= 0:
                self.question = None
                self.time = None

    def submit(self, username: Username, answer: Answer) -> bool:
        user = next((user for user in self.users if user.username == username), None)
    
        if not user or answer.question != self.question:
            return False

        try:
            question: Question = self.quiz.questions[self.question]
        except IndexError:
            return False
        
        if any(user_answer.question == answer.question for user_answer in user.answers):
            return False

        user_answer = answer.answer
        correct_answer = question.answer
        is_correct = False

        try:
            if question.type == 'select':
                is_correct = Uint(user_answer) == Uint(correct_answer)
            elif question.type == 'multiselect':
                is_correct = set(user_answer) == set(correct_answer)
            elif question.type == 'input':
                is_correct = str(user_answer).lower() == str(correct_answer).lower()
        except (ValidationError, TypeError, ValueError):
            is_correct = False

        if is_correct:
            streak_bonus = min(1 + user.answers_streak * 0.1, 1.5)
            user.score += question.score * streak_bonus
            user.answers_streak += 1
        else:
            user.answers_streak = 0

        user.answers.add(answer)

        return is_correct
    
    def ban(self, username: Username) -> bool:
        user = next((user for user in self.users if user.username == username), None)

        if not user:
            return False
        
        user.connection = 'banned'
        return True

    def unban(self, username: Username) -> bool:
        user = next((user for user in self.users if user.username == username), None)

        if not user:
            return False
        
        user.connection = 'disconnected'
        return True
    
    def can_submit(self, username: Username):
        user = next((user for user in self.users if user.username == username), None)
        return user and user.connection == 'connected'

    def join(self, username: Username, nickname: Name | None = None, force: bool = False):
        user = next((user for user in self.users if user.username == username), None)

        if user:
            if not force and user.connection == 'banned':
                return False
            
            return True

        new_user = RoomUser(
            username=username,
            nickname=nickname or username,
            connection='disconnected',
            score=0,
            answers_streak=0,
            answers=set(),
        )

        self.users.add(new_user)
        return True

    def add_team(self, team: RoomTeam) -> bool:
        team = next((_team for _team in self.teams if _team.title == team.title), None)

        if team:
            return False
        
        self.teams.add(team)
        return True

    def delete_team(self, title: Name) -> bool:
        team = next((team for team in self.teams if team.title == title), None)

        if not team:
            return False
        
        self.teams.remove(team)
        return True

    def set_user_team(self, username: Username, title: Name | None) -> bool:
        user = next((user for user in self.users if user.username == username), None)

        if not user:
            return False

        for team in self.teams:
            user_team = next((_username for _username in team.users if _username == username), None)

            if user_team:
                team.users.remove(username)

        if title is not None:
            team = next((team for team in self.teams if team.title == title), None)

            if not team:
                return False
            
            team.users.add(username)

        return True
    

class RoomControl(BaseModel):
    command: Literal['show', 'start', 'stop', 'shutdown']
    question: Uint | None = None
    

class AchievementCreate(BaseModel):
    title: Name
    icon: Uint | Base64 = 2
    condition: Text


class Achievement(BaseModel):
    id: Uint
    title: Name
    icon: Uint | Base64 = 2
    condition: Text