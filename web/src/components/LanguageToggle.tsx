"use client";

import { useLocale } from "@/lib/i18n";

export default function LanguageToggle() {
  const { locale, setLocale, t } = useLocale();

  return (
    <div
      aria-label={t("languageAria")}
      className="flex items-center gap-0.5 text-xs font-medium rounded-lg border border-zinc-200 dark:border-zinc-700 overflow-hidden"
    >
      {(["de", "en"] as const).map((l) => (
        <button
          key={l}
          onClick={() => setLocale(l)}
          className={[
            "px-2 py-1 uppercase transition-colors",
            locale === l
              ? "bg-[#219EBC] text-white"
              : "text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300",
          ].join(" ")}
        >
          {l}
        </button>
      ))}
    </div>
  );
}
