"""
NexaMind AI - Database Engine & Session Management (SQLAlchemy)
Hỗ trợ PostgreSQL (Production Enterprise) và SQLite (Cục bộ/Dự phòng).
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SQLITE_PATH = DATA_DIR / "nexamind.db"
DEFAULT_SQLITE_URL = f"sqlite:///{SQLITE_PATH}"

# Đọc cấu hình từ biến môi trường
TARGET_DB_URL = os.getenv("DATABASE_URL", "").strip() or DEFAULT_SQLITE_URL


def build_engine(url: str):
    """Khởi tạo SQLAlchemy Engine với cấu hình tối ưu theo từng hệ cơ sở dữ liệu."""
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
        )
    elif url.startswith("postgresql") or url.startswith("postgres"):
        # Chuẩn hóa tiền tố postgres:// thành postgresql:// cho SQLAlchemy >= 1.4
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return create_engine(
            url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    else:
        return create_engine(url)


# Thử kết nối cơ sở dữ liệu mục tiêu (PostgreSQL nếu có), nếu lỗi sẽ tự động fallback về SQLite
try:
    engine = build_engine(TARGET_DB_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    ACTIVE_DB_URL = TARGET_DB_URL
except Exception as err:
    if not TARGET_DB_URL.startswith("sqlite"):
        print(f"[Database] ⚠️ Không thể kết nối tới PostgreSQL ({TARGET_DB_URL}): {err}")
        print(f"[Database] 🔄 Tự động chuyển sang sử dụng SQLite dự phòng tại: {SQLITE_PATH}")
    engine = build_engine(DEFAULT_SQLITE_URL)
    ACTIVE_DB_URL = DEFAULT_SQLITE_URL

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI Dependency cung cấp Database Session cho từng request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Khởi tạo tất cả bảng dữ liệu (conversations, messages) nếu chưa tồn tại."""
    import backend.app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    if "postgresql" in ACTIVE_DB_URL:
        # Ẩn mật khẩu khi in log
        safe_url = ACTIVE_DB_URL.split("@")[-1] if "@" in ACTIVE_DB_URL else "postgresql"
        print(f"[Database] ✅ Đã kết nối và khởi tạo thành công trên PostgreSQL: {safe_url}")
    else:
        print(f"[Database] ℹ️ Đang sử dụng cơ sở dữ liệu SQLite tại: {SQLITE_PATH}")
