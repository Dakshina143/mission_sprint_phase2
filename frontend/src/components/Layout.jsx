import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { get } from "../api/client";

const NAV = [
  ["/", "Dashboard"], ["/missions", "Missions"], ["/backlog", "Backlog"], ["/sprints", "Sprints"], ["/board", "Board"],
  ["/analytics", "Analytics"], ["/blockers", "Blockers"], ["/retrospectives", "Retrospectives"],
  ["/notifications", "Notifications"], ["/reports", "Reports"],
];

function useHealth() {
  const [h, setH] = useState({ state: "checking" });
  useEffect(() => {
    let alive = true;
    const check = () => get("/health")
      .then(() => alive && setH({ state: "ok", text: "API and database healthy" }))
      .catch((e) => alive && setH({
        state: "down",
        text: e.response?.data?.data?.database === "unreachable" ? "API up, database unreachable" : "API unreachable",
      }));
    check();
    const t = setInterval(check, 30000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  return h;
}

export default function Layout() {
  const health = useHealth();
  const [unread, setUnread] = useState(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const load = () => get("/notifications", { is_read: "false" }).then((r) => setUnread(r.unread_count)).catch(() => setUnread(null));
    load();
    const t = setInterval(load, 30000);
    window.addEventListener("notifications-changed", load);
    return () => { clearInterval(t); window.removeEventListener("notifications-changed", load); };
  }, []);

  return (
    <div className="shell">
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand">MissionSprint</div>
        <nav onClick={() => setOpen(false)}>
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
              {label}
              {label === "Notifications" && unread > 0 && <span className="count">{unread}</span>}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <button className="icon-btn menu-btn" aria-label="Toggle navigation" onClick={() => setOpen((o) => !o)}>☰</button>
          <span className={`health health-${health.state}`} role="status">
            <i />{health.state === "checking" ? "Checking API…" : health.text}
          </span>
        </header>
        <main><Outlet /></main>
      </div>
    </div>
  );
}
