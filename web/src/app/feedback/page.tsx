"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ThemeToggle from "@/components/ThemeToggle";
import { submitFeedback } from "@/lib/api";

function FeedbackForm() {
  const router = useRouter();
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
        <span className="text-3xl">🙏</span>
        <h2 className="text-lg font-semibold text-[#023047] dark:text-white">Danke für dein Feedback!</h2>
        <p className="text-sm text-zinc-500">Es hilft uns, die Zusammenfassungen zu verbessern.</p>
        <button
          onClick={() => router.push(from)}
          className="mt-4 text-sm text-[#219EBC] hover:underline"
        >
          ← Zurück
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wide block mb-2">
          Dein Feedback
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Was hat gefehlt, was war falsch, was hat gut funktioniert?"
          rows={6}
          className="w-full rounded-xl border border-zinc-200 dark:border-zinc-700 bg-transparent px-4 py-3 text-sm text-zinc-800 dark:text-zinc-200 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-[#219EBC] resize-none"
        />
      </div>
      <div>
        <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wide block mb-2">
          E-Mail <span className="font-normal normal-case">(optional, falls du eine Antwort möchtest)</span>
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="deine@email.de"
          className="w-full rounded-xl border border-zinc-200 dark:border-zinc-700 bg-transparent px-4 py-2.5 text-sm text-zinc-800 dark:text-zinc-200 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-[#219EBC]"
        />
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={!text.trim() || loading}
          className="bg-[#219EBC] text-white rounded-xl px-6 py-2.5 text-sm font-medium hover:bg-[#1a7fa0] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
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
          <button onClick={() => router.back()} className="text-sm text-[#219EBC] hover:underline">
            ← Zurück
          </button>
          <ThemeToggle />
        </div>
        <h1 className="text-xl font-bold text-[#023047] dark:text-white mb-1">Feedback</h1>
        <p className="text-sm text-zinc-500 mb-6">
          Fehler in einer Zusammenfassung? Ideen? Schreib uns direkt.
        </p>
        <Suspense>
          <FeedbackForm />
        </Suspense>
      </div>
    </div>
  );
}
