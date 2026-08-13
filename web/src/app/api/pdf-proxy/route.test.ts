import { afterEach, describe, expect, test, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET } from "./route";

function request(url?: string) {
  const target = new URL("http://localhost/api/pdf-proxy");
  if (url !== undefined) target.searchParams.set("url", url);
  return new NextRequest(target);
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("GET /api/pdf-proxy", () => {
  test("rejects a request with no url param", async () => {
    const res = await GET(request());
    expect(res.status).toBe(400);
  });

  test("rejects a malformed url", async () => {
    const res = await GET(request("not-a-url"));
    expect(res.status).toBe(400);
  });

  test("rejects a host outside the allowlist", async () => {
    const fetchSpy = vi.fn().mockRejectedValue(new Error("must not fetch a non-allowlisted host"));
    vi.stubGlobal("fetch", fetchSpy);

    const res = await GET(request("https://evil.example/malicious.pdf"));

    expect(res.status).toBe(403);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  test("rejects a non-https request to the allowed host", async () => {
    const fetchSpy = vi.fn().mockRejectedValue(new Error("must not fetch a non-https url"));
    vi.stubGlobal("fetch", fetchSpy);

    const res = await GET(request("http://dserver.bundestag.de/btp/21/21046.pdf"));

    expect(res.status).toBe(403);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  test("relays the PDF bytes and content type when the upstream fetch succeeds", async () => {
    const pdfBytes = new TextEncoder().encode("%PDF-1.4 fake pdf content");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(pdfBytes, { status: 200 }))
    );

    const res = await GET(request("https://dserver.bundestag.de/btp/21/21046.pdf"));

    expect(res.status).toBe(200);
    expect(res.headers.get("Content-Type")).toBe("application/pdf");
    expect(new Uint8Array(await res.arrayBuffer())).toEqual(pdfBytes);
  });

  test("requests the exact upstream url for an allowed host", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(new Uint8Array(), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    await GET(request("https://dserver.bundestag.de/btp/21/21046.pdf"));

    expect(fetchSpy).toHaveBeenCalledWith(
      "https://dserver.bundestag.de/btp/21/21046.pdf",
      expect.objectContaining({ redirect: "manual" })
    );
  });

  test("returns a gateway error when the upstream fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 404 })));

    const res = await GET(request("https://dserver.bundestag.de/btp/21/21999.pdf"));

    expect(res.status).toBe(502);
  });

  // The host allowlist alone still leaves the route relaying anything else on
  // that domain, which is bandwidth we pay for and traffic we have no reason
  // to carry. Only plenary protocol PDFs are ever requested by the app.
  test("rejects a path on the allowed host that is not a protocol PDF", async () => {
    const fetchSpy = vi.fn().mockRejectedValue(new Error("must not fetch a non-allowlisted path"));
    vi.stubGlobal("fetch", fetchSpy);

    for (const path of ["/", "/dip/irgendwas.pdf", "/btp/21/21046.pdf/../../secret", "/btp/21/notanumber.pdf"]) {
      const res = await GET(request(`https://dserver.bundestag.de${path}`));
      expect(res.status).toBe(403);
    }
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  test("does not forward a query string or embedded credentials upstream", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(new Uint8Array(), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    await GET(request("https://user:pw@dserver.bundestag.de/btp/21/21046.pdf?redirect=http://evil.example"));

    expect(fetchSpy).toHaveBeenCalledWith(
      "https://dserver.bundestag.de/btp/21/21046.pdf",
      expect.objectContaining({ redirect: "manual" })
    );
  });

  // The allowlist above only ever sees the URL we were asked for. If the
  // allowed host answers with a redirect and we follow it, that check is
  // bypassed for every hop after the first — the classic SSRF pivot onto
  // internal addresses the browser could never reach itself.
  test("does not follow a redirect away from the allowed host", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(null, { status: 302, headers: { Location: "http://169.254.169.254/latest/meta-data/" } })
    );
    vi.stubGlobal("fetch", fetchSpy);

    const res = await GET(request("https://dserver.bundestag.de/btp/21/21046.pdf"));

    expect(res.status).toBe(502);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(res.headers.get("Content-Type")).not.toBe("application/pdf");
  });

  test("returns a gateway error when the upstream connection rejects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));

    const res = await GET(request("https://dserver.bundestag.de/btp/21/21046.pdf"));

    expect(res.status).toBe(502);
  });

  test("bounds the upstream fetch with an abort signal so a stalled host cannot pin the handler", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(new Uint8Array(), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    await GET(request("https://dserver.bundestag.de/btp/21/21046.pdf"));

    const options = fetchSpy.mock.calls[0][1];
    expect(options.signal).toBeInstanceOf(AbortSignal);
  });
});
