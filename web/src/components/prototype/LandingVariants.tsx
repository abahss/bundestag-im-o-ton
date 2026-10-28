"use client";

// PROTOTYPE — wipe me. Three structurally different landing-page variants for
// a 15–18 audience, rendered on the existing "/" route via ?variant=A|B|C|D.
// A = current page (rendered by HomeClient itself). Question being answered:
// "How can the landing page be less text-heavy and more inviting to teens?"
//
//   B  Chips-first   — big headline, search + tappable topic chips, intro
//                      shrunk to three icon pills, details behind a toggle.
//   C  Heute-Karten  — dark hero with the latest session as swipeable,
//                      colourful story cards; intro is a single line.
//   D  Zwei Modi     — segmented control "Thema suchen | Nach Datum":
//                      only one navigation tool visible at a time.

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Top } from "@/lib/api";
import Calendar from "./CalendarProto";
import TopList from "./TopListProto";
import ThemeToggle from "@/components/ThemeToggle";
import DomeBackdrop from "./DomeBackdrop";
import ProtoThemeFlag from "./ProtoThemeFlag";

export const VARIANTS = [
  { key: "A", name: "Aktuell" },
  { key: "B", name: "Chips-first" },
  { key: "C", name: "Heute-Karten" },
  { key: "D", name: "Zwei Modi" },
  { key: "E", name: "Zwei Spalten" },
  { key: "F", name: "Web E / Mobil D" },
] as const;

export type LandingProps = {
  sessionDates: Set<string>;
  search: string;
  onSearchChange: (value: string) => void;
  onSearchClear: () => void;
  searchMatches: Top[];
  searchMatchDates: Set<string>;
  selectedDate: string;
  calYear: number;
  calMonth: number;
  onSelect: (date: string) => void;
  onMonthChange: (year: number, month: number) => void;
  onTopFocus: (date: string) => void;
  grouped: Map<string, Top[]>;
  sessionTops: Top[];
};

const TOPIC_CHIPS = [
  "Klima",
  "Rente",
  "Bürgergeld",
  "Wehrpflicht",
  "Social Media",
  "Bildung",
  "Gesundheit",
  "Mobilität",
];

function shortId(topId: string): string {
  return topId
    .replace("Tagesordnungspunkt", "TOP")
    .replace("Zusatzpunkt", "ZP")
    .replace("Einzelplan", "EP");
}

const CARD_GRADIENTS = [
  "from-[#3e3ac6] to-[#6f6be0] text-white",
  "from-[#ceec97] to-[#e3f5c0] text-[#2a2790]",
  "from-[#2a2790] to-[#3e3ac6] text-white",
  "from-[#b5df6f] to-[#ceec97] text-[#2a2790]",
  "from-[#6f6be0] to-[#3e3ac6] text-white",
];

function SearchBox({ search, onChange, onClear, big }: { search: string; onChange: (v: string) => void; onClear: () => void; big?: boolean }) {
  return (
    <div className="relative">
      <svg aria-hidden="true" viewBox="0 0 20 20" className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-zinc-400" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <circle cx="9" cy="9" r="6" />
        <path d="m14 14 4 4" />
      </svg>
      <input
        type="text"
        value={search}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Welches Thema interessiert dich?"
        className={`w-full pl-11 pr-10 rounded-md border-2 border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 text-base focus:outline-none focus:border-[#3e3ac6] ${big ? "py-4 text-lg shadow-lg" : "py-3"}`}
      />
      {search && (
        <button onClick={onClear} aria-label="Suche zurücksetzen" className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600">
          ✕
        </button>
      )}
    </div>
  );
}

function Chips({ onPick, twoRows }: { onPick: (v: string) => void; twoRows?: boolean }) {
  const chip = (label: string) => (
    <button
      key={label}
      onClick={() => onPick(label)}
      className={`rounded-md bg-[#e2e1f6] hover:bg-[#3e3ac6] hover:text-white text-[#3e3ac6] dark:text-white dark:bg-zinc-800 dark:hover:bg-zinc-700 font-semibold transition-colors whitespace-nowrap ${
        twoRows ? "px-2.5 sm:px-3.5 py-2 text-xs sm:text-sm" : "px-3.5 py-2 text-sm"
      }`}
    >
      {label}
    </button>
  );
  // twoRows: fixed 4 + 4 split, pills keep their natural width
  if (twoRows) {
    const half = Math.ceil(TOPIC_CHIPS.length / 2);
    return (
      <div className="flex flex-col gap-2">
        {[TOPIC_CHIPS.slice(0, half), TOPIC_CHIPS.slice(half)].map((row, i) => (
          <div key={i} className="flex justify-center gap-2">{row.map(chip)}</div>
        ))}
      </div>
    );
  }
  return <div className="flex flex-wrap gap-2 justify-center">{TOPIC_CHIPS.map(chip)}</div>;
}

