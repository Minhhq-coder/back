import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_optional_current_user, require_permission
from app.models import ChatKnowledgeItem, ChatMessage, ChatSession, User
from app.schemas import (
    ChatbotAuditMessageOut,
    ChatbotAuditPageOut,
    ChatbotFeedbackIn,
    ChatbotKnowledgeItemCreate,
    ChatbotKnowledgeItemOut,
    ChatbotKnowledgeItemUpdate,
    ChatbotMessageRequest,
    ChatbotMessageResponse,
    ChatbotSuggestedQuestionsOut,
)
from app.services.chatbot_service import (
    get_suggested_questions,
    handle_chat_message,
    stream_chat_response,
)

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    without_marks = without_marks.replace("đ", "d")
    slug = re.sub(r"[^a-z0-9]+", "-", without_marks).strip("-")
    return slug


def _normalize_tags(values: list[str] | None) -> list[str]:
    tags: list[str] = []
    for value in values or []:
        cleaned = " ".join(value.split())
        if cleaned and cleaned not in tags:
            tags.append(cleaned)
    return tags


async def _ensure_unique_slug(
    db: AsyncSession,
    slug: str | None,
    exclude_id: int | None = None,
) -> str | None:
    if slug is None:
        return None

    normalized_slug = _slugify(slug)
    if not normalized_slug:
        return None

    query = select(ChatKnowledgeItem).where(ChatKnowledgeItem.slug == normalized_slug)
    if exclude_id is not None:
        query = query.where(ChatKnowledgeItem.id != exclude_id)

    result = await db.execute(query)
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Knowledge item slug already exists")

    return normalized_slug


@router.get("/suggested-questions", response_model=ChatbotSuggestedQuestionsOut)
async def list_suggested_questions(
    product_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    return await get_suggested_questions(db, product_id, current_user)


@router.post("/messages", response_model=ChatbotMessageResponse)
async def create_chat_message(
    payload: ChatbotMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    return await handle_chat_message(db, payload, current_user)


@router.post("/messages/stream")
async def create_chat_message_stream(
    payload: ChatbotMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    response = await handle_chat_message(db, payload, current_user)
    return StreamingResponse(
        stream_chat_response(response),
        media_type="text/event-stream",
    )


@router.post("/messages/{message_id}/feedback", response_model=dict)
async def submit_chat_feedback(
    message_id: int,
    payload: ChatbotFeedbackIn,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    result = await db.execute(
        select(ChatMessage, ChatSession)
        .join(ChatSession, ChatMessage.chat_session_id == ChatSession.id)
        .where(ChatMessage.id == message_id, ChatMessage.role == "assistant")
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Chat message not found")

    message, session = row
    if session.session_id != payload.session_id:
        raise HTTPException(status_code=403, detail="Feedback session mismatch")

    if message.user_id is not None:
        if current_user is None or message.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Feedback is not allowed for this message")

    message.helpful = payload.helpful
    message.feedback_note = payload.note
    await db.flush()
    return {"message": "Feedback saved successfully."}


@router.get("/admin/knowledge", response_model=list[ChatbotKnowledgeItemOut])
async def list_knowledge_items(
    _: User = Depends(require_permission("chatbot:manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatKnowledgeItem).order_by(
            ChatKnowledgeItem.priority.desc(),
            ChatKnowledgeItem.updated_at.desc(),
        )
    )
    return result.scalars().all()


@router.post(
    "/admin/knowledge",
    response_model=ChatbotKnowledgeItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_item(
    payload: ChatbotKnowledgeItemCreate,
    _: User = Depends(require_permission("chatbot:manage")),
    db: AsyncSession = Depends(get_db),
):
    slug = await _ensure_unique_slug(db, payload.slug or payload.title)
    item = ChatKnowledgeItem(
        kind=payload.kind,
        slug=slug,
        title=payload.title.strip(),
        content=payload.content.strip(),
        source_label=payload.source_label.strip() if payload.source_label else None,
        source_url=payload.source_url.strip() if payload.source_url else None,
        tags=_normalize_tags(payload.tags),
        priority=payload.priority,
        is_active=payload.is_active,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.put("/admin/knowledge/{item_id}", response_model=ChatbotKnowledgeItemOut)
async def update_knowledge_item(
    item_id: int,
    payload: ChatbotKnowledgeItemUpdate,
    _: User = Depends(require_permission("chatbot:manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatKnowledgeItem).where(ChatKnowledgeItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Knowledge item not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "slug" in update_data:
        item.slug = await _ensure_unique_slug(db, update_data["slug"], exclude_id=item_id)
    elif "title" in update_data and not item.slug:
        item.slug = await _ensure_unique_slug(db, update_data["title"], exclude_id=item_id)

    if "kind" in update_data:
        item.kind = update_data["kind"]
    if "title" in update_data:
        item.title = update_data["title"].strip()
    if "content" in update_data:
        item.content = update_data["content"].strip()
    if "source_label" in update_data:
        item.source_label = update_data["source_label"].strip() if update_data["source_label"] else None
    if "source_url" in update_data:
        item.source_url = update_data["source_url"].strip() if update_data["source_url"] else None
    if "tags" in update_data:
        item.tags = _normalize_tags(update_data["tags"])
    if "priority" in update_data:
        item.priority = update_data["priority"]
    if "is_active" in update_data:
        item.is_active = update_data["is_active"]

    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/admin/knowledge/{item_id}", response_model=dict)
async def delete_knowledge_item(
    item_id: int,
    _: User = Depends(require_permission("chatbot:manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatKnowledgeItem).where(ChatKnowledgeItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Knowledge item not found")

    await db.delete(item)
    await db.flush()
    return {"message": "Knowledge item deleted successfully."}


@router.get("/admin/messages", response_model=ChatbotAuditPageOut)
async def list_chat_messages(
    role: str | None = Query(default="assistant"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permission("chatbot:manage")),
    db: AsyncSession = Depends(get_db),
):
    count_query = select(func.count()).select_from(ChatMessage).join(
        ChatSession,
        ChatMessage.chat_session_id == ChatSession.id,
    )
    query = (
        select(ChatMessage, ChatSession.session_id)
        .join(ChatSession, ChatMessage.chat_session_id == ChatSession.id)
        .order_by(ChatMessage.created_at.desc())
    )

    if role:
        count_query = count_query.where(ChatMessage.role == role)
        query = query.where(ChatMessage.role == role)

    total = (await db.execute(count_query)).scalar_one() or 0
    total_pages = (total + page_size - 1) // page_size if total else 0

    rows = (
        await db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
    ).all()

    items = [
        ChatbotAuditMessageOut(
            id=message.id,
            session_id=session_id,
            user_id=message.user_id,
            role=message.role,
            content=message.content,
            sources=message.sources or [],
            actions=message.actions or [],
            helpful=message.helpful,
            feedback_note=message.feedback_note,
            is_fallback=message.is_fallback,
            error_reason=message.error_reason,
            created_at=message.created_at,
        )
        for message, session_id in rows
    ]

    return ChatbotAuditPageOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
