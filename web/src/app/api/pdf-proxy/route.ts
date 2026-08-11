import { NextRequest } from "next/server";

// Supporting route for PdfSplitScreenViewer.tsx. dserver.bundestag.de sends
// neither CORS headers nor allows framing (X-Frame-Options: SAMEORIGIN), so
// the real PDF can't be fetched or embedded directly from the browser. This
// proxies it server-side (no CORS/framing restrictions apply to
// server-to-server fetches) and re-serves it same-origin. Locked to the one
// host we actually need — an open proxy would let anyone relay arbitrary
// URLs through us.

const ALLOWED_HOST = "dserver.bundestag.de";

export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get("url");
  if (!url) return new Response("Missing url", { status: 400 });

  let target: URL;
  try {
    target = new URL(url);
  } catch {
    return new Response("Invalid url", { status: 400 });
  }
  if (target.protocol !== "https:" || target.hostname !== ALLOWED_HOST) {
    return new Response("Host not allowed", { status: 403 });
  }

  const upstream = await fetch(target.toString());
  if (!upstream.ok || !upstream.body) {
    return new Response("Upstream fetch failed", { status: 502 });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "application/pdf",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