function IconPills() {
  return (
    <ul className="grid grid-cols-3 gap-2 text-center text-xs sm:text-sm font-semibold text-[#3e3ac6] dark:text-white">
      {[
        ["💬", "Echte Zitate"],
        ["🗳️", "Wer stimmt wie ab?"],
        ["🤖", "KI fasst's kurz"],
      ].map(([e, t]) => (
        <li key={t} className="rounded-md border border-zinc-300 dark:border-zinc-600 bg-[#ceec97]/40 dark:bg-zinc-900 px-2 py-3">
          <div className="text-2xl mb-1" aria-hidden="true">{e}</div>
          {t}
        </li>
      ))}
    </ul>
  );
}

function Details() {
  const [open, setOpen] = useState(false);
  return (
    <div className="text-center">
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="text-sm text-[#3e3ac6] dark:text-[#ceec97] font-medium hover:underline">
        {open ? "Schließen" : "Wie funktioniert das?"}
      </button>
      {open && (
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-300 text-left max-w-xl mx-auto leading-relaxed">
          Nach jeder Sitzung veröffentlicht der Bundestag ein Wortprotokoll. Diese App fasst es mit KI neutral zusammen – mit Zitaten als Beleg und Link zur Quelle. Mehr im <a href="/faq" className="underline">FAQ</a>.
        </p>
      )}
    </div>
  );
}

function Header({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div className="flex-1">{children}</div>
      <ThemeToggle />
    </div>
  );
}

function newestDate(dates: Set<string>): string | undefined {
  const toTime = (d: string) => {
    const [day, month, year] = d.split(".");
    return new Date(+year, +month - 1, +day).getTime();
  };
  return [...dates].sort((a, b) => toTime(b) - toTime(a))[0];
}

// Separates the search tools from the list below and names what the list shows:
// the newest session by default, switching to "Suchergebnisse" while searching.
function Divider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 mb-3 text-[#3e3ac6] dark:text-[#ceec97]">
      <span className="h-0.5 w-6 bg-current" aria-hidden="true" />
      <h2 className="text-sm font-bold uppercase tracking-wider whitespace-nowrap">{label}</h2>
      <span className="h-0.5 flex-1 bg-current opacity-40" aria-hidden="true" />
    </div>
  );
}

function Results({ p, showCount = true }: { p: LandingProps; showCount?: boolean }) {
  return (
    <>
      <Divider
        label={
          p.search.trim()
            ? "Suchergebnisse"
            : p.selectedDate === newestDate(p.sessionDates)
              ? "Neueste Sitzung"
              : "Frühere Sitzung"
        }
      />
      {showCount && p.search.trim() && (
        <p className="text-xs text-zinc-400 mb-4">
          {p.searchMatches.length} Ergebnis{p.searchMatches.length !== 1 ? "se" : ""} in allen Sitzungen
        </p>
      )}
      <TopList
        key={p.search.trim() ? "search" : "browse"}
        grouped={p.grouped}
        onTopFocus={p.onTopFocus}
        defaultOpen={!p.search.trim()}
        focusDate={p.search.trim() ? p.selectedDate : undefined}
        longDate
        alwaysOpenFirst
      />
    </>
  );
}

function FaqHint({ className = "" }: { className?: string }) {
  const variant = useSearchParams().get("variant");
  const href = variant ? `/faq?variant=${variant}` : "/faq";
  return (
    <p className={`text-sm text-zinc-600 dark:text-zinc-300 ${className}`}>
      Noch Fragen? Schau ins{" "}
      <a href={href} className="font-semibold text-[#3e3ac6] dark:text-[#ceec97] underline">FAQ</a>{" "}
      oder schreib mir über den Feedback-Button unten rechts.
    </p>
  );
}

function CalendarBlock({ p }: { p: LandingProps }) {
  // Solid backing with a light border and a faint shadow: lifts off the dome pattern, but gently.
  return (
    <div className="rounded-md border border-zinc-200 bg-white p-3 shadow-sm dark:border-zinc-700 dark:bg-zinc-950">
      <Calendar
        sessionDates={p.sessionDates}
        highlightedDates={p.search.trim() ? p.searchMatchDates : undefined}
        selectedDate={p.selectedDate}
        year={p.calYear}
        month={p.calMonth}
        onSelect={p.onSelect}
        onMonthChange={p.onMonthChange}
      />
    </div>
  );
}

