"use client";

import { Top } from "@/lib/api";
import TopAccordion from "./TopAccordion";

export default function TopList({ grouped, onTopFocus, defaultOpen = true, focusDate }: { grouped: Map<string, Top[]>; onTopFocus?: (date: string) => void; defaultOpen?: boolean; focusDate?: string }) {
  if (grouped.size === 0) {
    return <p className="text-sm text-zinc-400 mt-4">Keine Tagesordnungspunkte gefunden.</p>;
  }

  return (
    <div className="space-y-6">
      {[...grouped.entries()].map(([date, tops]) => (
        <div key={date}>
          <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">
            {date} · {tops.length} TOP{tops.length !== 1 ? "s" : ""}
          </h2>
          <div className="space-y-1">
            {tops.map((top, i) => {
              const isFocusFirst = i === 0 && date === focusDate;
              return (
                <TopAccordion
                  key={isFocusFirst ? `${top.top_key}-focus-${focusDate}` : top.top_key}
                  top={top}
                  defaultOpen={isFocusFirst || (defaultOpen && i === 0)}
                  autoScroll={isFocusFirst}
                  onOpen={() => onTopFocus?.(top.date)}
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
