import { createContext, useContext, useEffect, useState, useRef } from "react";
import api, { getCurrentUser, getToken } from "../lib/api.js";

const NotificationContext = createContext(null);

export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [toasts, setToasts] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const currentUser = getCurrentUser();

  useEffect(() => {
    if (!currentUser) return;

    // Load initial persistent notifications & unread count via REST
    loadInitialData();

    // Connect WebSocket
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [currentUser?.id]);

  function loadInitialData() {
    api
      .get("/notifications")
      .then(({ data }) => setNotifications(data))
      .catch(() => setNotifications([]));

    api
      .get("/notifications/unread-count")
      .then(({ data }) => setUnreadCount(data.unread_count))
      .catch(() => setUnreadCount(0));
  }

  function connectWebSocket() {
    const token = getToken();
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.hostname || "localhost";
    const wsUrl = `${protocol}//${host}:8000/ws/notifications?token=${token}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        // Send heartbeat ping every 25s
        ws._pingInterval = setInterval(() => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            try {
              ws.send("ping");
            } catch (e) {}
          }
        }, 25000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (!data || data.type === "pong") return;

          // New notification arrived live!
          setNotifications((prev) => [data, ...(prev || [])]);
          setUnreadCount((prev) => (prev || 0) + 1);

          // Add transient toast popup
          const toastId = data.id || `toast-${Date.now()}`;
          const newToast = {
            id: toastId,
            type: data.type,
            title: data.title,
            message: data.message,
            related_case_id: data.related_case_id,
          };

          setToasts((prev) => [newToast, ...(prev || [])]);

          // Auto-remove toast after 5s
          setTimeout(() => {
            removeToast(toastId);
          }, 5000);
        } catch (err) {
          // ignore non-JSON messages
        }
      };

      ws.onclose = () => {
        if (ws._pingInterval) clearInterval(ws._pingInterval);
        // Retry connection after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket();
        }, 5000);
      };

      ws.onerror = () => {
        try {
          ws.close();
        } catch (e) {}
      };
    } catch (err) {
      // WS connection failure fallback
    }
  }


  function removeToast(toastId) {
    setToasts((prev) => prev.filter((t) => t.id !== toastId));
  }

  async function markAsRead(notificationId) {
    try {
      await api.patch(`/notifications/${notificationId}/read`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notificationId ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      // ignore error
    }
  }

  async function markAllAsRead() {
    try {
      await api.patch("/notifications/read-all");
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      // ignore error
    }
  }

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        toasts,
        markAsRead,
        markAllAsRead,
        removeToast,
      }}
    >
      {children}

      {/* Render Toast SnackBar Container */}
      <div className="fixed bottom-5 right-5 z-50 space-y-2 max-w-sm pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="pointer-events-auto bg-panel border border-amber/60 text-ink p-3.5 rounded-lg shadow-xl font-mono text-xs animate-slide-up flex items-start justify-between gap-3"
          >
            <div>
              <p className="font-bold text-amber text-xs mb-0.5">{t.title}</p>
              <p className="text-muted text-[11px] leading-snug font-body">{t.message}</p>
            </div>
            <button
              onClick={() => removeToast(t.id)}
              className="text-muted hover:text-ink text-xs font-mono"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    return {
      notifications: [],
      unreadCount: 0,
      toasts: [],
      markAsRead: () => {},
      markAllAsRead: () => {},
      removeToast: () => {},
    };
  }
  return ctx;
}

