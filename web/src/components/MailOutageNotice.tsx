"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "mail-outage-notice-2026-10";

export default function MailOutageNotice() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (!sessionStorage.getItem(STORAGE_KEY)) setVisible(true);
    } catch {
      setVisible(true);
    }
  }, []);

  function dismiss() {
    setVisible(false);
    try {
      sessionStorage.setItem(STORAGE_KEY, "1");
    } catch {}
  }

  if (!visible) return null;

  return (
    <div
      role="status"
      className="flex items-start gap-3 bg-amber-50 dark:bg-amber-950 text-amber-900 dark:text-amber-100 border-b border-amber-200 dark:border-amber-800 px-4 py-3 text-sm"
    >
      <p className="flex-1">
        <strong className="font-semibold">E-Mail Ausfall:</strong> Unser
        E-Mail-Postfach war kurzzeitig nicht erreichbar, und in dieser Zeit
        gesendete Nachrichten sind möglicherweise nicht bei uns angekommen.
        Falls Sie noch keine Rückmeldung auf Ihre Nachricht erhalten haben,
        senden Sie sie bitte erneut. Vielen Dank!
      </p>
      <button
        onClick={dismiss}
        aria-label="Hinweis schließen"
        className="shrink-0 -my-1 -mr-1 px-2 py-1 text-lg leading-none rounded hover:bg-amber-100 dark:hover:bg-amber-900"
      >
        ×
      </button>
    </div>
  );
}
