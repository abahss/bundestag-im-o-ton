export const VOTE_COLOR = {
  ja: "#10b981",
  nein: "#ef4444",
  enthalten: "#a1a1aa",
};

export interface VoteSeg {
  key: "ja" | "nein" | "enthalten";
  value: number;
}

// Guarantees a minimum visible share per nonzero category, so a
// proportionally tiny count (e.g. a handful of defectors) still renders as
// a real, colored segment instead of a hairline.
export function floorLayout(segs: VoteSeg[], floor = 0.07) {
  const total = segs.reduce((s, x) => s + x.value, 0);
  if (total === 0) return segs.map((s) => ({ ...s, pct: 0 }));

  const flexible: VoteSeg[] = [];
  const floored = new Map<string, number>();
  let usedByFloor = 0;
  for (const s of segs) {
    const raw = s.value / total;
    if (s.value > 0 && raw < floor) {
      floored.set(s.key, floor);
      usedByFloor += floor;
    } else if (s.value > 0) {
      flexible.push(s);
    }
  }
  const remaining = 1 - usedByFloor;
  const flexTotal = flexible.reduce((s, x) => s + x.value, 0);

  return segs.map((s) => {
    if (s.value === 0) return { ...s, pct: 0 };
    if (floored.has(s.key)) return { ...s, pct: floored.get(s.key)! };
    return { ...s, pct: flexTotal > 0 ? (s.value / flexTotal) * remaining : 0 };
  });
}
