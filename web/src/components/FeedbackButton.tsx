"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { usePdfSplitScreen } from "@/components/PdfSplitScreenProvider";

export default function FeedbackButton() {
  const pathname = usePathname();
  const [expanded, setExpanded] = useState(true);
  const { open: panelOpen } = usePdfSplitScreen();
  // Text pills normally. Once the PDF panel is open these float over its narrow
  // white padding rim, which has no room for text labels, so they fall back to
  // icon-only there.
  const labelClass = panelOpen ? "sr-only" : undefined;

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;

    const expand = () => {
      setExpanded(true);
      clearTimeout(timer);
      timer = setTimeout(() => setExpanded(false), 1000);
    };

    timer = setTimeout(() => setExpanded(false), 1000);
    window.addEventListener("scroll", expand, { passive: true });
    return () => {
      window.removeEventListener("scroll", expand);
      clearTimeout(timer);
    };
  }, []);

  if (pathname === "/feedback") return null;

  return (
    <div className={`fixed bottom-14 right-4 z-[65] flex flex-col items-end gap-2 transition-opacity duration-200 sm:opacity-100 ${
      expanded ? "opacity-100" : "opacity-0 pointer-events-none sm:pointer-events-auto"
    }`}>
      <a
        href="https://ko-fi.com/bundestagimoton"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 bg-white dark:bg-zinc-950 text-[#3e3ac6] dark:text-[#ceec97] border border-[#3e3ac6] dark:border-[#ceec97] rounded-md shadow-md px-3 py-2 text-sm font-bold hover:bg-[#e2e1f6] dark:hover:bg-zinc-900 transition-colors"
      >
        {panelOpen && <span aria-hidden="true">🫶</span>}
        <span className={labelClass}>Unterstützen</span>
      </a>
      {/* Temporarily hidden — kept in code, not deleted, per explicit request. */}
      <a
        href="https://abahss.github.io/cv.html"
        target="_blank"
        rel="noopener noreferrer"
        className="hidden items-center gap-1.5 bg-white dark:bg-zinc-950 text-[#3e3ac6] dark:text-[#ceec97] border border-[#3e3ac6] dark:border-[#ceec97] rounded-md shadow-md px-3 py-2 text-sm font-bold hover:bg-[#e2e1f6] dark:hover:bg-zinc-900 transition-colors"
      >
        {panelOpen && <span aria-hidden="true">👤</span>}
        <span className={labelClass}>Über mich</span>
      </a>
      <Link
        href={`/feedback?from=${encodeURIComponent(pathname)}`}
        className="flex items-center gap-1.5 bg-[#3e3ac6] text-white border border-[#3e3ac6] rounded-md shadow-md px-3 py-2 text-sm font-bold hover:bg-[#2a2790] transition-colors"
      >
        {panelOpen && <span aria-hidden="true">💬</span>}
        <span className={labelClass}>Feedback</span>
      </Link>
    </div>
  );
}
