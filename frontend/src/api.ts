export type Alert = {
  id: string;
  centre_id: string;
  analysis_id: string;
  alert_type: string;
  severity: string;
  status: string;
  description: string;
  evidence_path: string | null;
  created_at: string;
};

export type Dashboard = {
  note: string;
  centres_monitored: number;
  open_attendance_alerts: number;
  open_infrastructure_alerts: number;
  assessed_checks: number;
  compliant_checks: number;
  centres: {
    id: string;
    name: string;
    location: string;
    status: string;
    observed_presence: number | null;
    submitted_attendance: number | null;
  }[];
  alerts: Alert[];
  activity: { created_at: string; text: string; analysis_id: string }[];
};

export type CentreDetail = {
  centre: {
    id: string;
    name: string;
    location: string;
    submitted_attendance: number;
  };
  inventory: {
    item_key: string;
    label: string;
    sanctioned: number;
    observed: number | null;
    variance: number | null;
    status: string;
    source: string;
    coco_name: string | null;
    note: string;
  }[];
  latest_analysis: null | {
    analysis_id: string;
    occupancy: { per_frame_counts: number[]; observed_presence: number };
    compliance: {
      attendance: { expected: number | null; observed: number; variance: number | null; status: string };
    };
    evidence: { peak_frame: string };
  };
  alerts: Alert[];
};

async function read<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  dashboard: () => read<Dashboard>("/api/dashboard"),
  centre: (id: string) => read<CentreDetail>(`/api/centres/${id}`),
  alerts: () => read<Alert[]>("/api/alerts"),
  alert: (id: string) => read<Alert>(`/api/alerts/${id}`),
  setStatus: (id: string, status: string) =>
    read<Alert>(`/api/alerts/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }),
  analyzeDemo: () =>
    read<{
      alerts: Alert[];
      report: {
        analysis_id: string;
        occupancy?: { observed_presence: number };
        compliance?: { attendance: { expected: number | null; observed: number; variance: number | null; status: string } };
      };
    }>("/api/analyze/demo", { method: "POST" }),
  analyzeVideo: (file: File) => {
    const body = new FormData();
    body.append("video", file);
    body.append("centre_id", "TC-PB-001");
    return read<{
      analysis_id: string;
      status: string;
      observed_presence: number;
      expected_attendance: number | null;
      variance: number | null;
    }>("/api/analyze/video", { method: "POST", body });
  },
};
