import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Building2, CircleAlert, CircleCheck, CircleMinus, ClipboardCheck, Inbox, TriangleAlert, Users } from "lucide-react";
import { api, type Alert, type CentreDetail, type Dashboard } from "./api";
import { Shell, refreshShell, useQuery } from "./components/Shell";
import { useToast } from "./components/toast";
import {
  alertStatusLabel,
  figuresFromDescription,
  gapValue,
  matchesQuery,
  observedText,
  recordedText,
  relativeTime,
  severityLabel,
  toneForStatus,
  typeLabel,
  type Tone,
} from "./format";

function Pill({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}

function Loading({ label }: { label: string }) {
  return (
    <div className="skeleton" role="status" aria-live="polite">
      <span className="muted small">{label}</span>
    </div>
  );
}

function Ring({ passed, total }: { passed: number; total: number }) {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const fraction = total > 0 ? passed / total : 0;
  return (
    <svg width="92" height="92" viewBox="0 0 92 92" role="img" aria-label={`${passed} of ${total} compliant checks`}>
      <circle cx="46" cy="46" r={radius} fill="none" stroke="var(--line)" strokeWidth="8" />
      <circle
        cx="46"
        cy="46"
        r={radius}
        fill="none"
        stroke="var(--gov-2)"
        strokeWidth="8"
        strokeDasharray={`${circumference * fraction} ${circumference}`}
        transform="rotate(-90 46 46)"
      />
      <text x="46" y="50" textAnchor="middle" fill="var(--ink)" fontSize="15" fontWeight="700">{passed}/{total || 0}</text>
    </svg>
  );
}

function Kpi({ label, value, hint, icon }: { label: string; value: number; hint: string; icon: ReactNode }) {
  return (
    <section className="card kpi">
      <p className="kpi-label">{icon}{label}</p>
      <p className="kpi-value">{value}</p>
      <p className="kpi-hint">{hint}</p>
    </section>
  );
}

function AlertMenus({ alert, onChanged }: { alert: Alert; onChanged: () => void }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const toast = useToast();
  async function mark(status: string) {
    setBusy(true);
    try {
      await api.setStatus(alert.id, status);
      toast(status === "resolved" ? "Marked resolved" : "Marked under review");
      refreshShell();
      onChanged();
      setOpen(false);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Could not update the alert");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="actions">
      <button className="btn" aria-expanded={open} aria-label={`Actions for ${alert.id}`} disabled={busy} onClick={() => setOpen((value) => !value)}>
        Actions
      </button>
      {open && (
        <div className="actions-pop" role="menu">
          <button role="menuitem" onClick={() => navigate(`/alerts/${alert.id}`)}>Open</button>
          <button role="menuitem" onClick={() => mark("under_review")}>Under review</button>
          <button role="menuitem" onClick={() => mark("resolved")}>Resolved</button>
        </div>
      )}
    </div>
  );
}

function AlertTable({ alerts, onChanged, empty, title = "Recent alerts" }: { alerts: Alert[]; onChanged: () => void; empty: string; title?: string }) {
  const query = useQuery();
  const [severity, setSeverity] = useState("all");
  const [status, setStatus] = useState("all");
  const [sort, setSort] = useState("recorded");
  const rows = useMemo(() => {
    let next = alerts.filter((alert) => matchesQuery(alert, query));
    if (severity !== "all") next = next.filter((alert) => alert.severity === severity);
    if (status !== "all") next = next.filter((alert) => alert.status === status);
    const copy = [...next];
    if (sort === "severity") {
      const rank: Record<string, number> = { high: 0, medium: 1 };
      copy.sort((a, b) => (rank[a.severity] ?? 2) - (rank[b.severity] ?? 2));
    } else if (sort === "gap") {
      copy.sort((a, b) => Number(gapValue(figuresFromDescription(b.description)) ?? -1) - Number(gapValue(figuresFromDescription(a.description)) ?? -1));
    } else if (sort === "time") {
      copy.sort((a, b) => b.created_at.localeCompare(a.created_at));
    }
    return copy;
  }, [alerts, query, severity, status, sort]);

  return (
    <section className="card" style={{ marginTop: "0.75rem" }}>
      <div className="card-pad" style={{ paddingBottom: 0 }}>
        <h2 className="section-title">{title}</h2>
        <div className="filters">
          <label className="small muted">Severity
            <select aria-label="Filter by severity" value={severity} onChange={(event) => setSeverity(event.target.value)}>
              <option value="all">All</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
            </select>
          </label>
          <label className="small muted">Status
            <select aria-label="Filter by status" value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="all">All</option>
              <option value="new">Open</option>
              <option value="under_review">Under review</option>
              <option value="resolved">Resolved</option>
            </select>
          </label>
          <label className="small muted">Sort
            <select aria-label="Sort alerts" value={sort} onChange={(event) => setSort(event.target.value)}>
              <option value="recorded">Recorded order</option>
              <option value="time">Newest</option>
              <option value="severity">Severity</option>
              <option value="gap">Gap</option>
            </select>
          </label>
        </div>
      </div>
      {rows.length === 0 ? (
        <div className="empty"><Inbox aria-hidden="true" size={18} /> {empty}</div>
      ) : (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Type</th>
                <th>Status</th>
                <th>When</th>
                <th>Recorded</th>
                <th>Observed</th>
                <th>Gap</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((alert) => {
                const figures = figuresFromDescription(alert.description);
                const gap = gapValue(figures);
                return (
                  <tr key={alert.id}>
                    <td><Pill tone={toneForStatus(alert.severity)}>{severityLabel(alert.severity)}</Pill></td>
                    <td><Link to={`/alerts/${alert.id}`}>{typeLabel(alert.alert_type)}</Link></td>
                    <td><Pill tone={toneForStatus(alert.status)}>{alertStatusLabel(alert.status)}</Pill></td>
                    <td title={alert.created_at}>{relativeTime(alert.created_at)}</td>
                    {figures ? (
                      <>
                        <td>{recordedText(figures)}</td>
                        <td>{observedText(figures)}</td>
                        <td><Pill tone={toneForStatus(alert.severity)}>{gap}</Pill></td>
                      </>
                    ) : (
                      <td colSpan={3}>{alert.description}</td>
                    )}
                    <td><AlertMenus alert={alert} onChanged={onChanged} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const query = useQuery();
  function load() {
    api.dashboard().then(setData).catch((err: Error) => setError(err.message));
  }
  useEffect(() => { load(); }, []);
  if (error) return <p className="warn">{error}. Start the API, then refresh.</p>;
  if (!data) return <Loading label="Loading records…" />;
  const centres = data.centres.filter((centre) => `${centre.name} ${centre.id} ${centre.location}`.toLowerCase().includes(query.trim().toLowerCase()));
  const byType = [
    { name: "Attendance", value: data.alerts.filter((alert) => alert.alert_type === "attendance").length },
    { name: "Infrastructure", value: data.alerts.filter((alert) => alert.alert_type === "infrastructure").length },
  ].filter((item) => item.value > 0);
  const byDate = Object.entries(
    data.alerts.reduce<Record<string, number>>((groups, alert) => {
      const day = alert.created_at.slice(0, 10) || alert.created_at;
      groups[day] = (groups[day] ?? 0) + 1;
      return groups;
    }, {}),
  ).map(([day, count]) => ({ day, count }));

  return (
    <>
      <header className="page-head">
        <h1>Monitoring</h1>
        <p className="lede">{data.note}</p>
      </header>
      <div className="kpi-grid">
        <Kpi label="Centres in this database" value={data.centres_monitored} hint="Local rows only" icon={<Building2 aria-hidden="true" />} />
        <Kpi label="Open attendance alerts" value={data.open_attendance_alerts} hint="Status is not resolved" icon={<Users aria-hidden="true" />} />
        <Kpi label="Open infrastructure alerts" value={data.open_infrastructure_alerts} hint="From model counts" icon={<TriangleAlert aria-hidden="true" />} />
        <section className="card kpi">
          <p className="kpi-label"><ClipboardCheck aria-hidden="true" />Compliant checks</p>
          <div className="ring-row">
            <Ring passed={data.compliant_checks} total={data.assessed_checks || 0} />
            <p className="kpi-hint">Assessed lines that passed. The ring is the same {data.compliant_checks}/{data.assessed_checks || 0} fraction.</p>
          </div>
        </section>
      </div>
      <div className="split">
        <section className="card card-pad">
          <h2 className="section-title">Open alerts by recorded date</h2>
          {byDate.length === 0 ? <div className="empty"><Inbox size={18} aria-hidden="true" />No open alerts. Run an analysis.</div> : (
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={byDate}>
                  <XAxis dataKey="day" stroke="var(--muted)" tick={{ fill: "var(--muted)", fontSize: 12 }} />
                  <YAxis allowDecimals={false} stroke="var(--muted)" tick={{ fill: "var(--muted)", fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#1a5c48" maxBarSize={42} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>
        <section className="card card-pad">
          <h2 className="section-title">Open alerts by type</h2>
          {byType.length === 0 ? <div className="empty"><Inbox size={18} aria-hidden="true" />No open alerts.</div> : (
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={byType} dataKey="value" nameKey="name" innerRadius={52} outerRadius={74} isAnimationActive={false}>
                    {byType.map((entry) => (
                      <Cell key={entry.name} fill={entry.name === "Attendance" ? "#8f2d2a" : "#b86a1b"} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
          <p className="small muted">Counts are the open alert rows already stored. They are not a time series beyond those rows.</p>
        </section>
      </div>
      <section className="card card-pad" style={{ marginTop: "0.75rem" }}>
        <h2 className="section-title">Centres</h2>
        {centres.length === 0 && <div className="empty"><Inbox size={18} aria-hidden="true" />No centre matches this search.</div>}
        {centres.map((centre) => {
          const observed = centre.observed_presence;
          const submitted = centre.submitted_attendance;
          const width = submitted && observed !== null ? Math.min(100, Math.round((observed / submitted) * 100)) : 0;
          return (
            <Link key={centre.id} to={`/centres/${centre.id}`} className="centre-row">
              <span>
                <strong>{centre.name}</strong>
                <span className="small muted" style={{ display: "block" }}>{centre.location} · {centre.id}</span>
                {observed !== null && submitted !== null && (
                  <>
                    <span className="small muted">{observed} observed of {submitted} submitted</span>
                    <span className="meter" aria-hidden="true"><span style={{ width: `${width}%` }} /></span>
                  </>
                )}
              </span>
              <Pill tone={toneForStatus(centre.status)}>{centre.status}</Pill>
            </Link>
          );
        })}
      </section>
      <AlertTable alerts={data.alerts} onChanged={load} empty={query ? "No alert matches this search." : "No open alerts. Run an analysis."} />
      <div className="split">
        <section className="card card-pad">
          <h2 className="section-title">Privacy by design</h2>
          <ul>
            <li>Person, chair, and dining-table boxes only.</li>
            <li>No facial recognition.</li>
            <li>No name or biometric record.</li>
            <li>Attendance uses the peak person count.</li>
          </ul>
        </section>
        <section className="card card-pad">
          <h2 className="section-title">Edge processing architecture</h2>
          <p className="muted">
            The demo samples frames on this computer and stores counts, alerts, and one evidence image.
            It is not installed on centre hardware, and it does not stream the full video to a ministry server.
          </p>
        </section>
      </div>
      
    </>
  );
}

function statusIcon(status: string) {
  if (status === "COMPLIANT" || status === "resolved") return <CircleCheck aria-hidden="true" size={16} />;
  if (status === "NOT_ASSESSED" || status === "NOT_RUN") return <CircleMinus aria-hidden="true" size={16} />;
  return <CircleAlert aria-hidden="true" size={16} />;
}

function CentrePage() {
  const { centreId = "" } = useParams();
  const [data, setData] = useState<CentreDetail | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("overview");
  useEffect(() => {
    api.centre(centreId).then(setData).catch((err: Error) => setError(err.message));
  }, [centreId]);
  if (error) return <p className="warn">{error}</p>;
  if (!data) return <Loading label="Loading centre…" />;
  const attendance = data.latest_analysis?.compliance.attendance;
  const counts = data.latest_analysis?.occupancy.per_frame_counts.map((count, index) => ({ frame: String(index + 1), people: count })) ?? [];
  const tabs = [
    ["overview", "Overview"],
    ["attendance", "Attendance"],
    ["infrastructure", "Infrastructure"],
    ["compliance", "Compliance"],
  ] as const;

  return (
    <>
      <header className="page-head">
        <h1>{data.centre.name}</h1>
        <p className="lede">{data.centre.location} · {data.centre.id} · submitted attendance {data.centre.submitted_attendance}</p>
      </header>
      <div className="tabs" role="tablist" aria-label="Centre sections">
        {tabs.map(([id, label]) => (
          <button key={id} className={tab === id ? "tab tab-on" : "tab"} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>
      {(tab === "overview" || tab === "attendance") && (
        <div className="tile-grid">
          <section className="card kpi"><p className="kpi-label">Submitted attendance</p><p className="kpi-value">{attendance ? (attendance.expected ?? "—") : data.centre.submitted_attendance}</p></section>
          <section className="card kpi"><p className="kpi-label">Observed people</p><p className="kpi-value">{attendance ? attendance.observed : "—"}</p></section>
          <section className="card kpi"><p className="kpi-label">Gap</p><p className="kpi-value">{attendance ? (attendance.variance ?? "—") : "—"}</p></section>
        </div>
      )}
      {attendance && (tab === "overview" || tab === "attendance" || tab === "compliance") && (
        <p style={{ marginTop: "0.8rem" }}><Pill tone={toneForStatus(attendance.status)}>{attendance.status}</Pill></p>
      )}
      {(tab === "overview" || tab === "infrastructure" || tab === "compliance") && (
        <div className="table-wrap card" style={{ marginTop: "0.75rem" }}>
          <table className="data">
            <thead>
              <tr><th>Line</th><th>Sanctioned</th><th>Observed</th><th>Source</th><th>Status</th></tr>
            </thead>
            <tbody>
              {data.inventory.map((item) => (
                <tr key={item.item_key}>
                  <td>{item.label}<span className="small muted" style={{ display: "block" }}>{item.note}</span></td>
                  <td>{item.sanctioned}</td>
                  <td>{item.observed ?? "—"}{item.coco_name ? ` ${item.coco_name}` : ""}</td>
                  <td>{item.source}</td>
                  <td><Pill tone={toneForStatus(item.status)}>{item.status}</Pill></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {tab === "compliance" && (
        <section className="card card-pad" style={{ marginTop: "0.75rem" }}>
          <h2 className="section-title">Checks from the latest run</h2>
          {attendance && (
            <div className="check-row">
              <span>{statusIcon(attendance.status)} Attendance · observed {attendance.observed} · submitted {attendance.expected ?? "—"} · gap {attendance.variance ?? "—"}</span>
              <Pill tone={toneForStatus(attendance.status)}>{attendance.status}</Pill>
            </div>
          )}
          {data.inventory.map((item) => {
            const width = item.observed !== null && item.sanctioned > 0 ? Math.min(100, Math.round((item.observed / item.sanctioned) * 100)) : null;
            return (
              <div className="check-row" key={item.item_key}>
                <span>
                  {statusIcon(item.status)} {item.label}
                  {item.coco_name ? ` · ${item.observed ?? "—"} ${item.coco_name}` : ""}
                  {width !== null && <span className="meter" aria-hidden="true"><span style={{ width: `${width}%` }} /></span>}
                </span>
                <Pill tone={toneForStatus(item.status)}>{item.status}</Pill>
              </div>
            );
          })}
        </section>
      )}
      {tab === "attendance" && counts.length > 0 && (
        <section className="card card-pad" style={{ marginTop: "0.75rem" }}>
          <h2 className="section-title">Person count on each sampled frame</h2>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={counts}>
                <XAxis dataKey="frame" stroke="var(--muted)" tick={{ fill: "var(--muted)", fontSize: 12 }} />
                <YAxis allowDecimals={false} stroke="var(--muted)" tick={{ fill: "var(--muted)", fontSize: 12 }} />
                <Bar dataKey="people" fill="#1a5c48" maxBarSize={42} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}
      {tab === "overview" && data.latest_analysis && (
        <figure className="figure">
          <img alt="Evidence frame with detection boxes" src={`/api/analysis/${data.latest_analysis.analysis_id}/evidence/peak_frame.jpg`} />
          <figcaption>
            <span style={{ display: "block", color: "var(--ink)" }}>{data.latest_analysis.analysis_id}</span>
            boxes are person, chair, and dining table.
          </figcaption>
        </figure>
      )}
    </>
  );
}

function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [error, setError] = useState("");
  function load() {
    api.alerts().then(setAlerts).catch((err: Error) => setError(err.message));
  }
  useEffect(() => { load(); }, []);
  return (
    <>
      <header className="page-head"><h1>Alerts</h1></header>
      {error && <p className="warn">{error}</p>}
      {!alerts && !error && <Loading label="Loading alerts…" />}
      {alerts && <AlertTable alerts={alerts} onChanged={load} empty="No alerts stored yet." title="Stored alerts" />}
    </>
  );
}

function AlertPage() {
  const { alertId = "" } = useParams();
  const [alert, setAlert] = useState<Alert | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  useEffect(() => {
    api.alert(alertId).then(setAlert).catch((err: Error) => setError(err.message));
  }, [alertId]);
  async function mark(status: string) {
    setBusy(true);
    setError("");
    try {
      const updated = await api.setStatus(alertId, status);
      setAlert(updated);
      toast(status === "resolved" ? "Marked resolved" : "Marked under review");
      refreshShell();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update the alert");
    } finally {
      setBusy(false);
    }
  }
  if (!alert && !error) return <Loading label="Loading alert…" />;
  const figures = alert ? figuresFromDescription(alert.description) : null;
  return (
    <>
      {error && <p className="warn">{error}</p>}
      {alert && (
        <>
          <div className="btn-row">
            <Pill tone={toneForStatus(alert.severity)}>{severityLabel(alert.severity)}</Pill>
            <Pill tone="neutral">{typeLabel(alert.alert_type)}</Pill>
            <Pill tone={toneForStatus(alert.status)}>{alertStatusLabel(alert.status)}</Pill>
          </div>
          {figures && (
            <div className="tile-grid">
              {figures.map((figure) => (
                <section className="card kpi" key={figure.label}>
                  <p className="kpi-label">{figure.label}</p>
                  <p className="kpi-value">{figure.value}</p>
                </section>
              ))}
            </div>
          )}
          <h1 className="section-title" style={{ marginTop: "1rem" }}>{alert.description}</h1>
          <p className="small muted">{alert.centre_id} · {alert.created_at} · {alert.id}</p>
          <div className="btn-row" style={{ marginTop: "0.8rem" }}>
            <button className={alert.status === "under_review" ? "btn-primary" : "btn"} disabled={busy} onClick={() => mark("under_review")}>Under review</button>
            <button className={alert.status === "resolved" ? "btn-primary" : "btn"} disabled={busy} onClick={() => mark("resolved")}>Resolved</button>
          </div>
          <figure className="figure">
            <img alt="Saved evidence frame" src={`/api/analysis/${alert.analysis_id}/evidence/peak_frame.jpg`} />
            <figcaption>
              <span style={{ display: "block", color: "var(--ink)" }}>{alert.analysis_id}</span>
              boxes are person, chair, and dining table.
            </figcaption>
          </figure>
        </>
      )}
    </>
  );
}

const ANALYZE_STEPS = ["Sample selected", "Frames processing", "Alerts stored"];

function AnalyzePage() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState<"idle" | "running" | "done">("idle");
  const [findings, setFindings] = useState("");
  async function finish(text: string, detail: string) {
    setPhase("done");
    setMessage(text);
    setFindings(detail);
    refreshShell();
  }
  async function runDemo() {
    setBusy(true);
    setError("");
    setMessage("");
    setFindings("");
    setPhase("running");
    try {
      const result = await api.analyzeDemo();
      const attendance = result.report.compliance?.attendance;
      const detail = attendance
        ? `Observed ${attendance.observed}. Submitted ${attendance.expected ?? "—"}. Gap ${attendance.variance ?? "—"}. Status ${attendance.status}.`
        : "The run is stored. Open the centre to read the counts.";
      await finish(`Stored ${result.alerts.length} alerts for ${result.report.analysis_id}.`, detail);
    } catch (err) {
      setPhase("idle");
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }
  async function upload(file: File) {
    setBusy(true);
    setError("");
    setMessage("");
    setFindings("");
    setPhase("running");
    try {
      const result = await api.analyzeVideo(file);
      await finish(
        `Stored analysis ${result.analysis_id}.`,
        `Observed ${result.observed_presence}. Submitted ${result.expected_attendance ?? "—"}. Gap ${result.variance ?? "—"}. Status ${result.status}.`,
      );
    } catch (err) {
      setPhase("idle");
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <header className="page-head">
        <h1>Analyze demo clip</h1>
        <p className="lede">
          This runs demo/workshop.mp4, a slow pan of a synthetic workshop photo. It is not a live centre camera.
          Person, chair, and dining-table counts come from the model.
        </p>
      </header>
      <button className="btn-primary" style={{ marginTop: "1rem" }} disabled={busy} onClick={runDemo}>
        {busy ? "Processing…" : "Analyze camera sample"}
      </button>
      <ol className="step-list">
        {ANALYZE_STEPS.map((label, index) => {
          const state = phase === "done" ? "done" : phase === "running" && index === 0 ? "done" : phase === "running" && index === 1 ? "now" : "wait";
          return (
            <li key={label} className={`step ${state === "now" ? "step-now" : ""} ${state === "done" ? "step-done" : ""}`}>
              <span className="step-index">{index + 1}</span>{label}
            </li>
          );
        })}
      </ol>
      <form
        className="drop"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          const file = event.dataTransfer.files[0];
          if (file && !busy) upload(file);
        }}
      >
        <p style={{ marginTop: 0 }}>Or choose a video file on this computer. It is a file you select, not a connected camera.</p>
        <input
          aria-label="Video file"
          type="file"
          accept="video/mp4,video/webm,video/quicktime,.mkv,.avi"
          disabled={busy}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) upload(file);
          }}
        />
      </form>
      {message && <p>{message}</p>}
      {findings && <section className="card card-pad" style={{ marginTop: "0.75rem" }}><h2 className="section-title">Stored result</h2><p>{findings}</p></section>}
      {error && <p className="warn">{error}</p>}
      {message.startsWith("Stored") && <Link to="/centres/TC-PB-001">Open the centre</Link>}
    </>
  );
}

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/centres/:centreId" element={<CentrePage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/alerts/:alertId" element={<AlertPage />} />
        <Route path="/analyze" element={<AnalyzePage />} />
      </Routes>
    </Shell>
  );
}
