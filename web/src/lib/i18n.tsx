"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";

export type Locale = "de" | "en";

export const LOCALE_COOKIE = "locale";

const MESSAGES = {
  de: {
    // Home
    homeTitle: "Was im Bundestag wirklich gesagt wird.",
    summerBreakNotice:
      "Der Bundestag befindet sich derzeit in der Sommerpause. Daten sind seit März 2026 verfügbar – die Abdeckung wird bald erweitert.",
    searchPlaceholder: "z.B. Gesundheit, Kinder, Mobilität…",
    resultSingular: "Ergebnis",
    resultPlural: "Ergebnisse",
    inAllSessions: "in allen Sitzungen",
    noTopsFound: "Keine Tagesordnungspunkte gefunden.",
    // TopAccordion
    noPartySpeeches: "Keine Parteireden",
    viewSummaries: "Zusammenfassungen ansehen →",
    openDrucksache: "📄 Drucksache öffnen",
    openPdf: "📄 PDF öffnen",
    // ParliamentChart / party card
    seats: "Sitze",
    noSummaryAvailable: "Keine Zusammenfassung verfügbar.",
    source: "📋 Quelle",
    sourceTooltipMain: "Kopiert Zitat in Zwischenablage und öffnet Quelle",
    sourceTooltipHint: "Strg+F / ⌘+F drücken, dann Strg+V / ⌘+V einfügen.",
    regenerate: "↻ Neu generieren",
    generating: "Wird generiert…",
    limitReached: "Limit erreicht",
    remaining: "übrig",
    clickParty: "Klicke auf eine Partei, um ihre Position zu lesen",
    quoteNote: "",
    // GeneralSummary
    generalSummary: "Allgemeine Zusammenfassung",
    introducedBy: "Eingebracht von:",
    // Navigation / chrome
    back: "← Zurück",
    support: "Unterstützen",
    aboutMe: "Über mich",
    feedback: "Feedback",
    dark: "Dunkel",
    light: "Hell",
    themeAria: "Dark/Light Mode umschalten",
    languageAria: "Sprache wechseln",
    // Footer
    footerDisclaimer:
      "Zusammenfassungen und Kurztitel werden KI-generiert und können Fehler enthalten.",
    imprint: "Impressum",
    privacy: "Datenschutz",
    // Loading
    loadingStepProtocol: "Protokoll",
    loadingStepProtocolDesc: "Offizielles Wortprotokoll wird gelesen",
    loadingStepSpeeches: "Reden",
    loadingStepSpeechesDesc: "Redebeiträge werden extrahiert",
    loadingStepVectors: "Vektoren",
    loadingStepVectorsDesc: "Relevante Passagen werden gesucht",
    loadingStepAi: "KI",
    loadingStepAiDesc: "Positionen werden zusammengefasst",
    loadingColdStart: "Nach längerer Pause kann der Start 20–30 Sekunden dauern.",
    // Feedback page
    feedbackIntro: "Fehler in einer Zusammenfassung? Ideen? Schreib mir direkt.",
    yourFeedback: "Dein Feedback",
    feedbackPlaceholder: "Was hat gefehlt, was war falsch, was hat gut funktioniert?",
    emailLabel: "E-Mail",
    emailOptional: "(optional, falls du eine Antwort möchtest)",
    emailPlaceholder: "deine@email.de",
    send: "Senden →",
    sending: "Wird gesendet…",
    sendFailed: "Senden fehlgeschlagen. Bitte versuche es nochmal.",
    thanks: "Danke für dein Feedback!",
    thanksSub: "Es hilft uns, die Zusammenfassungen zu verbessern.",
    // FAQ
    faqTitle: "Häufige Fragen",
  },
  en: {
    // Home
    homeTitle: "What is really said in the Bundestag.",
    summerBreakNotice:
      "The Bundestag is currently in its summer recess. Data is available from March 2026 – coverage will be extended soon.",
    searchPlaceholder: "e.g. health, children, mobility…",
    resultSingular: "result",
    resultPlural: "results",
    inAllSessions: "across all sessions",
    noTopsFound: "No agenda items found.",
    // TopAccordion
    noPartySpeeches: "No party speeches",
    viewSummaries: "View summaries →",
    openDrucksache: "📄 Open document (Drucksache)",
    openPdf: "📄 Open PDF",
    // ParliamentChart / party card
    seats: "seats",
    noSummaryAvailable: "No summary available.",
    source: "📋 Source",
    sourceTooltipMain: "Copies the quote to the clipboard and opens the source",
    sourceTooltipHint: "Press Ctrl+F / ⌘+F, then paste with Ctrl+V / ⌘+V.",
    regenerate: "↻ Regenerate",
    generating: "Generating…",
    limitReached: "Limit reached",
    remaining: "left",
    clickParty: "Click a party to read its position",
    quoteNote: "Quotes are verbatim from the official German protocol.",
    // GeneralSummary
    generalSummary: "General summary",
    introducedBy: "Introduced by:",
    // Navigation / chrome
    back: "← Back",
    support: "Support",
    aboutMe: "About me",
    feedback: "Feedback",
    dark: "Dark",
    light: "Light",
    themeAria: "Toggle dark/light mode",
    languageAria: "Switch language",
    // Footer
    footerDisclaimer:
      "Summaries and short titles are AI-generated and may contain errors.",
    imprint: "Imprint",
    privacy: "Privacy",
    // Loading
    loadingStepProtocol: "Protocol",
    loadingStepProtocolDesc: "Reading the official verbatim protocol",
    loadingStepSpeeches: "Speeches",
    loadingStepSpeechesDesc: "Extracting speech contributions",
    loadingStepVectors: "Vectors",
    loadingStepVectorsDesc: "Searching relevant passages",
    loadingStepAi: "AI",
    loadingStepAiDesc: "Summarizing positions",
    loadingColdStart: "After a longer pause, startup can take 20–30 seconds.",
    // Feedback page
    feedbackIntro: "Error in a summary? Ideas? Write to me directly.",
    yourFeedback: "Your feedback",
    feedbackPlaceholder: "What was missing, what was wrong, what worked well?",
    emailLabel: "Email",
    emailOptional: "(optional, if you would like a reply)",
    emailPlaceholder: "your@email.com",
    send: "Send →",
    sending: "Sending…",
    sendFailed: "Sending failed. Please try again.",
    thanks: "Thank you for your feedback!",
    thanksSub: "It helps us improve the summaries.",
    // FAQ
    faqTitle: "Frequently asked questions",
  },
} as const;

