import { VoteResult } from "@/lib/api";
import { VOTE_COLOR, floorLayout } from "@/lib/voteVisuals";

const OUTER = 88;
const HOLE = 64;
const INNER = 48;

// Donut ring showing the Ja/Nein/Enthalten split, with the Angenommen/
// Abgelehnt outcome as a colored check/cross at the ring's own center
// instead of a separate badge. Segment proportions use the same
// minimum-visible-share floor as the per-party VoteBar, so a small
// minority (e.g. a handful of defectors) doesn't vanish into a hairline.
export default function VoteOutcomeRing({ vote }: { vote: VoteResult }) {
  const outcomeColor = vote.angenommen ? VOTE_COLOR.ja : VOTE_COLOR.nein;
  const segs = floorLayout([
    { key: "ja", value: vote.ja },
    { key: "nein", value: vote.nein },
    { key: "enthalten", value: vote.enthalten },
  ]);

  let cum = 0;
  const stops: string[] = [];
  for (const s of segs) {
    if (s.pct <= 0) continue;
    const from = cum * 100;
    cum += s.pct;
    const to = cum * 100;
    stops.push(`${VOTE_COLOR[s.key]} ${from}% ${to}%`);
  }
  const gradient = `conic-gradient(${stops.join(", ")})`;

  return (
    <div className="flex flex-col items-center py-1">
      <div className="flex items-center justify-center gap-4">
        <span className="flex items-center gap-1 text-lg font-bold text-zinc-800 dark:text-zinc-100">
          <span
            className="flex items-center justify-center w-4 h-4 rounded-full text-white text-[9px]"
            style={{ background: VOTE_COLOR.ja }}
          >
            ✓
          </span>
          {vote.ja}
        </span>

        <div className="relative shrink-0" style={{ width: OUTER, height: OUTER }}>
          <div className="absolute inset-0 rounded-full" style={{ background: gradient }} />
          <div
            className="absolute rounded-full bg-zinc-50 dark:bg-zinc-900"
            style={{
              width: HOLE,
              height: HOLE,
              top: (OUTER - HOLE) / 2,
              left: (OUTER - HOLE) / 2,
            }}
          />
          <div
            className="absolute flex items-center justify-center font-bold text-2xl"
            style={{
              width: INNER,
              height: INNER,
              top: (OUTER - INNER) / 2,
              left: (OUTER - INNER) / 2,
              color: outcomeColor,
            }}
          >
            {vote.angenommen ? "✓" : "✗"}
          </div>
        </div>

        <span className="flex items-center gap-1 text-lg font-bold text-zinc-800 dark:text-zinc-100">
          <span
            className="flex items-center justify-center w-4 h-4 rounded-full text-white text-[9px]"
            style={{ background: VOTE_COLOR.nein }}
          >
            ✗
          </span>
          {vote.nein}
        </span>
      </div>

      {vote.enthalten > 0 && (
        <div className="mt-1.5 flex items-center gap-1 text-[10px] text-zinc-500 dark:text-zinc-400">
          <span className="w-2 h-2 rounded-full inline-block" style={{ background: VOTE_COLOR.enthalten }} />
          {vote.enthalten} Enth.
        </div>
      )}
    </div>
  );
}
