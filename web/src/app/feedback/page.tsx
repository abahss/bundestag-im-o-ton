"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ThemeToggle from "@/components/ThemeToggle";
import { submitFeedback } from "@/lib/api";

function FeedbackForm() {
  const searchParams = useSearchParams();
  const from = searchParams.get("from") ?? "/";

  const [text, setText] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit() {
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    try {
      await submitFeedback(text, email, from);
      setSubmitted(true);
    } catch {
      setError("Senden fehlgeschlagen. Bitte versuche es nochmal.");
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
                <h2 className="text-lg font-semibold text-[#3e3ac6] dark:text-white">Danke für dein Feedback!</h2>
        <p className="text-sm text-zinc-500">Es hilft uns, die Zusammenfassungen zu verbessern.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <label htmlFor="feedback-text" className="text-xs font-semibold text-zinc-600 dark:text-zinc-400 uppercase tracking-wide block mb-2">
          Dein Feedback
        </label>
        <textarea
          id="feedback-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Was hat gefehlt, was war falsch, was hat gut funktioniert?"
          rows={6}
          className="w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-transparent px-4 py-3 text-base text-zinc-800 dark:text-zinc-200 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-[#3e3ac6] resize-none"
        />
      </div>
      <div>
        <label htmlFor="feedback-email" className="text-xs font-semibold text-zinc-600 dark:text-zinc-400 uppercase tracking-wide block mb-2">
          E-Mail <span className="font-normal normal-case">(optional, falls du eine Antwort möchtest)</span>
        </label>
        <input
          id="feedback-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="deine@email.de"
          className="w-full rounded-md border border-zinc-300 dark:border-zinc-600 bg-transparent px-4 py-2.5 text-base text-zinc-800 dark:text-zinc-200 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-[#3e3ac6]"
        />
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={!text.trim() || loading}
          className="bg-[#3e3ac6] text-white rounded-md px-6 py-2.5 text-sm font-medium hover:bg-[#2a2790] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Wird gesendet…" : "Senden →"}
        </button>
      </div>
    </div>
  );
}

export default function FeedbackPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      <div className="max-w-xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-8">
          <button onClick={() => router.back()} className="text-sm text-[#3e3ac6] dark:text-[#ceec97] hover:underline">
            ← Zurück
          </button>
          <ThemeToggle />
        </div>
        <h1 className="text-xl font-bold text-[#3e3ac6] dark:text-white mb-1">Feedback</h1>
        <p className="text-sm text-zinc-500 mb-6">
          Fehler in einer Zusammenfassung? Ideen? Schreib mir direkt.
        </p>
        <Suspense>
          <FeedbackForm />
        </Suspense>
      </div>
    </div>
  );
}
