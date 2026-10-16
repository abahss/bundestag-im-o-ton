import { describe, expect, test } from "vitest";
import { SPEECH_ID_PATTERN, idToPdfUrl } from "./speechId";

describe("idToPdfUrl", () => {
  test("zweistellige Sitzung", () => {
    expect(idToPdfUrl("ID219900200")).toBe("https://dserver.bundestag.de/btp/21/21099.pdf");
  });
  test("dreistellige Sitzung (Regression: Sitzung 100)", () => {
    expect(idToPdfUrl("ID2110000500")).toBe("https://dserver.bundestag.de/btp/21/21100.pdf");
  });
});

describe("SPEECH_ID_PATTERN", () => {
  test("erkennt 9- und 10-stellige IDs", () => {
    expect("x [ID219900200]".match(SPEECH_ID_PATTERN)?.[1]).toBe("ID219900200");
    expect("x [ID2110000500]".match(SPEECH_ID_PATTERN)?.[1]).toBe("ID2110000500");
  });
});
