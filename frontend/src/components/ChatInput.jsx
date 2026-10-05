import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, Square } from 'lucide-react';

export default function ChatInput({
  onSendMessage,
  disabled,
  isStreaming,
  onStopStreaming,
  hasDocuments
}) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled || isStreaming) return;
    onSendMessage(trimmed);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleInputChange = (e) => {
    setText(e.target.value);
    // Auto-adjust height
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  const placeholder = !hasDocuments
    ? 'Hãy tải tài liệu lên và lập chỉ mục trước khi đặt câu hỏi'
    : isStreaming
    ? 'NexaMind đang phân tích tài liệu và trả lời…'
    : 'Nhập câu hỏi về tài liệu của bạn (Nhấn Enter để gửi)…';

  return (
    <div className="chat-input-bar">
      <div className="chat-input-wrapper">
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || (!hasDocuments && !isStreaming)}
          className="chat-input"
        />

        {isStreaming ? (
          <button
            className="chat-send-btn"
            onClick={onStopStreaming}
            title="Dừng sinh câu trả lời"
            style={{ background: 'var(--nx-surface-3)' }}
          >
            <Square size={16} fill="currentColor" />
          </button>
        ) : (
          <button
            className="chat-send-btn"
            onClick={handleSubmit}
            disabled={!text.trim() || disabled || !hasDocuments}
            title="Gửi câu hỏi"
          >
            <ArrowUp size={18} />
          </button>
        )}
      </div>
    </div>
  );
}
