import { fetchAllTopics } from "@/lib/api";
import HomeClient from "@/components/HomeClient";
import { homeRecessNotice } from "@/lib/recesses";

function parseGermanDate(str: string): Date {
  const [day, month, year] = str.split(".");
  return new Date(+year, +month - 1, +day);
}

export default async function Home() {
  const topics = await fetchAllTopics();
  const latestSession = topics
    .map((t) => parseGermanDate(t.date))
    .sort((a, b) => b.getTime() - a.getTime())[0] ?? null;
  const recessNotice = homeRecessNotice(latestSession);
  return <HomeClient topics={topics} recessNotice={recessNotice} />;
}
