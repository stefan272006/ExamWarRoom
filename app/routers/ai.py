import json
import logging
import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Note, UploadedFile
from app.router_utils import get_course_or_404
from app.schemas import AIGenerateFlashcardsRequest, GeneratedFlashcard

try:
    import anthropic  # type: ignore
except ImportError as exc:
    anthropic = None  # type: ignore[assignment]
    ANTHROPIC_IMPORT_ERROR = exc
else:
    ANTHROPIC_IMPORT_ERROR = None

try:
    import fitz  # type: ignore
except ImportError as exc:
    fitz = None  # type: ignore[assignment]
    PYMUPDF_IMPORT_ERROR = exc
else:
    PYMUPDF_IMPORT_ERROR = None

try:
    import google.generativeai as genai  # type: ignore
except ImportError as exc:
    genai = None  # type: ignore[assignment]
    GEMINI_IMPORT_ERROR = exc
else:
    GEMINI_IMPORT_ERROR = None

router = APIRouter(prefix="/ai", tags=["ai"])

UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / "static" / "uploads"
DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
logger = logging.getLogger(__name__)


class PDFExtractionUnavailable(RuntimeError):
    pass


def _collect_note_content(db: Session) -> str:
    notes = (
        db.query(Note)
        .filter(Note.user_id == 1)
        .order_by(Note.created_at.desc())
        .all()
    )
    note_text = "\n\n".join(note.text.strip() for note in notes if note.text and note.text.strip())
    return note_text.strip()


def _raise_anthropic_unavailable() -> None:
    raise HTTPException(
        status_code=503,
        detail="Anthropic SDK not installed. Run: pip install anthropic",
    ) from ANTHROPIC_IMPORT_ERROR


def _raise_pymupdf_unavailable() -> None:
    raise HTTPException(
        status_code=503,
        detail="PyMuPDF not installed. Run: pip install pymupdf",
    ) from PYMUPDF_IMPORT_ERROR


def _raise_gemini_unavailable() -> None:
    raise HTTPException(
        status_code=503,
        detail="Google Generative AI SDK not installed. Run: pip install google-generativeai",
    ) from GEMINI_IMPORT_ERROR


ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
ANTHROPIC_MAX_TOKENS = 1024
GEMINI_MODEL = "gemini-1.5-flash"
MAX_GENERATED_FLASHCARDS = 10
MAX_PDF_FILES = 3
PDF_MAX_PAGES = 5
PDF_CHAR_LIMIT = 3000
TEXT_CHAR_LIMIT = 6000
MAX_SOURCE_CHARS = 6000


def _extract_pdf_text(file_path: Path, char_limit: int = PDF_CHAR_LIMIT, max_pages: int = PDF_MAX_PAGES) -> str:
    if fitz is None:
        raise PDFExtractionUnavailable("PyMuPDF is not installed")

    extracted = ""
    with fitz.open(file_path) as document:
        for page_index in range(min(max_pages, document.page_count)):
            extracted += document.load_page(page_index).get_text()
            if len(extracted) >= char_limit:
                break

    return extracted.strip()[:char_limit]


def _extract_docx_text(file_path: Path, char_limit: int = TEXT_CHAR_LIMIT) -> str:
    try:
        with ZipFile(file_path) as archive:
            xml_bytes = archive.read("word/document.xml")
    except (BadZipFile, KeyError, OSError):
        return ""

    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError:
        return ""

    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", DOCX_NS):
        text_parts = [node.text for node in paragraph.findall(".//w:t", DOCX_NS) if node.text]
        if text_parts:
            paragraphs.append("".join(text_parts))

    return "\n".join(paragraphs).strip()[:char_limit]


def _extract_text_file(file_path: Path, char_limit: int = TEXT_CHAR_LIMIT) -> str:
    try:
        return file_path.read_text(encoding="utf-8", errors="ignore").strip()[:char_limit]
    except OSError:
        return ""


def _extract_uploaded_file_text(
    uploaded_file: UploadedFile,
    *,
    pdf_char_limit: int = PDF_CHAR_LIMIT,
    pdf_max_pages: int = PDF_MAX_PAGES,
    text_char_limit: int = TEXT_CHAR_LIMIT,
) -> str:
    file_path = UPLOAD_ROOT / uploaded_file.section / uploaded_file.stored_name
    if not file_path.exists():
        return ""

    suffix = file_path.suffix.lower()
    file_type = (uploaded_file.file_type or "").upper()

    try:
        if file_type == "PDF" or suffix == ".pdf":
            return _extract_pdf_text(file_path, char_limit=pdf_char_limit, max_pages=pdf_max_pages)
        if file_type == "DOCX" or suffix == ".docx":
            return _extract_docx_text(file_path, char_limit=text_char_limit)
        if suffix == ".txt":
            return _extract_text_file(file_path, char_limit=text_char_limit)
        return ""
    except PDFExtractionUnavailable:
        raise
    except Exception:
        logger.exception("Failed to extract text from uploaded file %s", uploaded_file.id)
        return ""


def _list_course_pdf_files(db: Session, course_id: int) -> list[UploadedFile]:
    return (
        db.query(UploadedFile)
        .filter(
            UploadedFile.course_id == course_id,
            UploadedFile.file_type == "PDF",
        )
        .order_by(UploadedFile.uploaded_at.desc())
        .limit(MAX_PDF_FILES)
        .all()
    )


def _collect_uploaded_file_content(db: Session, course_id: int) -> list[str]:
    chunks: list[str] = []
    for uploaded_file in _list_course_pdf_files(db, course_id):
        extracted = _extract_uploaded_file_text(uploaded_file)
        if extracted:
            chunks.append(f"{uploaded_file.filename}\n{extracted}")
    return chunks


