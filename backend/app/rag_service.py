"""
NexaMind AI - RAG Service Singleton
Quản lý vòng đời Vector Store, Embedding Model, Chunker và Document Loader
"""

import os
import sys
import time
import json
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator

# Đảm bảo import được thư mục core/ từ thư mục gốc dự án
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.loader import DocumentLoader
from core.chunker import MarkdownChunker
from core.embedding import LocalEmbeddingService
from core.vector_store import NumPyVectorStore
from core.generator import RAGGenerator
from core.bm25 import BM25Index
from core.reranker import Reranker

CACHE_DIR = ROOT_DIR / "data" / "cache_index"
UPLOAD_DIR = ROOT_DIR / "data" / "uploads"
META_FILE = CACHE_DIR / "doc_metadata.json"


class RAGService:
    """
    Singleton service cung cấp toàn bộ năng lực RAG cho FastAPI:
    - Thread-safe nạp và xóa tài liệu
    - Tự động lưu và khôi phục Vector Store & Metadata từ ổ đĩa
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_service()
            return cls._instance

    def _init_service(self):
        self.lock = threading.Lock()
        self.upload_dir = UPLOAD_DIR
        self.cache_dir = CACHE_DIR
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Khởi tạo các module lõi
        self.loader = DocumentLoader()
        self.chunker = MarkdownChunker(chunk_size=600, chunk_overlap=120)
        self.embedding = LocalEmbeddingService(model_name="all-MiniLM-L6-v2")
        self.vector_store = NumPyVectorStore()
        self.generator = RAGGenerator()
        self.reranker = Reranker()
        self._bm25: Optional[BM25Index] = None
        self._bm25_sig = None

        # Metadata lưu trữ {filename: {chunks_count, size_kb, indexed_at, ext}}
        self.doc_metadata: Dict[str, Dict[str, Any]] = {}

        # Khôi phục dữ liệu đã lưu nếu có
        self._load_cache()

    def _load_cache(self):
        """Khôi phục Vector Store và Metadata từ cache nếu tồn tại."""
        try:
            if CACHE_DIR.exists():
                loaded = self.vector_store.load(str(CACHE_DIR), base_name="nexamind_index")
                if loaded and META_FILE.exists():
                    with open(META_FILE, "r", encoding="utf-8") as f:
                        self.doc_metadata = json.load(f)
                    print(f"[RAGService] Đã khôi phục cache thành công: {len(self.doc_metadata)} tài liệu, {self.vector_store.total_chunks} chunks.")
        except Exception as e:
            print(f"[RAGService] Cảnh báo: Không thể tải cache cũ: {e}")

    def _save_cache(self):
        """Lưu Vector Store và Metadata ra đĩa."""
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            self.vector_store.save(str(CACHE_DIR), base_name="nexamind_index")
            with open(META_FILE, "w", encoding="utf-8") as f:
                json.dump(self.doc_metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[RAGService] Lỗi khi lưu cache: {e}")

    # ===== Multi-tenancy: Mỗi chunk và tài liệu thuộc về duy nhất một owner_id =====
    @staticmethod
    def _safe_owner(owner_id: Optional[str]) -> str:
        import re
        clean = (owner_id or "default").strip()
        return re.sub(r"[^a-zA-Z0-9_.@-]", "_", clean)[:100]

    @staticmethod
    def _safe_filename(filename: str) -> str:
        name = os.path.basename((filename or "").replace("\\", "/")).strip()
        if not name or name in (".", ".."):
            raise ValueError("Tên file không hợp lệ.")
        return name

    @staticmethod
    def _mkey(owner_id: str, filename: str) -> str:
        return f"{owner_id}::{filename}"

    def _iter_meta(self, owner_id: Optional[str] = None):
        """Duyệt metadata tài liệu của riêng owner_id được yêu cầu."""
        for key, meta in list(self.doc_metadata.items()):
            if "::" in key:
                o, fname = key.split("::", 1)
            else:
                o, fname = meta.get("owner_id", "default"), key
            # Nếu truyền owner_id, chỉ lấy tài liệu của đúng owner này
            if owner_id is not None:
                if o == owner_id:
                    yield o, fname, meta
            else:
                yield o, fname, meta

    def _allowed_mask(self, owner_id: Optional[str] = None):
        """Mảng boolean cho biết chunk nào thuộc quyền sở hữu của user."""
        import numpy as np
        chunks = self.vector_store.chunks
        if not chunks:
            return np.zeros(0, dtype=bool)
        if owner_id is None:
            return np.ones(len(chunks), dtype=bool)
        return np.array(
            [c.get("owner_id") == owner_id for c in chunks],
            dtype=bool
        )

    def get_stats(self, owner_id: Optional[str] = None) -> Dict[str, Any]:
        """Lấy số liệu thống kê tài liệu và chunks của riêng user."""
        with self.lock:
            docs = []
            for o, name, meta in self._iter_meta(owner_id):
                docs.append({
                    "filename": name,
                    "chunks_count": meta.get("chunks_count", 0),
                    "size_kb": meta.get("size_kb", 0.0),
                    "indexed_at": meta.get("indexed_at", ""),
                    "ext": meta.get("ext", ""),
                    "scope": "personal"
                })
            visible_chunks = int(self._allowed_mask(owner_id).sum()) if not self.vector_store.is_empty else 0

            return {
                "documents_count": len(docs),
                "chunks_count": visible_chunks,
                "vector_dimension": self.vector_store.dimension or self.embedding.dimension,
                "active_model": os.getenv("GEMINI_MODEL", self.generator.DEFAULT_MODEL),
                "is_ready": visible_chunks > 0,
                "documents": docs
            }

    def user_upload_dir(self, owner_id: str) -> Path:
        d = UPLOAD_DIR / self._safe_owner(owner_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_uploaded_file(self, filename: str, content: bytes, owner_id: str = "default") -> Path:
        """Lưu file được upload vào thư mục riêng của user (chống path traversal)."""
        safe_name = self._safe_filename(filename)
        target_path = self.user_upload_dir(owner_id) / safe_name
        with open(target_path, "wb") as f:
            f.write(content)
        return target_path

    def process_and_index_files(self, file_paths: List[Path], owner_id: str = "default") -> Dict[str, Any]:
        """
        Thực hiện toàn bộ quy trình RAG cho một chủ sở hữu:
        1. Đọc file qua MarkItDown
        2. Phân mảnh table-aware
        3. Tạo embedding vector 384D
        4. Nạp vào NumPyVectorStore (gắn owner_id)
        """
        with self.lock:
            total_added_chunks = 0
            indexed_files = []

            for path in file_paths:
                filename = path.name
                ext = path.suffix.lower().lstrip(".")
                size_kb = round(path.stat().st_size / 1024, 1)
                mkey = self._mkey(owner_id, filename)

                try:
                    # Nếu file đã tồn tại trong kho của chính user này, xóa chunk cũ trước
                    if mkey in self.doc_metadata:
                        self.vector_store.remove_source(filename, owner_id=owner_id)

                    doc_data = self.loader.load_document(str(path))
                    if not doc_data.get("content", "").strip():
                        continue

                    start_id = self.vector_store.total_chunks + 1
                    chunks = self.chunker.chunk_document(doc_data, start_chunk_id=start_id)
                    if not chunks:
                        continue

                    for c in chunks:
                        c["owner_id"] = owner_id

                    texts_to_embed = [c.get("content_with_header", c.get("text", "")) for c in chunks]
                    vectors = self.embedding.embed_texts(texts_to_embed)
                    self.vector_store.add_documents(chunks, vectors)

                    self.doc_metadata[mkey] = {
                        "chunks_count": len(chunks),
                        "size_kb": size_kb,
                        "indexed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "ext": ext,
                        "owner_id": owner_id
                    }

                    total_added_chunks += len(chunks)
                    indexed_files.append(filename)

                except Exception as e:
                    print(f"[RAGService] Lỗi khi xử lý file {filename}: {e}")
                    raise

            self._save_cache()

            return {
                "indexed_files": indexed_files,
                "added_chunks": total_added_chunks,
                "total_chunks": self.vector_store.total_chunks,
                "total_documents": len(self.doc_metadata)
            }

    def remove_document(self, filename: str, owner_id: str = "default") -> int:
        """Xóa 1 tài liệu của chính chủ sở hữu."""
        with self.lock:
            removed_count = self.vector_store.remove_source(filename, owner_id=owner_id)
            self.doc_metadata.pop(self._mkey(owner_id, filename), None)
            self._save_cache()
            return removed_count

    def clear_all(self, owner_id: str = "default"):
        """Xóa toàn bộ tài liệu của riêng chủ sở hữu này."""
        with self.lock:
            names = [f for o, f, _ in self._iter_meta(owner_id) if o == owner_id]
            for fname in names:
                self.vector_store.remove_source(fname, owner_id=owner_id)
                self.doc_metadata.pop(self._mkey(owner_id, fname), None)
            self._save_cache()

    def get_document_preview(self, filename: str, owner_id: Optional[str] = None) -> Dict[str, Any]:
        """Lấy các chunk của tài liệu để xem trước trực tiếp trong ứng dụng."""
        with self.lock:
            chunks = []
            for c in self.vector_store.chunks:
                if c.get("source") == filename:
                    c_owner = c.get("owner_id", "default")
                    if owner_id is None or c_owner == owner_id:
                        chunks.append({
                            "chunk_id": c.get("chunk_id"),
                            "section": c.get("section", ""),
                            "text": c.get("text", "")
                        })
            return {
                "filename": filename,
                "chunks_count": len(chunks),
                "chunks": chunks
            }

    def _get_bm25(self) -> BM25Index:
        """Chỉ mục BM25 được dựng lại tự động khi kho chunk thay đổi."""
        chunks = self.vector_store.chunks
        sig = (len(chunks), id(chunks), chunks[-1].get("chunk_id") if chunks else None)
        if self._bm25 is None or self._bm25_sig != sig:
            idx = BM25Index()
            idx.build(chunks)
            self._bm25, self._bm25_sig = idx, sig
        return self._bm25

    def _hybrid_search(
        self,
        query_text: str,
        top_k: int = 4,
        threshold: float = 0.25,
        owner_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid Search: Dense (cosine) + BM25 -> Reciprocal Rank Fusion -> FlashRank re-rank.
        Đảm bảo cô lập dữ liệu theo owner_id (chỉ tìm trong tài liệu của owner hoặc shared).
        """
        import numpy as np
        store = self.vector_store
        if store.is_empty:
            return []

        RRF_K, CAND = 60, 20
        allowed = self._allowed_mask(owner_id)
        if not np.any(allowed):
            return []

        q_vec = self.embedding.embed_query(query_text)
        cos = store.cosine_similarity(q_vec, store.vectors)

        # 1. Dense: top CAND theo ngữ nghĩa thuộc owner hoặc shared
        sorted_indices = np.argsort(cos)[::-1]
        dense_rank = [int(i) for i in sorted_indices if allowed[i] and cos[i] >= min(threshold, 0.15)][:CAND]

        # 2. Sparse: BM25 theo từ khóa nguyên văn thuộc owner hoặc shared
        bm25_all = self._get_bm25().top(query_text, CAND * 3)
        bm25_rank = [int(i) for i in bm25_all if allowed[i]][:CAND]

        # 3. RRF (Reciprocal Rank Fusion)
        fused: Dict[int, float] = {}
        for ranking in (dense_rank, bm25_rank):
            for r, idx in enumerate(ranking):
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (RRF_K + r + 1)
        ordered = sorted(fused, key=fused.get, reverse=True)[:15]

        def build(idx: int) -> Dict[str, Any]:
            c = dict(store.chunks[idx])
            s = float(cos[idx])
            c["score"] = round(s, 4)
            c["score_percent"] = f"{max(0.0, s) * 100:.1f}%"
            c["rrf_score"] = round(fused[idx], 5)
            return c

        candidates = [build(i) for i in ordered]
        if not candidates:
            return []

        # 4. Re-rank (nếu khả dụng), ngược lại dùng thứ tự RRF
        reranked = self.reranker.rerank(query_text, candidates, top_n=top_k)
        return reranked if reranked else candidates[:top_k]

    def _retrieve_smart_chunks(
        self,
        query_text: str,
        top_k: int = 4,
        threshold: float = 0.25,
        owner_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm ngữ nghĩa thông minh:
        - Tự động nới lỏng ngưỡng threshold nếu câu hỏi diễn đạt gián tiếp
        - Bổ sung đoạn giới thiệu / mở đầu của tài liệu cho các câu hỏi tổng quan (chủ đề, tóm tắt)
        """
        if self.vector_store.is_empty:
            return []

        chunks = self._hybrid_search(query_text, top_k=top_k, threshold=threshold, owner_id=owner_id)

        # 2. Xử lý các câu hỏi khái quát / tổng quan (chủ đề chính, tóm tắt, tài liệu nói về gì)
        overview_keywords = ["chủ đề", "tóm tắt", "tổng quan", "nội dung chính", "nói về", "giới thiệu", "về cái gì", "toàn bộ", "ý nghĩa", "mục đích"]
        query_lower = query_text.lower()
        if any(kw in query_lower for kw in overview_keywords):
            target_source = chunks[0]["source"] if chunks else None
            if not target_source and self.vector_store.chunks:
                for c in self.vector_store.chunks:
                    if c.get("owner_id", self.SHARED) in (owner_id or self.SHARED, self.SHARED):
                        target_source = c.get("source")
                        break

            if target_source:
                existing_texts = {c.get("text", "") for c in chunks}
                for c in self.vector_store.chunks:
                    if c.get("source") == target_source:
                        if c.get("text", "") not in existing_texts:
                            c_intro = dict(c)
                            c_intro["score"] = 0.70
                            c_intro["score_percent"] = "Tổng quan"
                            chunks.insert(0, c_intro)
                        break

        return chunks

    def query(
        self,
        query_text: str,
        top_k: int = 4,
        threshold: float = 0.25,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        owner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Truy vấn tìm kiếm và sinh câu trả lời đồng bộ."""
        if self.vector_store.is_empty:
            return {
                "answer": "Kho tài liệu đang trống. Hãy tải file lên và lập chỉ mục trước khi đặt câu hỏi.",
                "sources": [],
                "model_used": model_name or self.generator.DEFAULT_MODEL,
                "elapsed_seconds": 0.0,
                "is_error": True
            }

        t0 = time.time()
        chunks = self._retrieve_smart_chunks(
            query_text=query_text, top_k=top_k, threshold=threshold, owner_id=owner_id
        )

        gen_result = self.generator.generate_answer(
            query=query_text,
            retrieved_chunks=chunks,
            api_key=api_key,
            model_name=model_name
        )
        elapsed = round(time.time() - t0, 2)

        return {
            "answer": gen_result["answer"],
            "sources": gen_result["used_sources"],
            "model_used": gen_result.get("model_used", model_name or self.generator.DEFAULT_MODEL),
            "elapsed_seconds": elapsed,
            "is_error": gen_result["answer"].lstrip().startswith("⚠️")
        }

    def query_stream(
        self,
        query_text: str,
        top_k: int = 4,
        threshold: float = 0.25,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        owner_id: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Truy vấn và stream phản hồi theo từng sự kiện:
        - Event 'sources': Danh sách trích dẫn tìm được
        - Event 'token': Từng token sinh ra từ Gemini
        - Event 'done': Thời gian và thống kê hoàn tất
        """
        if self.vector_store.is_empty:
            yield {
                "event": "error",
                "data": {"message": "Kho tài liệu đang trống. Hãy tải file lên và lập chỉ mục trước."}
            }
            return

        t0 = time.time()
        search_query = query_text
        if chat_history:
            search_query = self.generator.condense_query(query_text, chat_history, api_key=api_key)

        chunks = self._retrieve_smart_chunks(
            query_text=search_query, top_k=top_k, threshold=threshold, owner_id=owner_id
        )

        yield {
            "event": "sources",
            "data": {
                "sources": chunks,
                "count": len(chunks)
            }
        }

        stream_gen = self.generator.generate_answer_stream(
            query=query_text,
            retrieved_chunks=chunks,
            api_key=api_key,
            model_name=model_name,
            chat_history=chat_history
        )

        for chunk_text in stream_gen:
            yield {
                "event": "token",
                "data": {"token": chunk_text}
            }

        elapsed = round(time.time() - t0, 2)
        yield {
            "event": "done",
            "data": {
                "elapsed_seconds": elapsed,
                "model_used": model_name or self.generator.DEFAULT_MODEL
            }
        }
