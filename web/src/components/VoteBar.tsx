import { VOTE_COLOR as COLOR, floorLayout } from "@/lib/voteVisuals";

export interface VoteCountsBasic {
  ja: number;
  nein: number;
  enthalten: number;
}

// Segmented bar with a guaranteed minimum-visible-width floor per nonzero
// category. Counts are labeled below, not squeezed inside the bar, so a
// floored sliver still carries its number legibly.
export function VoteBar({ ja, nein, enthalten, compact }: VoteCountsBasic & { compact?: boolean }) {
  const segs = floorLayout([
    { key: "ja", value: ja },
    { key: "nein", value: nein },
    { key: "enthalten", value: enthalten },
  ]);
  return (
    <div>
      <div className={`flex w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800 ${compact ? "h-2" : "h-3"}`}>
        {segs
          .filter((s) => s.pct > 0)
          .map((s) => (
            <div key={s.key} style={{ width: `${s.pct * 100}%`, background: COLOR[s.key] }} />
          ))}
      </div>
      <div className={`mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 ${compact ? "text-[10px]" : "text-xs"} text-zinc-500 dark:text-zinc-400`}>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full inline-block" style={{ background: COLOR.ja }} />
          {ja} Ja
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full inline-block" style={{ background: COLOR.nein }} />
          {nein} Nein
        </span>
        {enthalten > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full inline-block" style={{ background: COLOR.enthalten }} />
            {enthalten} Enth.
          </span>
        )}
      </div>
    </div>
  );
}
