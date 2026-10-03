import type { Alert } from "./api";

export type Tone = "alert" | "review" | "ok" | "neutral" | "info";

export function toneForStatus(status: string): Tone {
  if (status === "ALERT" || status === "high") return "alert";
  if (status === "REVIEW" || status === "medium" || status === "under_review") return "review";
  if (status === "COMPLIANT" || status === "resolved") return "ok";
  return "neutral";
}

export function alertStatusLabel(status: string) {
  if (status === "new") return "Open";
  if (status === "under_review") return "Under review";
  if (status === "resolved") return "Resolved";
  return status;
}

export function severityLabel(severity: string) {
  if (severity === "high") return "High";
  if (severity === "medium") return "Medium";
  return severity;
}

export function typeLabel(alertType: string) {
  if (alertType === "attendance") return "Attendance";
  if (alertType === "infrastructure") return "Infrastructure";
  return alertType;
}

export function figuresFromDescription(description: string): { label: string; value: string }[] | null {
  const attendance = description.match(/^Submitted attendance (\d+)\. Peak person count (\d+)\. Gap (-?\d+)\.$/);
  if (attendance) {
    return [
      { label: "Submitted", value: attendance[1] },
      { label: "Observed", value: attendance[2] },
      { label: "Gap", value: attendance[3] },
    ];
  }
  const infrastructure = description.match(/^.+ sanctioned (\d+)\. Peak (.+) count (\d+)\. Gap (-?\d+)\. Source: AI_DETECTED\.$/);
  if (infrastructure) {
    return [
      { label: "Sanctioned", value: infrastructure[1] },
      { label: infrastructure[2], value: infrastructure[3] },
      { label: "Gap", value: infrastructure[4] },
    ];
  }
  return null;
}

export function recordedText(figures: { label: string; value: string }[]) {
  const item = figures.find((figure) => figure.label === "Submitted" || figure.label === "Sanctioned");
  return item ? `${item.label} ${item.value}` : "—";
}

export function observedText(figures: { label: string; value: string }[]) {
  const item = figures.find((figure) => figure.label !== "Submitted" && figure.label !== "Sanctioned" && figure.label !== "Gap");
  if (!item) return "—";
  if (item.label === "Observed") return item.value;
  return `${item.value} ${item.label}`;
}

export function gapValue(figures: { label: string; value: string }[] | null) {
  return figures?.find((figure) => figure.label === "Gap")?.value ?? null;
}

export function relativeTime(iso: string) {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const minutes = Math.round((Date.now() - then) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

export function matchesQuery(alert: Alert, query: string) {
  const haystack = `${alert.description} ${alert.alert_type} ${alert.centre_id} ${alert.status} ${alert.severity}`.toLowerCase();
  return haystack.includes(query.trim().toLowerCase());
}
