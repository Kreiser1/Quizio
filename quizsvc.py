from datetime import datetime
import database as db
import schema

def create_quiz(
    session: db.Session, 
    author: schema.Username, 
    quiz_payload: schema.QuizCreate,
) -> schema.Quiz | None:
    creation_time = schema.format_datetime(datetime.now())
    
    new_quiz = db.Quiz(
        title=quiz_payload.title,
        icon=quiz_payload.icon or '0',
        creation_time=creation_time,
        last_edit_username=author
    )

    new_quiz.questions = quiz_payload.questions

    try:
        session.add(new_quiz)
        session.flush()

        session.execute(db.insert(db.user_quiz).values(username=author, quiz_id=new_quiz.id))

        if quiz_payload.tags:
            tag_values = [{"tag": tag, "quiz_id": new_quiz.id} for tag in quiz_payload.tags]
            session.execute(db.insert(db.tag_quiz).values(tag_values))

        return schema.Quiz(
            id=new_quiz.id,
            title=new_quiz.title,
            icon=new_quiz.icon,
            questions=new_quiz.questions,
            creation_time=new_quiz.creation_time,
            tags=quiz_payload.tags or set(),
            authors=set((author,))
        )
    except db.IntegrityError:
        return None


def get_quiz(session: db.Session, id: schema.Index) -> schema.Quiz | None:
    quiz = session.execute(db.select(db.Quiz).where(db.Quiz.id == id)).scalar_one_or_none()

    if not quiz:
        return None

    tags = session.execute(db.select(db.tag_quiz.c.tag).where(db.tag_quiz.c.quiz_id == id)).scalars().all()

    return schema.Quiz(
        id=quiz.id,
        title=quiz.title,
        icon=quiz.icon,
        questions=quiz.questions,
        creation_time=quiz.creation_time,
        edit_time=quiz.edit_time,
        last_edit_username=quiz.last_edit_username,
        tags=set(tags) if tags else None,
        authors=get_quiz_authors(session, quiz.id)
    )


def get_user_quizzes(session: db.Session, username: schema.Username) -> list[schema.QuizPreview]:
    quizzes = session.execute(
        db.select(db.Quiz)
        .join(db.user_quiz, db.Quiz.id == db.user_quiz.c.quiz_id)
        .where(db.user_quiz.c.username == username)
    ).scalars().all()

    if not quizzes:
        return []

    quiz_ids = [quiz.id for quiz in quizzes]

    tags_result = session.execute(
        db.select(db.tag_quiz.c.quiz_id, db.tag_quiz.c.tag).where(db.tag_quiz.c.quiz_id.in_(quiz_ids))
    ).all()

    tags_map = {}

    for quiz_id, tag in tags_result:
        if quiz_id not in tags_map:
            tags_map[quiz_id] = set()
        tags_map[quiz_id].add(tag)

    result = []

    for quiz in quizzes:
        result.append(schema.QuizPreview(
            id=quiz.id,
            title=quiz.title,
            icon=quiz.icon,
            creation_time=quiz.creation_time,
            tags=tags_map.get(quiz.id, set()),
            authors=get_quiz_authors(session, quiz.id)
        ))
        
    return result


def update_quiz(
    session: db.Session, 
    username: schema.Username,
    id: schema.Index,
    quiz_payload: schema.QuizCreate 
) -> bool:
    quiz = session.execute(db.select(db.Quiz).where(db.Quiz.id == id)).scalar_one_or_none()

    if not quiz:
        return False

    quiz.title = quiz_payload.title
    quiz.icon = quiz_payload.icon
    quiz.questions = quiz_payload.questions

    quiz.edit_time = schema.format_datetime(datetime.now())
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
    query: schema.Title | None = None, 
    tags: set[schema.Tag] | None = None,
    count: schema.Count = 25,
    offset: schema.Index = 0
) -> list[schema.QuizPreview]:
    stmt = db.select(db.Quiz)
    conditions = []

    if query:
        search_pattern = f"%{query}%"
        conditions.append(db.Quiz.title.ilike(search_pattern))

    if tags:
        stmt = stmt.join(db.tag_quiz, db.Quiz.id == db.tag_quiz.c.quiz_id)
        conditions.append(db.tag_quiz.c.tag.in_(tags))
        stmt = stmt.group_by(db.Quiz.id)
        stmt = stmt.having(db.func.count(db.tag_quiz.c.tag) == len(tags))

    if conditions:
        stmt = stmt.where(db.and_(*conditions))
        
    stmt = stmt.limit(count).offset(offset)
    quizzes = session.execute(stmt).scalars().all()

    if not quizzes:
        return []

    quiz_ids = [quiz.id for quiz in quizzes]

    tags_result = session.execute(db.select(db.tag_quiz.c.quiz_id, db.tag_quiz.c.tag).where(db.tag_quiz.c.quiz_id.in_(quiz_ids))).all()

    tags_map = {}

    for quiz_id, tag in tags_result:
        if quiz_id not in tags_map:
            tags_map[quiz_id] = set()
        tags_map[quiz_id].add(tag)

    result = []
    
    for quiz in quizzes:
        result.append(schema.QuizPreview(
            id=quiz.id,
            title=quiz.title,
            icon=quiz.icon,
            creation_time=quiz.creation_time,
            tags=tags_map.get(quiz.id, set()),
            authors=get_quiz_authors(session, quiz.id)
        ))
        
    return result

def is_quiz_author(session: db.Session, id: schema.Index, username: schema.Username) -> bool:
    return session.query(db.user_quiz.c.username).filter(
        db.user_quiz.c.quiz_id == id,
        db.user_quiz.c.username == username
    ).scalar() is not None


def add_quiz_author(session: db.Session, id: schema.Index, author: schema.Username) -> bool:
    if not session.query(db.User).filter_by(username=author).scalar():
        return False
        
    try:
        session.execute(db.insert(db.user_quiz).values(username=author, quiz_id=id))
        session.flush()
        return True
    except db.IntegrityError:
        return False

def remove_quiz_author(session: db.Session, id: schema.Index, author: schema.Username) -> bool:
    return session.execute(
        db.delete(db.user_quiz).where(
            db.user_quiz.c.quiz_id == id,
            db.user_quiz.c.username == author
        )
    ).rowcount > 0

def get_quiz_authors(session: db.Session, id: schema.Index) -> list[schema.Username]:
    return session.execute(db.select(db.user_quiz.c.username).where(db.user_quiz.c.quiz_id == id)).scalars().all()

def delete_quiz(session: db.Session, quiz_id: int) -> bool:
    return session.execute(db.delete(db.Quiz).where(db.Quiz.id == quiz_id)).rowcount > 0