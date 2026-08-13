import { NextRequest } from "next/server";

// Supporting route for PdfSplitScreenViewer.tsx. dserver.bundestag.de sends
// neither CORS headers nor allows framing (X-Frame-Options: SAMEORIGIN), so
// the real PDF can't be fetched or embedded directly from the browser. This
// proxies it server-side (no CORS/framing restrictions apply to
// server-to-server fetches) and re-serves it same-origin. Locked to the one
// host we actually need — an open proxy would let anyone relay arbitrary
// URLs through us.

const ALLOWED_HOST = "dserver.bundestag.de";
// Plenary protocol PDFs only, e.g. /btp/21/21046.pdf — the single shape
// idToPdfUrl() in ParliamentChart.tsx ever produces (2-digit Wahlperiode, then
// Wahlperiode + 3-digit sitting number). Without a path check the route still
// relays anything else on that host, which costs us bandwidth and makes us an
// anonymising relay for requests we have no reason to serve.
const ALLOWED_PATH = /^\/btp\/\d{2}\/\d{5}\.pdf$/;
const UPSTREAM_TIMEOUT_MS = 20_000;

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
  if (!ALLOWED_PATH.test(target.pathname)) {
    return new Response("Path not allowed", { status: 403 });
  }

  // Rebuilt from the two parts we validated rather than forwarding the caller's
  // string, so a query, fragment or embedded credentials cannot ride along to
  // the upstream host.
  const upstreamUrl = `https://${ALLOWED_HOST}${target.pathname}`;

  // `redirect: "manual"` matters for more than tidiness: following redirects
  // would apply the allowlist to the first hop only, so a 3xx from the allowed
  // host could walk us onto any URL — including cloud-metadata and other
  // internal addresses reachable from the server but not from the client —
  // and we would relay the body back as a publicly cacheable PDF.
  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, {
      redirect: "manual",
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    });
  } catch {
    // Network-level failure (DNS, TLS, reset) or the timeout above. Without
    // this the rejection escapes as an opaque 500 that blames our own route.
    return new Response("Upstream fetch failed", { status: 502 });
  }
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
