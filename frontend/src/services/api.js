/**
 * NexaMind AI - API Client Service
 * Kết nối với FastAPI Backend (REST & SSE Streaming) kèm JWT Auth & Multi-tenancy
 */

function getAuthHeaders(extra = {}) {
  const token = localStorage.getItem('nexamind_jwt');
  const headers = { ...extra };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

const jsonOrThrow = async (res, msg) => {
  if (!res.ok) {
    let detail = '';
    try {
      const errJson = await res.json();
      detail = errJson.detail || errJson.message || '';
    } catch (e) {
      detail = res.statusText;
    }
    throw new Error(`${msg}: ${detail}`);
  }
  return await res.json();
};

export async function loginUser(payload) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await jsonOrThrow(res, 'Đăng nhập không thành công');
  if (data.access_token) {
    localStorage.setItem('nexamind_jwt', data.access_token);
  }
  return data;
}

export async function getStats(ownerId = null) {
  const url = ownerId ? `/api/stats?owner_id=${encodeURIComponent(ownerId)}` : '/api/stats';
  const res = await fetch(url, { headers: getAuthHeaders() });
  return jsonOrThrow(res, 'Lỗi tải thống kê');
}

export async function getDocuments(ownerId = null) {
  const url = ownerId ? `/api/documents?owner_id=${encodeURIComponent(ownerId)}` : '/api/documents';
  const res = await fetch(url, { headers: getAuthHeaders() });
  return jsonOrThrow(res, 'Lỗi tải danh sách tài liệu');
}

export async function previewDocument(filename, ownerId = null) {
  const url = ownerId
    ? `/api/documents/${encodeURIComponent(filename)}/preview?owner_id=${encodeURIComponent(ownerId)}`
    : `/api/documents/${encodeURIComponent(filename)}/preview`;
  const res = await fetch(url, { headers: getAuthHeaders() });
  return jsonOrThrow(res, 'Lỗi nạp xem trước tài liệu');
}

export async function uploadFiles(files, ownerId = null) {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }
  if (ownerId) {
    formData.append('owner_id', ownerId);
  }
  const res = await fetch('/api/documents/upload', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
  });
  return jsonOrThrow(res, 'Lỗi tải lên tài liệu');
}

export async function indexDocuments(filenames = null, ownerId = null) {
  const res = await fetch('/api/documents/index', {
    method: 'POST',
    headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      filenames: filenames || null,
      owner_id: ownerId || null,
    }),
  });
  return jsonOrThrow(res, 'Lỗi lập chỉ mục tài liệu');
}

export async function deleteDocument(filename, ownerId = null) {
  const url = ownerId
    ? `/api/documents/${encodeURIComponent(filename)}?owner_id=${encodeURIComponent(ownerId)}`
    : `/api/documents/${encodeURIComponent(filename)}`;
  const res = await fetch(url, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  return jsonOrThrow(res, 'Lỗi xóa tài liệu');
}

export async function clearAllDocuments(ownerId = null) {
  const url = ownerId
    ? `/api/documents?owner_id=${encodeURIComponent(ownerId)}`
    : `/api/documents`;
  const res = await fetch(url, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  return jsonOrThrow(res, 'Lỗi dọn kho tài liệu');
}

export async function getConversations(userId) {
  const res = await fetch(`/api/conversations?user_id=${encodeURIComponent(userId)}`, {
    headers: getAuthHeaders(),
  });
  return jsonOrThrow(res, 'Lỗi tải lịch sử chat');
}

export async function createConversation(userId, title = 'Đoạn chat mới') {
  const res = await fetch('/api/conversations', {
    method: 'POST',
    headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ user_id: userId, title }),
  });
  return jsonOrThrow(res, 'Lỗi tạo đoạn chat');
}

export async function getConversation(userId, convId) {
  const res = await fetch(`/api/conversations/${convId}?user_id=${encodeURIComponent(userId)}`, {
    headers: getAuthHeaders(),
  });
  return jsonOrThrow(res, 'Lỗi tải đoạn chat');
}

export async function updateConversation(userId, convId, patch) {
  const res = await fetch(`/api/conversations/${convId}?user_id=${encodeURIComponent(userId)}`, {
    method: 'PATCH',
    headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(patch),
  });
  return jsonOrThrow(res, 'Lỗi cập nhật đoạn chat');
}

export async function deleteConversation(userId, convId) {
  const res = await fetch(`/api/conversations/${convId}?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  return jsonOrThrow(res, 'Lỗi xóa đoạn chat');
}

/**
 * Gửi câu hỏi và nhận SSE Stream từ endpoint /api/chat/stream
 */
export async function streamChat(payload, { onSources, onToken, onDone, onError, signal }) {
  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
      signal,
    });

    if (!response.ok) {
      let detail = '';
      try {
        const errJson = await response.json();
        detail = errJson.detail || errJson.message || '';
      } catch (e) {
        detail = response.statusText;
      }
      throw new Error(`Máy chủ phản hồi mã lỗi ${response.status}: ${detail}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      let currentEvent = 'message';
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
          currentEvent = 'message';
          continue;
        }

        if (trimmed.startsWith('event:')) {
          currentEvent = trimmed.replace('event:', '').trim();
        } else if (trimmed.startsWith('data:')) {
          const jsonStr = trimmed.replace('data:', '').trim();
          try {
            const data = JSON.parse(jsonStr);
            if (currentEvent === 'sources') {
              onSources?.(data.sources || []);
            } else if (currentEvent === 'token') {
              onToken?.(data.token || '');
            } else if (currentEvent === 'done') {
              onDone?.(data);
            } else if (currentEvent === 'error') {
              onError?.(data.message || 'Lỗi không xác định từ server');
            }
          } catch (e) {
            console.error('Không thể parse dữ liệu SSE JSON:', jsonStr, e);
          }
        }
      }
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      console.log('User cancelled stream');
      return;
    }
    onError?.(err.message || 'Lỗi kết nối tới máy chủ');
  }
}
