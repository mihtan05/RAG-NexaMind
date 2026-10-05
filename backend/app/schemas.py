"""
Pydantic Schemas cho NexaMind AI API
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., description="Câu hỏi của người dùng")
    top_k: int = Field(default=4, ge=1, le=20, description="Số lượng đoạn trích dẫn tối đa")
    threshold: float = Field(default=0.25, ge=0.0, le=1.0, description="Ngưỡng tương đồng cosine tối thiểu")
    model_name: Optional[str] = Field(default=None, description="Tên mô hình Gemini tùy chọn")
    api_key: Optional[str] = Field(default=None, description="Gemini API Key tùy chọn từ client")
    conversation_id: Optional[str] = Field(default=None, description="ID hội thoại để lưu lịch sử & ngữ cảnh đa lượt")
    user_id: Optional[str] = Field(default=None, description="Định danh người dùng (email/sub)")


class SourceChunk(BaseModel):
    source: str
    section: str
    score: float
    score_percent: str
    text: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]] = []
    model_used: str
    elapsed_seconds: float
    is_error: bool = False


class DocumentItem(BaseModel):
    filename: str
    chunks_count: int
    size_kb: float
    indexed_at: str
    ext: str
    scope: Optional[str] = "shared"


class StatsResponse(BaseModel):
    documents_count: int
    chunks_count: int
    vector_dimension: Optional[int]
    active_model: str
    is_ready: bool
    documents: List[DocumentItem] = []


class IndexRequest(BaseModel):
    filenames: Optional[List[str]] = Field(default=None, description="Danh sách tên file cần index (None = tất cả file trong staging)")
    owner_id: Optional[str] = Field(default="shared", description="Chủ sở hữu kho tài liệu (email/sub hoặc 'shared')")


class GenericResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class LoginRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    provider: Optional[str] = "password"
    google_token: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class DocumentPreviewResponse(BaseModel):
    filename: str
    chunks_count: int
    chunks: List[Dict[str, Any]] = []


class ConversationCreate(BaseModel):
    user_id: str
    title: Optional[str] = "Đoạn chat mới"


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None


class ConversationOut(BaseModel):
    id: str
    user_id: str
    title: str
    is_pinned: bool = False
    created_at: str
    updated_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: List[Dict[str, Any]] = []
    model_used: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    is_error: bool = False
    created_at: str


class ConversationDetail(ConversationOut):
    messages: List[MessageOut] = []
