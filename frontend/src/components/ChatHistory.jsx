import React, { useState } from 'react';
import { MessageSquarePlus, MessageSquare, Pencil, Trash2, Pin, Check, X, PanelLeftClose } from 'lucide-react';
import './ChatHistory.css';

function groupLabel(iso) {
  const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diffDays = Math.floor((startToday - new Date(d.getFullYear(), d.getMonth(), d.getDate())) / 86400000);
  if (diffDays <= 0) return 'Hôm nay';
  if (diffDays === 1) return 'Hôm qua';
  if (diffDays <= 7) return '7 ngày trước';
  return 'Cũ hơn';
}

export default function ChatHistory({
  conversations,
  activeId,
  loading,
  onSelect,
  onNew,
  onRename,
  onDelete,
  onPin,
  onClose,
}) {
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState('');

  const pinned = conversations.filter((c) => c.is_pinned);
  const groups = {};
  conversations
    .filter((c) => !c.is_pinned)
    .forEach((c) => {
      const g = groupLabel(c.updated_at);
      (groups[g] = groups[g] || []).push(c);
    });

  const startEdit = (c) => {
    setEditingId(c.id);
    setDraft(c.title);
  };
  const commitEdit = () => {
    if (draft.trim()) onRename(editingId, draft.trim());
    setEditingId(null);
  };

  const renderItem = (c) => (
    <div
      key={c.id}
      className={`ch-item ${c.id === activeId ? 'active' : ''}`}
      onClick={() => editingId !== c.id && onSelect(c.id)}
    >
      <MessageSquare size={14} className="ch-icon" />
      {editingId === c.id ? (
        <>
          <input
            className="ch-input"
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitEdit();
              if (e.key === 'Escape') setEditingId(null);
            }}
            onClick={(e) => e.stopPropagation()}
          />
          <button className="ch-act" onClick={(e) => { e.stopPropagation(); commitEdit(); }}><Check size={13} /></button>
          <button className="ch-act" onClick={(e) => { e.stopPropagation(); setEditingId(null); }}><X size={13} /></button>
        </>
      ) : (
        <>
          <span className="ch-title" title={c.title}>{c.title}</span>
          <span className="ch-actions">
            <button className="ch-act" title="Ghim" onClick={(e) => { e.stopPropagation(); onPin(c.id, !c.is_pinned); }}>
              <Pin size={13} fill={c.is_pinned ? 'currentColor' : 'none'} />
            </button>
            <button className="ch-act" title="Đổi tên" onClick={(e) => { e.stopPropagation(); startEdit(c); }}>
              <Pencil size={13} />
            </button>
            <button className="ch-act danger" title="Xóa" onClick={(e) => { e.stopPropagation(); onDelete(c.id); }}>
              <Trash2 size={13} />
            </button>
          </span>
        </>
      )}
    </div>
  );

  return (
    <aside className="chat-history">
      <div className="ch-header">
        <button className="ch-new" onClick={onNew}>
          <MessageSquarePlus size={16} />
          <span>Đoạn chat mới</span>
        </button>
        <button className="ch-act" onClick={onClose} title="Ẩn lịch sử"><PanelLeftClose size={16} /></button>
      </div>

      <div className="ch-list">
        {loading && (
          <>
            <div className="ch-skeleton" />
            <div className="ch-skeleton" />
            <div className="ch-skeleton" />
          </>
        )}
        {!loading && conversations.length === 0 && (
          <div className="ch-empty">Chưa có đoạn chat nào</div>
        )}
        {pinned.length > 0 && (
          <>
            <div className="ch-group">Đã ghim</div>
            {pinned.map(renderItem)}
          </>
        )}
        {['Hôm nay', 'Hôm qua', '7 ngày trước', 'Cũ hơn'].map(
          (g) =>
            groups[g] && (
              <React.Fragment key={g}>
                <div className="ch-group">{g}</div>
                {groups[g].map(renderItem)}
              </React.Fragment>
            )
        )}
      </div>
    </aside>
  );
}
