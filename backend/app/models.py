"""
NexaMind AI - ORM Models (SQLAlchemy)
Lưu trữ lâu dài hội thoại và tin nhắn theo từng người dùng.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import relationship

from backend.app.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(32), primary_key=True, default=_uuid)
    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="Đoạn chat mới")
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(32), primary_key=True, default=_uuid)
    conversation_id = Column(
        String(32), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(20), nullable=False)  # 'user' | 'assistant'
    content = Column(Text, nullable=False, default="")
    sources_json = Column(Text, nullable=True)
    model_used = Column(String(100), nullable=True)
    elapsed_seconds = Column(Float, nullable=True)
    is_error = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


Index("ix_messages_conversation_created", Message.conversation_id, Message.created_at)
