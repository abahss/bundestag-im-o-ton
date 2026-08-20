"use client";

import Link from "next/link";
import { usePdfSplitScreen } from "@/components/PdfSplitScreenProvider";

export default function SiteFooter() {
  const { open } = usePdfSplitScreen();

  return (
    <footer
      // Fixed to the viewport only from md up — on mobile it sits in normal
      // flow at the end of the page instead, so it doesn't permanently eat
      // into the small viewport. On mobile the split-screen panel also goes
      // full-screen when open and sits above this in z-order, so it already
      // covers the footer there — only desktop needs the width shrunk to the
      // panel's left edge.
      className={`md:fixed md:bottom-0 md:left-0 md:right-0 border-t border-zinc-100 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-4 py-2 text-center z-50 transition-[right] duration-200 ${
        open ? "md:right-[46%]" : ""
      }`}
    >
      <p className="text-xs text-zinc-400">
        Zusammenfassungen und Kurztitel werden KI-generiert und können Fehler enthalten.{" "}
        <Link href="/impressum" className="underline hover:text-zinc-600 dark:hover:text-zinc-300">
          Impressum
        </Link>
        {" · "}
        <Link href="/datenschutz" className="underline hover:text-zinc-600 dark:hover:text-zinc-300">
          Datenschutz
        </Link>
      </p>
    </footer>
  );
}
