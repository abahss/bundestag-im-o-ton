"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Top } from "@/lib/api";

function navLabel(top: Top): string {
  return top.top_id
    .replace("Tagesordnungspunkt ", "TOP ")
    .replace("Zusatzpunkt ", "ZP ");
}

export default function TopAccordion({ top, defaultOpen = false, onOpen, autoScroll = false }: { top: Top; defaultOpen?: boolean; onOpen?: () => void; autoScroll?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
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
    <div ref={ref} className="rounded-xl border border-zinc-100 dark:border-zinc-800 overflow-hidden">
      <button
        onClick={() => { const next = !open; setOpen(next); if (next) onOpen?.(); }}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors"
      >
        <div className="min-w-0">
          <span className="text-xs font-semibold text-[#219EBC] mr-2">{label}</span>
          <span className="text-sm text-zinc-800 dark:text-zinc-200 break-words">{topic}</span>
        </div>
        <span className="ml-2 shrink-0 text-zinc-400 text-sm">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="px-4 pb-5 pt-3 border-t border-zinc-100 dark:border-zinc-800">
          {top.title && top.title !== topic && (
            <p className="text-xs text-zinc-500 mb-2">{top.title}</p>
          )}
          {top.subtopics?.length > 0 && (
            <ul className="mb-4 space-y-1">
              {top.subtopics.map((s) => (
                <li key={s.key} className="text-xs text-zinc-400">
                  <span className="font-medium text-zinc-500">{s.key})</span> {s.title}
                </li>
              ))}
            </ul>
          )}
          {top.active ? (
            <button
              onClick={() => router.push(`/zusammenfassungen/${encodeURIComponent(top.top_key)}`)}
              className="mt-3 text-sm border border-[#219EBC] text-[#219EBC] rounded-lg px-4 py-2 hover:bg-[#219EBC] hover:text-white transition-colors"
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
