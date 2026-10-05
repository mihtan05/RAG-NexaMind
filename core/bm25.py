"""
Module: core/bm25.py
Chức năng: Tìm kiếm từ khóa BM25 (Okapi) thuần Python/NumPy, không cần thư viện ngoài.
Tokenize thân thiện tiếng Việt: unigram + bigram, có bản không dấu để bắt từ khóa gõ thiếu dấu.
"""

import math
import re
import unicodedata
from collections import Counter
from typing import List, Dict, Any

import numpy as np

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def strip_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def tokenize(text: str) -> List[str]:
    """Unigram + bigram (đã bỏ dấu, lowercase) để khớp tốt cả tiếng Việt lẫn mã số/viết tắt."""
    words = _TOKEN_RE.findall(strip_accents(text.lower()))
    bigrams = [f"{a}_{b}" for a, b in zip(words, words[1:])]
    return words + bigrams


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_freqs: List[Counter] = []
        self.doc_lens: np.ndarray = np.zeros(0)
        self.idf: Dict[str, float] = {}
        self.avgdl = 0.0

    def build(self, chunks: List[Dict[str, Any]]) -> None:
        self.doc_freqs = []
        df: Counter = Counter()
        for c in chunks:
            text = f"{c.get('section', '')} {c.get('text', '')}"
            tf = Counter(tokenize(text))
            self.doc_freqs.append(tf)
            df.update(tf.keys())
        n = len(chunks)
        self.doc_lens = np.array([sum(tf.values()) for tf in self.doc_freqs], dtype=np.float32)
        self.avgdl = float(self.doc_lens.mean()) if n else 0.0
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: str) -> np.ndarray:
        n = len(self.doc_freqs)
        out = np.zeros(n, dtype=np.float32)
        if n == 0:
            return out
        q_tokens = set(tokenize(query))
        for i, tf in enumerate(self.doc_freqs):
            dl = self.doc_lens[i]
            s = 0.0
            for t in q_tokens:
                f = tf.get(t)
                if not f:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1.0))
                s += self.idf.get(t, 0.0) * f * (self.k1 + 1) / denom
            out[i] = s
        return out

    def top(self, query: str, k: int = 20) -> List[int]:
        sc = self.scores(query)
        idx = np.argsort(sc)[::-1][:k]
        return [int(i) for i in idx if sc[i] > 0]
