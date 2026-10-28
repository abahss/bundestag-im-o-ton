import { fetchAllTopics } from "@/lib/api";
import HomeClient from "@/components/HomeClient";

export default async function Home() {
  const topics = await fetchAllTopics();
  return <HomeClient topics={topics} />;
}
