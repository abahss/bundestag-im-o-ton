"use client";

// Real PDF.js rendering + highlight for the quote-source split-screen panel.
// Fetches the actual Bundestag protocol PDF through /api/pdf-proxy, finds
// the exact page containing the quote via lib/pdfQuoteMatch.ts, renders that
// page to a canvas, and overlays the matched text's real position.

import { useEffect, useRef, useState } from "react";
import type { PDFDocumentLoadingTask, RenderTask } from "pdfjs-dist";
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
  const [highlightBoxes, setHighlightBoxes] = useState<React.CSSProperties[]>([]);

  useEffect(() => {
    let cancelled = false;
    let loadingTask: PDFDocumentLoadingTask | null = null;
    let renderTask: RenderTask | null = null;

    async function run() {
      try {
        const pdfjsLib = await import("pdfjs-dist");
        // public/pdf.worker.min.mjs must be the *modern* build, matching what
        // `import("pdfjs-dist")` resolves to above. Serving the legacy worker
        // instead fails silently: both builds carry the same version string, so
        // pdf.js's API-vs-worker version guard passes, but the text layer comes
        // out subtly different and quote matching returns null with no error.
        // The postinstall script in package.json keeps the copy in sync.
        pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

        const proxiedUrl = `/api/pdf-proxy?url=${encodeURIComponent(pdfUrl)}`;
        loadingTask = pdfjsLib.getDocument({ url: proxiedUrl });
        const doc = await loadingTask.promise;
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
        renderTask = page.render({ canvasContext: ctx, viewport, canvas });
        await renderTask.promise;
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
        setStatus("found");
        // Still reported upward even though the viewer no longer shows the page
        // itself: the provider turns it into the #page=N deep link behind
        // "Ursprungsquelle".
        onPageFound?.(match.pageNumber);
      } catch (e) {
        // Switching quotes mid-flight rejects whatever was in progress
        // (render cancellation, or a destroyed document). That is the expected
        // outcome of the cleanup below, not a failure worth reporting.
        if (cancelled) return;
        console.error("PdfSplitScreenViewer:", e);
        setStatus("error");
        // Beacon rather than fetch: guaranteed to be sent even if the user
        // closes the panel or navigates away right after seeing the error,
        // and it's the only signal we have for how often this happens to
        // real visitors (see api/log-pdf-error/route.ts).
        navigator.sendBeacon?.(
          "/api/log-pdf-error",
          JSON.stringify({
            name: e instanceof Error ? e.name : undefined,
            message: e instanceof Error ? e.message : String(e),
            pdfUrl,
            quotePreview: quoteText.slice(0, 80),
          })
        );
      }
    }

    run();
    return () => {
      cancelled = true;
      // Without cancelling, a second page.render() can start on the same canvas
      // while this one is still going, which pdf.js rejects outright ("Cannot
      // use the same canvas during multiple render() operations").
      renderTask?.cancel();
      // Aborts any in-flight download and releases the worker and the buffered
      // PDF; otherwise every quote the user opens leaks both for the lifetime
      // of the page.
      void loadingTask?.destroy();
    };
  }, [pdfUrl, quoteText]);

  return (
    <div className="h-full overflow-y-auto">
      {status === "loading" && <p className="text-sm text-zinc-400">PDF wird geladen…</p>}
      {status === "searching" && <p className="text-sm text-zinc-400">Zitat wird auf den Seiten gesucht…</p>}
      {/* Deliberately not "Zitat nicht im PDF gefunden": the backend keeps a
          quote only if it matched the protocol transcript literally (see
          _attach_citation_ids in rag.py, which drops unverifiable quotes), so a
          miss here is this viewer failing to locate a quote that is provably
          there — most often because it breaks across a page or column boundary,
          which the per-page search cannot follow. Claiming the quote is absent
          would cast doubt on a citation we have already verified. */}
      {status === "not-found" && (
        <div className="text-sm text-zinc-600 dark:text-zinc-400">
          <p>Die Stelle konnte im PDF nicht automatisch markiert werden.</p>
          <p className="text-xs mt-1">
            Das Zitat ist gegen das Protokoll geprüft — nachlesen lässt es sich im{" "}
            <a
              href={pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#219EBC] hover:underline"
            >
              Original-Protokoll ↗
            </a>
            .
          </p>
        </div>
      )}
      {status === "error" && <p className="text-sm text-red-500">Fehler beim Laden des PDFs.</p>}
      {/* Hidden rather than unmounted while searching: the canvas has to stay
          in the DOM for canvasRef to be there when the page renders into it.
          `hidden` keeps the previous quote's pixels off screen until the new
          page has actually been drawn — and it has to *replace* `inline-block`
          rather than sit beside it, since two display utilities of equal
          specificity leave the winner down to stylesheet order. */}
      <div className={status === "found" ? "relative inline-block" : "hidden"}>
        <canvas ref={canvasRef} className="max-w-full border border-zinc-200 dark:border-zinc-700 rounded shadow-sm" />
        {highlightBoxes.map((style, i) => (
          <div key={i} style={style} className="bg-amber-300/50 rounded-[1px] pointer-events-none" />
        ))}
      </div>
    </div>
  );
}
