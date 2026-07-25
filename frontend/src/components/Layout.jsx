import { useEffect, useState } from "react";
import { NavLink, useNavigate, useLocation } from "react-router-dom";
import { getCurrentUser, logout, fetchMyTasks } from "../lib/api.js";
import Header from "./Header.jsx";
import ChatWidget from "./ChatWidget.jsx";


const NAV = [
  { to: "/", label: "Dashboard", code: "01" },
  { to: "/cases", label: "Case Search", code: "02" },
  { to: "/map", label: "Hotspot Map", code: "03" },
  { to: "/network", label: "Network Graph", code: "04" },
  { to: "/assistant", label: "AI Assistant", code: "05" },
  { to: "/my-work", label: "My Work", code: "06", hasBadge: true },
  { to: "/audit", label: "Audit Trail", code: "07" },
];

export default function Layout({ children }) {
  const user = getCurrentUser();
  const navigate = useNavigate();
  const location = useLocation();
  const [openTasksCount, setOpenTasksCount] = useState(0);

  useEffect(() => {
    if (user) {
      fetchMyTasks()
        .then((tasks) => setOpenTasksCount(tasks.length))
        .catch(() => setOpenTasksCount(0));
    }
  }, [location.pathname]);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const role = user?.role || "viewer";

  // Build role-specific navigation links
  const dynamicNav = [];
  if (role === "admin" || role === "investigator") {
    dynamicNav.push({ to: "/import", label: "Import Cases", code: "08" });
  }
  if (role === "admin" || role === "investigator" || role === "analyst") {
    dynamicNav.push({ to: "/offenders", label: "Offender Profiles", code: "09" });
  }
  if (role === "admin" || role === "analyst") {
    dynamicNav.push({ to: "/insights", label: "Socio Insights", code: "10" });
  }
  if (role === "admin") {
    dynamicNav.push({ to: "/admin", label: "User Admin", code: "11" });
  }

  return (
    <div className="min-h-screen bg-base font-body flex">
      <aside className="w-56 border-r border-line bg-panel flex flex-col flex-shrink-0">
        <div className="px-5 py-5 border-b border-line">
          <p className="font-mono text-teal text-[10px] tracking-[0.3em]">CASE-ACCESS-SYS</p>
          <h1 className="font-display text-2xl text-ink tracking-wide leading-tight">
            CRIME<span className="text-amber">INTEL</span>
          </h1>
        </div>
        <nav className="flex-1 py-4 overflow-y-auto">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm transition border-l-2 ${
                  isActive
                    ? "border-amber text-ink bg-panel2 font-semibold"
                    : "border-transparent text-muted hover:text-ink hover:bg-panel2/60"
                }`
              }
            >
              <span className="font-mono text-xs text-muted">{item.code}</span>
              <span>{item.label}</span>
              {item.hasBadge && openTasksCount > 0 && (
                <span className="ml-auto bg-amber text-base font-mono text-[10px] font-bold px-1.5 py-0.2 rounded-full">
                  {openTasksCount}
                </span>
              )}
            </NavLink>
          ))}
          {/* Dynamic role-gated navigation */}
          {dynamicNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm transition border-l-2 ${
                  isActive
                    ? "border-amber text-ink bg-panel2 font-semibold"
                    : "border-transparent text-muted hover:text-ink hover:bg-panel2/60"
                }`
              }
            >
              <span className="font-mono text-xs text-muted">{item.code}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-4 border-t border-line">
          <p className="text-ink text-sm">{user?.name}</p>
          <p className="text-muted text-xs font-mono uppercase tracking-wide mb-3">{user?.role}</p>
          <button
            onClick={handleLogout}
            className="text-xs font-mono text-muted hover:text-crit transition"
          >
            SIGN OUT →
          </button>
        </div>
      </aside>
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
      <ChatWidget />
    </div>
  );
}



