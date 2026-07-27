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

  // Restore open state from sessionStorage after hydration
  useEffect(() => {
    try {
      const lastOpened = sessionStorage.getItem("lastOpenedTop");
      if (lastOpened !== null) {
        setOpen(lastOpened === top.top_key);
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

  return (
    <div ref={ref} className="rounded-xl border border-zinc-100 dark:border-zinc-800">
      <button
        onClick={() => { const next = !open; setOpen(next); if (next) onOpen?.(); }}
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
        <span className="ml-2 shrink-0 text-zinc-400 text-sm">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="px-4 pb-5 pt-3 border-t border-zinc-100 dark:border-zinc-800 rounded-b-xl">
          {top.title && top.title !== topic && (
            <p className="text-xs text-zinc-600 dark:text-zinc-300 mb-2">{top.title}</p>
          )}
          {top.subtopics?.length > 0 && (
            <ul className="mb-4 space-y-1">
              {top.subtopics.map((s) => (
                <li key={s.key} className="text-xs text-zinc-600 dark:text-zinc-300">
                  <span className="font-medium text-zinc-700 dark:text-zinc-200">{s.key})</span> {s.title}
                </li>
              ))}
            </ul>
          )}
          {top.active ? (
            <button
              onClick={() => {
                try { sessionStorage.setItem("lastOpenedTop", top.top_key); } catch {}
                router.push(`/zusammenfassungen/${encodeURIComponent(top.top_key)}`);
              }}
              className="mt-3 text-sm bg-[#BEE3F2] text-[#023047] font-medium rounded-lg px-4 py-2 hover:bg-[#219EBC] hover:text-white transition-colors dark:bg-[#219EBC]/30 dark:text-white"
            >
              Zusammenfassungen ansehen →
            </button>
          ) : (
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
