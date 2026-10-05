"""
Core Package cho Hệ thống RAG "From Scratch"
Bao gồm:
- DocumentLoader: Nạp tài liệu đa định dạng bằng Microsoft MarkItDown
- MarkdownChunker: Băm nhỏ Markdown thông minh kèm ngữ cảnh tiêu đề
- LocalEmbeddingService: Tạo vector nhúng cục bộ bằng sentence-transformers
- NumPyVectorStore: Vector Store và tìm kiếm tương đồng Cosine bằng NumPy thuần
- RAGGenerator: Ghép prompt chống ảo giác và gọi LLM API (Google Gemini)
"""

from .loader import DocumentLoader
from .chunker import MarkdownChunker
from .embedding import LocalEmbeddingService
from .vector_store import NumPyVectorStore
from .generator import RAGGenerator

__all__ = [
    "DocumentLoader",
    "MarkdownChunker",
    "LocalEmbeddingService",
    "NumPyVectorStore",
    "RAGGenerator",
]