export type MessageKey = keyof (typeof MESSAGES)["de"];

export const MONTHS: Record<Locale, string[]> = {
  de: [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
  ],
  en: [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ],
};

export const WEEKDAYS: Record<Locale, string[]> = {
  de: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
  en: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
};

export function getMessage(locale: Locale, key: MessageKey): string {
  return MESSAGES[locale][key];
}

interface LocaleContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: MessageKey) => string;
}

const LocaleContext = createContext<LocaleContextValue>({
  locale: "de",
  setLocale: () => {},
  t: (key) => MESSAGES.de[key],
});

export function readLocaleCookie(): Locale {
  if (typeof document === "undefined") return "de";
  const match = document.cookie.match(/(?:^|;\s*)locale=(de|en)/);
  return (match?.[1] as Locale) ?? "de";
}

export function LocaleProvider({
  initialLocale,
  children,
}: {
  initialLocale?: Locale;
  children: ReactNode;
}) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale ?? "de");
  const router = useRouter();

  // Same post-hydration pattern as the theme toggle: SSR renders the default,
  // the cookie value is applied after mount.
  useEffect(() => {
    if (initialLocale) return;
    const fromCookie = readLocaleCookie();
    if (fromCookie !== locale) setLocaleState(fromCookie);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function setLocale(l: Locale) {
    setLocaleState(l);
    document.cookie = `${LOCALE_COOKIE}=${l};path=/;max-age=31536000;samesite=lax`;
    document.documentElement.lang = l;
    // Re-render server components (summary pages fetch content per language)
    router.refresh();
  }

  return (
    <LocaleContext.Provider
      value={{ locale, setLocale, t: (key) => MESSAGES[locale][key] }}
    >
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale(): LocaleContextValue {
  return useContext(LocaleContext);
}
