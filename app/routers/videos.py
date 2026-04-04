import json
import subprocess
import sys

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Video
from app.router_utils import get_course_or_404, timestamp_now
from app.schemas import PlaylistImportRequest, VideoCreate, VideoOut

router = APIRouter(prefix="/videos", tags=["videos"])


def _parse_playlist_entries(raw_output: str) -> list[dict[str, str]]:
    entries: list[dict[str, str | None]] = []

    for line in raw_output.splitlines():
        if not line.strip():
            continue

        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue

        video_id = payload.get("id")
        if not video_id:
            continue

        thumbnail_url = payload.get("thumbnail")
        if not thumbnail_url:
            thumbnails = payload.get("thumbnails") or []
            if thumbnails:
                thumbnail_url = thumbnails[0].get("url")
        if not thumbnail_url:
            thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        entries.append(
            {
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": (payload.get("title") or video_id).strip(),
                "thumbnail_url": thumbnail_url,
            }
        )

    return entries


def _get_video_or_404(db: Session, video_id: int, course_id: int | None = None) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    if course_id is not None and video.course_id != course_id:
        raise HTTPException(status_code=404, detail="Video not found")

    return video


@router.get("", response_model=list[VideoOut])
def list_videos(course_id: int, db: Session = Depends(get_db)):
    get_course_or_404(db, course_id)
    return (
        db.query(Video)
        .filter(Video.course_id == course_id)
        .order_by(Video.added_at.desc())
        .all()
    )


@router.post("", response_model=VideoOut, status_code=201)
def create_video(data: VideoCreate, db: Session = Depends(get_db)):
    get_course_or_404(db, data.course_id)
    existing_video = (
        db.query(Video)
        .filter(
            Video.course_id == data.course_id,
            Video.url == data.url,
        )
        .first()
    )
    if existing_video is not None:
        raise HTTPException(status_code=409, detail="Video already exists")

    video = Video(
        course_id=data.course_id,
        url=data.url,
        title=data.title,
        thumbnail_url=data.thumbnail_url,
        added_at=timestamp_now(),
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


@router.post("/import-playlist", response_model=list[VideoOut], status_code=201)
def import_playlist(data: PlaylistImportRequest, db: Session = Depends(get_db)):
    get_course_or_404(db, data.course_id)
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "yt_dlp",
                "--flat-playlist",
                "--dump-json",
                data.playlist_url,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "yt-dlp failed to import playlist"
        raise HTTPException(status_code=502, detail=detail) from exc

    parsed_entries = _parse_playlist_entries(result.stdout)
    if not parsed_entries:
        return []

    candidate_urls = [entry["url"] for entry in parsed_entries]
    existing_urls = {
        video.url
        for video in (
            db.query(Video)
            .filter(
                Video.course_id == data.course_id,
                Video.url.in_(candidate_urls),
            )
            .all()
        )
    }

    new_videos: list[Video] = []
    seen_urls: set[str] = set()
    for entry in parsed_entries:
        if entry["url"] in existing_urls or entry["url"] in seen_urls:
            continue
        seen_urls.add(entry["url"])
        new_videos.append(
            Video(
                course_id=data.course_id,
                url=entry["url"],
                title=entry["title"],
                thumbnail_url=entry["thumbnail_url"],
                added_at=timestamp_now(),
            )
        )

    if not new_videos:
        return []

    db.add_all(new_videos)
    db.commit()
    for video in new_videos:
        db.refresh(video)
    return new_videos


@router.delete("/{video_id}", status_code=204)
def delete_video(video_id: int, course_id: int | None = None, db: Session = Depends(get_db)) -> Response:
    if course_id is not None:
        get_course_or_404(db, course_id)
    video = _get_video_or_404(db, video_id, course_id)

    db.delete(video)
    db.commit()
    return Response(status_code=204)
