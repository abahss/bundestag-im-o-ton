"use client";

// Real PDF.js rendering + highlight for the quote-source split-screen panel.
// Fetches the actual Bundestag protocol PDF through /api/pdf-proxy, finds
// the exact page containing the quote via lib/pdfQuoteMatch.ts, renders that
// page to a canvas, and overlays the matched text's real position.

import { useEffect, useRef, useState } from "react";
import type { PdfBox } from "@/lib/pdfQuoteMatch";

// pdf.js uses `for await (const value of readableStream)` in a couple of
// places (page text-content streaming, network body reading). That relies on
// ReadableStream.prototype[Symbol.asyncIterator], which only shipped in
// Safari 16.4 (March 2023) — older iOS Safari throws
// "TypeError: undefined is not a function (near '...value of readableStream...')"
// the moment it's hit. Polyfill it with the universally-supported getReader()
// API before any pdf.js code runs.
if (typeof ReadableStream !== "undefined" && !(Symbol.asyncIterator in ReadableStream.prototype)) {
  (ReadableStream.prototype as unknown as Record<typeof Symbol.asyncIterator, () => AsyncGenerator<unknown>>)[
    Symbol.asyncIterator
  ] = async function* (this: ReadableStream) {
    const reader = this.getReader();
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) return;
        yield value;
      }
    } finally {
      reader.releaseLock();
    }
  };
}

interface Props {
  pdfUrl: string;
  quoteText: string;
  onPageFound?: (pageNumber: number) => void;
}

type Status = "loading" | "searching" | "found" | "not-found" | "error";

export default function PdfSplitScreenViewer({ pdfUrl, quoteText, onPageFound }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [pageInfo, setPageInfo] = useState<{ page: number; total: number } | null>(null);
  const [highlightBoxes, setHighlightBoxes] = useState<React.CSSProperties[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      try {
        const pdfjsLib = await import("pdfjs-dist");
        pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

        const proxiedUrl = `/api/pdf-proxy?url=${encodeURIComponent(pdfUrl)}`;
        const doc = await pdfjsLib.getDocument({ url: proxiedUrl }).promise;
        if (cancelled) return;

        setStatus("searching");
        const { findQuoteInPdf } = await import("@/lib/pdfQuoteMatch");
        const match = await findQuoteInPdf(doc, quoteText);
        if (cancelled) return;

        if (!match) {
          setStatus("not-found");
          return;
        }

        const page = await doc.getPage(match.pageNumber);
        const viewport = page.getViewport({ scale: 1.3 });
        const canvas = canvasRef.current;
        if (!canvas) return;
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const ctx = canvas.getContext("2d")!;
        await page.render({ canvasContext: ctx, viewport, canvas }).promise;
        if (cancelled) return;

        // Percentages, not pixels: the canvas is CSS-scaled (max-w-full) to fit
        // its panel, so its rendered size rarely matches viewport.width/height in
        // real pixels. The overlay divs are absolutely positioned inside the same
        // wrapper the canvas fills, so percentages of that wrapper track whatever
        // size the canvas actually renders at.
        const boxStyles = match.boxes.map((box: PdfBox): React.CSSProperties => {
          const [vx0, vy0] = viewport.convertToViewportPoint(box.x, box.y);
          const [vx1, vy1] = viewport.convertToViewportPoint(box.x + box.width, box.y + box.height);
          return {
            position: "absolute",
            left: `${(Math.min(vx0, vx1) / viewport.width) * 100}%`,
            top: `${(Math.min(vy0, vy1) / viewport.height) * 100}%`,
            width: `${(Math.abs(vx1 - vx0) / viewport.width) * 100}%`,
            height: `${(Math.abs(vy1 - vy0) / viewport.height) * 100}%`,
          };
        });

        setHighlightBoxes(boxStyles);
        setPageInfo({ page: match.pageNumber, total: doc.numPages });
        setStatus("found");
        onPageFound?.(match.pageNumber);
      } catch (e) {
        console.error("PdfSplitScreenViewer:", e);
        if (!cancelled) {
          setStatus("error");
        }
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, [pdfUrl, quoteText]);

  return (
    <div className="h-full overflow-y-auto">
      {status === "loading" && <p className="text-sm text-zinc-400">PDF wird geladen…</p>}
      {status === "searching" && <p className="text-sm text-zinc-400">Zitat wird auf den Seiten gesucht…</p>}
      {status === "not-found" && <p className="text-sm text-red-500">Zitat nicht im PDF gefunden.</p>}
      {status === "error" && <p className="text-sm text-red-500">Fehler beim Laden des PDFs.</p>}
      <div className="relative inline-block">
        <canvas ref={canvasRef} className="max-w-full border border-zinc-200 dark:border-zinc-700 rounded shadow-sm" />
        {highlightBoxes.map((style, i) => (
          <div key={i} style={style} className="bg-amber-300/50 rounded-[1px] pointer-events-none" />
        ))}
      </div>
      {pageInfo && (
        <p className="text-xs text-zinc-400 mt-2">
          Original-Seite {pageInfo.page} von {pageInfo.total} — echtes PDF, keine Nachbildung.
        </p>
      )}
    </div>
  );
}
