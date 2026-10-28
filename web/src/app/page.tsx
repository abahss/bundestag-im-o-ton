import { fetchAllTopics } from "@/lib/api";
import { Suspense } from "react";
import HomeClient from "@/components/HomeClient";

export default async function Home() {
  const topics = await fetchAllTopics();
  return (
    <Suspense>
      <HomeClient topics={topics} />
    </Suspense>
  );
}
