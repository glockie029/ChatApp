from collections.abc import Iterable

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from core.config import settings
from db.session import get_db
from models.message import Message
from schemas.message import (
    HealthResponse,
    MessageCreate,
    MessageResponse,
    ModerationSummary,
)


router = APIRouter()
unsafe_router = APIRouter()


def build_risk_tags(content: str) -> list[str]:
    lowered_content = content.lower()
    tags: list[str] = []

    for keyword in settings.moderation_keyword_list:
        if keyword in lowered_content:
            tags.append(keyword)

    return tags


def serialize_message(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        username=message.username,
        content=message.content,
        created_at=message.created_at,
        risk_tags=build_risk_tags(message.content),
    )


def count_flagged_messages(messages: Iterable[Message]) -> int:
    return sum(1 for message in messages if build_risk_tags(message.content))


@router.get("/health", response_model=HealthResponse)
def read_health(request: Request) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=settings.app_version,
        unsafe_routes_enabled=request.app.state.unsafe_routes_enabled,
    )


@router.post(
    "/messages/",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(message: MessageCreate, db: Session = Depends(get_db)) -> MessageResponse:
    db_message = Message(username=message.username, content=message.content)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return serialize_message(db_message)


@router.get("/messages/search", response_model=list[MessageResponse])
def search_messages(
    keyword: str = Query(..., min_length=1, max_length=100),
    db: Session = Depends(get_db),
) -> list[MessageResponse]:
    normalized_keyword = keyword.strip()
    if not normalized_keyword:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="keyword must not be empty",
        )

    like_pattern = f"%{normalized_keyword}%"
    messages = (
        db.query(Message)
        .filter(
            or_(
                Message.content.ilike(like_pattern),
                Message.username.ilike(like_pattern),
            )
        )
        .order_by(Message.created_at.desc(), Message.id.desc())
        .all()
    )
    return [serialize_message(message) for message in messages]


@router.get("/messages/", response_model=list[MessageResponse])
def get_messages(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[MessageResponse]:
    messages = (
        db.query(Message)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [serialize_message(message) for message in messages]


@router.get("/messages/{message_id}", response_model=MessageResponse)
def get_message(message_id: int, db: Session = Depends(get_db)) -> MessageResponse:
    message = db.query(Message).filter(Message.id == message_id).first()
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="message not found",
        )
    return serialize_message(message)


@router.get("/moderation/summary", response_model=ModerationSummary)
def get_moderation_summary(db: Session = Depends(get_db)) -> ModerationSummary:
    messages = db.query(Message).all()
    return ModerationSummary(
        total_messages=len(messages),
        flagged_messages=count_flagged_messages(messages),
        monitored_keywords=settings.moderation_keyword_list,
    )


@unsafe_router.get("/unsafe_search/")
def unsafe_search_messages(query: str, db: Session = Depends(get_db)) -> dict[str, object]:
    """
    Intentionally vulnerable training endpoint.
    Remove the nosec marker to make Bandit fail the pipeline on purpose.
    """
    sql = f"SELECT * FROM messages WHERE content LIKE '%{query}%'"  # nosec B608
    result = db.execute(text(sql)).fetchall()
    return {"result": [row._asdict() for row in result]}


@unsafe_router.post("/unsafe_messages/", status_code=status.HTTP_201_CREATED)
def unsafe_add_message(
    message: MessageCreate, db: Session = Depends(get_db)
) -> dict[str, str]:
    """
    Intentionally vulnerable training endpoint.
    Remove the nosec marker to make Bandit fail the pipeline on purpose.
    """
    sql = f"INSERT INTO messages (username, content, created_at) VALUES ('{message.username}', '{message.content}', CURRENT_TIMESTAMP)"  # nosec B608
    db.execute(text(sql))
    db.commit()
    return {"status": "message added (unsafe)", "content": message.content}
