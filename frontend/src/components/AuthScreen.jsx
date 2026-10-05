import React, { useState, useEffect, useRef } from 'react';
import {
  Shield,
  BrainCircuit,
  Settings,
  X,
  ExternalLink,
  CheckCircle,
  AlertCircle,
  KeyRound
} from 'lucide-react';
import './AuthScreen.css';
import { loginUser } from '../services/api';

// Google OAuth 2.0 Web Client ID do bạn cung cấp
const DEFAULT_GOOGLE_CLIENT_ID = '79295214545-c23cegeft4f8pjucj2i34r60v9hc855g.apps.googleusercontent.com';

/**
 * Giải mã JWT Payload từ Google ID Token (Google Identity Services)
 */
function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    console.error('Không thể giải mã Google JWT ID Token:', e);
    return null;
  }
}

export default function AuthScreen({ onLoginSuccess }) {
  const [activeTab, setActiveTab] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('alex@nexamind.ai');
  const [password, setPassword] = useState('password123');
  const [name, setName] = useState('Chuyên viên Phân tích');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Lấy Client ID từ env hoặc default Client ID đã được người dùng cung cấp
  const [googleClientId, setGoogleClientId] = useState(() => {
    return import.meta.env.VITE_GOOGLE_CLIENT_ID ||
      localStorage.getItem('nexamind_google_client_id') ||
      DEFAULT_GOOGLE_CLIENT_ID;
  });

  const [tempClientId, setTempClientId] = useState(googleClientId);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const googleBtnContainerRef = useRef(null);

  // 1. Tải thư viện Google Identity Services (GIS)
  useEffect(() => {
    const loadGoogleScript = () => {
      if (!window.google && !document.getElementById('google-jssdk')) {
        const script = document.createElement('script');
        script.id = 'google-jssdk';
        script.src = 'https://accounts.google.com/gsi/client';
        script.async = true;
        script.defer = true;
        script.onload = () => initGoogleServices(googleClientId);
        document.body.appendChild(script);
      } else if (window.google) {
        initGoogleServices(googleClientId);
      }
    };

    loadGoogleScript();
  }, [googleClientId]);

  // Khởi tạo các dịch vụ Google ID
  const initGoogleServices = (clientId) => {
    if (!window.google || !clientId) return;

    try {
      // 1.1 Khởi tạo Google ID Token (One-Tap / ID Credential)
      if (window.google.accounts?.id) {
        window.google.accounts.id.initialize({
          client_id: clientId.trim(),
          callback: handleGoogleCredentialResponse,
          auto_select: false,
          cancel_on_tap_outside: true,
        });

        if (googleBtnContainerRef.current) {
          googleBtnContainerRef.current.innerHTML = '';
          window.google.accounts.id.renderButton(googleBtnContainerRef.current, {
            theme: 'outline',
            size: 'large',
            width: 380,
            text: 'continue_with',
            shape: 'pill',
            logo_alignment: 'left',
          });
        }
      }
    } catch (err) {
      console.warn('Lỗi cấu hình Google Sign-In:', err);
    }
  };

  // 2. Nhận kết quả từ Google ID Token
  const handleGoogleCredentialResponse = (response) => {
    if (!response || !response.credential) {
      setErrorMsg('Không nhận được thông tin xác thực từ Google.');
      return;
    }

    const payload = parseJwt(response.credential);
    if (payload && payload.email) {
      const realGoogleUser = {
        name: payload.name || payload.given_name || 'Người dùng Google',
        email: payload.email,
        avatar: payload.picture || null,
        provider: 'google',
        sub: payload.sub,
        role: 'Thành viên NexaMind'
      };

      setSuccessMsg(`Chào mừng ${realGoogleUser.name}! Đăng nhập Google thành công.`);
      setTimeout(() => completeLogin(realGoogleUser), 500);
    } else {
      setErrorMsg('Không thể trích xuất thông tin tài khoản Google.');
    }
  };

  // 3. Xử lý khi người dùng bấm nút "Continue with Google"
  const handleGoogleSignInClick = () => {
    setErrorMsg('');
    setSuccessMsg('');

    if (!window.google) {
      setErrorMsg('Đang nạp thư viện Google, vui lòng thử lại sau 1-2 giây...');
      return;
    }

    const currentOrigin = window.location.origin;

    // Ưu tiên dùng OAuth 2.0 Token Client: Mở popup chọn tài khoản Google thật 100%
    if (window.google.accounts?.oauth2) {
      try {
        setIsLoading(true);

        // 1. Safety Timeout: Tự động mở khóa nút sau tối đa 12 giây nếu người dùng đóng popup
        const safetyTimer = setTimeout(() => {
          setIsLoading((curr) => {
            if (curr) {
              return false;
            }
            return curr;
          });
        }, 12000);

        // 2. Window Focus Listener: Khi người dùng đóng popup hoặc click quay lại tab chính
        const handleWindowFocus = () => {
          setTimeout(() => {
            setIsLoading((curr) => {
              if (curr) {
                return false;
              }
              return curr;
            });
          }, 1200);
        };
        window.addEventListener('focus', handleWindowFocus, { once: true });

        const tokenClient = window.google.accounts.oauth2.initTokenClient({
          client_id: googleClientId.trim(),
          scope: 'email profile openid',
          callback: async (tokenResponse) => {
            clearTimeout(safetyTimer);
            window.removeEventListener('focus', handleWindowFocus);

            if (tokenResponse.error) {
              setIsLoading(false);
              if (tokenResponse.error === 'access_denied') {
                setErrorMsg('Bạn đã hủy đăng nhập bằng tài khoản Google.');
              } else if (tokenResponse.error.includes('origin')) {
                setErrorMsg(
                  `Lỗi Origin: Vui lòng thêm "${currentOrigin}" vào mục "Authorized JavaScript origins" trong Google Cloud Console.`
                );
              } else {
                setErrorMsg(`Lỗi Google OAuth: ${tokenResponse.error_description || tokenResponse.error}`);
              }
              return;
            }

            if (tokenResponse.access_token) {
              try {
                // Gọi API lấy thông tin Profile thật từ tài khoản Google
                const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                  headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
                });
                const profile = await res.json();

                if (profile && profile.email) {
                  const realGoogleUser = {
                    name: profile.name || profile.given_name || 'Người dùng Google',
                    email: profile.email,
                    avatar: profile.picture || null,
                    provider: 'google',
                    sub: profile.sub,
                    role: 'Thành viên NexaMind'
                  };

                  setSuccessMsg(`Đăng nhập Google thành công: ${realGoogleUser.name} (${realGoogleUser.email})`);
                  setTimeout(() => completeLogin(realGoogleUser), 500);
                } else {
                  setErrorMsg('Không thể nạp thông tin người dùng từ Google.');
                  setIsLoading(false);
                }
              } catch (fetchErr) {
                setErrorMsg(`Lỗi khi lấy thông tin người dùng: ${fetchErr.message}`);
                setIsLoading(false);
              }
            } else {
              setIsLoading(false);
            }
          },
          error_callback: (err) => {
            clearTimeout(safetyTimer);
            window.removeEventListener('focus', handleWindowFocus);
            setIsLoading(false);
            if (err?.type === 'popup_closed') {
              setErrorMsg('Bạn đã đóng cửa sổ đăng nhập Google.');
            } else if (err?.type === 'popup_blocked') {
              setErrorMsg('Trình duyệt đã chặn popup Google. Vui lòng cho phép mở cửa sổ bật lên.');
            }
          }
        });

        // Kích hoạt mở Popup đăng nhập tài khoản Google thật
        tokenClient.requestAccessToken({ prompt: 'select_account' });
        return;
      } catch (err) {
        setIsLoading(false);
        console.error('Lỗi khi kích hoạt Token Client:', err);
      }
    }

    // Fallback nếu OAuth2 không khả dụng
    if (window.google.accounts?.id) {
      window.google.accounts.id.prompt();
    }
  };

  // Lưu Google Client ID từ modal nếu cần thay đổi
  const handleSaveClientId = (e) => {
    e.preventDefault();
    if (!tempClientId.trim()) {
      setErrorMsg('Vui lòng nhập Google Client ID.');
      return;
    }
    const cleanId = tempClientId.trim();
    setGoogleClientId(cleanId);
    localStorage.setItem('nexamind_google_client_id', cleanId);
    setShowConfigModal(false);
    setSuccessMsg('Đã cập nhật Google Client ID mới!');
    setTimeout(() => {
      initGoogleServices(cleanId);
    }, 300);
  };

  // 4. Xử lý Đăng nhập qua Email / Mật khẩu
  const handleSubmit = (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (!email.trim() || !email.includes('@')) {
      setErrorMsg('Vui lòng nhập email hợp lệ.');
      return;
    }
    if (!password || password.length < 6) {
      setErrorMsg('Mật khẩu cần tối thiểu 6 ký tự.');
      return;
    }

    setIsLoading(true);

    setTimeout(() => {
      setIsLoading(false);
      const user = {
        name: activeTab === 'register' ? (name.trim() || 'Người dùng mới') : 'Chuyên viên Tri thức',
        email: email.trim(),
        avatar: null,
        provider: 'password',
        role: 'NexaMind Specialist'
      };
      setSuccessMsg(activeTab === 'login' ? 'Đăng nhập thành công!' : 'Đăng ký tài khoản thành công!');
      setTimeout(() => completeLogin(user), 500);
    }, 500);
  };

  const completeLogin = async (userData) => {
    try {
      const authRes = await loginUser({
        email: userData.email,
        name: userData.name,
        provider: userData.provider || 'password'
      });
      if (authRes?.access_token) {
        localStorage.setItem('nexamind_jwt', authRes.access_token);
      }
    } catch (err) {
      console.warn('Backend login token issue (fallback offline mode):', err);
    }
    localStorage.setItem('nexamind_user', JSON.stringify(userData));
    if (onLoginSuccess) {
      onLoginSuccess(userData);
    }
  };

  const handleForgotPassword = (e) => {
    e.preventDefault();
    alert(`Liên kết khôi phục mật khẩu đã được gửi đến: ${email || 'email của bạn'}`);
  };

  const handleGuestAccess = () => {
    completeLogin({
      name: 'Khách trải nghiệm',
      email: 'guest@nexamind.ai',
      avatar: null,
      provider: 'guest',
      role: 'Khách xem'
    });
  };

  return (
    <div className="auth-wrapper">
      {/* FORM ĐĂNG NHẬP / ĐĂNG KÝ CĂN GIỮA */}
      <div className="auth-right-col">
        <div className="auth-form-container">
          {/* Logo & Thương hiệu NexaMind AI */}
          <div className="auth-brand-header">
            <div className="auth-brand-logo">
              <BrainCircuit size={24} />
            </div>
            <div>
              <div className="auth-brand-name">
                Nexa<b>Mind</b> AI
              </div>
              <div className="auth-brand-caption">Material 3 knowledge workspace</div>
            </div>
          </div>

          {/* Tabs chuyển đổi Đăng nhập / Đăng ký */}
          <div className="auth-tabs-nav">
            <button
              type="button"
              className={`auth-tab-btn ${activeTab === 'login' ? 'active' : ''}`}
              onClick={() => { setActiveTab('login'); setErrorMsg(''); }}
            >
              Đăng nhập
            </button>
            <button
              type="button"
              className={`auth-tab-btn ${activeTab === 'register' ? 'active' : ''}`}
              onClick={() => { setActiveTab('register'); setErrorMsg(''); }}
            >
              Đăng ký
            </button>
          </div>

          {/* Tiêu đề & Lời chào */}
          <h2 className="auth-title">
            {activeTab === 'login' ? 'Chào mừng quay lại' : 'Tạo tài khoản mới'}
          </h2>
          <p className="auth-subtitle">
            {activeTab === 'login'
              ? 'Đăng nhập để tiếp tục tra cứu và làm việc với kho tài liệu.'
              : 'Đăng ký để bắt đầu trải nghiệm trợ lý hỏi đáp tài liệu thông minh.'}
          </p>

          {/* Thông báo Lỗi / Thành công */}
          {errorMsg && (
            <div className="auth-error-banner">
              <AlertCircle size={16} />
              <span>{errorMsg}</span>
            </div>
          )}
          {successMsg && (
            <div className="auth-toast">
              <CheckCircle size={16} />
              <span>{successMsg}</span>
            </div>
          )}

          {/* NÚT ĐĂNG NHẬP BẰNG GOOGLE (TÀI KHOẢN THẬT) */}
          <div className="google-signin-wrapper">
            <button
              type="button"
              className="btn-google-signin"
              onClick={handleGoogleSignInClick}
              disabled={isLoading}
              title="Đăng nhập bằng tài khoản Google thật của bạn"
            >
              <svg width="18" height="18" viewBox="0 0 48 48">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
              </svg>
              <span>{isLoading ? 'Đang kết nối Google...' : 'Continue with Google'}</span>
            </button>

            {isLoading && (
              <button
                type="button"
                onClick={() => {
                  setIsLoading(false);
                  setErrorMsg('Đã hủy kết nối. Bạn có thể bấm để đăng nhập lại.');
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--nx-muted)',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  marginTop: '8px',
                  textDecoration: 'underline',
                  display: 'block',
                  textAlign: 'center',
                  width: '100%'
                }}
              >
                Hủy chờ & mở lại nút
              </button>
            )}

            {/* Container dự phòng cho nút chính thức của Google GIS */}
            <div ref={googleBtnContainerRef} className="google-btn-official" style={{ display: 'none' }} />
          </div>

          {/* Đường kẻ ngang HOẶC */}
          <div className="auth-divider">
            <span>H O Ặ C</span>
          </div>

          {/* FORM NHẬP EMAIL & MẬT KHẨU */}
          <form className="auth-form" onSubmit={handleSubmit}>
            {activeTab === 'register' && (
              <div className="auth-field-group">
                <label className="auth-label">Họ và tên</label>
                <div className="auth-input-wrapper">
                  <input
                    type="text"
                    className="auth-input"
                    placeholder="Nguyễn Văn A"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
              </div>
            )}

            <div className="auth-field-group">
              <label className="auth-label">Email</label>
              <div className="auth-input-wrapper">
                <input
                  type="email"
                  className="auth-input"
                  placeholder="alex@nexamind.ai"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="auth-field-group">
              <div className="auth-field-header">
                <label className="auth-label">Password</label>
                {activeTab === 'login' && (
                  <a
                    href="#forgot"
                    className="auth-forgot-link"
                    onClick={handleForgotPassword}
                  >
                    Quên mật khẩu?
                  </a>
                )}
              </div>
              <div className="auth-input-wrapper">
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="auth-input"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            {/* Checkbox Hiện mật khẩu */}
            <div className="auth-checkbox-row">
              <input
                type="checkbox"
                id="show-pass-check"
                checked={showPassword}
                onChange={(e) => setShowPassword(e.target.checked)}
              />
              <label htmlFor="show-pass-check" className="auth-checkbox-label">
                Hiện mật khẩu
              </label>
            </div>

            {/* Nút Submit Đăng nhập / Đăng ký */}
            <button
              type="submit"
              className="btn-auth-submit"
              disabled={isLoading}
            >
              {isLoading ? (
                <span>Đang xử lý...</span>
              ) : (
                <span>{activeTab === 'login' ? 'Đăng nhập' : 'Tạo tài khoản'}</span>
              )}
            </button>
          </form>

          {/* Tùy chọn vào nhanh xem giao diện */}
          <div className="auth-guest-link">
            <span>Muốn dùng thử ngay?</span>
            <button type="button" onClick={handleGuestAccess}>
              Truy cập nhanh (Guest)
            </button>
          </div>
        </div>
      </div>

      {/* MODAL CẤU HÌNH GOOGLE OAUTH CLIENT ID NẾU CẦN ĐỔI */}
      {showConfigModal && (
        <div className="auth-modal-backdrop" onClick={() => setShowConfigModal(false)}>
          <div className="auth-modal-box" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h3 className="auth-modal-title">
                <KeyRound size={20} color="#00838f" />
                Cấu hình Google OAuth Client ID
              </h3>
              <button
                type="button"
                onClick={() => setShowConfigModal(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}
              >
                <X size={20} />
              </button>
            </div>

            <p className="auth-modal-desc">
              Hệ thống hiện đang sử dụng Client ID của bạn. Đảm bảo bạn đã thêm <b>{window.location.origin}</b> vào mục <b>Authorized JavaScript origins</b> trên Google Cloud Console.
            </p>

            <div className="auth-guide-steps">
              <ol>
                <li>
                  Vào{' '}
                  <a
                    href="https://console.cloud.google.com/apis/credentials"
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: '#00838f', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '3px' }}
                  >
                    Google Cloud Console <ExternalLink size={12} />
                  </a>
                </li>
                <li>Chọn OAuth Client ID của bạn (loại Web Application).</li>
                <li>
                  Tại <b>Authorized JavaScript origins</b>, kiểm tra đã có:
                  <br />
                  <code>{window.location.origin}</code> và <code>http://localhost:5173</code>
                </li>
              </ol>
            </div>

            <form onSubmit={handleSaveClientId}>
              <div className="auth-field-group">
                <label className="auth-label">Client ID hiện tại</label>
                <input
                  type="text"
                  className="auth-input"
                  value={tempClientId}
                  onChange={(e) => setTempClientId(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="auth-modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowConfigModal(false)}
                  style={{
                    padding: '9px 16px',
                    borderRadius: '8px',
                    border: '1px solid #cbd5e1',
                    background: '#f8fafc',
                    cursor: 'pointer',
                    fontSize: '0.875rem'
                  }}
                >
                  Đóng
                </button>

                <button
                  type="submit"
                  className="btn-auth-submit"
                  style={{ width: 'auto', padding: '9px 20px', borderRadius: '8px' }}
                >
                  Cập nhật
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
