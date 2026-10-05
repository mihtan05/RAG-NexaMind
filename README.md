# NexaMind — Hệ Thống Hỏi Đáp & Phân Tích Tài Liệu Doanh Nghiệp

NexaMind là hệ thống hỏi đáp và phân tích tài liệu thông minh xây dựng theo kiến trúc RAG (Retrieval-Augmented Generation) "From Scratch" bằng Python thuần và NumPy. Hệ thống kết hợp Dense Embeddings, BM25 Okapi và FlashRank Cross-Encoder để trả lời có căn cứ, ưu tiên trích dẫn nguồn văn bản chính xác thay vì suy đoán hay ảo giác.

Nội dung trọng tâm gồm hỗ trợ nạp đa định dạng (PDF, DOCX, XLSX, PPTX, CSV, Markdown) qua Microsoft MarkItDown, băm nhỏ dữ liệu thông minh bảo toàn cấu trúc bảng biểu, phản hồi thời gian thực qua Server-Sent Events (SSE) và cô lập dữ liệu 100% theo từng người dùng.

---

## Mục lục
- [Tính năng](#tính-năng)
- [Kiến trúc](#kiến-trúc)
- [Tech stack](#tech-stack)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Dữ liệu & database](#dữ-liệu--database)
- [API](#api)
- [Chạy local](#chạy-local)
- [Chạy Docker Compose](#chạy-docker-compose)
- [Biến môi trường](#biến-môi-trường)
- [Bảo mật & an toàn](#bảo-mật--an-toàn)

---

## Tính năng

- **Hybrid Retrieval & Re-ranking** — kết hợp Dense Embeddings, BM25 Okapi (RRF) và FlashRank Cross-Encoder lọc sạch nhiễu trên CPU.
- **Câu trả lời có căn cứ & Streaming** — phản hồi realtime qua SSE, bám sát tài liệu gốc và trích dẫn minh bạch, chống ảo giác.
- **Table-aware Chunking** — tự động nhận diện bảng biểu Markdown, nhân bản tiêu đề cột để giữ nguyên ngữ cảnh số liệu từ PDF, DOCX, XLSX.
- **Cô lập dữ liệu người dùng tuyệt đối** — xác thực JWT / Google OAuth; tài liệu, vector chunks và lịch sử chat được phân quyền riêng biệt 100%.
- **Quản lý hội thoại & Document Viewer** — giao diện ChatGPT-style (ghim, đổi tên, xuất `.md`) kèm modal đọc trước file và kiểm tra từng chunk.
- **Operational readiness** — tự động failover giữa PostgreSQL và SQLite, tích hợp API rate limiting và kiểm duyệt file an toàn.

---

## Kiến trúc

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend: React 18 + Vite                   │
│                    Port :5173 (Dev) / :8000 (Prod)              │
│  • Dark Glassmorphism UI (Inter / Be Vietnam Pro)               │
│  • Streaming chat qua Server-Sent Events (SSE)                  │
│  • Quản lý hội thoại (Pin, Rename, Delete, Export .md)          │
│  • Trình đọc tài liệu & kiểm tra Chunk Inspector trực tiếp      │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP REST / SSE Stream (JWT Bearer)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend: FastAPI + Uvicorn                  │
│                             Port :8000                          │
│  • JWT Authentication & Multi-Tenancy Data Isolation            │
│  • Sliding-window Rate Limiter & File Security Guards           │
│  • Query Condensation (tổng hợp lịch sử đa lượt chat)           │
│  • REST API & SSE EventSource Producer                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   PostgreSQL    │   │  NumPy Vector   │   │  Google Gemini  │
│  / SQLite DB    │   │   & BM25 Store  │   │   API (LLM)     │
│   users/chat    │   │   local cache   │   │ 2.5/3.8 Flash   │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

| Service | Port | Trách nhiệm |
| :--- | :--- | :--- |
| **frontend** | 5173 (dev) / 8000 (prod) | Giao diện React SPA, SSE client, hiển thị trích dẫn và quản lý kho tài liệu |
| **backend** | 8000 | API nghiệp vụ, auth, hybrid RAG, băm tài liệu, SSE stream |
| **postgres** | 5432 (container/host) | Lưu trữ người dùng, danh sách hội thoại và lịch sử tin nhắn |
| **storage** | — | Lưu trữ bền vững cục bộ: `data/uploads`, `data/cache_index`, `data/rerank_models` |

---

## Tech stack

| Thành phần | Công nghệ |
| :--- | :--- |
| **API backend** | FastAPI, Uvicorn, Pydantic v2, SSE-Starlette |
| **Frontend client** | React 18, Vite, Lucide Icons, Vanilla CSS (Dark Glassmorphism) |
| **ORM & Database** | SQLAlchemy 2.0, PostgreSQL 16 (psycopg2) / SQLite failover |
| **Authentication** | PyJWT, Google Identity Services (GIS OAuth 2.0) |
| **Trích xuất văn bản** | Microsoft MarkItDown (PDF, DOCX, XLSX, PPTX, CSV, MD) |
| **Chunking** | Table-Aware Markdown Chunker (Tự viết bằng Python) |
| **Dense Retrieval** | Sentence-Transformers (`all-MiniLM-L6-v2`) 384D + NumPy Cosine Similarity |
| **Sparse Retrieval** | BM25 Okapi Engine (Tự viết bằng Python/NumPy, chuẩn hóa tiếng Việt) |
| **Rank Fusion** | Reciprocal Rank Fusion (RRF $k=60$) |
| **Re-ranking** | FlashRank CPU Cross-Encoder (`ms-marco-TinyBERT-L-2-v2`) |
| **LLM Provider** | Google Gemini API (`google-genai` SDK: `gemini-2.5-flash`, `gemini-3.8-flash`) |
| **Bảo mật & Guards** | Sliding-window Rate Limiter, Magic Bytes MIME Validator |
| **Deployment** | Docker, Docker Compose, Windows Batch Scripts |

---

## Cấu trúc thư mục

```text
RAG/
├── backend/                      # FastAPI Backend Server
│   └── app/
│       ├── main.py               # REST API, SSE streaming & Static SPA mount
│       ├── rag_service.py        # Singleton RAG Service (Hybrid Search, Condenser)
│       ├── database.py           # Kết nối PostgreSQL connection pool & SQLite failover
│       ├── models.py             # SQLAlchemy Models (Conversation, Message)
│       ├── schemas.py            # Pydantic Schemas xác thực request/response
│       ├── auth.py               # Xử lý JWT Bearer token & Google Auth
│       └── guardrails.py         # Rate limiter & kiểm tra file an toàn
│
├── frontend/                     # React 18 Frontend (Vite)
│   ├── src/
│   │   ├── components/           # Sidebar, StatCards, ChatHistory, DocViewerModal...
│   │   ├── services/api.js       # API Client & SSE Stream parser (JWT header)
│   │   ├── App.jsx               # Central Controller & Application State
│   │   └── index.css             # NexaMind Dark Glassmorphism Design Tokens
│   ├── vite.config.js            # Proxy /api sang port 8000
│   └── package.json
│
├── core/                         # Bộ thư viện RAG tự viết (100% Pure Python)
│   ├── loader.py                 # Nạp tài liệu đa định dạng bằng Microsoft MarkItDown
│   ├── chunker.py                # Thuật toán băm Markdown Table-Aware & overlap
│   ├── bm25.py                   # Động cơ BM25 Okapi thuần Python & NumPy
│   ├── reranker.py               # FlashRank CPU Cross-Encoder Re-ranker
│   ├── embedding.py              # Dịch text thành vector bằng sentence-transformers
│   ├── vector_store.py           # Vector Store thuần NumPy & Cosine Similarity
│   └── generator.py              # Ghép prompt chống ảo giác & streaming Gemini API
│
├── data/                         # Thư mục dữ liệu bền vững (Persistent Storage)
│   ├── nexamind.db               # SQLite database dự phòng (tự động tạo)
│   ├── uploads/                  # File tải lên (cô lập theo từng user_id)
│   ├── cache_index/              # Cache ma trận Vector .npz và metadata JSON
│   └── rerank_models/            # Trọng số FlashRank ONNX offline
│
├── docker-compose.yml            # Docker Compose chạy App + PostgreSQL 16
├── Dockerfile                    # Multi-stage Docker build (Node.js + Python 3.11)
├── run_all.bat                   # Phím tắt 1-click khởi chạy toàn bộ hệ thống (Postgres + Backend + Frontend)
├── requirements.txt              # Thư viện Python phụ thuộc
├── .env.example                  # Mẫu cấu hình môi trường
└── .env                          # File cấu hình biến môi trường cục bộ
```

---

## Dữ liệu & database

Hệ thống quản lý dữ liệu hội thoại qua SQLAlchemy với mô hình quan hệ:

```text
User ──< Conversation ──< Message
  │
  └────< Uploaded Documents & Vector Chunks (cô lập theo user_id)
```
- **`conversations`** — lưu danh sách phiên hội thoại (`id`, `user_id`, `title`, `is_pinned`, `created_at`, `updated_at`).
- **`messages`** — lưu lịch sử tin nhắn (`id`, `conversation_id`, `role`, `content`, `sources_json`, `model_used`, `elapsed_seconds`, `is_error`, `created_at`).
- **`cache_index`** — lưu trữ ma trận vector dạng nén `.npz` và file `doc_metadata.json` liên kết với từng phân đoạn tài liệu.

### Cơ chế Database Failover tự động
Hệ thống ưu tiên kết nối tới **PostgreSQL 16** (có Connection Pooling: `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`).  
Nếu máy chủ PostgreSQL chưa bật hoặc gặp sự cố, hệ thống **tự động chuyển sang cơ sở dữ liệu SQLite** cục bộ tại `data/nexamind.db` mà không gây gián đoạn dịch vụ.

---

## API

| Nhóm | Ví dụ endpoint | Mô tả |
| :--- | :--- | :--- |
| **Health** | `GET /api/health` | Kiểm tra trạng thái hoạt động của server |
| **Auth** | `POST /api/auth/login` | Đăng nhập tài khoản / Google OAuth và cấp JWT token |
| | `GET /api/auth/me` | Lấy thông tin phiên người dùng hiện tại |
| **Chat & Stream** | `POST /api/chat/stream` | Gửi câu hỏi và nhận luồng Server-Sent Events (SSE) theo thời gian thực |
| **Conversations** | `GET /api/conversations?user_id=...` | Lấy danh sách hội thoại của người dùng |
| | `POST /api/conversations` | Tạo hội thoại mới |
| | `PATCH /api/conversations/:id?user_id=...` | Đổi tên hoặc ghim (Pin) hội thoại |
| | `DELETE /api/conversations/:id?user_id=...` | Xóa hội thoại và toàn bộ tin nhắn liên quan |
| | `GET /api/conversations/:id?user_id=...` | Lấy chi tiết hội thoại kèm toàn bộ tin nhắn |
| **Documents** | `GET /api/documents?owner_id=...` | Lấy danh sách tài liệu thuộc quyền sở hữu của user |
| | `POST /api/documents/upload` | Tải lên tài liệu (kiểm duyệt Rate Limit & Magic bytes) |
| | `GET /api/documents/:filename/preview?owner_id=...` | Xem trước các phân đoạn (chunks) của tài liệu |
| | `DELETE /api/documents/:filename?owner_id=...` | Xóa tài liệu khỏi kho và cập nhật lại vector index |
| | `DELETE /api/documents/clear?owner_id=...` | Xóa sạch toàn bộ kho tài liệu của user |
| | `GET /api/stats?owner_id=...` | Thống kê số lượng file, chunk và dung lượng lưu trữ |

Khi stack đang chạy:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- **Health check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **Frontend App**: [http://localhost:5173](http://localhost:5173) (hoặc [http://localhost:8000](http://localhost:8000) khi chạy qua Docker/Production)

---

## Chạy local

### Yêu cầu
- Python 3.10+ (khuyên dùng Python 3.11)
- Node.js 18+
- Google Gemini API key (lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/))

### Cài đặt & Khởi động 1-Click (Khuyên dùng)
Chỉ cần nhấp đúp file **`run_all.bat`** (hoặc chạy từ terminal):
```powershell
.\run_all.bat
```
> ⚡ **Tự động 100%**: Script sẽ tự tạo `.env`, tự tạo Python `.venv`, tự chạy `pip install` và `npm install` nếu chạy lần đầu, sau đó tự bật Web App tại `http://localhost:5173`. Bạn chỉ cần mở file `.env` điền thêm `GEMINI_API_KEY`.

---

### Khởi động bằng dòng lệnh thủ công
Cài đặt trọn gói tất cả thư viện bằng **1 dòng lệnh duy nhất**:
```powershell
Copy-Item .env.example .env; python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt; cd frontend; npm install; cd ..
```
Khởi động từng tiến trình riêng biệt (khi cần debug):
- **Backend (Port 8000):** `.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload`
- **Frontend (Port 5173):** `cd frontend; npm run dev`
- **PostgreSQL (Docker):** `docker compose up -d postgres`

---

## Chạy Docker Compose

Triển khai toàn bộ hệ thống (App + PostgreSQL 16) chỉ với 1 lệnh:

```bash
docker compose up -d --build
```

Kiểm tra trạng thái stack:
```powershell
Invoke-WebRequest http://localhost:8000/api/health
docker compose ps
```

Truy cập ứng dụng tại: 👉 **http://localhost:8000**

Dừng stack:
```bash
docker compose down
```

---

## Biến môi trường

| Biến | Bắt buộc | Mô tả |
| :--- | :---: | :--- |
| `GEMINI_API_KEY` | **Có** | Khóa API Google Gemini để sinh câu trả lời |
| `JWT_SECRET_KEY` | **Có** | Chuỗi bí mật dùng để ký và xác thực JWT token |
| `DATABASE_URL` | Không | URL kết nối PostgreSQL (ví dụ `postgresql://nexamind_user:nexamind_pass@127.0.0.1:5432/nexamind`). Nếu không có, hệ thống dùng SQLite `data/nexamind.db` |
| `VITE_GOOGLE_CLIENT_ID` | Không | Client ID Google OAuth (GIS) hiển thị nút đăng nhập Google |
| `PORT` | Không | Cổng chạy dịch vụ Backend (mặc định: `8000`) |

---
