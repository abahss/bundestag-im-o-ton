"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { usePdfSplitScreen } from "@/components/PdfSplitScreenProvider";

export default function FeedbackButton() {
  const pathname = usePathname();
  const [expanded, setExpanded] = useState(true);
  const { open: panelOpen } = usePdfSplitScreen();
  // Same icon-only look these already fall back to on narrow screens
  // (`sm:not-sr-only sm:inline` below) — forced here too so the labels don't
  // compete with the panel for width once it's reserved 46% of the page.
  const labelClass = panelOpen ? "sr-only" : "sr-only sm:not-sr-only sm:inline";

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
    <div className={`fixed bottom-14 right-4 z-40 flex flex-col items-end gap-2 transition-[opacity,right] duration-200 sm:opacity-100 ${
      expanded ? "opacity-100" : "opacity-0 pointer-events-none sm:pointer-events-auto"
    } ${panelOpen ? "md:right-[calc(46%+1rem)]" : ""}`}>
      <a
        href="https://ko-fi.com/bundestagimoton"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700 rounded-full shadow-lg px-3 py-2 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors"
      >
        <span>🫶</span>
        <span className={labelClass}>Unterstützen</span>
      </a>
      <a
        href="https://abahss.github.io/cv.html"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700 rounded-full shadow-lg px-3 py-2 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors"
      >
        <span>👤</span>
        <span className={labelClass}>Über mich</span>
      </a>
      <Link
        href={`/feedback?from=${encodeURIComponent(pathname)}`}
        className="flex items-center gap-1.5 bg-[#219EBC] text-white rounded-full shadow-lg px-3 py-2 text-sm font-medium hover:bg-[#1a7fa0] transition-colors"
      >
        <span>💬</span>
        <span className={labelClass}>Feedback</span>
      </Link>
    </div>
  );
}
