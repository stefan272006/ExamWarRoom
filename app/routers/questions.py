import json

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Question
from app.router_utils import get_course_or_404, timestamp_now
from app.schemas import QuestionCreate, QuestionOut

router = APIRouter(prefix="/questions", tags=["questions"])


def _serialize_question(question: Question) -> QuestionOut:
    return QuestionOut(
        id=question.id,
        course_id=question.course_id,
        text=question.text,
        question_type=question.question_type,
        options=json.loads(question.options) if question.options else None,
        correct_index=question.correct_index,
        created_at=question.created_at,
    )


def _get_question_or_404(db: Session, question_id: int, course_id: int | None = None) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    if course_id is not None and question.course_id != course_id:
        raise HTTPException(status_code=404, detail="Question not found")

    return question


@router.get("", response_model=list[QuestionOut])
def list_questions(course_id: int, db: Session = Depends(get_db)):
    get_course_or_404(db, course_id)
    questions = (
        db.query(Question)
        .filter(Question.course_id == course_id)
        .order_by(Question.created_at.desc())
        .all()
    )
    return [_serialize_question(question) for question in questions]


@router.post("", response_model=QuestionOut, status_code=201)
def create_question(data: QuestionCreate, db: Session = Depends(get_db)):
    get_course_or_404(db, data.course_id)
    question = Question(
        course_id=data.course_id,
        text=data.text,
        question_type=data.question_type,
        options=json.dumps(data.options) if data.options is not None else None,
        correct_index=data.correct_index,
        created_at=timestamp_now(),
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return _serialize_question(question)


@router.delete("/{question_id}", status_code=204)
def delete_question(question_id: int, course_id: int | None = None, db: Session = Depends(get_db)) -> Response:
    if course_id is not None:
        get_course_or_404(db, course_id)
    question = _get_question_or_404(db, question_id, course_id)

    db.delete(question)
    db.commit()
    return Response(status_code=204)
