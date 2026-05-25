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


Username = Annotated[str, StringConstraints(min_length=4, max_length=32, strip_whitespace=True, to_lower=True, pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$')]
Password = Annotated[str, StringConstraints(min_length=5, max_length=64, pattern=r'^\S+$')]
Text = Annotated[str, StringConstraints(min_length=4, max_length=16384, strip_whitespace=True, pattern=r'^[^\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]+$')]
Title = Annotated[str, StringConstraints(min_length=3, max_length=128, strip_whitespace=True, pattern=r'^[^\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]+$')]
Device = Annotated[str, StringConstraints(max_length=128, strip_whitespace=True, pattern=r'^[^\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]*$')]
Color = Annotated[str, StringConstraints(pattern=r'^#[a-fA-F0-9]{6}$')]
Code = Annotated[str, StringConstraints(min_length=4, max_length=16384, strip_whitespace=False)]
Base64 = Annotated[str, StringConstraints(pattern=r'^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$')]
Email = Annotated[str, StringConstraints(min_length=5, max_length=254, strip_whitespace=True, to_lower=True, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')]
Index = Annotated[int, Field(ge=0)]
Count = Annotated[int, Field(ge=0)]
Time = Annotated[float, Field(ge=0)]
AccessToken = Annotated[str, StringConstraints(pattern=r'^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$')]
RecoveryToken = Annotated[str, StringConstraints(pattern=r'^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$')]
RefreshToken = Annotated[str, StringConstraints(max_length=256, pattern=r'^(?:[0-9a-fA-F]{2})+$')]
RoomToken = Annotated[str, StringConstraints(max_length=32, strip_whitespace=True, pattern=r'^(?:[0-9a-fA-F]{2})+$')]
Role = Literal['user', 'moderator', 'administrator']
DateTime = Annotated[str, StringConstraints(pattern=r'^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]) (?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$')]
FullName = Annotated[str, StringConstraints(min_length=2, max_length=128, strip_whitespace=True, pattern=r'^[a-zA-Zа-яА-ЯёЁ]+(?:-[a-zA-Zа-яА-ЯёЁ]+)?(?:\s+[a-zA-Zа-яА-ЯёЁ]+(?:-[a-zA-Zа-яА-ЯёЁ]+)?){0,2}$')]
QuestionType = Literal['select', 'multiselect', 'input']
Tag = Annotated[str, StringConstraints(strip_whitespace=True, max_length=32, pattern=r'^#\w+(?:_\w+)*$')]
RoomPrivacy = Literal['public', 'private']
UserSession = tuple[RefreshToken, Device, DateTime, Count]

def format_datetime(datetime: datetime) -> DateTime:
    return datetime.strftime('%Y-%m-%d %H:%M:%S')

def parse_datetime(datetime_: DateTime) -> datetime:
    return datetime.strptime(datetime_, '%Y-%m-%d %H:%M:%S')


class Configuration(BaseModel):
    auth_cooldown: Count
    auth_expiration: Count
    image_size_limit: Count
    quiz_size_limit: Count
    frequency: Time


class Tokens(BaseModel):
    access_token: AccessToken
    refresh_token: RefreshToken | None = None


class UserProfile(BaseModel):
    username: Username
    full_name: FullName | None = None
    email: Email | None = None
    avatar: Base64 | Index = 0
    creation_time: DateTime | None = None
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
    full_name: FullName | None = None
    avatar: Base64 | Index = 0


class UserRecovery(BaseModel):
    username: Username
    email: Email


class UserCredentialsUpdate(BaseModel):
    password: Password
    new_password: Password | None = None
    new_email: Email | None = None


class Question(BaseModel):
    score: Count
    text: Text
    title: Title | None = None
    image: Base64 | None = None
    code: Code | None = None
    type: QuestionType | None
    answer: Text | set[Index] | Index | None
    time: Time | None = None


class Answer(BaseModel):
    question: Index
    answer: Text | set[Index] | Index


class QuizPreview(BaseModel):
    id: Index
    title: Title
    icon: Base64 | Index = 0
    creation_time: DateTime
    tags: set[Tag] | None = None


class QuizCreate(BaseModel):
    title: Title
    icon: Base64 | Index = 0
    questions: list[Question]
    tags: set[Tag] | None = None

class Quiz(BaseModel):
    id: Index
    title: Title
    icon: Base64 | Index = 0
    questions: list[Question]
    creation_time: DateTime
    edit_time: DateTime | None = None
    last_edit_username: Username | None = None
    tags: set[Tag] | None = None

    @computed_field
    def questions_count(self) -> Count:
        return len(self.questions)
    
    @computed_field
    def score(self) -> Count:
        return sum(map(lambda question: question.score, self.questions))
    

    class QuestionsYaml(BaseModel):
        questions: list[Question]


    @classmethod
    def from_yaml(cls, text: str) -> list[Question]:
        return cls.QuestionsYaml.model_validate(yaml.safe_load(text)).questions

    @classmethod
    def to_yaml(cls, questions: list[Question]) -> str:
        return yaml.safe_dump(cls.QuestionsYaml(questions=questions).model_dump(mode='json'), sort_keys=False, allow_unicode=True)
    

class RoomUser(BaseModel):
    username: Username
    connection_state: Literal['connected', 'disconnected', 'banned']
    score: Count
    answers_streak: Count
    answers: set[tuple[Index, bool]]

    @computed_field
    def answers_count(self) -> Count:
        return len(self.answers)
    
    @computed_field
    def correct_answers_count(self) -> Count:
        return sum(tuple(map(lambda answer: 1 if answer[1] else 0, self.answers)))
    
    def __hash__(self):
        return hash(self.username)

    def __eq__(self, other):
        if not isinstance(other, RoomUser):
            return False
        return self.username == other.username


class RoomTeam(BaseModel):
    title: Title | None = None
    color: Color
    users: set[RoomUser]

    @computed_field
    def users_count(self) -> Count:
        return len(self.users)

    @computed_field
    def score(self) -> Count:
        return sum(map(lambda user: user.score, self.users))
    
    def __hash__(self):
        return hash((self.title, self.color))

    def __eq__(self, other):
        if not isinstance(other, RoomTeam):
            return False
        return self.title == other.title and self.color == other.color

class RoomCreate(BaseModel):
    title: Title
    privacy: RoomPrivacy
    quiz_id: Index


class RoomPreview(BaseModel):
    title: Title
    owner: Username
    users_count: Count
    privacy: RoomPrivacy
    quiz: QuizPreview
    room_token: RoomToken


class RoomStream(BaseModel):
    title: Title
    users: set[RoomUser]
    teams: set[RoomTeam]
    privacy: RoomPrivacy
    current_question: Index | None
    question_score: Count | None
    question_text: Text | None
    question_title: Title | None
    question_image: Base64 | None
    question_code: Code | None
    question_type: QuestionType | None
    question_time: Time | None = None

    @computed_field
    def users_count(self) -> Count:
        return len(self.users)
    
    @computed_field
    def teams_count(self) -> Count:
        return len(self.teams)


class Room(BaseModel):
    title: Title
    owner: Username
    users: set[RoomUser]
    teams: set[RoomTeam]
    privacy: RoomPrivacy
    quiz: Quiz
    current_question: Index | None
    time: Time | None = None

    @computed_field
    def users_count(self) -> Count:
        return len(self.users)
    

class RoomControl(BaseModel):
    command: Literal['show', 'start', 'stop', 'end']
    question: Index | None
    

class AchievementCreate(BaseModel):
    title: Title
    icon: Base64 | Index = 0
    condition: Code


class Achievement(BaseModel):
    id: Index
    title: Title
    icon: Base64 | Index = 0
    condition: Code


    class AchievementsYaml(BaseModel):
        achievements: list[Achievement]


    @classmethod
    def from_yaml(cls, text: str) -> list[Achievement]:
        return cls.AchievementsYaml.model_validate(yaml.safe_load(text)).achievements

    @classmethod
    def to_yaml(cls, achievements: list[Achievement]) -> str:
        return yaml.safe_dump(cls.AchievementsYaml(achievements=achievements).model_dump(mode='json'), sort_keys=False, allow_unicode=True)