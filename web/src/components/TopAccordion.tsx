"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Top } from "@/lib/api";

function navLabel(top: Top): string {
  return top.top_id
    .replace("Tagesordnungspunkt ", "TOP ")
    .replace("Zusatzpunkte ", "ZP ")
    .replace("Zusatzpunkt ", "ZP ")
    .replace(/ und /g, ", ")
    .replace(/ sowie /g, ", ")
    .replace(/ bis /g, " - ");
}

export default function TopAccordion({ top, defaultOpen = false, onOpen, autoScroll = false }: { top: Top; defaultOpen?: boolean; onOpen?: () => void; autoScroll?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);

  // Restore open state from sessionStorage after hydration. Every open
  // accordion is tracked (not just the one last navigated from), so
  // returning via the back button reproduces the whole expanded/collapsed
  // layout the user left behind, not just a single re-opened item. This is
  // a one-shot read of a snapshot written elsewhere (see the "Zusammenfassungen
  // ansehen" handler below) — every accordion only ever writes its own local
  // `open` state, never sessionStorage directly, so there's no race between
  // sibling accordions restoring concurrently on mount.
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("openTops");
      if (raw !== null) {
        const openTops: string[] = JSON.parse(raw);
        setOpen(openTops.includes(top.top_key));
      }
    } catch {}
  }, []);

  const router = useRouter();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!autoScroll || !ref.current) return;
    const footer = document.querySelector("footer");
    const footerH = footer ? footer.getBoundingClientRect().height : 0;
    const rect = ref.current.getBoundingClientRect();
    const visibleBottom = window.innerHeight - footerH;
    if (rect.top < 0) {
      window.scrollTo({ top: window.scrollY + rect.top - 8, behavior: "smooth" });
    } else if (rect.bottom > visibleBottom) {
      window.scrollTo({ top: window.scrollY + rect.bottom - visibleBottom + 8, behavior: "smooth" });
    }
  }, []);

  const label = navLabel(top);
  const topic = top.topic || top.title || top.subtitle || label;
  const contentId = `top-content-${top.top_key.replace(/\s+/g, "-")}`;

  // Bundled TOPs (a/b/c-style subtopics) carry no title/subtitle of their
  // own — build a preview from the subtopics so there's still a clamped
  // line above the CTA button instead of the button leading straight off.
  const previewText =
    top.title && top.title !== topic
      ? top.title
      : top.subtopics?.length > 0
      ? top.subtopics.map((s) => `${s.key}) ${s.title}`).join("  ")
      : "";

  return (
    <div
      ref={ref}
      data-top-key={top.top_key}
      data-open={open}
      className="rounded-xl border border-zinc-100 dark:border-zinc-800"
    >
      <button
        onClick={() => { const next = !open; setOpen(next); if (next) onOpen?.(); }}
        aria-expanded={open}
        aria-controls={contentId}
        className={`w-full flex items-center justify-between px-4 py-3 text-left hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors ${open ? "rounded-t-xl" : "rounded-xl"}`}
      >
        <div className="min-w-0 flex flex-wrap items-baseline gap-x-2">
          <span className="text-xs font-semibold text-[#219EBC] shrink-0">{label}</span>
          <span className="text-sm text-zinc-800 dark:text-zinc-200 break-words">{topic}</span>
          {top.has_abstimmung && (
            <span className="relative group shrink-0">
              <span>🗳️</span>
              <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 whitespace-nowrap rounded-lg bg-zinc-800 text-white text-xs px-2 py-1 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-75 z-10 shadow-lg">
                Namentliche Abstimmung
              </span>
            </span>
          )}
          {!top.active && <span className="text-xs text-zinc-400 dark:text-zinc-500 italic shrink-0">Keine Parteireden</span>}
        </div>
        <span aria-hidden="true" className="ml-2 shrink-0 text-zinc-400 text-sm">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div id={contentId} className="px-4 pb-5 pt-3 border-t border-zinc-100 dark:border-zinc-800 rounded-b-xl">
          {previewText && (
            <p className="text-xs text-zinc-600 dark:text-zinc-300 mb-2 line-clamp-2">{previewText}</p>
          )}
          {top.active && (
            <button
              onClick={() => {
                try {
                  const openKeys = Array.from(
                    document.querySelectorAll('[data-top-key][data-open="true"]')
                  ).map((el) => (el as HTMLElement).dataset.topKey);
                  sessionStorage.setItem("openTops", JSON.stringify(openKeys));
                  sessionStorage.setItem("homeScrollY", String(window.scrollY));
                } catch {}
                router.push(`/zusammenfassungen/${encodeURIComponent(top.top_key)}`);
              }}
              className="mb-3 text-sm bg-[#BEE3F2] text-[#023047] font-medium rounded-lg px-4 py-2 hover:bg-[#219EBC] hover:text-white transition-colors dark:bg-[#219EBC]/30 dark:text-white"
            >
              Zusammenfassungen ansehen →
            </button>
          )}
          {!top.active && (
            <div className="space-y-1">
              {top.drucksache_url && (
                <a
                  href={top.drucksache_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-[#FB8500] hover:underline block"
                >
                  📄 Drucksache öffnen
                </a>
              )}
              {!top.drucksache_url && top.pdf_url && (
                <a
                  href={top.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-[#FB8500] hover:underline block"
                >
                  📄 PDF öffnen
                </a>
              )}
              <p className="text-xs text-zinc-400 italic">Keine Parteireden</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
