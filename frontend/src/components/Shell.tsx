import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { Bell, Building2, FileSearch, LayoutDashboard, Menu, Moon, PanelLeft, Search, Sun, TriangleAlert } from "lucide-react";
import { api } from "../api";

const QueryContext = createContext("");
export function useQuery() {
  return useContext(QueryContext);
}

export function Shell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("prastuti-sidebar") === "collapsed");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [dark, setDark] = useState(() => document.documentElement.dataset.theme === "dark");
  const [query, setQuery] = useState("");
  const [openAlerts, setOpenAlerts] = useState<number | null>(null);

  useEffect(() => {
    const load = () => {
      api.dashboard()
        .then((data) => setOpenAlerts(data.open_attendance_alerts + data.open_infrastructure_alerts))
        .catch(() => setOpenAlerts(null));
    };
    load();
    window.addEventListener("prastuti-refresh", load);
    return () => window.removeEventListener("prastuti-refresh", load);
  }, []);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.dataset.theme = next ? "dark" : "light";
    if (!next) delete document.documentElement.dataset.theme;
    localStorage.setItem("prastuti-theme", next ? "dark" : "light");
  }

  function toggleSidebar() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem("prastuti-sidebar", next ? "collapsed" : "open");
  }

  const item = ({ isActive }: { isActive: boolean }) => (isActive ? "nav-link nav-on" : "nav-link");

  return (
    <QueryContext.Provider value={query}>
      <a className="skip" href="#content">Skip to content</a>
      {mobileOpen && <button className="backdrop" aria-label="Close menu" onClick={() => setMobileOpen(false)} />}
      <div className={`shell ${collapsed ? "collapsed" : ""}`}>
        <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
          <div className="brand">
            <strong>Prastuti AI</strong>
            <span>Training centre monitoring</span>
          </div>
          <nav className="menu" aria-label="Primary">
            <NavLink to="/" end className={item} aria-label="Dashboard" onClick={() => setMobileOpen(false)}>
              <LayoutDashboard aria-hidden="true" /> <span className="nav-label">Dashboard</span>
            </NavLink>
            <NavLink to="/centres/TC-PB-001" className={item} aria-label="Centre" onClick={() => setMobileOpen(false)}>
              <Building2 aria-hidden="true" /> <span className="nav-label">Centre</span>
            </NavLink>
            <NavLink to="/alerts" className={item} aria-label="Alerts" onClick={() => setMobileOpen(false)}>
              <TriangleAlert aria-hidden="true" /> <span className="nav-label">Alerts</span>
            </NavLink>
            <NavLink to="/analyze" className={item} aria-label="Analyze" onClick={() => setMobileOpen(false)}>
              <FileSearch aria-hidden="true" /> <span className="nav-label">Analyze</span>
            </NavLink>
          </nav>
        
        </aside>
        <div className="main-col">
          <header className="topbar">
            <button className="icon-btn menu-btn" aria-label="Open menu" onClick={() => setMobileOpen(true)}>
              <Menu aria-hidden="true" />
            </button>
            <button className="icon-btn" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-pressed={collapsed} onClick={toggleSidebar}>
              <PanelLeft aria-hidden="true" />
            </button>
            <label className="search">
              <Search aria-hidden="true" size={16} />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search centres and alerts"
                aria-label="Search centres and alerts"
              />
            </label>
            <Link className="icon-btn bell" to="/alerts" aria-label={openAlerts === null ? "Open alerts" : `${openAlerts} open alerts`}>
              <Bell aria-hidden="true" />
              {openAlerts !== null && openAlerts > 0 && <span className="badge">{openAlerts}</span>}
            </Link>
            <button className="icon-btn" aria-label={dark ? "Switch to light theme" : "Switch to dark theme"} aria-pressed={dark} onClick={toggleTheme}>
              {dark ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
            </button>
            
          </header>
          <main id="content" className="content">{children}</main>
        </div>
      </div>
    </QueryContext.Provider>
  );
}

export function refreshShell() {
  window.dispatchEvent(new Event("prastuti-refresh"));
}
