"use client";

import { useRouter } from "next/navigation";
import ThemeToggle from "@/components/ThemeToggle";

const SECTIONS: { h: string; content: React.ReactNode }[] = [
  {
    h: "Angaben gemäß § 5 DDG",
    content: (
      <p className="text-sm text-zinc-500 leading-relaxed">
        Anna Chelsea Bahß<br />
        Baesweilerhof 40<br />
        50933 Köln<br />
        Deutschland
      </p>
    ),
  },
  {
    h: "Kontakt",
    content: (
      <p className="text-sm text-zinc-500 leading-relaxed">
        E-Mail: bundestag.im.o.ton@gmail.com
      </p>
    ),
  },
  {
    h: "Projekthinweis",
    content: (
      <p className="text-sm text-zinc-500 leading-relaxed">
        Bundestag-im-O-Ton ist ein privates Technologie-Demonstrationsprojekt. Es werden keine Waren oder
        Dienstleistungen angeboten oder verkauft. Die Nutzung erfolgt unentgeltlich.
      </p>
    ),
  },
  {
    h: "Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV",
    content: (
      <p className="text-sm text-zinc-500 leading-relaxed">
        Anna Chelsea Bahß<br />
        Baesweilerhof 40<br />
        50933 Köln
      </p>
    ),
  },
  {
    h: "EU-Streitschlichtung",
    content: (
      <>
        <p className="text-sm text-zinc-500 leading-relaxed">
          Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit:{" "}
          <a
            href="https://ec.europa.eu/consumers/odr/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#219EBC] hover:underline"
          >
            https://ec.europa.eu/consumers/odr/
          </a>
        </p>
        <p className="text-sm text-zinc-500 leading-relaxed mt-2">
          Wir sind nicht bereit oder verpflichtet, an Streitbeilegungsverfahren vor einer
          Verbraucherschlichtungsstelle teilzunehmen.
        </p>
      </>
    ),
  },
  {
    h: "Haftung für Inhalte",
    content: (
      <>
        <p className="text-sm text-zinc-500 leading-relaxed">
          Als Diensteanbieter sind wir gemäß § 7 Abs.1 DDG für eigene Inhalte auf diesen Seiten nach den
          allgemeinen Gesetzen verantwortlich. Nach §§ 8 bis 10 DDG sind wir als Diensteanbieter jedoch nicht
          verpflichtet, übermittelte oder gespeicherte fremde Informationen zu überwachen oder nach Umständen
          zu forschen, die auf eine rechtswidrige Tätigkeit hinweisen.
        </p>
        <p className="text-sm text-zinc-500 leading-relaxed mt-2">
          Verpflichtungen zur Entfernung oder Sperrung der Nutzung von Informationen nach den allgemeinen
          Gesetzen bleiben hiervon unberührt. Eine diesbezügliche Haftung ist jedoch erst ab dem Zeitpunkt der
          Kenntnis einer konkreten Rechtsverletzung möglich.
        </p>
      </>
    ),
  },
];

export default function ImpressumPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      <div className="max-w-2xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-8">
          <button onClick={() => router.back()} className="text-sm text-[#219EBC] hover:underline">
            ← Zurück
          </button>
          <ThemeToggle />
        </div>

        <h1 className="text-xl font-bold text-[#023047] dark:text-white mb-8">
          Impressum
        </h1>

        <div className="space-y-8">
          {SECTIONS.map(({ h, content }) => (
            <div key={h}>
              <h2 className="text-sm font-semibold text-[#023047] dark:text-white mb-2">{h}</h2>
              {content}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
