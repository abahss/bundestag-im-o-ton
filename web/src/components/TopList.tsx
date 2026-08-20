"use client";

import { useEffect, useState } from "react";
import { Top } from "@/lib/api";
import TopAccordion from "./TopAccordion";

function readOpenTopsSnapshot(): string[] | null {
  try {
    const raw = sessionStorage.getItem("openTops");
    return raw !== null ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function TopList({ grouped, onTopFocus, defaultOpen = true, focusDate }: { grouped: Map<string, Top[]>; onTopFocus?: (date: string) => void; defaultOpen?: boolean; focusDate?: string }) {
  // Starts `null` so the client's first (hydration) render matches the
  // server-rendered HTML — sessionStorage doesn't exist during SSR, so
  // reading it any earlier than an effect would mismatch. The two effects
  // below then ping-pong it: the first reads the real snapshot post-hydration
  // (if TopList just had a genuine fresh mount, e.g. back-navigation); the
  // second immediately reverts it to null on the next commit, once children
  // have each had exactly one chance to consult it (see TopAccordion). That
  // reversion is what keeps accordions that mount later — e.g. the user
  // switching dates, since TopList itself stays mounted across that — from
  // picking up a now-outdated snapshot.
  const [restoreOpenKeys, setRestoreOpenKeys] = useState<string[] | null>(null);
  useEffect(() => {
    const snapshot = readOpenTopsSnapshot();
    if (snapshot !== null) setRestoreOpenKeys(snapshot);
  }, []);
  useEffect(() => {
    if (restoreOpenKeys !== null) setRestoreOpenKeys(null);
  }, [restoreOpenKeys]);

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
                  restoreOpenKeys={restoreOpenKeys}
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
