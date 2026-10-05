"""
Module: core/generator.py
Chức năng: Ghép Context từ các chunk thu được (Retrieved Chunks), xây dựng Prompt chống ảo giác
nghiêm ngặt và gọi LLM API (Google Gemini qua SDK google-genai) để sinh câu trả lời kèm trích dẫn nguồn.
"""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Tải biến môi trường từ .env
load_dotenv()


class RAGGenerator:
    """
    Module phụ trách quá trình sinh câu trả lời (Generation) có kiểm soát:
    - Bắt buộc LLM tuân thủ chặt chẽ tài liệu (Grounding).
    - Cấm bịa đặt / suy diễn thông tin ngoài tài liệu (Anti-Hallucination).
    - Tự động gắn nhãn trích dẫn nguồn [Nguồn: file - Mục: section].
    """

    DEFAULT_MODEL = "gemini-3.8-flash"

    SYSTEM_INSTRUCTION = (
        "Bạn là trợ lý AI NexaMind - chuyên gia phân tích và hỏi đáp tài liệu chuyên sâu, chính xác và trung thực.\n"
        "Nhiệm vụ của bạn là trả lời câu hỏi của người dùng dựa trên thông tin được cung cấp trong thẻ <CONTEXT> "
        "(bao gồm nội dung các đoạn trích, tiêu đề mục và tên tài liệu nguồn).\n\n"
        "QUY TẮC PHÂN TÍCH & TRẢ LỜI QUAN TRỌNG:\n"
        "1. TỔNG HỢP & KHÁI QUÁT HÓA (RẤT QUAN TRỌNG):\n"
        "   - Khi người dùng hỏi các câu hỏi khái quát như: 'chủ đề chính là gì', 'tài liệu nói về gì', 'tóm tắt', 'nội dung cơ bản': "
        "Hãy xâu chuỗi, tổng hợp các đề mục, tên file và nội dung các đoạn trích trong <CONTEXT> để khái quát và đúc kết chủ đề chính của tài liệu một cách thông minh, rõ ràng.\n"
        "   - Hiểu các từ đồng nghĩa, từ viết tắt và cách diễn đạt tương đương thay vì chỉ tìm khớp từ khóa nguyên văn.\n"
        "2. TRUNG THỰC & BÁM SÁT DỮ LIỆU (GROUNDING):\n"
        "   - Mọi thông tin, số liệu, định nghĩa phải dựa trên ngữ cảnh được cung cấp. KHÔNG bịa đặt thông tin không có cơ sở ngoài phạm vi tài liệu.\n"
        "   - Nếu câu hỏi chỉ được trả lời một phần trong <CONTEXT>, hãy trả lời đầy đủ phần đó và chỉ rõ phần tài liệu chưa đề cập.\n"
        "3. KHI NÀO MỚI TỪ CHỐI:\n"
        "   - Chỉ từ chối khi câu hỏi HOÀN TOÀN KHÔNG LIÊN QUAN đến bất kỳ nội dung nào trong <CONTEXT> "
        "(ví dụ tài liệu về công nghệ/quản lý dự án nhưng hỏi về công thức nấu ăn, thời tiết hôm nay).\n"
        "   - Khi từ chối, giải thích rõ: 'Các đoạn trích tài liệu hiện tại không đề cập đến [nội dung câu hỏi].'\n"
        "4. ĐỊNH DẠNG & TRÍCH DẪN:\n"
        "   - Đính kèm trích dẫn chuẩn: [Nguồn: {filename} - Mục: {section}] sau mỗi luận điểm hoặc đoạn thông tin.\n"
        "   - Trình bày dạng Markdown mạch lạc, có gạch đầu dòng và in đậm điểm then chốt để người dùng dễ theo dõi."
    )

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        Khởi tạo Generator.

        Args:
            api_key: Google Gemini API Key. Nếu không truyền sẽ đọc từ os.getenv("GEMINI_API_KEY").
            model_name: Tên model Gemini. Mặc định đọc từ GEMINI_MODEL hoặc 'gemini-2.5-flash'.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)
        self._client = None

    def _get_client(self, override_key: Optional[str] = None):
        """Khởi tạo Google GenAI Client."""
        key = override_key or self.api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "Chưa cấu hình GEMINI_API_KEY! "
                "Vui lòng nhập API Key trên giao diện hoặc thêm vào file .env."
            )
        from google import genai
        return genai.Client(api_key=key)

    def condense_query(
        self,
        query: str,
        chat_history: List[Dict[str, str]],
        api_key: Optional[str] = None
    ) -> str:
        """Viết lại câu hỏi phụ thuộc ngữ cảnh thành câu hỏi độc lập. Lỗi -> trả về câu gốc."""
        if not chat_history:
            return query
        try:
            lines = []
            for m in chat_history[-6:]:
                who = "Người dùng" if m.get("role") == "user" else "Trợ lý"
                lines.append(f"{who}: {m.get('content', '')[:500]}")
            prompt = (
                "Dựa vào lịch sử hội thoại, viết lại CÂU HỎI MỚI thành một câu hỏi độc lập, đầy đủ chủ ngữ, "
                "giữ nguyên ngôn ngữ. Nếu đã độc lập thì giữ nguyên. Chỉ trả về đúng câu hỏi, không giải thích.\n\n"
                f"LỊCH SỬ:\n{chr(10).join(lines)}\n\nCÂU HỎI MỚI: {query}"
            )
            client = self._get_client(override_key=api_key)
            for model in ["gemini-2.5-flash-lite", "gemini-3.8-flash"]:
                try:
                    resp = client.models.generate_content(model=model, contents=prompt)
                    text = (resp.text or "").strip().strip('"')
                    if text:
                        return text
                except Exception:
                    continue
        except Exception:
            pass
        return query

    def _build_context_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        """Ghép danh sách các đoạn trích dẫn thành văn bản ngữ cảnh có cấu trúc."""
        context_parts = []
        for i, chunk in enumerate(chunks, start=1):
            source = chunk.get("source", "Tài liệu")
            section = chunk.get("section", "Chung")
            score_pct = chunk.get("score_percent", "N/A")
            text = chunk.get("text", "").strip()

            part = (
                f"--- [Đoạn trích {i}] ---\n"
                f"Tên file: {source}\n"
                f"Mục: {section}\n"
                f"Độ khớp (Relevance): {score_pct}\n"
                f"Nội dung:\n{text}\n"
            )
            context_parts.append(part)

        return "\n".join(context_parts)

    def generate_answer(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Thực hiện sinh câu trả lời dựa trên query và các chunk được truy xuất từ Vector Store.

        Args:
            query: Câu hỏi người dùng
            retrieved_chunks: Danh sách các chunk có độ tương đồng cao nhất
            api_key: Tùy chọn truyền API Key trực tiếp (ví dụ từ giao diện Streamlit)
            model_name: Tùy chọn model Gemini

        Returns:
            Dict chứa:
                - answer: Câu trả lời từ LLM
                - used_sources: Danh sách các chunk được dùng làm context
                - context_text: Chuỗi context đầy đủ
                - model_used: Model đã gọi
        """
        # Trường hợp không tìm thấy đoạn văn bản nào đạt ngưỡng
        if not retrieved_chunks:
            return {
                "answer": (
                    "Xin lỗi, hệ thống không tìm thấy đoạn nội dung nào trong tài liệu phù hợp với câu hỏi của bạn. "
                    "(Có thể do tài liệu chưa có thông tin này hoặc ngưỡng lọc tương đồng Threshold đang đặt quá cao)."
                ),
                "used_sources": [],
                "context_text": "",
                "model_used": self.model_name
            }

        context_text = self._build_context_prompt(retrieved_chunks)

        user_content = (
            f"<CONTEXT>\n{context_text}\n</CONTEXT>\n\n"
            f"Dựa vào thông tin được cung cấp trong <CONTEXT> ở trên, hãy trả lời câu hỏi sau một cách chi tiết và chính xác:\n"
            f"CÂU HỎI: {query.strip()}\n\n"
            f"Yêu cầu:\n"
            f"- Nếu câu hỏi hỏi về chủ đề chính, tóm tắt hoặc ý nghĩa tổng thể: Hãy đúc kết từ nội dung, các đề mục và tên tài liệu trong <CONTEXT>.\n"
            f"- Đính kèm trích dẫn [Nguồn: {{filename}} - Mục: {{section}}] sau các ý trả lời."
        )

        target_model = model_name or self.model_name
        client = self._get_client(override_key=api_key)

        # Danh sách mô hình dự phòng nếu mô hình chính bị quá tải tạm thời (503 UNAVAILABLE / 429)
        candidate_models = [target_model]
        for alt in ["gemini-3.8-flash", "gemini-2.5-flash-lite", "gemini-3-flash-preview", "gemini-flash-latest"]:
            if alt not in candidate_models:
                candidate_models.append(alt)

        last_error = None
        for current_model in candidate_models:
            try:
                from google.genai import types

                response = client.models.generate_content(
                    model=current_model,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=self.SYSTEM_INSTRUCTION,
                        temperature=0.2,
                    )
                )

                answer_text = response.text if response and response.text else "Không nhận được phản hồi từ mô hình."

                return {
                    "answer": answer_text,
                    "used_sources": retrieved_chunks,
                    "context_text": context_text,
                    "model_used": current_model
                }

            except Exception as e:
                last_error = e
                err_str = str(e)
                # Nếu gặp lỗi quá tải tạm thời (503/429), tự động chuyển sang model dự phòng
                if any(code in err_str for code in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"]):
                    continue
                else:
                    break

        error_msg = str(last_error) if last_error else "Lỗi không xác định."
        return {
            "answer": f"⚠️ Đã xảy ra lỗi khi gọi Gemini API ({target_model}):\n\n`{error_msg}`\n\n"
                      f"Gợi ý khắc phục:\n"
                      f"- Kiểm tra lại GEMINI_API_KEY trong file `.env` hoặc trên Sidebar.\n"
                      f"- Đảm bảo bạn có kết nối mạng ổn định.",
            "used_sources": retrieved_chunks,
            "context_text": context_text,
            "model_used": target_model
        }

    def generate_answer_stream(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ):
        """
        Stream từng token/chunk của câu trả lời từ Gemini API trong thời gian thực.
        Phục vụ cho Server-Sent Events (SSE) trên FastAPI hoặc stream generators.

        Yields:
            str: Đoạn text (token/chunk) vừa được mô hình sinh ra.
        """
        if not retrieved_chunks:
            yield (
                "Xin lỗi, hệ thống không tìm thấy đoạn nội dung nào trong tài liệu phù hợp với câu hỏi của bạn. "
                "(Có thể do tài liệu chưa có thông tin này hoặc ngưỡng lọc tương đồng Threshold đang đặt quá cao)."
            )
            return

        context_text = self._build_context_prompt(retrieved_chunks)
        history_text = ""
        if chat_history:
            lines = []
            for m in chat_history[-6:]:
                who = "Người dùng" if m.get("role") == "user" else "Trợ lý"
                lines.append(f"{who}: {m.get('content', '')[:800]}")
            history_text = "<HISTORY>\n" + "\n".join(lines) + "\n</HISTORY>\n\n"
        user_content = (
            f"{history_text}"
            f"<CONTEXT>\n{context_text}\n</CONTEXT>\n\n"
            f"Dựa vào thông tin được cung cấp trong <CONTEXT> ở trên, hãy trả lời câu hỏi sau một cách chi tiết và chính xác:\n"
            f"CÂU HỎI: {query.strip()}\n\n"
            f"Yêu cầu:\n"
            f"- Nếu câu hỏi hỏi về chủ đề chính, tóm tắt hoặc ý nghĩa tổng thể: Hãy đúc kết từ nội dung, các đề mục và tên tài liệu trong <CONTEXT>.\n"
            f"- Đính kèm trích dẫn [Nguồn: {{filename}} - Mục: {{section}}] sau các ý trả lời."
        )

        target_model = model_name or self.model_name
        client = self._get_client(override_key=api_key)

        candidate_models = [target_model]
        for alt in ["gemini-3.8-flash", "gemini-2.5-flash-lite", "gemini-3-flash-preview", "gemini-flash-latest"]:
            if alt not in candidate_models:
                candidate_models.append(alt)

        from google.genai import types
        success = False
        last_error = None
        for current_model in candidate_models:
            try:
                response_stream = client.models.generate_content_stream(
                    model=current_model,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=self.SYSTEM_INSTRUCTION,
                        temperature=0.2,
                    )
                )
                for chunk in response_stream:
                    if chunk and chunk.text:
                        yield chunk.text
                success = True
                break
            except Exception as e:
                last_error = e
                err_str = str(e)
                if any(code in err_str for code in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"]):
                    continue
                else:
                    break

        if not success:
            err_msg = str(last_error) if last_error else "Lỗi không xác định."
            yield f"\n\n⚠️ Đã xảy ra lỗi khi gọi Gemini API ({target_model}): {err_msg}"

