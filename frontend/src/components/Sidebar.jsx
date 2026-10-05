import React, { useRef, useState } from 'react';
import {
  BrainCircuit,
  UploadCloud,
  FileText,
  Trash2,
  RefreshCw,
  ChevronLeft,
  Settings,
  CheckCircle2,
  AlertCircle,
  Eye
} from 'lucide-react';

export default function Sidebar({
  isOpen,
  onToggle,
  documents,
  stagedFiles,
  onStagedFilesChange,
  onIndexFiles,
  onDeleteDocument,
  onClearAll,
  isIndexing,
  config,
  onConfigChange,
  onPreviewDocument
}) {
  const fileInputRef = useRef(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(Array.from(e.target.files));
    }
  };

  const addFiles = (newFiles) => {
    // Lọc trùng tên
    const existingNames = new Set(stagedFiles.map((f) => f.name));
    const unique = newFiles.filter((f) => !existingNames.has(f.name));
    onStagedFilesChange([...stagedFiles, ...unique]);
  };

  const removeStagedFile = (index) => {
    const updated = stagedFiles.filter((_, i) => i !== index);
    onStagedFilesChange(updated);
  };

  return (
    <aside className={`sidebar ${isOpen ? '' : 'collapsed'}`}>
      <div className="sidebar-header">
        <div className="brand-wrapper">
          <div className="brand-icon">
            <BrainCircuit size={20} />
          </div>
          <div>
            <div className="brand-title">
              Nexa<b>Mind</b>
            </div>
            <div className="brand-subtitle">Hệ thống RAG Tài liệu</div>
          </div>
        </div>
        <button
          className="btn btn-secondary btn-icon-only"
          onClick={onToggle}
          title="Thu gọn thanh bên"
          aria-label="Thu gọn"
        >
          <ChevronLeft size={18} />
        </button>
      </div>

      <div className="sidebar-body">
        {/* VÙNG UPLOAD TÀI LIỆU */}
        <div>
          <div style={{ marginBottom: '8px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--nx-text)' }}>
              Tải lên tài liệu
            </span>
          </div>

          <div
            className={`dropzone ${isDragOver ? 'drag-active' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              multiple
              style={{ display: 'none' }}
              accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.html,.txt,.csv,.md"
            />
            <div className="dropzone-icon">
              <UploadCloud size={28} />
            </div>
            <div className="dropzone-text">Kéo thả file hoặc bấm để chọn</div>
            <div className="dropzone-sub">
              Hỗ trợ PDF, DOCX, XLSX, PPTX, TXT, MD
            </div>
          </div>
        </div>

        {/* DANH SÁCH FILE ĐÃ CHỌN CHỜ LẬP CHỈ MỤC */}
        {stagedFiles.length > 0 && (
          <div>
            <div
              style={{
                fontSize: '0.8rem',
                fontWeight: 600,
                color: 'var(--nx-muted)',
                marginBottom: '8px',
                display: 'flex',
                justifyContent: 'space-between'
              }}
            >
              <span>File đã chọn ({stagedFiles.length})</span>
              <button
                className="btn-danger-ghost"
                style={{ fontSize: '0.75rem', cursor: 'pointer', border: 'none', background: 'transparent' }}
                onClick={() => onStagedFilesChange([])}
              >
                Hủy tất cả
              </button>
            </div>

            <div style={{ maxHeight: '140px', overflowY: 'auto' }}>
              {stagedFiles.map((file, idx) => (
                <div key={idx} className="doc-card" style={{ padding: '8px 10px' }}>
                  <div className="doc-card-info">
                    <FileText size={16} color="var(--nx-primary-light)" />
                    <span className="doc-name">{file.name}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--nx-muted)' }}>
                      {(file.size / 1024).toFixed(0)} KB
                    </span>
                    <button
                      className="btn-danger-ghost"
                      onClick={() => removeStagedFile(idx)}
                      title="Bỏ chọn file"
                      style={{ padding: '2px', border: 'none', background: 'transparent' }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <button
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '10px' }}
              onClick={onIndexFiles}
              disabled={isIndexing}
            >
              <RefreshCw size={16} className={isIndexing ? 'animate-spin' : ''} />
              {isIndexing ? 'Đang xử lý & Lập chỉ mục…' : 'Xử lý & Lập chỉ mục'}
            </button>
          </div>
        )}

        {/* DANH SÁCH TÀI LIỆU TRONG KHO */}
        <div style={{ flex: 1 }}>
          <div
            style={{
              fontSize: '0.85rem',
              fontWeight: 600,
              color: 'var(--nx-text)',
              marginBottom: '10px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <span>Tài liệu trong kho ({documents.length})</span>
            {documents.length > 0 && (
              <button
                className="btn-danger-ghost"
                onClick={onClearAll}
                title="Xóa toàn bộ kho tài liệu"
                style={{ fontSize: '0.75rem', cursor: 'pointer', border: 'none', background: 'transparent' }}
              >
                Xóa tất cả
              </button>
            )}
          </div>

          {documents.length === 0 ? (
            <div
              style={{
                padding: '24px 16px',
                textAlign: 'center',
                color: 'var(--nx-muted)',
                fontSize: '0.8rem',
                border: '1px dashed var(--nx-border)',
                borderRadius: 'var(--nx-r-md)'
              }}
            >
              Kho tài liệu đang trống. Hãy kéo thả tài liệu vào ô phía trên.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {documents.map((doc, idx) => (
                <div key={idx} className="doc-card">
                  <div
                    className="doc-card-info"
                    onClick={() => onPreviewDocument?.(doc.filename)}
                    style={{ cursor: 'pointer', minWidth: 0, flex: 1 }}
                    title="Bấm để xem các phân đoạn tài liệu"
                  >
                    <FileText size={16} color="var(--nx-primary-light)" style={{ flexShrink: 0 }} />
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div className="doc-name" title={doc.filename}>
                        {doc.filename}
                      </div>
                      <div className="doc-meta">
                        <span className="doc-badge">{doc.chunks_count} chunks</span>
                        <span>•</span>
                        <span>{doc.size_kb} KB</span>
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '2px', flexShrink: 0 }}>
                    <button
                      className="btn-secondary"
                      onClick={() => onPreviewDocument?.(doc.filename)}
                      title={`Xem trước ${doc.filename}`}
                      style={{ padding: '4px', width: '26px', height: '26px', border: 'none', background: 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
                    >
                      <Eye size={14} />
                    </button>
                    <button
                      className="btn-danger-ghost"
                      onClick={() => onDeleteDocument(doc.filename)}
                      title={`Xóa ${doc.filename}`}
                      style={{ padding: '4px', width: '26px', height: '26px', border: 'none', background: 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
