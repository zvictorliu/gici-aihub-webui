const CURRENT_USER_KEY = 'aihub_current_user';

export const authService = {
  // Register via Python backend
  async register(username, password) {
    const response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || '注册失败');
    }
    return data;
  },

  // Login via Python backend
  async login(username, password) {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || '登录失败');
    }
    
    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify({ username: data.username }));
    return data;
  },

  // Logout
  logout() {
    localStorage.removeItem(CURRENT_USER_KEY);
  },

  // Get current session
  getCurrentUser() {
    const userJson = localStorage.getItem(CURRENT_USER_KEY);
    return userJson ? JSON.parse(userJson) : null;
  }
};
