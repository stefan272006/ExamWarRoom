from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Flashcard
from app.router_utils import get_course_or_404, timestamp_now
from app.schemas import FlashcardCreate, FlashcardOut, FlashcardUpdate

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


def _get_flashcard_or_404(db: Session, flashcard_id: int, course_id: int | None = None) -> Flashcard:
    flashcard = db.get(Flashcard, flashcard_id)
    if flashcard is None:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    if course_id is not None and flashcard.course_id != course_id:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    return flashcard


@router.get("", response_model=list[FlashcardOut])
def list_flashcards(course_id: int, db: Session = Depends(get_db)):
    get_course_or_404(db, course_id)
    return (
        db.query(Flashcard)
        .filter(Flashcard.course_id == course_id)
        .order_by(Flashcard.created_at.desc())
        .all()
    )


@router.post("", response_model=FlashcardOut, status_code=201)
def create_flashcard(data: FlashcardCreate, db: Session = Depends(get_db)):
    get_course_or_404(db, data.course_id)
    now = timestamp_now()
    flashcard = Flashcard(
        course_id=data.course_id,
        front=data.front,
        back=data.back,
        created_at=now,
        updated_at=now,
    )
    db.add(flashcard)
    db.commit()
    db.refresh(flashcard)
    return flashcard


@router.put("/{flashcard_id}", response_model=FlashcardOut)
def update_flashcard(
    flashcard_id: int,
    data: FlashcardUpdate,
    course_id: int | None = None,
    db: Session = Depends(get_db),
):
    if course_id is not None:
        get_course_or_404(db, course_id)
    flashcard = _get_flashcard_or_404(db, flashcard_id, course_id)

    changed = False
    if data.front is not None:
        flashcard.front = data.front
        changed = True

    if data.back is not None:
        flashcard.back = data.back
        changed = True

    if changed:
        flashcard.updated_at = timestamp_now()
        db.commit()
        db.refresh(flashcard)

    return flashcard


@router.delete("/{flashcard_id}", status_code=204)
def delete_flashcard(
    flashcard_id: int,
    course_id: int | None = None,
    db: Session = Depends(get_db),
) -> Response:
    if course_id is not None:
        get_course_or_404(db, course_id)
    flashcard = _get_flashcard_or_404(db, flashcard_id, course_id)

    db.delete(flashcard)
    db.commit()
    return Response(status_code=204)
