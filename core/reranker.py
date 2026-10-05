"""
Module: core/reranker.py
Chức năng: Tái xếp hạng (re-rank) kết quả bằng FlashRank (cross-encoder ONNX chạy CPU).
Tải lười (lazy) và tự động bỏ qua nếu thiếu thư viện/model -> hệ thống vẫn chạy bằng RRF.
"""

import os
from typing import List, Dict, Any, Optional

MODEL_NAME = os.getenv("RERANK_MODEL", "ms-marco-MultiBERT-L-12")
CACHE_DIR = os.getenv("RERANK_CACHE", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rerank_models"))


class Reranker:
    def __init__(self):
        self._ranker = None
        self._failed = os.getenv("DISABLE_RERANK", "0") == "1"

    def _load(self):
        if self._ranker is not None or self._failed:
            return self._ranker
        try:
            from flashrank import Ranker
            os.makedirs(CACHE_DIR, exist_ok=True)
            self._ranker = Ranker(model_name=MODEL_NAME, cache_dir=CACHE_DIR)
            print(f"[Reranker] Đã nạp FlashRank: {MODEL_NAME}")
        except Exception as e:
            print(f"[Reranker] Bỏ qua re-rank ({e})")
            self._failed = True
        return self._ranker

    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_n: int) -> Optional[List[Dict[str, Any]]]:
        """Trả về top_n chunk đã xếp lại, hoặc None nếu re-ranker không khả dụng."""
        ranker = self._load()
        if ranker is None or not chunks:
            return None
        try:
            from flashrank import RerankRequest
            passages = [
                {"id": i, "text": c.get("text", ""), "meta": {}} for i, c in enumerate(chunks)
            ]
            result = ranker.rerank(RerankRequest(query=query, passages=passages))
            out = []
            for r in result[:top_n]:
                c = dict(chunks[r["id"]])
                c["rerank_score"] = round(float(r["score"]), 4)
                out.append(c)
            return out
        except Exception as e:
            print(f"[Reranker] Lỗi khi re-rank: {e}")
            return None
