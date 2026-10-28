"use client";

import { useEffect, useState } from "react";
import { Top } from "@/lib/api";
import TopAccordion from "./TopAccordionProto";

function readOpenTopsSnapshot(): string[] | null {
  try {
    const raw = sessionStorage.getItem("openTops");
    return raw !== null ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function formatLongDate(date: string): string {
  const [day, month, year] = date.split(".");
  return new Date(+year, +month - 1, +day).toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

export default function TopListProto({ grouped, onTopFocus, defaultOpen = true, focusDate, longDate = false, alwaysOpenFirst = false }: { grouped: Map<string, Top[]>; onTopFocus?: (date: string) => void; defaultOpen?: boolean; focusDate?: string; longDate?: boolean; alwaysOpenFirst?: boolean }) {
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
      {[...grouped.entries()].map(([date, tops], gi) => (
        <div key={date}>
          <h2 className={longDate ? "mb-2 text-base font-normal text-zinc-700 dark:text-zinc-300" : "mb-3 pb-2 border-b-2 border-[#3e3ac6]/40 dark:border-zinc-600 text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400"}>
            {longDate ? formatLongDate(date) : date}
            <span className={longDate ? "ml-2 font-normal text-zinc-500 dark:text-zinc-400" : undefined}> · {tops.length} TOP{tops.length !== 1 ? "s" : ""}</span>
          </h2>
          <div>
            {tops.map((top, i) => {
              const isFocusFirst = i === 0 && date === focusDate;
              // alwaysOpenFirst: exactly one TOP is open on load — the very first on the page,
              // also in search results — as a nudge to click. Keyed so it re-opens when it changes.
              const isPageFirst = alwaysOpenFirst && gi === 0 && i === 0;
              return (
                <TopAccordion
                  key={isPageFirst ? `${top.top_key}-first` : isFocusFirst ? `${top.top_key}-focus-${focusDate}` : top.top_key}
                  top={top}
                  defaultOpen={alwaysOpenFirst ? isPageFirst : isFocusFirst || (defaultOpen && i === 0)}
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
