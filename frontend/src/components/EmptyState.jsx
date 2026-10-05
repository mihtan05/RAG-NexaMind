import React from 'react';
import { BrainCircuit, Sparkles, FileUp, Cpu, MessageSquare } from 'lucide-react';

const SUGGESTIONS = [
  'Tóm tắt tài liệu',
  'Các ý chính là gì?',
  'Liệt kê số liệu quan trọng',
  'Có những quy định nào cần lưu ý?',
];

export default function EmptyState({ hasDocuments, onSelectSuggestion }) {
  if (!hasDocuments) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">
          <BrainCircuit size={32} />
        </div>
        <h2 className="empty-state-title">Chào mừng bạn đến với NexaMind AI</h2>
        <p className="empty-state-desc">
          Hệ thống hỏi đáp tài liệu chính xác, phân tích chuyên sâu và tự động dẫn nguồn trích dẫn minh bạch.
        </p>

        <div className="steps-grid">
          <div className="step-card">
            <FileUp size={22} color="var(--nx-primary-light)" style={{ marginBottom: '8px' }} />
            <div className="step-num">Bước 1</div>
            <div className="step-text">Tải file tài liệu lên từ thanh bên trái</div>
          </div>

          <div className="step-card">
            <Cpu size={22} color="var(--nx-accent)" style={{ marginBottom: '8px' }} />
            <div className="step-num">Bước 2</div>
            <div className="step-text">Bấm "Xử lý & Lập chỉ mục" vào Vector Store</div>
          </div>

          <div className="step-card">
            <MessageSquare size={22} color="var(--nx-success)" style={{ marginBottom: '8px' }} />
            <div className="step-num">Bước 3</div>
            <div className="step-text">Đặt câu hỏi và nhận câu trả lời có trích dẫn</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="empty-state">
      <div className="empty-state-icon">
        <Sparkles size={32} />
      </div>
      <h2 className="empty-state-title">Kho tài liệu đã sẵn sàng!</h2>
      <p className="empty-state-desc">
        Hãy đặt bất kỳ câu hỏi nào về nội dung trong tài liệu, hoặc bắt đầu với một trong các câu hỏi gợi ý:
      </p>

      <div className="suggestion-chips-wrapper">
        {SUGGESTIONS.map((text, idx) => (
          <button
            key={idx}
            className="chip"
            onClick={() => onSelectSuggestion(text)}
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}
