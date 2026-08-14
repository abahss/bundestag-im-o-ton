import { NextRequest } from "next/server";

// Fired via navigator.sendBeacon() from PdfSplitScreenViewer.tsx's catch
// block, so a failed PDF load in a real visitor's browser shows up in
// Vercel's function logs instead of only their own devtools console — the
// only way we had of measuring how often that failure actually happens.
// Fire-and-forget: never throws, always responds fast.

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    console.error("pdf-viewer-client-error", {
      name: body?.name,
      message: body?.message,
      pdfUrl: body?.pdfUrl,
      quotePreview: typeof body?.quotePreview === "string" ? body.quotePreview.slice(0, 80) : undefined,
    });
  } catch {
    // Malformed beacon payload isn't worth failing the request over.
  }
  return new Response(null, { status: 204 });
}