// ── E ───────────────────────────────────────────────────────────────
// Desktop: sticky tool column (search, chips, calendar) left, wide list right.
// Mobile: single column, calendar tucked behind a toggle.
function VariantE(p: LandingProps) {
  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      <Header>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-center text-[#3e3ac6] dark:text-white">
          Politik auf einen <span className="bg-[#ceec97] text-[#3e3ac6] px-2 rounded-sm">Blick.</span>
        </h1>
        <p className="text-center mt-2 text-zinc-500">Knappe Zusammenfassungen der Bundestagssitzungen</p>
      </Header>
      <div className="grid gap-6 md:grid-cols-[20rem_minmax(0,1fr)] md:gap-10">
        <aside className="space-y-4 md:sticky md:top-4 md:self-start">
          <SearchBox search={p.search} onChange={p.onSearchChange} onClear={p.onSearchClear} />
          <Chips onPick={p.onSearchChange} />
          <div className="hidden md:block pt-2"><CalendarBlock p={p} /></div>
          <FaqHint className="hidden md:block pt-1" />
          <details className="md:hidden">
            <summary className="cursor-pointer text-sm font-semibold text-[#3e3ac6] dark:text-[#ceec97]">Kalender öffnen</summary>
            <div className="max-w-xs pt-3"><CalendarBlock p={p} /></div>
          </details>
        </aside>
        <section className="min-w-0"><Results p={p} /></section>
      </div>
    </div>
  );
}

// ── F ───────────────────────────────────────────────────────────────
// Chosen combination: E on desktop (md+), D on mobile. Both layouts are rendered
// and swapped with CSS, same pattern as the current page.
function VariantF(p: LandingProps) {
  return (
    <>
      <div className="hidden md:block"><VariantE {...p} /></div>
      <div className="md:hidden"><VariantD {...p} /></div>
    </>
  );
}

// ── B ───────────────────────────────────────────────────────────────
function VariantB(p: LandingProps) {
  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
      <Header>
        <h1 className="text-4xl sm:text-5xl font-extrabold text-center leading-tight text-[#3e3ac6] dark:text-white">
          Politik auf einen <span className="bg-[#ceec97] text-[#3e3ac6] px-2 rounded-sm">Blick.</span>
        </h1>
        <p className="text-center mt-2 text-zinc-500">Knappe Zusammenfassungen der Bundestagssitzungen</p>
      </Header>
      <SearchBox search={p.search} onChange={p.onSearchChange} onClear={p.onSearchClear} big />
      <Chips onPick={p.onSearchChange} />
      <IconPills />
      <Details />
      <div className="pt-2 flex flex-col gap-6 md:flex-row md:gap-8">
        <div className="md:w-72 shrink-0"><CalendarBlock p={p} /></div>
        <div className="flex-1 min-w-0"><Results p={p} /></div>
      </div>
      <FaqHint />
    </div>
  );
}

// ── C ───────────────────────────────────────────────────────────────
function VariantC(p: LandingProps) {
  const [showCal, setShowCal] = useState(false);
  const searching = !!p.search.trim();
  return (
    <div>
      <section className="bg-gradient-to-br from-[#3e3ac6] to-[#2a2790] text-white">
        <div className="max-w-5xl mx-auto px-4 pt-5 pb-8 space-y-5">
          <div className="flex items-center justify-between">
            <span className="font-extrabold tracking-tight">Bundestag im O-Ton</span>
            <ThemeToggle />
          </div>
          <div>
            <p className="text-[#ceec97] font-bold text-sm uppercase tracking-wider">Sitzung vom {p.selectedDate || "—"}</p>
            <h1 className="text-3xl sm:text-4xl font-extrabold leading-tight mt-1">
              Politik auf einen <span className="text-[#ceec97]">Blick.</span>
            </h1>
            <p className="mt-2 text-white/80">Knappe Zusammenfassungen der Bundestagssitzungen</p>
          </div>
          {!searching && (
            <div className="-mx-4 px-4 flex gap-3 overflow-x-auto snap-x snap-mandatory pb-2 [scrollbar-width:none]">
              {p.sessionTops.slice(0, 12).map((t, i) => (
                <button
                  key={t.top_key}
                  onClick={() => p.onSearchChange(t.title)}
                  className={`snap-start shrink-0 w-44 h-56 rounded-md bg-gradient-to-br ${CARD_GRADIENTS[i % CARD_GRADIENTS.length]} text-white p-4 flex flex-col justify-between text-left shadow-xl active:scale-95 transition-transform`}
                >
                  <span className="self-start rounded-sm bg-black/20 px-2.5 py-1 text-xs font-bold uppercase tracking-wide">{shortId(t.top_id)}</span>
                  <span className="font-bold leading-snug line-clamp-5 text-sm">{t.title}</span>
                </button>
              ))}
            </div>
          )}
          <SearchBox search={p.search} onChange={p.onSearchChange} onClear={p.onSearchClear} />
        </div>
      </section>
      <div className="max-w-5xl mx-auto px-4 py-6 space-y-4">
        <p className="text-sm text-zinc-500 text-center">💬 Echte Zitate · 🗳️ Abstimmungen · 🤖 KI-Kurzfassung</p>
        <button onClick={() => setShowCal((s) => !s)} className="text-sm font-semibold text-[#3e3ac6] dark:text-[#ceec97]">
          {showCal ? "Kalender ausblenden" : "Andere Sitzung wählen"}
        </button>
        {showCal && <div className="max-w-xs"><CalendarBlock p={p} /></div>}
        <Results p={p} />
        <FaqHint />
      </div>
    </div>
  );
}

