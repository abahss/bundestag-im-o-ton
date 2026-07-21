import { cookies } from "next/headers";
import type { Locale } from "./i18n";

/** Read the locale cookie in a server component. Defaults to German. */
export async function getServerLocale(): Promise<Locale> {
  const store = await cookies();
  const value = store.get("locale")?.value;
  return value === "en" ? "en" : "de";
}
