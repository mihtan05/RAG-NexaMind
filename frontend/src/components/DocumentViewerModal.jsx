import React, { useState, useEffect } from 'react';
import { X, Search, FileText, Layers, Hash } from 'lucide-react';
import './DocumentViewerModal.css';

export default function DocumentViewerModal({ docData, onClose, initialQuery = '' }) {
  const [searchTerm, setSearchTerm] = useState(initialQuery);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!docData) return null;

  const chunks = docData.chunks || [];
  const filteredChunks = searchTerm.trim()
    ? chunks.filter(
        (c) =>
          (c.text && c.text.toLowerCase().includes(searchTerm.toLowerCase())) ||
          (c.section && c.section.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    : chunks;

  const highlightMatches = (text, term) => {
    if (!term || !term.trim()) return text;
    const parts = text.split(new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
    return parts.map((part, i) =>
      part.toLowerCase() === term.toLowerCase() ? (
        <mark key={i} className="doc-highlight">{part}</mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="doc-modal-overlay" onClick={onClose}>
      <div className="doc-modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Header Modal */}
        <div className="doc-modal-header">
          <div className="doc-modal-title-wrap">
            <div className="doc-modal-icon">
              <FileText size={20} color="var(--nx-primary-light, #00e5ff)" />
            </div>
            <div>
              <h3 className="doc-modal-filename">{docData.filename}</h3>
              <div className="doc-modal-meta">
                <span><Layers size={13} /> {chunks.length} phân đoạn (chunks)</span>
              </div>
            </div>
          </div>
          <button className="doc-modal-close" onClick={onClose} title="Đóng (ESC)">
            <X size={18} />
          </button>
        </div>

        {/* Thanh tìm kiếm nội dung trong tài liệu */}
        <div className="doc-modal-search-bar">
          <Search size={16} className="doc-search-icon" />
          <input
            type="text"
            placeholder="Tìm kiếm từ khóa bên trong các phân đoạn..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="doc-search-input"
            autoFocus
          />
          {searchTerm && (
            <button className="doc-search-clear" onClick={() => setSearchTerm('')}>
              <X size={14} />
            </button>
          )}
        </div>

        {/* Danh sách các đoạn trích (Chunks) */}
        <div className="doc-modal-content">
          {filteredChunks.length === 0 ? (
            <div className="doc-modal-empty">
              Không tìm thấy đoạn nội dung nào khớp với từ khóa "{searchTerm}".
            </div>
          ) : (
            filteredChunks.map((chunk, index) => (
              <div key={chunk.chunk_id || index} className="doc-chunk-card">
                <div className="doc-chunk-header">
                  <span className="doc-chunk-badge">
                    <Hash size={12} /> Chunk #{chunk.chunk_id || index + 1}
                  </span>
                  <span className="doc-chunk-section" title={chunk.section}>
                    Mục: {chunk.section || 'Nội dung chung'}
                  </span>
                </div>
                <div className="doc-chunk-text">
                  {highlightMatches(chunk.text, searchTerm)}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="doc-modal-footer">
          <span>Hiển thị {filteredChunks.length} / {chunks.length} phân đoạn</span>
          <button className="btn btn-secondary" onClick={onClose}>Đóng</button>
        </div>
      </div>
    </div>
  );
}
