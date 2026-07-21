"use client";

import Link from "next/link";
import { useLocale } from "@/lib/i18n";

export default function Footer() {
  const { t } = useLocale();

  return (
    <footer className="fixed bottom-0 left-0 right-0 border-t border-zinc-100 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-4 py-2 text-center z-50">
      <p className="text-xs text-zinc-400">
        {t("footerDisclaimer")}{" "}
        <Link href="/impressum" className="underline hover:text-zinc-600 dark:hover:text-zinc-300">
          {t("imprint")}
        </Link>
        {" · "}
        <Link href="/datenschutz" className="underline hover:text-zinc-600 dark:hover:text-zinc-300">
          {t("privacy")}
        </Link>
      </p>
    </footer>
  );
}
