"use client";

import { useEffect, useState } from "react";
import { useLocale } from "@/lib/i18n";

export default function ThemeToggle() {
  const { t } = useLocale();
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  }

  return (
    <button
      onClick={toggle}
      aria-label={t("themeAria")}
      className="flex flex-col items-center gap-1 group"
    >
      {/* Track */}
      <div
        className={[
          "relative w-11 h-6 rounded-full transition-colors duration-200",
          dark ? "bg-zinc-700" : "bg-zinc-200",
        ].join(" ")}
      >
        {/* Knob */}
        <div
          className={[
            "absolute top-1 w-4 h-4 rounded-full shadow transition-all duration-200",
            dark
              ? "translate-x-6 bg-zinc-400"
              : "translate-x-1 bg-white",
          ].join(" ")}
        />
      </div>
      <span className="text-[10px] text-zinc-400 group-hover:text-zinc-600 dark:group-hover:text-zinc-300 transition-colors">
        {dark ? t("dark") : t("light")}
      </span>
    </button>
  );
}
