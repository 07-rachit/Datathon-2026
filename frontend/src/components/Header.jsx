import { useState, useRef, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useNotifications } from "../context/NotificationContext.jsx";

const PATH_TITLES = {
  "/": "OPERATIONS DASHBOARD",
  "/cases": "CASE SEARCH & MANAGEMENT",
  "/map": "SPATIAL HOTSPOT MAP",
  "/network": "CRIMINAL NETWORK GRAPH",
  "/assistant": "AI RESEARCH DESK",
  "/my-work": "MY WORK & ASSIGNED TASKS",
  "/audit": "SYSTEM AUDIT TRAIL",
  "/import": "BULK CASE IMPORT",
  "/offenders": "OFFENDER PROFILES",
  "/insights": "SOCIO-DEMOGRAPHIC INSIGHTS",
  "/admin": "USER ADMINISTRATION",
};

export default function Header() {
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const title = PATH_TITLES[location.pathname] || "CASE INTELLIGENCE";

  function handleNotificationClick(n) {
    markAsRead(n.id);
    setIsOpen(false);
    if (n.related_case_id) {
      navigate(`/cases/${n.related_case_id}`);
    }
  }

  return (
    <header className="h-14 border-b border-line bg-panel px-6 flex items-center justify-between font-mono text-xs">
      {/* Screen Title Breadcrumb */}
      <div className="flex items-center gap-2">
        <span className="text-teal font-bold tracking-widest">{title}</span>
      </div>

      {/* Right Controls: Notification Bell */}
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="relative p-2 rounded hover:bg-panel2 transition text-ink flex items-center gap-1.5 focus:outline-none"
          title="In-App Alerts"
        >
          <span className="text-base">🔔</span>
          <span className="hidden md:inline text-muted text-[11px]">Alerts</span>
          {unreadCount > 0 && (
            <span className="bg-amber text-base font-bold text-[10px] px-1.5 py-0.2 rounded-full min-w-[18px] text-center">
              {unreadCount}
            </span>
          )}
        </button>

        {/* Dropdown Panel */}
        {isOpen && (
          <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-panel border border-line rounded-lg shadow-2xl z-50 overflow-hidden animate-fade-in">
            <div className="p-3 border-b border-line bg-panel2 flex items-center justify-between">
              <span className="font-bold text-ink uppercase text-[11px] tracking-wider">
                In-App Live Alerts ({unreadCount} unread)
              </span>
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="text-amber hover:underline text-[10px] transition"
                >
                  Mark all read
                </button>
              )}
            </div>

            <div className="max-h-80 overflow-y-auto divide-y divide-line/40">
              {notifications.length === 0 ? (
                <div className="p-6 text-center text-muted text-xs">
                  No notifications recorded.
                </div>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    onClick={() => handleNotificationClick(n)}
                    className={`p-3 transition cursor-pointer flex items-start gap-2.5 hover:bg-panel2 ${
                      !n.is_read ? "bg-amber/5 border-l-2 border-amber" : "opacity-80"
                    }`}
                  >
                    <span className="text-sm mt-0.5">
                      {n.type === "high_severity_case"
                        ? "🚨"
                        : n.type === "case_assigned"
                        ? "📋"
                        : n.type === "task_assigned"
                        ? "📌"
                        : n.type === "district_trend_alert"
                        ? "📈"
                        : "🔔"}
                    </span>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <p className="font-bold text-ink text-xs leading-snug">{n.title}</p>
                        <span className="text-[9px] text-muted whitespace-nowrap ml-2">
                          {new Date(n.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                      <p className="text-muted text-[11px] font-body leading-relaxed">{n.message}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
