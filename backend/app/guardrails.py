"""
NexaMind AI - Rate Limiter & File Upload Guardrails
Bảo vệ hệ thống chống brute-force, quá tải và tải lên tệp tin độc hại.
"""

import hashlib
import time
from collections import defaultdict
from typing import Dict, List, Set
from fastapi import HTTPException

# Whitelist các đuôi file hợp lệ
ALLOWED_EXTENSIONS: Set[str] = {
    ".pdf", ".docx", ".xlsx", ".xls", ".md", ".markdown",
    ".txt", ".csv", ".pptx", ".json"
}

# Giới hạn dung lượng tối đa 30MB
MAX_FILE_SIZE_BYTES = 30 * 1024 * 1024

# Danh sách magic bytes của các tệp tin độc hại nguy hiểm
BLOCKED_MAGIC_PREFIXES = [
    b"MZ",  # Windows Executable / DLL (.exe, .dll)
    b"\x7fELF",  # Linux Executable (.elf, .so)
    b"#!/bin/sh", b"#!/bin/bash",  # Shell scripts
    b"<?php",  # PHP scripts
]


class InMemoryRateLimiter:
    """Sliding-window Rate Limiter theo địa chỉ IP hoặc định danh User."""

    def __init__(self):
        # key -> list of timestamps
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def check_rate_limit(self, key: str, max_requests: int = 30, window_seconds: int = 60):
        now = time.time()
        timestamps = self.requests[key]

        # Xóa các mốc thời gian ngoài cửa sổ trượt
        cutoff = now - window_seconds
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

        if len(timestamps) >= max_requests:
            retry_after = int(window_seconds - (now - timestamps[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Quá giới hạn tần suất ({max_requests} lượt/{window_seconds}s). Vui lòng thử lại sau {retry_after}s.",
                headers={"Retry-After": str(retry_after)}
            )

        timestamps.append(now)


rate_limiter = InMemoryRateLimiter()


def validate_file_guard(filename: str, content: bytes) -> str:
    """
    Kiểm tra file upload:
    - Kích thước không vượt 30MB
    - Đuôi file nằm trong whitelist
    - Không chứa header của file thực thi (.exe, script)
    - Trả về mã băm SHA-256 của file
    """
    if not filename or len(filename.strip()) == 0:
        raise HTTPException(status_code=400, detail="Tên tệp tin không hợp lệ.")

    # Kiểm tra kích thước
    size = len(content)
    if size == 0:
        raise HTTPException(status_code=400, detail=f"Tệp tin '{filename}' rỗng (0 bytes).")
    if size > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"Tệp '{filename}' vượt quá dung lượng tối đa cho phép ({max_mb} MB)."
        )

    # Kiểm tra phần mở rộng
    lower_name = filename.lower()
    has_allowed_ext = any(lower_name.endswith(ext) for ext in ALLOWED_EXTENSIONS)
    if not has_allowed_ext:
        allowed_str = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng tệp '{filename}' không được hỗ trợ. Các định dạng hợp lệ: {allowed_str}"
        )

    # Kiểm tra Magic Bytes chống mã độc
    prefix = content[:16]
    for blocked in BLOCKED_MAGIC_PREFIXES:
        if prefix.startswith(blocked):
            raise HTTPException(
                status_code=400,
                detail=f"Tệp '{filename}' bị từ chối do chứa định dạng mã thực thi không an toàn."
            )

    # Tính SHA-256
    sha256_hash = hashlib.sha256(content).hexdigest()
    return sha256_hash
