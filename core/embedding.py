"""
Module: core/embedding.py
Chức năng: Dịch chuyển văn bản thành vector biểu diễn ngữ nghĩa (Embedding)
sử dụng mô hình mã nguồn mở chạy local hoàn toàn miễn phí (sentence-transformers).
"""

import os
from typing import List, Union, Optional
import numpy as np


class LocalEmbeddingService:
    """
    Dịch vụ tạo Embedding chạy hoàn toàn trên máy cục bộ (Offline / Local)
    sử dụng thư viện sentence-transformers.
    """

    DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self, model_name: Optional[str] = None):
        """
        Khởi tạo mô hình Embedding.

        Args:
            model_name: Tên mô hình trên HuggingFace Hub, ví dụ:
                        - "all-MiniLM-L6-v2" (nhẹ, nhanh, rất tốt cho tiếng Anh và tổng quan)
                        - "paraphrase-multilingual-MiniLM-L12-v2" (hỗ trợ đa ngôn ngữ, tiếng Việt tốt)
                        - "BAAI/bge-m3" (rất mạnh mẽ cho RAG đa ngữ)
        """
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL_NAME", self.DEFAULT_MODEL_NAME)
        self._model = None

    @property
    def model(self):
        """Lazy load model để khởi động ứng dụng nhanh chóng chỉ khi bắt đầu vector hóa."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print(f"[Embedding] Đang tải mô hình local: {self.model_name}...")
            self._model = SentenceTransformer(self.model_name)
            print("[Embedding] Tải mô hình thành công.")
        return self._model

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Tạo ma trận vector 2D cho danh sách các đoạn văn bản.

        Args:
            texts: Danh sách các chuỗi văn bản (chunks).
            batch_size: Kích thước batch khi encode.

        Returns:
            np.ndarray: Ma trận 2D kích thước (N, Dim) kiểu float32.
        """
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        # encode trả về mảng numpy, chuẩn hóa L2 vector
        vectors = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 5,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return vectors.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Tạo vector 1D cho câu hỏi của người dùng.

        Args:
            query: Chuỗi câu hỏi.

        Returns:
            np.ndarray: Vector 1D kích thước (Dim,) kiểu float32.
        """
        if not query or not query.strip():
            raise ValueError("Câu hỏi query không được để trống.")

        vector = self.model.encode(
            query.strip(),
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        # Đảm bảo trả về vector 1D
        vector = np.squeeze(vector).astype(np.float32)
        return vector

    @property
    def dimension(self) -> int:
        """Trả về số chiều vector nhúng của mô hình (mặc định 384 cho all-MiniLM-L6-v2)."""
        if self._model is not None:
            return self._model.get_sentence_embedding_dimension()
        return 384
