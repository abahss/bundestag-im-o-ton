const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export interface Subtopic {
  key: string;
  title: string;
  nas: string;
  drucksache_url: string;
}

export interface Top {
  top_key: string;
  top_id: string;
  title: string;
  subtitle: string;
  session: string;
  date: string;
  drucksache: string;
  drucksache_url: string;
  subtopics: Subtopic[];
  topic: string;
  active: boolean;
  pdf_url: string;
}

export interface PartySummary {
  summary: string;
  label: string | null;
  refresh_count: number | null;
}

export interface SummaryResponse {
  general?: { summary: string };
  [party: string]: PartySummary | { summary: string } | undefined;
}

export const PARTIES: Record<string, string> = {
  AFD: "AfD",
  SPD: "SPD",
  CDUCSU: "CDU/CSU",
  GRÜNEN: "Grüne",
  LINKE: "Linke",
};

export async function fetchAllTopics(): Promise<Top[]> {
  const res = await fetch(`${BACKEND_URL}/all_topics`, { next: { revalidate: 300 } });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchSummaries(topKey: string, lang: string = "de"): Promise<SummaryResponse> {
  const res = await fetch(
    `${BACKEND_URL}/summaries?top_key=${encodeURIComponent(topKey)}&lang=${encodeURIComponent(lang)}`,
    { cache: "no-store" }
  );
  if (!res.ok) return {};
  return res.json();
}

export async function refreshGeneralSummary(
  topKey: string,
  lang: string = "de"
): Promise<{ summary: string }> {
  const res = await fetch(
    `${BACKEND_URL}/summaries/refresh-general?top_key=${encodeURIComponent(topKey)}&lang=${encodeURIComponent(lang)}`,
    { method: "POST" }
  );
  if (!res.ok) throw new Error("Refresh failed");
  return res.json();
}

export async function refreshSummary(
  topKey: string,
  party: string,
  lang: string = "de"
): Promise<{ summary: string; refresh_count: null }> {
  const res = await fetch(
    `${BACKEND_URL}/summaries/refresh?top_key=${encodeURIComponent(topKey)}&party=${encodeURIComponent(party)}&lang=${encodeURIComponent(lang)}`,
    { method: "POST" }
  );
  if (!res.ok) throw new Error("Refresh failed");
  return res.json();
}

export async function submitFeedback(
  text: string,
  email: string,
  fromUrl: string
): Promise<void> {
  const res = await fetch(`${BACKEND_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, email, from_url: fromUrl }),
  });
  if (!res.ok) throw new Error("Feedback konnte nicht gesendet werden.");
}
