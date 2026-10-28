"use client";

// PROTOTYPE — wipe me. Marks <html> with "proto-theme" while the URL carries
// ?variant=B|C|D, so the scoped rules in globals.css restyle the page. Renders
// nothing and runs after hydration, so pages without the param are untouched.

import { useEffect } from "react";

export default function ProtoThemeFlag() {
  useEffect(() => {
    const v = new URLSearchParams(window.location.search).get("variant");
    if (v !== "B" && v !== "C" && v !== "D" && v !== "E" && v !== "F") return;
    document.documentElement.classList.add("proto-theme");
    return () => document.documentElement.classList.remove("proto-theme");
  }, []);
  return null;
}
