"""
NexaMind AI - FastAPI Application Main Entry
Cung cấp REST API và Server-Sent Events (SSE) Streaming cho NexaMind Frontend
"""

import json
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

# Load môi trường
load_dotenv()

from backend.app.schemas import (
    ChatRequest,
    ChatResponse,
    StatsResponse,
    DocumentItem,
    IndexRequest,
    GenericResponse,
    ConversationCreate,
    ConversationUpdate,
    ConversationOut,
    ConversationDetail,
    MessageOut,
    LoginRequest,
    TokenResponse,
    DocumentPreviewResponse,
)
from backend.app.rag_service import RAGService
from backend.app.database import init_db, get_db, SessionLocal
from backend.app.models import Conversation, Message
from backend.app.auth import create_access_token, get_current_user_optional
from backend.app.guardrails import rate_limiter, validate_file_guard
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

app = FastAPI(
    title="NexaMind AI API",
    description="Backend API cho hệ thống RAG hỏi đáp tài liệu NexaMind AI",
    version="2.1.0"
)

# Cấu hình CORS cho phép React Frontend (Vite) truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo singleton RAGService
rag_service = RAGService()

init_db()


# ===== AUTHENTICATION ENDPOINTS =====

@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """Đăng nhập hoặc xác thực tài khoản (Password / Google OAuth) và cấp JWT Token."""
    user_email = (req.email or "").strip().lower()
    if not user_email:
        user_email = "user@nexamind.ai"
    display_name = req.name or user_email.split("@")[0].capitalize()
    user_payload = {
        "sub": user_email,
        "email": user_email,
        "name": display_name,
        "role": "member",
        "provider": req.provider or "password"
    }
    token = create_access_token(user_payload)
    return TokenResponse(access_token=token, token_type="bearer", user=user_payload)


@app.get("/api/auth/me")
def get_current_profile(user: dict = Depends(get_current_user_optional)):
    """Trả về thông tin phiên người dùng hiện tại từ JWT Token."""
    return user


def _conv_out(c: Conversation) -> ConversationOut:
    return ConversationOut(
        id=c.id, user_id=c.user_id, title=c.title, is_pinned=bool(c.is_pinned),
        created_at=c.created_at.isoformat(), updated_at=c.updated_at.isoformat(),
    )


def _msg_out(m: Message) -> MessageOut:
    try:
        sources = json.loads(m.sources_json) if m.sources_json else []
    except Exception:
        sources = []
    return MessageOut(
        id=m.id, role=m.role, content=m.content, sources=sources,
        model_used=m.model_used, elapsed_seconds=m.elapsed_seconds,
        is_error=bool(m.is_error), created_at=m.created_at.isoformat(),
    )


@app.get("/api/conversations", response_model=List[ConversationOut])
def list_conversations(user_id: str = Query(...), db: Session = Depends(get_db)):
    rows = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(desc(Conversation.is_pinned), desc(Conversation.updated_at))
        .all()
    )
    return [_conv_out(c) for c in rows]


@app.post("/api/conversations", response_model=ConversationOut)
def create_conversation(body: ConversationCreate, db: Session = Depends(get_db)):
    c = Conversation(user_id=body.user_id, title=(body.title or "Đoạn chat mới")[:255])
    db.add(c)
    db.commit()
    db.refresh(c)
    return _conv_out(c)


