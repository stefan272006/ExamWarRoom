import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Note, UploadedFile
from app.router_utils import get_course_or_404
from app.schemas import AIGenerateFlashcardsRequest, GeneratedFlashcard

router = APIRouter(prefix="/ai", tags=["ai"])

UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / "static" / "uploads"


def _collect_note_content(db: Session) -> str:
    notes = db.query(Note).order_by(Note.created_at.desc()).all()
    note_text = "\n\n".join(note.text.strip() for note in notes if note.text and note.text.strip())
    return note_text.strip()


def _collect_pdf_content(db: Session, course_id: int) -> list[str]:
    try:
        import fitz  # type: ignore
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="PyMuPDF is not installed") from exc

    chunks: list[str] = []
    pdf_files = (
        db.query(UploadedFile)
        .filter(
            UploadedFile.course_id == course_id,
            UploadedFile.file_type == "PDF",
        )
        .order_by(UploadedFile.uploaded_at.desc())
        .limit(3)
        .all()
    )

    for uploaded_file in pdf_files:
        file_path = UPLOAD_ROOT / uploaded_file.section / uploaded_file.stored_name
        if not file_path.exists():
            continue

        extracted = ""
        with fitz.open(file_path) as document:
            for page_index in range(min(5, document.page_count)):
                extracted += document.load_page(page_index).get_text()

        extracted = extracted.strip()[:3000]
        if extracted:
            chunks.append(f"{uploaded_file.filename}\n{extracted}")

    return chunks


def _truncate_chunks(chunks: list[str], limit: int = 6000) -> str:
    if not chunks:
        return ""

    parts: list[str] = []
    remaining = limit
    for chunk in chunks:
        if remaining <= 0:
            break

        piece = chunk[:remaining]
        if piece:
            parts.append(piece)
            remaining -= len(piece)
        if remaining > 2:
            remaining -= 2

    return "\n\n".join(parts).strip()


def _extract_json_array(text: str) -> list[dict]:
    text = text.strip()
    try:
        payload = json.loads(text)
        if isinstance(payload, list):
            return payload
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        raise ValueError("No JSON array found in response")

    payload = json.loads(match.group(0))
    if not isinstance(payload, list):
        raise ValueError("LLM response was not a JSON array")
    return payload


@router.post("/generate-flashcards", response_model=list[GeneratedFlashcard])
def generate_flashcards(data: AIGenerateFlashcardsRequest, db: Session = Depends(get_db)):
    get_course_or_404(db, data.course_id)

    if not data.api_key:
        raise HTTPException(status_code=400, detail="api_key is required")

    chunks: list[str] = []
    if data.source in {"notes", "both"}:
        notes_text = _collect_note_content(db)
        if notes_text:
            chunks.append(f"Quick Notes\n{notes_text}")

    if data.source in {"uploaded_files", "both"}:
        chunks.extend(_collect_pdf_content(db, data.course_id))

    source_text = _truncate_chunks(chunks, limit=6000)
    if not source_text:
        raise HTTPException(status_code=422, detail="No content found for flashcard generation")

    try:
        import anthropic  # type: ignore
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Anthropic SDK is not installed") from exc

    prompt = (
        "Generate exactly 5 study flashcards from the provided material. "
        "Return JSON only as an array of objects with keys front and back. "
        "Each card must be concise, specific, and non-empty.\n\n"
        f"Source material:\n{source_text}"
    )

    try:
        client = anthropic.Anthropic(api_key=data.api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1200,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = "".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        )
        raw_cards = _extract_json_array(response_text)
        cards: list[GeneratedFlashcard] = []
        for raw_card in raw_cards:
            if not isinstance(raw_card, dict):
                continue
            front = raw_card.get("front")
            back = raw_card.get("back")
            if not isinstance(front, str) or not isinstance(back, str):
                continue
            try:
                cards.append(GeneratedFlashcard(front=front, back=back))
            except Exception:
                continue
            if len(cards) == 5:
                break
        if not cards:
            raise HTTPException(status_code=502, detail="Failed to parse generated flashcards")
        return cards
    except anthropic.AuthenticationError as exc:  # type: ignore[attr-defined]
        raise HTTPException(status_code=401, detail="Invalid Anthropic API key") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to generate flashcards") from exc
