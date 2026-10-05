import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  User,
  BrainCircuit,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  ThumbsUp,
  ThumbsDown,
  BookOpen,
  Clock,
  AlertTriangle
} from 'lucide-react';

export default function ChatMessage({ message, onFeedback, onPreviewSource }) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [feedback, setFeedback] = useState(message.feedback || null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch (err) {
      console.error('Không thể sao chép:', err);
    }
  };

  const handleFeedback = (type) => {
    const next = feedback === type ? null : type;
    setFeedback(next);
    onFeedback?.(message.id, next);
  };

  return (
    <div className={`message-bubble-wrapper ${isUser ? 'user' : 'ai'}`}>
      {!isUser && (
        <div className="avatar ai">
          <BrainCircuit size={20} />
        </div>
      )}

      <div className="message-content">
        <div className={`bubble ${isUser ? 'user' : 'ai'}`}>
          {isUser ? (
            message.content
          ) : message.isError ? (
            <div style={{ display: 'flex', gap: '8px', color: 'var(--nx-error)' }}>
              <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{message.content}</div>
            </div>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Nguồn trích dẫn (chỉ dành cho AI) */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="sources-container">
            <div
              className="sources-header"
              onClick={() => setSourcesOpen(!sourcesOpen)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <BookOpen size={14} />
                <span>Nguồn tham khảo ({message.sources.length} đoạn trích)</span>
              </div>
              {sourcesOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </div>

            {sourcesOpen && (
              <div className="sources-list">
                {message.sources.map((src, idx) => (
                  <div
                    key={idx}
                    className="source-item"
                    onClick={() => onPreviewSource?.(src.source, src.text ? src.text.slice(0, 40) : '')}
                    style={{ cursor: onPreviewSource ? 'pointer' : 'default' }}
                    title="Bấm để mở trình xem tài liệu"
                  >
                    <div className="source-item-meta">
                      <span>📄 {src.source || 'Tài liệu'} • {src.section || 'Chung'}</span>
                      <span className="source-score">Độ khớp: {src.score_percent || 'N/A'}</span>
                    </div>
                    <div className="source-text">{src.text}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Action bar & metadata (chỉ dành cho AI) */}
        {!isUser && !message.isError && (
          <div className="message-actions">
            <button className="action-btn" onClick={handleCopy} title="Sao chép nội dung">
              {copied ? <Check size={13} color="var(--nx-success)" /> : <Copy size={13} />}
              <span>{copied ? 'Đã chép' : 'Sao chép'}</span>
            </button>

            <button
              className="action-btn"
              onClick={() => handleFeedback('up')}
              style={{ color: feedback === 'up' ? 'var(--nx-primary-light)' : undefined }}
              title="Câu trả lời hữu ích"
            >
              <ThumbsUp size={13} />
            </button>

            <button
              className="action-btn"
              onClick={() => handleFeedback('down')}
              style={{ color: feedback === 'down' ? 'var(--nx-error)' : undefined }}
              title="Câu trả lời chưa tốt"
            >
              <ThumbsDown size={13} />
            </button>

            {message.elapsed && (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', marginLeft: 'auto' }}>
                <Clock size={12} />
                {message.elapsed}s • {message.model || 'Gemini'}
              </span>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="avatar user">
          <User size={20} />
        </div>
      )}
    </div>
  );
}
