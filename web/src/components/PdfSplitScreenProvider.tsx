"use client";

// Lifts the split-screen panel's open/close state up to the page layout so
// the surrounding content can reserve real space for the panel (md:mr-[46%])
// instead of the panel floating on top of it. The trigger button lives deep
// inside ParliamentChart; a shared context lets it control layout this far
// up without prop-drilling through page.tsx.

import { createContext, useContext, useState, type ReactNode } from "react";
import PdfSplitScreenViewer from "@/components/PdfSplitScreenViewer";

interface PdfSplitScreenState {
  open: boolean;
  quoteText: string;
  pdfUrl: string;
  sessionLabel: string;
  pageNumber: number | null;
}

interface PdfSplitScreenContextValue {
  open: boolean;
  show: (args: { quoteText: string; pdfUrl: string; sessionLabel: string }) => void;
  hide: () => void;
}

const PdfSplitScreenContext = createContext<PdfSplitScreenContextValue | null>(null);

export function usePdfSplitScreen() {
  const ctx = useContext(PdfSplitScreenContext);
  if (!ctx) throw new Error("usePdfSplitScreen must be used within PdfSplitScreenProvider");
  return ctx;
}

export default function PdfSplitScreenProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<PdfSplitScreenState>({
    open: false,
    quoteText: "",
    pdfUrl: "",
    sessionLabel: "",
    pageNumber: null,
  });

  function show(args: { quoteText: string; pdfUrl: string; sessionLabel: string }) {
    setState({ open: true, pageNumber: null, ...args });
  }
  function hide() {
    setState((s) => ({ ...s, open: false }));
  }

  return (
    <PdfSplitScreenContext.Provider value={{ open: state.open, show, hide }}>
      <div className={`transition-[margin] duration-200 ${state.open ? "md:mr-[46%]" : ""}`}>{children}</div>
      {state.open && (
        <div
          className="fixed z-40 bg-white dark:bg-zinc-950 shadow-2xl border-l border-zinc-200 dark:border-zinc-800 overflow-y-auto
                     inset-x-0 bottom-0 max-h-[80vh] rounded-t-2xl p-4
                     md:inset-y-0 md:right-0 md:left-auto md:bottom-auto md:w-[46%] md:max-h-none md:rounded-t-none md:p-5"
        >
          <div className="flex items-center justify-between mb-3 gap-3">
            <p className="text-sm font-semibold text-[#023047] dark:text-white truncate">{state.sessionLabel}</p>
            <div className="flex items-center gap-3 shrink-0">
              <a
                href={state.pageNumber ? `${state.pdfUrl}#page=${state.pageNumber}` : state.pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[#219EBC] hover:underline whitespace-nowrap"
              >
                Ursprungsquelle ↗
              </a>
              <button
                onClick={hide}
                aria-label="Schließen"
                className="text-zinc-400 hover:text-zinc-600 text-lg leading-none px-1"
              >
                ✕
              </button>
            </div>
          </div>
          <PdfSplitScreenViewer
            pdfUrl={state.pdfUrl}
            quoteText={state.quoteText}
            onPageFound={(pageNumber) => setState((s) => ({ ...s, pageNumber }))}
          />
        </div>
      )}
    </PdfSplitScreenContext.Provider>
  );
}
