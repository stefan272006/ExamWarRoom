from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GroupMember, GroupMessage, InviteToken
from app.router_utils import timestamp_now
from app.schemas import (
    GroupMemberCreate,
    GroupMemberOut,
    GroupMemberUpdate,
    InviteOut,
    JoinRequest,
    GroupMessageCreate,
    GroupMessageOut,
)

router = APIRouter(prefix="/group", tags=["group"])

def _generate_unique_token(db: Session) -> str:
    while True:
        token = uuid4().hex[:8]
        if db.query(InviteToken).filter(InviteToken.token == token).first() is None:
            return token


@router.get("/members", response_model=list[GroupMemberOut])
def list_members(db: Session = Depends(get_db)):
    return db.query(GroupMember).order_by(GroupMember.joined_at).all()


@router.post("/members", response_model=GroupMemberOut, status_code=201)
def create_member(data: GroupMemberCreate, db: Session = Depends(get_db)):
    member = GroupMember(
        name=data.name,
        is_online=0,
        hours_this_week=0.0,
        current_streak=0,
        joined_at=timestamp_now(),
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.put("/members/{member_id}", response_model=GroupMemberOut)
def update_member(member_id: int, data: GroupMemberUpdate, db: Session = Depends(get_db)):
    member = db.get(GroupMember, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Group member not found")

    member.is_online = 1 if data.is_online else 0
    db.commit()
    db.refresh(member)
    return member


@router.get("/messages", response_model=list[GroupMessageOut])
def list_messages(db: Session = Depends(get_db)):
    messages = (
        db.query(GroupMessage)
        .order_by(GroupMessage.created_at.desc())
        .limit(100)
        .all()
    )
    messages.reverse()
    return messages


@router.post("/messages", response_model=GroupMessageOut, status_code=201)
def create_message(data: GroupMessageCreate, db: Session = Depends(get_db)):
    member = db.get(GroupMember, data.member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Group member not found")

    message = GroupMessage(
        member_id=member.id,
        author_name=member.name,
        text=data.text,
        created_at=timestamp_now(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.delete("/messages/{message_id}", status_code=204)
def delete_message(message_id: int, db: Session = Depends(get_db)) -> Response:
    message = db.get(GroupMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    db.delete(message)
    db.commit()
    return Response(status_code=204)


@router.post("/invite", response_model=InviteOut, status_code=201)
def create_invite(request: Request, db: Session = Depends(get_db)):
    token = _generate_unique_token(db)
    invite = InviteToken(
        token=token,
        created_at=timestamp_now(),
        used=0,
    )
    db.add(invite)
    db.commit()

    base_url = str(request.base_url).rstrip("/")
    return InviteOut(token=token, url=f"{base_url}/?join={token}")


@router.post("/join", response_model=GroupMemberOut, status_code=201)
def join_group(data: JoinRequest, db: Session = Depends(get_db)):
    invite = (
        db.query(InviteToken)
        .filter(
            InviteToken.token == data.token,
            InviteToken.used == 0,
        )
        .first()
    )
    if invite is None:
        raise HTTPException(status_code=404, detail="Invalid or already-used invite token")

    member = GroupMember(
        name=data.name,
        is_online=0,
        hours_this_week=0.0,
        current_streak=0,
        joined_at=timestamp_now(),
    )
    invite.used = 1
    db.add(member)
    db.commit()
    db.refresh(member)
    return member
