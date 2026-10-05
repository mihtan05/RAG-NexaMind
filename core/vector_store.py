"""
Module: core/vector_store.py
Chức năng: Kho lưu trữ Vector Store và thuật toán tìm kiếm Cosine Similarity bằng NumPy thuần.
Không phụ thuộc vào bất kỳ thư viện cơ sở dữ liệu vector bên thứ ba nào (như FAISS, Chroma, Pinecone).
"""

import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np


class NumPyVectorStore:
    """
    Vector Store thuần NumPy lưu trữ trong bộ nhớ RAM:
    - Quản lý ma trận vector (N x Dim) và danh sách metadata tương ứng.
    - Thuật toán Cosine Similarity chuẩn toán học:
      score = (a . B) / (||a|| * ||B||)
    - Hỗ trợ lưu / nạp cache dạng file nén .npz và .pkl để tái sử dụng.
    """

    def __init__(self):
        """Khởi tạo kho vector trống."""
        self.vectors: Optional[np.ndarray] = None  # Ma trận N x Dim
        self.chunks: List[Dict[str, Any]] = []      # Danh sách metadata của từng chunk

    @property
    def is_empty(self) -> bool:
        """Kiểm tra kho vector có rỗng không."""
        return self.vectors is None or len(self.chunks) == 0

    @property
    def total_chunks(self) -> int:
        """Tổng số chunks đang lưu trong kho."""
        return len(self.chunks)

    @property
    def dimension(self) -> Optional[int]:
        """Số chiều vector."""
        if self.vectors is not None and self.vectors.ndim == 2:
            return self.vectors.shape[1]
        return None

    def add_documents(self, chunks: List[Dict[str, Any]], vectors: np.ndarray) -> None:
        """
        Nạp thêm chunks và các vector nhúng tương ứng vào kho.

        Args:
            chunks: Danh sách metadata của từng chunk (source, section, text,...).
            vectors: Ma trận NumPy 2D kích thước (M, Dim) tương ứng với số chunk.
        """
        if len(chunks) == 0 or vectors.size == 0:
            return

        if len(chunks) != vectors.shape[0]:
            raise ValueError(f"Số lượng chunk ({len(chunks)}) không khớp với số vector ({vectors.shape[0]}).")

        vectors_f32 = vectors.astype(np.float32)

        if self.vectors is None:
            self.vectors = vectors_f32
            self.chunks = list(chunks)
        else:
            if self.vectors.shape[1] != vectors_f32.shape[1]:
                raise ValueError(
                    f"Kích thước vector không khớp: hiện tại là {self.vectors.shape[1]}, "
                    f"đầu vào mới là {vectors_f32.shape[1]}."
                )
            self.vectors = np.vstack([self.vectors, vectors_f32])
            self.chunks.extend(chunks)

    @staticmethod
    def cosine_similarity(vec_a: np.ndarray, mat_b: np.ndarray) -> np.ndarray:
        """
        Tính toán độ tương đồng Cosine giữa 1 query vector (1D) và một ma trận vector (2D).
        Công thức toán học:
            score = (vec_a . B^T) / (||vec_a|| * ||B||)

        Args:
            vec_a: Vector 1D có kích thước (Dim,)
            mat_b: Ma trận 2D có kích thước (N, Dim)

        Returns:
            np.ndarray: Mảng 1D kích thước (N,) chứa điểm tương đồng trong khoảng [-1, 1].
        """
        # Đảm bảo vec_a là 1D
        vec_a_1d = np.squeeze(vec_a)
        if vec_a_1d.ndim != 1 or mat_b.ndim != 2:
            raise ValueError("vec_a phải là vector 1D và mat_b phải là ma trận 2D.")

        # Tích vô hướng (dot product) giữa ma trận và vector: shape (N,)
        dot_product = np.dot(mat_b, vec_a_1d)

        # Tính chuẩn L2 (Euclidean norm)
        norm_a = np.linalg.norm(vec_a_1d)
        norm_b = np.linalg.norm(mat_b, axis=1)

        # Tránh chia cho 0 với epsilon rất nhỏ
        denominator = norm_a * norm_b
        epsilon = 1e-9
        denominator = np.where(denominator < epsilon, epsilon, denominator)

        similarity_scores = dot_product / denominator
        # Clip về khoảng [-1.0, 1.0] để tránh sai số số thực
        return np.clip(similarity_scores, -1.0, 1.0)

    def search(self, query_vector: np.ndarray, top_k: int = 3, threshold: float = 0.25) -> List[Dict[str, Any]]:
        """
        Tìm kiếm các đoạn văn bản (chunks) tương đồng nhất với câu hỏi.

        Args:
            query_vector: Vector 1D biểu diễn câu hỏi.
            top_k: Số lượng chunk tối đa muốn lấy về.
            threshold: Ngưỡng lọc độ tương đồng tối thiểu (0.0 đến 1.0).

        Returns:
            Danh sách chunk đã sắp xếp giảm dần theo điểm tương đồng,
            mỗi chunk có thêm trường:
                - score: float (từ 0.0 đến 1.0)
                - score_percent: str (ví dụ "86.4%")
        """
        if self.is_empty:
            return []

        # Tính toán điểm Cosine Similarity cho tất cả chunks trong kho
        scores = self.cosine_similarity(query_vector, self.vectors)

        # Sắp xếp các chỉ số giảm dần theo điểm số
        sorted_indices = np.argsort(scores)[::-1]

        results: List[Dict[str, Any]] = []
        for idx in sorted_indices:
            score_val = float(scores[idx])

            # Lọc theo ngưỡng similarity
            if score_val < threshold:
                continue

            chunk_copy = dict(self.chunks[idx])
            chunk_copy["score"] = round(score_val, 4)
            chunk_copy["score_percent"] = f"{max(0.0, score_val) * 100:.1f}%"
            results.append(chunk_copy)

            if len(results) >= top_k:
                break

        return results

    def clear(self) -> None:
        """Xóa toàn bộ dữ liệu trong kho."""
        self.vectors = None
        self.chunks = []

    def remove_source(self, source: str, owner_id: Optional[str] = None) -> int:
        """
        Xóa tất cả chunk (và vector tương ứng) thuộc một tài liệu (và owner nếu có).
        Trả về số chunk đã xóa.
        """
        if self.is_empty:
            return 0

        def should_remove(c):
            if c.get("source") != source:
                return False
            if owner_id is not None:
                return c.get("owner_id", "shared") == owner_id
            return True

        keep = [i for i, c in enumerate(self.chunks) if not should_remove(c)]
        removed = len(self.chunks) - len(keep)
        if not keep:
            self.clear()
        elif removed:
            self.vectors = self.vectors[keep]
            self.chunks = [self.chunks[i] for i in keep]
        return removed

    def save(self, directory: str, base_name: str = "vector_index") -> None:
        """Lưu trạng thái Vector Store ra đĩa (dạng .npz cho vector và .pkl cho chunks)."""
        target_dir = Path(directory)
        target_dir.mkdir(parents=True, exist_ok=True)

        if self.vectors is not None:
            vec_path = target_dir / f"{base_name}_vectors.npz"
            np.savez_compressed(vec_path, vectors=self.vectors)

        chunks_path = target_dir / f"{base_name}_chunks.pkl"
        with open(chunks_path, "wb") as f:
            pickle.dump(self.chunks, f)

    def load(self, directory: str, base_name: str = "vector_index") -> bool:
        """Nạp trạng thái Vector Store từ đĩa."""
        target_dir = Path(directory)
        vec_path = target_dir / f"{base_name}_vectors.npz"
        chunks_path = target_dir / f"{base_name}_chunks.pkl"

        if not vec_path.exists() or not chunks_path.exists():
            return False

        with np.load(vec_path) as data:
            self.vectors = data["vectors"]

        with open(chunks_path, "rb") as f:
            self.chunks = pickle.load(f)

        return True
