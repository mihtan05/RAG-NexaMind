"""
Module: core/chunker.py
Chức năng: Thuật toán băm nhỏ văn bản Markdown có cấu trúc (Markdown-aware Chunking).
Nhận diện tiêu đề (#, ##, ###), chia nhỏ theo ranh giới câu có gối đầu (sliding window + overlap)
và tự động gán tiêu đề ngữ cảnh vào đầu mỗi chunk (Contextual Header Prefixing).
"""

import re
from typing import List, Dict, Any


class MarkdownChunker:
    """
    Bộ băm nhỏ văn bản Markdown thông minh:
    1. Phân tích cấu trúc phân cấp theo thẻ tiêu đề (#, ##, ###).
    2. Cắt văn bản theo câu/đoạn, tránh ngắt ngang từ hay câu quan trọng.
    3. Gối đầu (overlap) để không làm mất ngữ cảnh giữa các đoạn tiếp giáp.
    4. Gán tiền tố tiêu đề mục (Contextual Header Prefixing) vào từng chunk.
    """

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 120):
        """
        Khởi tạo chunker với các tham số:
        Args:
            chunk_size: Độ dài mục tiêu tối đa của một chunk (tính theo ký tự).
            chunk_overlap: Độ dài gối đầu giữa 2 chunk liền kề (tính theo ký tự).
        """
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap phải nhỏ hơn chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Pattern nhận diện các cấp tiêu đề Markdown: # Tiêu đề, ## Mục con,...
        self.header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def _split_into_sections(self, text: str) -> List[Dict[str, str]]:
        """
        Phân rã văn bản Markdown thành các mục (sections) dựa theo tiêu đề #, ##, ###.
        Nếu không có tiêu đề nào, toàn bộ văn bản được coi là một mục 'Nội dung chung'.
        """
        lines = text.splitlines(keepends=True)
        sections: List[Dict[str, str]] = []

        current_header = "Nội dung chung"
        current_content_lines: List[str] = []

        for line in lines:
            header_match = self.header_pattern.match(line.strip())
            if header_match:
                # Nếu đã có nội dung tích lũy trước đó, lưu thành 1 section
                content_str = "".join(current_content_lines).strip()
                if content_str:
                    sections.append({
                        "section": current_header,
                        "content": content_str
                    })
                    current_content_lines = []

                # Cập nhật tiêu đề hiện tại (ví dụ: "Giới thiệu", "Điều khoản thanh toán")
                heading_level = len(header_match.group(1))
                heading_title = header_match.group(2).strip()
                current_header = heading_title
            else:
                current_content_lines.append(line)

        # Lưu section cuối cùng
        content_str = "".join(current_content_lines).strip()
        if content_str:
            sections.append({
                "section": current_header,
                "content": content_str
            })

        return sections

    def _split_text_with_overlap(self, text: str) -> List[str]:
        """
        Chia một đoạn văn dài thành các khối văn bản thỏa mãn chunk_size và chunk_overlap,
        tôn trọng ranh giới đoạn văn (\n\n) và ranh giới câu (dấu chấm, chấm hỏi, chấm than).
        """
        if len(text) <= self.chunk_size:
            return [text]

        # Tách theo đoạn hoặc câu để tránh cắt vụn
        # Phân tách ưu tiên: 2 dòng trống -> 1 dòng -> dấu câu
        delimiters_pattern = r"(?<=[.!?;\n])\s+"
        parts = re.split(delimiters_pattern, text)
        parts = [p.strip() for p in parts if p.strip()]

        if not parts:
            return [text]

        chunks: List[str] = []
        current_chunk_parts: List[str] = []
        current_len = 0

        i = 0
        while i < len(parts):
            part = parts[i]
            part_len = len(part)

            # Nếu một phần tử đơn lẻ vượt quá chunk_size (ví dụ bảng dài hoặc chuỗi dài)
            if part_len > self.chunk_size:
                # Nếu đang có các câu trước đó, lưu lại trước
                if current_chunk_parts:
                    chunk_text = " ".join(current_chunk_parts).strip()
                    if chunk_text:
                        chunks.append(chunk_text)
                    current_chunk_parts = []
                    current_len = 0

                # Cắt trực tiếp theo ký tự
                start = 0
                while start < part_len:
                    end = min(start + self.chunk_size, part_len)
                    sub_part = part[start:end].strip()
                    if sub_part:
                        chunks.append(sub_part)
                    start += (self.chunk_size - self.chunk_overlap)
                i += 1
                continue

            # Kiểm tra xem thêm part mới có vượt quá chunk_size không
            if current_len + part_len + 1 <= self.chunk_size:
                current_chunk_parts.append(part)
                current_len += part_len + 1
                i += 1
            else:
                # Đã đạt kích thước chunk
                if current_chunk_parts:
                    chunk_text = " ".join(current_chunk_parts).strip()
                    chunks.append(chunk_text)

                # Tạo overlap bằng cách lùi lại các câu gần cuối
                overlap_parts: List[str] = []
                overlap_len = 0
                for prev_part in reversed(current_chunk_parts):
                    if overlap_len + len(prev_part) + 1 <= self.chunk_overlap:
                        overlap_parts.insert(0, prev_part)
                        overlap_len += len(prev_part) + 1
                    else:
                        break

                current_chunk_parts = overlap_parts.copy()
                current_len = sum(len(p) + 1 for p in current_chunk_parts)

                # Nạp part hiện tại
                current_chunk_parts.append(part)
                current_len += part_len + 1
                i += 1

        # Nạp các câu còn lại
        if current_chunk_parts:
            chunk_text = " ".join(current_chunk_parts).strip()
            if chunk_text and (not chunks or chunk_text != chunks[-1]):
                chunks.append(chunk_text)

        return chunks

    _table_row = re.compile(r"^\s*\|.*\|\s*$")

    def _split_text_smart(self, text: str) -> List[str]:
        """
        Table-aware: tách bảng Markdown ra khỏi văn bản thường.
        - Bảng vừa chunk_size: giữ nguyên 1 chunk.
        - Bảng dài: cắt theo hàng, lặp lại hàng tiêu đề + dòng phân cách ở mỗi chunk.
        """
        lines = text.splitlines()
        if not any(self._table_row.match(l) for l in lines):
            return self._split_text_with_overlap(text)

        blocks: List[Any] = []  # (is_table, [lines])
        for line in lines:
            is_t = bool(self._table_row.match(line))
            if blocks and blocks[-1][0] == is_t:
                blocks[-1][1].append(line)
            else:
                blocks.append((is_t, [line]))

        result: List[str] = []
        for is_table, blines in blocks:
            if not is_table:
                prose = "\n".join(blines).strip()
                if prose:
                    result.extend(self._split_text_with_overlap(prose))
                continue

            full = "\n".join(blines)
            if len(full) <= self.chunk_size:
                result.append(full)
                continue

            has_sep = len(blines) > 1 and re.match(r"^\s*\|[\s:\-|]+\|\s*$", blines[1])
            header = blines[:2] if has_sep else blines[:1]
            body = blines[len(header):]
            head_text = "\n".join(header)
            cur: List[str] = []
            cur_len = len(head_text)
            for row in body:
                if cur and cur_len + len(row) + 1 > self.chunk_size:
                    result.append(head_text + "\n" + "\n".join(cur))
                    cur, cur_len = [], len(head_text)
                cur.append(row)
                cur_len += len(row) + 1
            if cur:
                result.append(head_text + "\n" + "\n".join(cur))
        return result or [text]

    def chunk_document(self, doc_data: Dict[str, Any], start_chunk_id: int = 1) -> List[Dict[str, Any]]:
        """
        Băm tài liệu hoàn chỉnh thành danh sách chunks có cấu trúc.

        Args:
            doc_data: Dict từ DocumentLoader gồm: filename, content, extension, filepath.
            start_chunk_id: Số thứ tự bắt đầu gán cho chunk_id.

        Returns:
            List các chunk dict:
            {
                "chunk_id": int,
                "source": str,
                "section": str,
                "text": str,
                "content_with_header": str  # Văn bản hoàn chỉnh được dùng để embedding
            }
        """
        filename = doc_data.get("filename", "unknown_file")
        content = doc_data.get("content", "")

        if not content:
            return []

        sections = self._split_into_sections(content)
        chunks: List[Dict[str, Any]] = []
        current_id = start_chunk_id

        for sec in sections:
            section_title = sec["section"]
            sec_content = sec["content"]

            sub_chunks = self._split_text_smart(sec_content)
            for sub_text in sub_chunks:
                # Tiền tố ngữ cảnh tiêu đề (Contextual Header Prefixing)
                header_prefix = f"[Mục: {section_title}]\n"
                full_text_with_header = f"{header_prefix}{sub_text}"

                chunks.append({
                    "chunk_id": current_id,
                    "source": filename,
                    "section": section_title,
                    "text": sub_text,
                    "content_with_header": full_text_with_header
                })
                current_id += 1

        return chunks
