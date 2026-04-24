from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    last_product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")
    last_product = relationship("Product")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id.asc()",
    )


class ChatKnowledgeItem(Base):
    __tablename__ = "chat_knowledge_items"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(50), nullable=False, default="faq", index=True)
    slug = Column(String(255), unique=True, nullable=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    source_label = Column(String(200), nullable=True)
    source_url = Column(String(500), nullable=True)
    tags = Column(JSON, nullable=False, default=list)
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    role = Column(String(20), nullable=False, index=True)
    content = Column(Text, nullable=False)
    message_metadata = Column("metadata", JSON, nullable=False, default=dict)
    sources = Column(JSON, nullable=False, default=list)
    actions = Column(JSON, nullable=False, default=list)
    suggested_questions = Column(JSON, nullable=False, default=list)
    helpful = Column(Boolean, nullable=True)
    feedback_note = Column(Text, nullable=True)
    is_fallback = Column(Boolean, nullable=False, default=False)
    error_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User")
