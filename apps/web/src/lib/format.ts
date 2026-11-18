export const fmt = (n: number) => n.toLocaleString("en-US");
export const pct = (x: number, digits = 1) => `${(x * 100).toFixed(digits)}%`;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function monthLabel(isoMonth: string) {
  const [y, m] = isoMonth.split("-").map(Number);
  return `${MONTHS[m - 1]} ${y}`;
}
export function dateLabel(iso: string | null) {
  if (!iso) return "Undated";
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}
export const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .filter((_, i, a) => i === 0 || i === a.length - 1)
    .map((p) => p[0]!.toUpperCase())
    .join("");
