"use client";

import { useEffect, useState } from "react";

export default function ThemeToggle() {
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
      aria-label="Dark/Light Mode umschalten"
      className="text-lg text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
    >
      {dark ? "☀️" : "🌙"}
    </button>
  );
}
