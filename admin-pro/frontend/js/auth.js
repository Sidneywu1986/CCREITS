/**
 * TokenManager — JWT authentication helper
 * Handles login, logout, token refresh, and authenticated fetch
 */
(function() {
  'use strict';

  const TOKEN_KEY = 'access_token';

  window.Auth = {
    /** Get stored access token */
    getToken() {
      return localStorage.getItem(TOKEN_KEY);
    },

    /** Store access token */
    setToken(token) {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    },

    /** Clear token (logout) */
    clearToken() {
      localStorage.removeItem(TOKEN_KEY);
    },

    /** Check if user is logged in */
    isLoggedIn() {
      return !!this.getToken();
    },

    /** Parse JWT payload (no verification) */
    parseToken(token) {
      if (!token) return null;
      try {
        const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        const json = decodeURIComponent(atob(base64).split('').map(function(c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(json);
      } catch (e) {
        return null;
      }
    },

    /** Get current user info from token */
    getUserInfo() {
      return this.parseToken(this.getToken());
    },

    /** Login via API */
    async login(username, password) {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (data.code === 200 && data.data && data.data.access_token) {
        this.setToken(data.data.access_token);
        return { success: true, user: data.data.user };
      }
      return { success: false, message: data.message || '登录失败' };
    },

    /** Logout via API */
    async logout() {
      try {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          credentials: 'include'
        });
      } catch (e) { /* ignore */ }
      this.clearToken();
    },

    /** Refresh access token using refresh cookie */
    async refreshToken() {
      try {
        const res = await fetch('/api/v1/auth/refresh', {
          method: 'POST',
          credentials: 'include'
        });
        const data = await res.json();
        if (data.code === 200 && data.data && data.data.access_token) {
          this.setToken(data.data.access_token);
          return true;
        }
      } catch (e) { /* ignore */ }
      this.clearToken();
      return false;
    },

    /** Fetch with automatic Authorization header and token refresh */
    async fetchWithAuth(url, options = {}) {
      let token = this.getToken();
      const headers = {
        ...(options.headers || {}),
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      };

      let response = await fetch(url, { ...options, headers });

      // Token expired → try refresh once
      if (response.status === 401 && token) {
        const refreshed = await this.refreshToken();
        if (refreshed) {
          headers['Authorization'] = `Bearer ${this.getToken()}`;
          response = await fetch(url, { ...options, headers });
        } else {
          // Refresh failed → redirect to login
          window.location.href = '/admin/login';
        }
      }

      return response;
    }
  };
})();
