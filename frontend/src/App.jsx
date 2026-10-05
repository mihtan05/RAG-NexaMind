import React, { useState, useEffect, useRef } from 'react';
import {
  Menu,
  Sun,
  Moon,
  Trash2,
  RefreshCw,
  BrainCircuit,
  MessageSquarePlus,
  LogOut,
  User as UserIcon,
  Download
} from 'lucide-react';
import Sidebar from './components/Sidebar';
import StatCards from './components/StatCards';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import EmptyState from './components/EmptyState';
import AuthScreen from './components/AuthScreen';
import ChatHistory from './components/ChatHistory';
import DocumentViewerModal from './components/DocumentViewerModal';
import {
  getStats,
  uploadFiles,
  indexDocuments,
  deleteDocument,
  clearAllDocuments,
  previewDocument,
  streamChat,
  getConversations,
  createConversation,
  getConversation,
  updateConversation,
  deleteConversation
} from './services/api';

export default function App() {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('nexamind_user');
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [theme, setTheme] = useState('dark');
  const [stats, setStats] = useState({
    documents_count: 0,
    chunks_count: 0,
    vector_dimension: 384,
    active_model: 'gemini-3.8-flash',
    is_ready: false,
    documents: [],
  });

  const [stagedFiles, setStagedFiles] = useState([]);
  const [isIndexing, setIsIndexing] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [messages, setMessages] = useState([]);
  const [previewModalData, setPreviewModalData] = useState(null);
  const [previewInitialQuery, setPreviewInitialQuery] = useState('');

  const [config, setConfig] = useState({
    model_name: 'gemini-3.8-flash',
    top_k: 4,
    threshold: 0.25,
    api_key: null,
  });

  const abortControllerRef = useRef(null);
  const chatScrollRef = useRef(null);

  // ===== Lịch sử hội thoại (lưu SQLite theo người dùng) =====
  const userId = user ? (user.email || user.sub || user.id || user.name || 'guest') : null;
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);

  const loadConversations = async () => {
    if (!userId) return [];
    try {
      const list = await getConversations(userId);
      setConversations(list);
      return list;
    } catch (e) {
      console.error(e);
      return [];
    }
  };

  const mapMessages = (msgs) =>
    msgs.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      sources: m.sources || [],
      model: m.model_used,
      elapsed: m.elapsed_seconds,
      isError: m.is_error,
    }));

  const openConversation = async (id) => {
    if (isStreaming) {
      abortControllerRef.current?.abort();
      setIsStreaming(false);
    }
    try {
      const detail = await getConversation(userId, id);
      setActiveConvId(id);
      setMessages(mapMessages(detail.messages));
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (!userId) return;
    (async () => {
      setHistoryLoading(true);
      const list = await loadConversations();
      if (list.length > 0) {
        await openConversation(list[0].id);
      }
      setHistoryLoading(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const handleRenameConversation = async (id, title) => {
    await updateConversation(userId, id, { title });
    loadConversations();
  };

  const handlePinConversation = async (id, pinned) => {
    await updateConversation(userId, id, { is_pinned: pinned });
    loadConversations();
  };

  const handleDeleteConversation = async (id) => {
    if (!window.confirm('Xóa đoạn chat này?')) return;
    await deleteConversation(userId, id);
    if (id === activeConvId) {
      setActiveConvId(null);
      setMessages([]);
    }
    loadConversations();
  };

  // Khởi tạo và nạp dữ liệu ban đầu từ Backend
  const refreshStats = async () => {
    try {
      const data = await getStats(userId);
      setStats(data);
      if (data.active_model) {
        setConfig((prev) => ({ ...prev, model_name: data.active_model }));
      }
    } catch (err) {
      console.error('Không thể kết nối Backend FastAPI:', err);
    }
  };

  useEffect(() => {
    refreshStats();
  }, [userId]);

  // Tự động cuộn xuống cuối khi có tin nhắn mới hoặc đang stream
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  // Đổi theme Dark / Light
  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    if (next === 'light') {
      document.body.classList.add('nx-light');
    } else {
      document.body.classList.remove('nx-light');
    }
  };

  // Xử lý Lập chỉ mục tài liệu (cô lập 100% theo từng người dùng)
  const handleIndexFiles = async () => {
    if (stagedFiles.length === 0) return;
    setIsIndexing(true);
    const targetOwner = userId || 'default';
    try {
      // 1. Tải file lên server theo owner_id của người dùng
      await uploadFiles(stagedFiles, targetOwner);
      // 2. Chạy quá trình MarkItDown -> Chunker -> Embedding -> Vector Store
      await indexDocuments(null, targetOwner);
      // 3. Cập nhật lại danh sách & thống kê
      await refreshStats();
      setStagedFiles([]);
    } catch (err) {
      alert(`Lỗi khi lập chỉ mục: ${err.message}`);
    } finally {
      setIsIndexing(false);
    }
  };

  // Xử lý Xóa 1 tài liệu
  const handleDeleteDocument = async (filename) => {
    if (!window.confirm(`Bạn có chắc muốn xóa tài liệu "${filename}" khỏi kho của bạn?`)) return;
    try {
      await deleteDocument(filename, userId || 'default');
      await refreshStats();
    } catch (err) {
      alert(`Lỗi khi xóa tài liệu: ${err.message}`);
    }
  };

  // Xử lý Xóa toàn bộ kho tài liệu của user
  const handleClearAll = async () => {
    if (!window.confirm('CẢNH BÁO: Toàn bộ tài liệu trong kho của bạn sẽ bị xóa! Tiếp tục?')) return;
    try {
      await clearAllDocuments(userId || 'default');
      await refreshStats();
    } catch (err) {
      alert(`Lỗi khi dọn kho: ${err.message}`);
    }
  };

  // Mở trình xem trước nội dung tài liệu & phân đoạn
  const handlePreviewDocument = async (filename, initialQuery = '') => {
    try {
      const data = await previewDocument(filename, userId);
      setPreviewModalData(data);
      setPreviewInitialQuery(initialQuery);
    } catch (err) {
      alert(`Không thể nạp xem trước tài liệu: ${err.message}`);
    }
  };

  // Xuất lịch sử đoạn chat ra định dạng Markdown (.md)
  const handleExportChat = () => {
    if (messages.length === 0) return;
    const now = new Date().toLocaleString('vi-VN');
    let md = `# BIÊN BẢN HỘI THOẠI - NEXAMIND AI\n`;
    md += `- **Thời gian xuất**: ${now}\n`;
    md += `- **Người dùng**: ${user?.name || 'Khách'} (${user?.email || 'N/A'})\n`;
    md += `- **Mô hình AI**: ${config.model_name}\n`;
    md += `\n---\n\n`;

    messages.forEach((msg, idx) => {
      if (msg.role === 'user') {
        md += `### 🧑 [${idx + 1}] Người dùng:\n${msg.content}\n\n`;
      } else {
        md += `### 🤖 [${idx + 1}] NexaMind AI:\n${msg.content}\n\n`;
        if (msg.sources && msg.sources.length > 0) {
          md += `> **Trích dẫn nguồn:**\n`;
          msg.sources.forEach((s) => {
            md += `> - **${s.source}** (${s.section || 'Chung'}) - Khớp: ${s.score_percent || 'N/A'}\n`;
            if (s.text) {
              md += `>   *${s.text.replace(/\n/g, ' ')}*\n`;
            }
          });
          md += `\n`;
        }
      }
      md += `---\n\n`;
    });

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `nexamind-chat-${Date.now()}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Bắt đầu cuộc trò chuyện mới
  const handleNewChat = () => {
    if (isStreaming) {
      abortControllerRef.current?.abort();
      setIsStreaming(false);
    }
    setMessages([]);
    setActiveConvId(null);
  };

  // Gửi câu hỏi và Stream câu trả lời
  const handleSendMessage = async (queryText) => {
    if (!queryText.trim() || isStreaming) return;

    const userMsgId = Date.now();
    const aiMsgId = userMsgId + 1;

    const userMessage = {
      id: userMsgId,
      role: 'user',
      content: queryText,
    };

    const aiMessagePlaceholder = {
      id: aiMsgId,
      role: 'assistant',
      content: '',
      sources: [],
      model: config.model_name,
      elapsed: null,
      isError: false,
    };

    setMessages((prev) => [...prev, userMessage, aiMessagePlaceholder]);
    setIsStreaming(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    let convId = activeConvId;
    if (!convId) {
      try {
        const created = await createConversation(userId);
        convId = created.id;
        setActiveConvId(convId);
      } catch (e) {
        console.error(e);
      }
    }

    try {
      await streamChat(
        {
          query: queryText,
          top_k: config.top_k,
          threshold: config.threshold,
          model_name: config.model_name,
          api_key: config.api_key,
          conversation_id: convId,
          user_id: userId,
        },
        {
          signal: controller.signal,
          onSources: (sourcesList) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMsgId ? { ...msg, sources: sourcesList } : msg
              )
            );
          },
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMsgId ? { ...msg, content: msg.content + token } : msg
              )
            );
          },
          onDone: (meta) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMsgId
                  ? {
                      ...msg,
                      elapsed: meta.elapsed_seconds,
                      model: meta.model_used || config.model_name,
                    }
                  : msg
              )
            );
            setIsStreaming(false);
            loadConversations();
          },
          onError: (errMsg) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMsgId
                  ? {
                      ...msg,
                      content: errMsg,
                      isError: true,
                    }
                  : msg
              )
            );
            setIsStreaming(false);
          },
        }
      );
    } catch (err) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMsgId
            ? {
                ...msg,
                content: `Lỗi kết nối: ${err.message}`,
                isError: true,
              }
            : msg
        )
      );
      setIsStreaming(false);
    }
  };

  const handleStopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  };

  const handleFeedback = (messageId, type) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === messageId ? { ...msg, feedback: type } : msg))
    );
  };

  const handleLogout = () => {
    localStorage.removeItem('nexamind_user');
    localStorage.removeItem('nexamind_jwt');
    setUser(null);
  };

  // Chưa đăng nhập -> Render màn hình Đăng nhập & Google Auth theo đúng mẫu thiết kế
  if (!user) {
    return <AuthScreen onLoginSuccess={(u) => setUser(u)} />;
  }

  const hasDocuments = stats.documents_count > 0;

  return (
    <div className="app-container">
      {/* SIDEBAR QUẢN LÝ TÀI LIỆU */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        documents={stats.documents || []}
        stagedFiles={stagedFiles}
        onStagedFilesChange={setStagedFiles}
        onIndexFiles={handleIndexFiles}
        onDeleteDocument={handleDeleteDocument}
        onClearAll={handleClearAll}
        isIndexing={isIndexing}
        config={config}
        onConfigChange={setConfig}
        onPreviewDocument={(fn) => handlePreviewDocument(fn)}
      />

      {historyOpen && (
        <ChatHistory
          conversations={conversations}
          activeId={activeConvId}
          loading={historyLoading}
          onSelect={openConversation}
          onNew={handleNewChat}
          onRename={handleRenameConversation}
          onDelete={handleDeleteConversation}
          onPin={handlePinConversation}
          onClose={() => setHistoryOpen(false)}
        />
      )}

      {/* VÙNG CHÍNH DASHBOARD + CHAT */}
      <main className="main-area">
        {/* HEADER TRÊN CÙNG */}
        <header className="top-header">
          <div className="top-header-left">
            {!sidebarOpen && (
              <button
                className="btn btn-secondary btn-icon-only"
                onClick={() => setSidebarOpen(true)}
                title="Mở thanh bên quản lý tài liệu"
                aria-label="Mở sidebar"
              >
                <Menu size={18} />
              </button>
            )}
            {!historyOpen && (
              <button
                className="btn btn-secondary btn-icon-only"
                onClick={() => setHistoryOpen(true)}
                title="Mở lịch sử trò chuyện"
                aria-label="Mở lịch sử chat"
              >
                <MessageSquarePlus size={18} />
              </button>
            )}
            <div>
              <div className="top-header-title">
                <BrainCircuit size={20} color="var(--nx-primary-light)" />
                <span>Nexa<b>Mind</b> AI</span>
              </div>
              <div className="top-header-desc">
                Hỏi đáp tài liệu thông minh • 100% câu trả lời đều có trích dẫn nguồn
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {messages.length > 0 && (
              <button
                className="btn btn-secondary"
                onClick={handleExportChat}
                title="Tải nội dung hội thoại dạng Markdown (.md)"
              >
                <Download size={16} />
                <span>Xuất chat</span>
              </button>
            )}

            <button
              className="btn btn-secondary"
              onClick={handleNewChat}
              title="Tạo hội thoại mới"
            >
              <MessageSquarePlus size={16} />
              <span>Đoạn chat mới</span>
            </button>

            <button
              className="btn btn-secondary btn-icon-only"
              onClick={toggleTheme}
              title={`Chuyển sang ${theme === 'dark' ? 'Giao diện Sáng' : 'Giao diện Tối'}`}
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>

            {/* Thông tin User & Nút Đăng xuất */}
            {user && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '4px 10px 4px 6px',
                  background: 'var(--nx-surface-2)',
                  borderRadius: '9999px',
                  border: '1px solid var(--nx-border)',
                  marginLeft: '4px'
                }}
              >
                {user.avatar ? (
                  <img
                    src={user.avatar}
                    alt={user.name}
                    style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover' }}
                  />
                ) : (
                  <div
                    style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      background: '#00838f',
                      color: '#fff',
                      fontSize: '11px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 600
                    }}
                  >
                    {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
                  </div>
                )}
                <span
                  style={{
                    fontSize: '0.85rem',
                    fontWeight: 500,
                    color: 'var(--nx-text)',
                    maxWidth: '120px',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}
                  title={`${user.name} (${user.email})`}
                >
                  {user.name}
                </span>
                <button
                  className="btn btn-secondary btn-icon-only"
                  style={{ width: '26px', height: '26px', padding: 0 }}
                  onClick={handleLogout}
                  title="Đăng xuất"
                >
                  <LogOut size={13} />
                </button>
              </div>
            )}
          </div>
        </header>

        {/* 4 THẺ THỐNG KÊ NGANG */}
        <StatCards stats={stats} />

        {/* KHUNG CUỘN NỘI DUNG CHAT */}
        <div className="chat-scroll-area" ref={chatScrollRef}>
          {messages.length === 0 ? (
            <EmptyState
              hasDocuments={hasDocuments}
              onSelectSuggestion={handleSendMessage}
            />
          ) : (
            messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                onFeedback={handleFeedback}
                onPreviewSource={(fn, term) => handlePreviewDocument(fn, term)}
              />
            ))
          )}

          {/* Typing Indicator khi đang chờ token đầu tiên */}
          {isStreaming && messages[messages.length - 1]?.content === '' && (
            <div className="message-bubble-wrapper ai">
              <div className="avatar ai">
                <BrainCircuit size={20} />
              </div>
              <div className="bubble ai">
                <div className="typing-indicator">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <span style={{ fontSize: '0.8rem', color: 'var(--nx-muted)', marginLeft: '6px' }}>
                    Đang tìm trong tài liệu…
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* KHUNG NHẬP CÂU HỎI CỐ ĐỊNH Ở ĐÁY */}
        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={isIndexing}
          isStreaming={isStreaming}
          onStopStreaming={handleStopStreaming}
          hasDocuments={hasDocuments}
        />
      </main>

      {/* MODAL XEM TRƯỚC VĂN BẢN VÀ CÁC PHÂN ĐOẠN (CHUNKS) */}
      {previewModalData && (
        <DocumentViewerModal
          docData={previewModalData}
          initialQuery={previewInitialQuery}
          onClose={() => setPreviewModalData(null)}
        />
      )}
    </div>
  );
}