def _truncate_chunks(chunks: list[str], limit: int = MAX_SOURCE_CHARS) -> str:
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


def _get_uploaded_file_or_404(db: Session, course_id: int, file_id: int) -> UploadedFile:
    uploaded_file = (
        db.query(UploadedFile)
        .filter(
            UploadedFile.id == file_id,
            UploadedFile.course_id == course_id,
        )
        .first()
    )
    if uploaded_file is None:
        raise HTTPException(status_code=404, detail="File not found for this course")
    return uploaded_file


def _parse_generated_cards(response_text: str) -> list[GeneratedFlashcard]:
    raw_cards = _extract_json_array(response_text)
    cards: list[GeneratedFlashcard] = []
    seen_pairs: set[tuple[str, str]] = set()
    for raw_card in raw_cards:
        if not isinstance(raw_card, dict):
            continue
        front = raw_card.get("front")
        back = raw_card.get("back")
        if not isinstance(front, str) or not isinstance(back, str):
            continue
        try:
            card = GeneratedFlashcard(front=front, back=back)
        except Exception:
            continue
        dedupe_key = (card.front.casefold(), card.back.casefold())
        if dedupe_key in seen_pairs:
            continue
        seen_pairs.add(dedupe_key)
        cards.append(card)
        if len(cards) == MAX_GENERATED_FLASHCARDS:
            break
    if not cards:
        raise HTTPException(status_code=502, detail="Failed to parse generated flashcards")
    return cards


def _build_flashcard_prompt(source_text: str) -> str:
    return (
        "Generate exactly 10 study flashcards from the provided material. "
        "Return raw JSON only as an array of objects with keys front and back. "
        "Do not wrap the JSON in markdown fences.\n\n"
        f"Source material:\n{source_text}"
    )


def _generate_with_anthropic(api_key: str, prompt: str) -> list[GeneratedFlashcard]:
    if anthropic is None:
        _raise_anthropic_unavailable()

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=ANTHROPIC_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text" and getattr(block, "text", None)]
        return _parse_generated_cards("\n".join(text_blocks))
    except anthropic.AuthenticationError as exc:
        raise HTTPException(status_code=401, detail="Invalid Anthropic API key") from exc
    except anthropic.BadRequestError as exc:
        detail = str(exc)
        if "credit" in detail.lower() or "billing" in detail.lower():
            raise HTTPException(status_code=402, detail="Anthropic account has no credits") from exc
        raise HTTPException(status_code=502, detail="Anthropic request failed") from exc


def _handle_gemini_error(exc: Exception) -> None:
    error_name = type(exc).__name__
    if error_name == "PermissionDenied":
        raise HTTPException(status_code=401, detail="Invalid Gemini API key") from exc
    if error_name == "ResourceExhausted":
        raise HTTPException(status_code=429, detail="Gemini quota exceeded") from exc
    raise HTTPException(status_code=502, detail="Gemini request failed") from exc


def _extract_gemini_text(response) -> str:
    try:
        text = response.text
    except Exception:
        text = None

    if isinstance(text, str) and text.strip():
        return text

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                return part_text

    raise HTTPException(status_code=502, detail="Unexpected Gemini response format")


def _generate_with_gemini(api_key: str, prompt: str) -> list[GeneratedFlashcard]:
    if genai is None:
        _raise_gemini_unavailable()

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        return _parse_generated_cards(_extract_gemini_text(response))
    except HTTPException:
        raise
    except Exception as exc:
        _handle_gemini_error(exc)


def _validate_provider_request(data: AIGenerateFlashcardsRequest) -> None:
    if data.provider == "gemini":
        if not data.gemini_api_key:
            raise HTTPException(status_code=400, detail="gemini_api_key is required")
        if genai is None:
            _raise_gemini_unavailable()
        return

    if not data.api_key:
        raise HTTPException(status_code=400, detail="api_key is required")
    if anthropic is None:
        _raise_anthropic_unavailable()


@router.post("/generate-flashcards", response_model=list[GeneratedFlashcard])
def generate_flashcards(data: AIGenerateFlashcardsRequest, db: Session = Depends(get_db)):
    get_course_or_404(db, data.course_id)
    _validate_provider_request(data)

    chunks: list[str] = []
    if data.file_id is not None:
        try:
            uploaded_file = _get_uploaded_file_or_404(db, data.course_id, data.file_id)
            extracted = _extract_uploaded_file_text(
                uploaded_file,
                pdf_char_limit=PDF_CHAR_LIMIT,
                pdf_max_pages=PDF_MAX_PAGES,
                text_char_limit=TEXT_CHAR_LIMIT,
            )
        except PDFExtractionUnavailable:
            _raise_pymupdf_unavailable()
        if extracted:
            chunks.append(f"{uploaded_file.filename}\n{extracted}")
    else:
        if data.source in {"notes", "both"}:
            notes_text = _collect_note_content(db)
            if notes_text:
                chunks.append(f"Quick Notes\n{notes_text}")

        if data.source in {"uploaded_files", "both"}:
            try:
                chunks.extend(_collect_uploaded_file_content(db, data.course_id))
            except PDFExtractionUnavailable:
                if not chunks:
                    _raise_pymupdf_unavailable()

    source_text = _truncate_chunks(chunks, limit=MAX_SOURCE_CHARS)
    if not source_text:
        raise HTTPException(status_code=422, detail="No content found for flashcard generation")

    prompt = _build_flashcard_prompt(source_text)

    try:
        if data.provider == "gemini":
            assert data.gemini_api_key is not None
            return _generate_with_gemini(data.gemini_api_key, prompt)

        assert data.api_key is not None
        return _generate_with_anthropic(data.api_key, prompt)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to generate flashcards")
        raise HTTPException(status_code=502, detail="Failed to generate flashcards") from exc
