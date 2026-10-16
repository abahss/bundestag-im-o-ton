/** Rede-ID: "ID" + Wahlperiode (2) + Sitzung (2, ab Sitzung 100: 3 Stellen) + laufende Nr. (5). */
export const SPEECH_ID_PATTERN = /\[(ID\d{9,10})\]/;

export function idToPdfUrl(id: string): string {
  const wp = id.slice(2, 4);
  const session = id.slice(4, id.length - 5).padStart(3, "0");
  return `https://dserver.bundestag.de/btp/${wp}/${wp}${session}.pdf`;
}
