"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

export default function FeedbackButton() {
  const pathname = usePathname();
  const [expanded, setExpanded] = useState(true);

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
    <div className={`fixed bottom-14 right-4 z-40 flex flex-col items-end gap-2 transition-opacity duration-500 sm:opacity-100 ${
      expanded ? "opacity-100" : "opacity-0 pointer-events-none sm:pointer-events-auto"
    }`}>
      <a
        href="https://www.paypal.com/paypalme/Ancheba"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700 rounded-full shadow-lg px-3 py-2 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors"
      >
        <span>🫶</span>
        <span className="hidden sm:inline">Unterstützen</span>
      </a>
      <a
        href="https://abahss.github.io/cv.html"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700 rounded-full shadow-lg px-3 py-2 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors"
      >
        <span>👤</span>
        <span className="hidden sm:inline">Über mich</span>
      </a>
      <Link
        href={`/feedback?from=${encodeURIComponent(pathname)}`}
        className="flex items-center gap-1.5 bg-[#219EBC] text-white rounded-full shadow-lg px-3 py-2 text-sm font-medium hover:bg-[#1a7fa0] transition-colors"
      >
        <span>💬</span>
        <span className="hidden sm:inline">Feedback</span>
      </Link>
    </div>
  );
}
