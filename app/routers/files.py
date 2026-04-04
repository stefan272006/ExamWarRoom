import mimetypes
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File as FastAPIFile, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UploadedFile
from app.router_utils import get_course_or_404, timestamp_now
from app.schemas import FileSection, UploadedFileOut

router = APIRouter(prefix="/files", tags=["files"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_ROOT = BASE_DIR / "static" / "uploads"
SECTION_NAMES = {"lecture_notes", "past_exams", "formula_sheets", "practice"}
EXTENSION_TO_TYPE = {
    ".pdf": "PDF",
    ".png": "PNG",
    ".jpg": "JPG",
    ".jpeg": "JPG",
    ".webp": "WEBP",
    ".docx": "DOCX",
}


def _validate_section(section: str) -> FileSection:
    if section not in SECTION_NAMES:
        raise HTTPException(status_code=400, detail="Invalid file section")
    return section


def _file_path(section: str, stored_name: str) -> Path:
    return UPLOAD_ROOT / section / stored_name


@router.get("", response_model=list[UploadedFileOut])
def list_files(course_id: int, section: str | None = None, db: Session = Depends(get_db)):
    get_course_or_404(db, course_id)
    query = db.query(UploadedFile).filter(UploadedFile.course_id == course_id)
    if section is not None:
        query = query.filter(UploadedFile.section == _validate_section(section))
    return query.order_by(UploadedFile.uploaded_at.desc()).all()


@router.post("/upload", response_model=UploadedFileOut, status_code=201)
def upload_file(
    section: str = Form(...),
    course_id: int = Form(...),
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
):
    get_course_or_404(db, course_id)
    validated_section = _validate_section(section)
    original_name = Path(file.filename or "").name
    extension = Path(original_name).suffix.lower()
    file_type = EXTENSION_TO_TYPE.get(extension)
    if not original_name or file_type is None:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    stored_name = f"{uuid4().hex}{extension}"
    destination = _file_path(validated_section, stored_name)
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        with destination.open("wb") as output_file:
            shutil.copyfileobj(file.file, output_file)

        uploaded_file = UploadedFile(
            course_id=course_id,
            section=validated_section,
            filename=original_name,
            stored_name=stored_name,
            file_type=file_type,
            uploaded_at=timestamp_now(),
        )
        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)
        return uploaded_file
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()


@router.get("/{file_id}/content")
def get_file_content(file_id: int, section: str | None = None, db: Session = Depends(get_db)):
    uploaded_file = db.get(UploadedFile, file_id)
    if uploaded_file is None:
        raise HTTPException(status_code=404, detail="File not found")

    if section is not None and uploaded_file.section != _validate_section(section):
        raise HTTPException(status_code=404, detail="File not found")

    file_path = _file_path(uploaded_file.section, uploaded_file.stored_name)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File content not found")

    media_type = mimetypes.guess_type(uploaded_file.filename)[0] or "application/octet-stream"
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=uploaded_file.filename,
        content_disposition_type="inline",
    )


@router.delete("/{file_id}", status_code=204)
def delete_file(file_id: int, db: Session = Depends(get_db)) -> Response:
    uploaded_file = db.get(UploadedFile, file_id)
    if uploaded_file is None:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = _file_path(uploaded_file.section, uploaded_file.stored_name)
    file_path.unlink(missing_ok=True)

    db.delete(uploaded_file)
    db.commit()
    return Response(status_code=204)
