"use client";

import { useRouter } from "next/navigation";
import ThemeToggle from "@/components/ThemeToggle";

const SECTIONS: { h: string; content: React.ReactNode }[] = [
  {
    h: "Verantwortlicher",
    content: (
      <p className="text-sm text-zinc-500 leading-relaxed">
        Anna Chelsea Bahß<br />
        Baesweilerhof 40<br />
        50933 Köln<br />
        Deutschland<br />
        E-Mail: bundestag.im.o.ton@gmail.com
      </p>
    ),
  },
  {
    h: "Hosting und Server-Logfiles",
    content: (
      <p className="text-sm text-zinc-500 leading-relaxed">
        Diese Website wird bei Vercel Inc. gehostet, das Backend läuft bei Google Cloud (Cloud Run,
        Rechenzentrum in der EU). Beim Aufruf der Seite werden automatisch technische Informationen
        (u.a. IP-Adresse, Zeitpunkt der Anfrage, aufgerufene Seite, Browsertyp) in Server-Logfiles
        verarbeitet. Das ist technisch notwendig, um die Seite auszuliefern und ihren sicheren Betrieb zu
        gewährleisten (Art. 6 Abs. 1 lit. f DSGVO). Eine Zusammenführung mit anderen Daten findet nicht statt.
      </p>
    ),
  },
  {
    h: "Vercel Analytics und Speed Insights",
    content: (
      <p className="text-sm text-zinc-500 leading-relaxed">
        Wir nutzen Vercel Analytics und Vercel Speed Insights, um anonymisierte, aggregierte Nutzungs- und
        Performance-Daten zu erfassen (z.B. aufgerufene Seiten, Ladezeiten). Beide Dienste arbeiten ohne
        Cookies und ohne Erstellung individueller Nutzerprofile. Rechtsgrundlage ist unser berechtigtes
        Interesse an der Verbesserung der Seite (Art. 6 Abs. 1 lit. f DSGVO).
      </p>
    ),
  },
  {
    h: "Feedback-Funktion",
    content: (
      <p className="text-sm text-zinc-500 leading-relaxed">
        Über das Feedback-Formular kannst du uns freiwillig einen Text sowie optional eine E-Mail-Adresse
        schicken. Diese Angaben werden auf unserem Server gespeichert und zusätzlich per E-Mail an unser
        Postfach weitergeleitet, um Rückmeldungen bearbeiten und ggf. beantworten zu können. Rechtsgrundlage
        ist Art. 6 Abs. 1 lit. a DSGVO (Einwilligung durch das aktive Absenden des Formulars) bzw. lit. f
        (berechtigtes Interesse an der Verbesserung der Inhalte). Die Angabe einer E-Mail-Adresse ist
        freiwillig. Du kannst die Löschung deines Feedbacks jederzeit formlos per E-Mail verlangen.
      </p>
    ),
  },
  {
    h: "Keine Cookies, kein Tracking",
    content: (
      <p className="text-sm text-zinc-500 leading-relaxed">
        Diese Website setzt keine Cookies zu Analyse- oder Werbezwecken ein. Im Browser gespeicherte Daten
        (localStorage/sessionStorage) dienen ausschließlich der Funktion der Seite selbst — z.B. der
        Anzeige-Präferenz (hell/dunkel) oder dem Zwischenspeichern bereits geladener Zusammenfassungen — und
        enthalten keine personenbezogenen Daten. Eine Einwilligung ist dafür gemäß § 25 Abs. 2 TTDSG nicht
        erforderlich.
      </p>
    ),
  },
  {
    h: "Deine Rechte",
    content: (
      <p className="text-sm text-zinc-500 leading-relaxed">
        Du hast das Recht auf Auskunft über die zu deiner Person gespeicherten Daten sowie auf Berichtigung,
        Löschung, Einschränkung der Verarbeitung, Datenübertragbarkeit und Widerspruch gegen die
        Verarbeitung. Wende dich dazu formlos an die oben genannte E-Mail-Adresse. Außerdem steht dir ein
        Beschwerderecht bei einer Datenschutz-Aufsichtsbehörde zu.
      </p>
    ),
  },
];

export default function DatenschutzPage() {
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
          Datenschutzerklärung
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
