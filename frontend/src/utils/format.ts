export function formatRelativeDays(days: number): string {
  if (days < 1) return "today";
  if (days === 1) return "1 day ago";
  if (days < 30) return `${days} days ago`;
  if (days < 365) return `${Math.round(days / 30)} months ago`;
  return `${(days / 365).toFixed(1)} years ago`;
}

export function formatAgeDays(days: number): string {
  if (days < 30) return `${days} days`;
  if (days < 365) return `${Math.round(days / 30)} months (${days.toLocaleString()} days)`;
  return `${(days / 365).toFixed(1)} years (${days.toLocaleString()} days)`;
}

export function formatLastPush(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const days = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
  return `${iso.split("T")[0]} · ${formatRelativeDays(days)}`;
}

export function parseDays(value: string): number | null {
  const m = value.match(/(\d[\d,]*)\s*days?/);
  if (!m) return null;
  return parseInt(m[1].replace(/,/g, ""), 10);
}
