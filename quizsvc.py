from datetime import datetime
import database as db
import schema

def create_quiz(
    session: db.Session, 
    author: schema.Username, 
    quiz_payload: schema.QuizCreate,
) -> schema.Quiz | None:
    creation_date = schema.format_datetime(datetime.now())
    
    new_quiz = db.Quiz(
        title=quiz_payload.title,
        icon=quiz_payload.icon,
        creation_date=creation_date,
        last_edit_username=author,
        last_edit_date=creation_date
    )

    if isinstance(quiz_payload.questions, str):
        try:
            quiz_payload.questions = schema.Quiz.from_yaml(quiz_payload.questions)
        except schema.YAMLError:
            return None

    new_quiz.questions = quiz_payload.questions

    session.add(new_quiz)
    session.execute(db.insert(db.author_quiz).values(username=author, quiz_id=new_quiz.id))

    if quiz_payload.tags:
        tag_values = [{"tag": tag, "quiz_id": new_quiz.id} for tag in quiz_payload.tags]
        session.execute(db.insert(db.tag_quiz).values(tag_values))

    try:
        session.flush()
    except db.IntegrityError:
        return None

    return schema.Quiz(
        id=new_quiz.id,
        title=quiz_payload.title,
        icon=quiz_payload.icon,
        questions=quiz_payload.questions,
        creation_date=creation_date,
        last_edit_date=creation_date,
        last_edit_username=author,
        tags=quiz_payload.tags or set(),
        authors=set((author,))
    )
    

def get_quiz(session: db.Session, id: schema.Uint) -> schema.Quiz | None:
    quiz = session.execute(db.select(db.Quiz).where(db.Quiz.id == id)).scalar_one_or_none()

    if not quiz:
        return None

    tags = session.execute(db.select(db.tag_quiz.c.tag).where(db.tag_quiz.c.quiz_id == id)).scalars().all()

    return schema.Quiz(
        id=quiz.id,
        title=quiz.title,
        icon=quiz.icon,
        questions=quiz.questions,
        creation_date=quiz.creation_date,
        last_edit_date=quiz.last_edit_date,
        last_edit_username=quiz.last_edit_username,
        tags=set(tags) if tags else None,
        authors=get_quiz_authors(session, quiz.id)
    )

def get_user_quizzes(session: db.Session, username: schema.Username) -> list[schema.Quiz]:
    quiz_ids = session.execute(
        db.select(db.Quiz.id)
        .join(db.author_quiz, db.Quiz.id == db.author_quiz.c.quiz_id)
        .where(db.author_quiz.c.username == username)
    ).scalars().all()

    if not quiz_ids:
        return []
        
    return [quiz.preview for q_id in quiz_ids if (quiz := get_quiz(session, q_id)) is not None]

def update_quiz(
    session: db.Session, 
    username: schema.Username,
    id: schema.Uint,
    quiz_payload: schema.QuizCreate
) -> bool:
    quiz = get_quiz(session, id)

    if not quiz:
        return False

    quiz.title = quiz_payload.title
    quiz.icon = quiz_payload.icon

    if isinstance(quiz_payload.questions, str):
        try:
            quiz_payload.questions = schema.Quiz.from_yaml(quiz_payload.questions)
        except schema.YAMLError:
            return False

    quiz.questions = quiz_payload.questions

    quiz.last_edit_date = schema.format_datetime(datetime.now())
    quiz.last_edit_username = username

    if quiz_payload.tags is not None:
        session.execute(db.delete(db.tag_quiz).where(db.tag_quiz.c.quiz_id == id))

        if quiz_payload.tags:
            tag_values = [{"tag": tag, "quiz_id": id} for tag in quiz_payload.tags]
            session.execute(db.insert(db.tag_quiz).values(tag_values))

    try:
        session.flush()
        return True
    except db.IntegrityError:
        return False


def search_quizzes(
    session: db.Session, 
    query: schema.Name | None = None, 
    tags: set[schema.Tag] | None = None,
    count: schema.Uint = 25,
    offset: schema.Uint = 0
) -> list[schema.QuizPreview]:
    stmt = db.select(db.Quiz.id)
    conditions = []

    if query:
        search_pattern = f'%{query}%'
        conditions.append(db.Quiz.title.ilike(search_pattern))

    if tags:
        stmt = stmt.join(db.tag_quiz, db.Quiz.id == db.tag_quiz.c.quiz_id)
        conditions.append(db.tag_quiz.c.tag.in_(tags))
        stmt = stmt.group_by(db.Quiz.id)
        stmt = stmt.having(db.func.count(db.tag_quiz.c.tag) == len(tags))

    if conditions:
        stmt = stmt.where(db.and_(*conditions))
        
    stmt = stmt.limit(count).offset(offset)
    quiz_ids = session.execute(stmt).scalars().all()

    if not quiz_ids:
        return []

    return [quiz.preview for quiz_id in quiz_ids if (quiz := get_quiz(session, quiz_id)) is not None]

def is_quiz_author(session: db.Session, id: schema.Uint, username: schema.Username) -> bool:
    return session.query(db.author_quiz.c.username).filter(
        db.author_quiz.c.quiz_id == id,
        db.author_quiz.c.username == username
    ).scalar() is not None


def add_quiz_author(session: db.Session, id: schema.Uint, author: schema.Username) -> bool:
    if not session.query(db.User).filter_by(username=author).scalar():
        return False
    
    session.execute(db.insert(db.author_quiz).values(username=author, quiz_id=id))
        
    try:
        session.flush()
        return True
    except db.IntegrityError:
        return False

def remove_quiz_author(session: db.Session, id: schema.Uint, author: schema.Username) -> bool:
    return session.execute(
        db.delete(db.author_quiz).where(
            db.author_quiz.c.quiz_id == id,
            db.author_quiz.c.username == author
        )
    ).rowcount > 0

def get_quiz_authors(session: db.Session, id: schema.Uint) -> set[schema.Username]:
    return session.execute(db.select(db.author_quiz.c.username).where(db.author_quiz.c.quiz_id == id)).scalars().all()

def delete_quiz(session: db.Session, quiz_id: int) -> bool:
    return session.execute(db.delete(db.Quiz).where(db.Quiz.id == quiz_id)).rowcount > 0