// ── D ───────────────────────────────────────────────────────────────
function VariantD(p: LandingProps) {
  const [mode, setMode] = useState<"thema" | "datum">("thema");
  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-5">
      <Header>
        <h1 className="text-3xl font-extrabold text-center text-[#3e3ac6] dark:text-white">
          Politik auf einen <span className="bg-[#ceec97] text-[#3e3ac6] px-2 rounded-sm">Blick.</span>
        </h1>
        <p className="text-center mt-2 text-zinc-500">Knappe Zusammenfassungen der Bundestagssitzungen</p>
      </Header>
      <div role="tablist" aria-label="Wie willst du stöbern?" className="grid grid-cols-2 p-1 rounded-md border border-zinc-300 dark:border-zinc-600 bg-zinc-100 dark:bg-zinc-900 font-semibold text-sm">
        {([["thema", "Thema suchen"], ["datum", "Nach Datum"]] as const).map(([k, label]) => (
          <button
            key={k}
            role="tab"
            aria-selected={mode === k}
            onClick={() => setMode(k)}
            className={`py-2.5 rounded-sm transition-colors ${mode === k ? "bg-[#3e3ac6] text-white" : "text-zinc-500"}`}
          >
            {label}
          </button>
        ))}
      </div>
      {mode === "thema" ? (
        <div className="space-y-4">
          <SearchBox search={p.search} onChange={p.onSearchChange} onClear={p.onSearchClear} />
          <Chips onPick={p.onSearchChange} twoRows />
        </div>
      ) : (
        <div className="max-w-xs mx-auto"><CalendarBlock p={p} /></div>
      )}
      <Results p={p} />
      <FaqHint />
    </div>
  );
}

export function LandingVariant(props: LandingProps & { variant: string }) {
  const { variant, ...p } = props;
  return (
    <div className="proto-fonts relative isolate overflow-x-clip">
      <DomeBackdrop />
      <ProtoThemeFlag />
      {variant === "B" && <VariantB {...p} />}
      {variant === "C" && <VariantC {...p} />}
      {variant === "D" && <VariantD {...p} />}
      {variant === "E" && <VariantE {...p} />}
      {variant === "F" && <VariantF {...p} />}
    </div>
  );
}

// ── Switcher ────────────────────────────────────────────────────────
// Sits at bottom-16 centre: the footer is fixed at bottom-0 on desktop and the
// feedback button lives bottom-right, so bottom-centre above the footer is free.
export function PrototypeSwitcher({ current }: { current: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const idx = Math.max(0, VARIANTS.findIndex((v) => v.key === current));

  function go(delta: number) {
    const next = VARIANTS[(idx + delta + VARIANTS.length) % VARIANTS.length].key;
    const q = new URLSearchParams(params.toString());
    q.set("variant", next);
    router.replace(`${pathname}?${q.toString()}`, { scroll: false });
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = document.activeElement as HTMLElement | null;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable)) return;
      if (e.key === "ArrowLeft") go(-1);
      if (e.key === "ArrowRight") go(1);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (process.env.NODE_ENV === "production") return null;
  return (
    <div className="fixed bottom-16 left-1/2 -translate-x-1/2 z-[80] flex items-center gap-3 rounded-full bg-black text-white px-4 py-2 shadow-2xl text-sm">
      <button onClick={() => go(-1)} aria-label="Vorherige Variante" className="px-2 hover:text-[#ceec97]">←</button>
      <span className="font-mono whitespace-nowrap">{VARIANTS[idx].key} — {VARIANTS[idx].name}</span>
      <button onClick={() => go(1)} aria-label="Nächste Variante" className="px-2 hover:text-[#ceec97]">→</button>
    </div>
  );
}
