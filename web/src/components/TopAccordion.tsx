"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Top } from "@/lib/api";
import { classifyTopDocType } from "@/lib/docType";
import { isHaushaltswoche } from "@/lib/haushaltswoche";

function navLabel(top: Top): string {
  if (isHaushaltswoche(top)) return "Haushalt";
  return top.top_id
    .replace("Tagesordnungspunkt ", "TOP ")
    .replace("Zusatzpunkte ", "ZP ")
    .replace("Zusatzpunkt ", "ZP ")
    .replace("Einzelplan ", "EP ") // erklärt im FAQ ("Was ist ein Einzelplan (EP)?")
    .replace(/ und /g, ", ")
    .replace(/ sowie /g, ", ")
    .replace(/ bis /g, " - ");
}

export default function TopAccordion({ top, defaultOpen = false, onOpen, autoScroll = false, restoreOpenKeys = null }: { top: Top; defaultOpen?: boolean; onOpen?: () => void; autoScroll?: boolean; restoreOpenKeys?: string[] | null }) {
  const [open, setOpen] = useState(defaultOpen);

  // `restoreOpenKeys`, when non-null, is a one-shot snapshot from TopList
  // (see there) written by the "Zusammenfassungen ansehen" handler below and
  // meant to reproduce the whole expanded/collapsed layout the user left
  // behind on back-navigation. Starting `open` from `defaultOpen` above (not
  // this) keeps the client's first render identical to the server-rendered
  // HTML — sessionStorage doesn't exist during SSR — and applying it here in
  // an effect instead means it only ever takes effect post-hydration.
  useEffect(() => {
    if (restoreOpenKeys !== null) {
      setOpen(restoreOpenKeys.includes(top.top_key));
    }
  }, [restoreOpenKeys, top.top_key]);

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
  const isHw = isHaushaltswoche(top);
  const topic = isHw ? top.title : top.topic || top.title || top.subtitle || label;
  const clickable = isHw || top.active;
  const contentId = `top-content-${top.top_key.replace(/\s+/g, "-")}`;

  const docType = classifyTopDocType(top);

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
      className="border border-zinc-300 dark:border-zinc-600 not-last:border-b-0"
    >
      <button
        onClick={() => { const next = !open; setOpen(next); if (next) onOpen?.(); }}
        aria-expanded={open}
        aria-controls={contentId}
        className={`w-full flex items-stretch text-left transition-colors ${
          open
            ? "bg-[#3e3ac6] text-white"
            : "bg-white text-zinc-900 hover:bg-[#3e3ac6]/10 dark:bg-zinc-950 dark:text-white dark:hover:bg-zinc-900"
        }`}
      >
        <div className="flex-1 min-w-0 px-4 py-4">
          <p className={open ? "break-words" : "line-clamp-1"}>
            <span className="mr-3 text-base font-bold uppercase tracking-wide opacity-60 font-[family-name:var(--font-space-grotesk)]">{label}</span>
            <span className="text-sm sm:text-base font-semibold">{topic}</span>
          </p>
          {top.has_abstimmung && (
            <div className="mt-2">
              <span className={`rounded-sm px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${open ? "bg-[#ceec97] text-[#3e3ac6]" : "bg-[#3e3ac6]/15 text-[#3e3ac6] dark:bg-[#3e3ac6]/40 dark:text-white"}`}>
                Abstimmung
              </span>
            </div>
          )}
          {!clickable && <p className={`mt-1 text-xs italic ${open ? "text-white/70" : "text-zinc-400 dark:text-zinc-500"}`}>Keine Parteireden</p>}
        </div>
        {docType && (
          <span className="hidden sm:flex shrink-0 items-center pr-4">
            <span
              // Single document (Gesetzentwurf, Antrag …): solid pill. Bundle ("3 Vorlagen"):
              // dashed outline only, so it reads as a container rather than the document itself.
              className={`rounded-sm px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide whitespace-nowrap ${
                docType.bundled
                  ? open
                    ? "border border-dashed border-white/70 text-white"
                    : "border border-dashed border-zinc-400 text-zinc-500 dark:border-zinc-500 dark:text-zinc-400"
                  : open
                    ? "bg-[#ceec97] text-[#3e3ac6]"
                    : "bg-[#3e3ac6] text-white"
              }`}
            >
              {docType.label}
            </span>
          </span>
        )}
        <span
          aria-hidden="true"
          className={`w-14 shrink-0 flex items-center justify-center text-2xl font-bold border-l ${
            open
              ? "bg-[#ceec97] text-[#3e3ac6] border-[#ceec97]"
              : "text-[#3e3ac6] dark:text-[#ceec97] border-zinc-300 dark:border-zinc-600"
          }`}
        >
          {open ? "\u2212" : "+"}
        </span>
      </button>

      {open && (
        <div id={contentId} className="bg-white dark:bg-zinc-900 px-4 pb-5 pt-4">
          {previewText && (
            <p className="text-sm sm:text-base text-zinc-800 dark:text-zinc-200 mb-4 line-clamp-3">{previewText}</p>
          )}
          {clickable && (
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
              style={{ clipPath: "polygon(4% 0, 100% 0, 96% 100%, 0 100%)" }}
              className="mb-1 bg-[#ceec97] text-[#3e3ac6] font-semibold px-6 py-2.5 hover:bg-[#3e3ac6] hover:text-white transition-colors"
            >
              Zusammenfassungen ansehen
            </button>
          )}
          {!clickable && (
            <div className="space-y-1">
              {top.drucksache_url && (
                <a
                  href={top.drucksache_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-[#3e3ac6] dark:text-[#ceec97] hover:underline block"
                >
                  📄 Drucksache öffnen
                </a>
              )}
              {!top.drucksache_url && top.subtopics?.some((s) => s.drucksache_url) && (
                top.subtopics
                  .filter((s) => s.drucksache_url)
                  .map((s) => (
                    <a
                      key={s.key}
                      href={s.drucksache_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-[#3e3ac6] dark:text-[#ceec97] hover:underline block"
                    >
                      📄 {s.key}) {s.title || "Drucksache"} öffnen
                    </a>
                  ))
              )}
              {!top.drucksache_url && !top.subtopics?.some((s) => s.drucksache_url) && top.pdf_url && (
                <a
                  href={top.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-[#3e3ac6] dark:text-[#ceec97] hover:underline block"
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
