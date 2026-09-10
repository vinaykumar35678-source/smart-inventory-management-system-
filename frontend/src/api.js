import axios from "axios";

const host = (typeof window !== "undefined" && window.location.hostname) ? window.location.hostname : "localhost";
const api = axios.create({
  baseURL: `http://${host}:8000/api`,
  withCredentials: true, // Enables browser transmission of HttpOnly; SameSite=Lax cookies
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Request Interceptor: attach Bearer token fallback if present ───────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("smartshelf_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor: graceful session expiry handling ─────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect if 401 happened on a protected data route, NOT during a login attempt or initial auth check
    const isLoginEndpoint = error.config && error.config.url && error.config.url.includes("/auth/login");
    const isMeEndpoint = error.config && error.config.url && error.config.url.includes("/auth/me");
    if (error.response && error.response.status === 401 && !isLoginEndpoint && !isMeEndpoint) {
      localStorage.removeItem("smartshelf_token");
      localStorage.removeItem("smartshelf_user");
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;