@app.get("/api/conversations/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: str, user_id: str = Query(...), db: Session = Depends(get_db)):
    c = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại.")
    out = _conv_out(c).model_dump()
    out["messages"] = [_msg_out(m) for m in c.messages]
    return ConversationDetail(**out)


@app.patch("/api/conversations/{conv_id}", response_model=ConversationOut)
def update_conversation(conv_id: str, body: ConversationUpdate, user_id: str = Query(...), db: Session = Depends(get_db)):
    c = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại.")
    if body.title is not None:
        c.title = body.title.strip()[:255] or c.title
    if body.is_pinned is not None:
        c.is_pinned = body.is_pinned
    db.commit()
    db.refresh(c)
    return _conv_out(c)


@app.delete("/api/conversations/{conv_id}", response_model=GenericResponse)
def delete_conversation(conv_id: str, user_id: str = Query(...), db: Session = Depends(get_db)):
    c = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại.")
    db.delete(c)
    db.commit()
    return GenericResponse(status="success", message="Đã xóa hội thoại.")


@app.get("/api/health")
def health_check():
    """Kiểm tra sức khỏe hệ thống."""
    return {"status": "ok", "app": "NexaMind AI", "version": "2.1.0"}


@app.get("/api/stats", response_model=StatsResponse)
def get_stats(owner_id: Optional[str] = Query(default=None)):
    """Lấy số liệu thống kê kho tài liệu trong phạm vi user được phép xem."""
    stats = rag_service.get_stats(owner_id=owner_id)
    return stats


@app.get("/api/documents", response_model=List[DocumentItem])
def list_documents(owner_id: Optional[str] = Query(default=None)):
    """Danh sách tất cả tài liệu user được xem (cá nhân + kho dùng chung)."""
    stats = rag_service.get_stats(owner_id=owner_id)
    return stats["documents"]


@app.get("/api/documents/{filename}/preview", response_model=DocumentPreviewResponse)
def preview_document(filename: str, owner_id: Optional[str] = Query(default=None)):
    """Xem trước các phân đoạn (chunks) của tài liệu trực tiếp trong ứng dụng."""
    preview = rag_service.get_document_preview(filename=filename, owner_id=owner_id)
    return DocumentPreviewResponse(**preview)


@app.post("/api/documents/upload", response_model=GenericResponse)
async def upload_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    owner_id: str = Form(default="default")
):
    """
    Tiếp nhận upload tài liệu có kiểm tra Rate Limiting & File Guardrails (dung lượng, magic bytes).
    Lưu vào thư mục riêng của từng user để cô lập dữ liệu.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_limiter.check_rate_limit(f"upload:{client_ip}:{owner_id}", max_requests=15, window_seconds=60)

    if not files:
        raise HTTPException(status_code=400, detail="Không có file nào được tải lên.")

    saved_files = []
    for file in files:
        if not file.filename:
            continue
        content = await file.read()
        # Kiểm tra tính an toàn của file
        sha256_hash = validate_file_guard(file.filename, content)
        saved_path = rag_service.save_uploaded_file(file.filename, content, owner_id=owner_id)
        saved_files.append({
            "filename": file.filename,
            "size_kb": round(len(content) / 1024, 1),
            "sha256": sha256_hash,
            "owner_id": owner_id,
            "path": str(saved_path)
        })

    return GenericResponse(
        status="success",
        message=f"Đã lưu an toàn {len(saved_files)} file vào kho. Hãy bấm Lập chỉ mục để xử lý.",
        data={"files": saved_files}
    )


@app.post("/api/documents/index", response_model=GenericResponse)
def index_documents(req: Optional[IndexRequest] = None):
    """
    Lập chỉ mục tài liệu cho chủ sở hữu cụ thể:
    MarkItDown -> Table-Aware Chunker -> Local Embeddings -> Vector Store & BM25.
    """
    owner_id = req.owner_id if req and req.owner_id else "default"
    upload_dir = rag_service.user_upload_dir(owner_id)

    if req and req.filenames:
        target_paths = [upload_dir / name for name in req.filenames if (upload_dir / name).exists()]
    else:
        target_paths = [p for p in upload_dir.iterdir() if p.is_file() and p.name != ""]

    if not target_paths:
        raise HTTPException(status_code=400, detail="Không tìm thấy tài liệu nào trong thư mục tải lên để lập chỉ mục.")

    try:
        result = rag_service.process_and_index_files(target_paths, owner_id=owner_id)
        return GenericResponse(
            status="success",
            message=f"Đã lập chỉ mục thành công {len(result['indexed_files'])} tài liệu ({result['added_chunks']} chunks mới).",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lập chỉ mục tài liệu: {str(e)}")


@app.delete("/api/documents/{filename}", response_model=GenericResponse)
def delete_document(filename: str, owner_id: str = Query(default="default")):
    """Xóa một tài liệu cụ thể của chủ sở hữu khỏi kho."""
    removed = rag_service.remove_document(filename, owner_id=owner_id)
    return GenericResponse(
        status="success",
        message=f"Đã xóa tài liệu '{filename}' ({removed} chunks) khỏi kho của bạn.",
        data={"removed_chunks": removed}
    )


@app.delete("/api/documents", response_model=GenericResponse)
def clear_all_documents(owner_id: str = Query(default="default")):
    """Xóa toàn bộ kho tài liệu của chủ sở hữu này."""
    rag_service.clear_all(owner_id=owner_id)
    return GenericResponse(
        status="success",
        message=f"Đã dọn dẹp sạch kho tài liệu của bạn ({owner_id})."
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat_sync(req: ChatRequest, request: Request):
    """Truy vấn hỏi đáp đồng bộ kèm kiểm soát tần suất truy cập (Rate Limit)."""
    client_ip = request.client.host if request.client else "unknown"
    rate_limiter.check_rate_limit(f"chat:{client_ip}:{req.user_id or 'guest'}", max_requests=40, window_seconds=60)

    result = rag_service.query(
        query_text=req.query,
        top_k=req.top_k,
        threshold=req.threshold,
        model_name=req.model_name,
        api_key=req.api_key,
        owner_id=req.user_id
    )
    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        model_used=result["model_used"],
        elapsed_seconds=result["elapsed_seconds"],
        is_error=result["is_error"]
    )


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    """
    Truy vấn hỏi đáp qua Server-Sent Events (SSE) kèm:
    - Rate Limiting 40 lượt/phút
    - Cô lập dữ liệu theo user_id
    - Tự động lưu hội thoại vào SQLite
    - Viết lại câu hỏi đa lượt (Query Condensation)
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_limiter.check_rate_limit(f"chat:{client_ip}:{req.user_id or 'guest'}", max_requests=40, window_seconds=60)

    history: List[dict] = []
    conv_id = req.conversation_id
    if conv_id:
        db = SessionLocal()
        try:
            conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
            if conv and (not req.user_id or conv.user_id == req.user_id):
                history = [{"role": m.role, "content": m.content} for m in conv.messages if not m.is_error]
                db.add(Message(conversation_id=conv.id, role="user", content=req.query))
                if conv.title in ("Đoạn chat mới", "") and not conv.messages:
                    conv.title = req.query.strip().replace("\n", " ")[:60]
                db.commit()
            else:
                conv_id = None
        finally:
            db.close()

    def save_assistant(content, sources, meta, is_error=False):
        if not conv_id:
            return
        db = SessionLocal()
        try:
            db.add(Message(
                conversation_id=conv_id, role="assistant", content=content,
                sources_json=json.dumps(sources, ensure_ascii=False, default=str),
                model_used=(meta or {}).get("model_used"),
                elapsed_seconds=(meta or {}).get("elapsed_seconds"),
                is_error=is_error,
            ))
            conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
            if conv:
                conv.updated_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()

    def event_generator():
        buf, sources, meta = [], [], None
        try:
            for item in rag_service.query_stream(
                query_text=req.query,
                top_k=req.top_k,
                threshold=req.threshold,
                model_name=req.model_name,
                api_key=req.api_key,
                chat_history=history,
                owner_id=req.user_id
            ):
                if item["event"] == "sources":
                    sources = item["data"].get("sources", [])
                elif item["event"] == "token":
                    buf.append(item["data"].get("token", ""))
                elif item["event"] == "done":
                    meta = item["data"]
                    save_assistant("".join(buf), sources, meta)
                elif item["event"] == "error":
                    save_assistant(item["data"].get("message", ""), [], None, True)
                yield {
                    "event": item["event"],
                    "data": json.dumps(item["data"], ensure_ascii=False)
                }
        except Exception as e:
            save_assistant(str(e), [], None, True)
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}, ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())


# Mount Frontend Single-Page Application (SPA) nếu thư mục frontend/dist tồn tại
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles
    from starlette.responses import FileResponse

    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            raise HTTPException(status_code=404, detail="Not Found")
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
