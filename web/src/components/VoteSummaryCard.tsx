"use client";

import { useState } from "react";
import { VoteResult } from "@/lib/api";
import VoteOutcomeRing from "@/components/VoteOutcomeRing";

export default function VoteSummaryCard({ vote }: { vote: VoteResult }) {
  const [descOpen, setDescOpen] = useState(false);

  return (
    <div className="bg-zinc-50 dark:bg-zinc-900 rounded-xl p-4">
      <div className="mb-3">
        <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">
          Abstimmung
        </h2>
        {vote.label && (
          <p className="text-sm text-zinc-500 mb-1">
            <span className="font-medium">Abstimmungsgegenstand:</span> {vote.label}
          </p>
        )}
        <div className="mt-2">
          <VoteOutcomeRing vote={vote} />
        </div>
      </div>
      {vote.beschreibung && (
        <div className="mb-1">
          <div className="relative">
            <p
              className={`text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed ${
                descOpen ? "" : "line-clamp-3"
              }`}
            >
              {vote.beschreibung}
            </p>
            {!descOpen && (
              <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-6 bg-linear-to-t from-zinc-50 dark:from-zinc-900 to-transparent" />
            )}
          </div>
          <button
            onClick={() => setDescOpen((o) => !o)}
            className="mt-1 text-xs font-medium text-[#219EBC] hover:underline"
          >
            {descOpen ? "Weniger anzeigen" : "Mehr anzeigen"}
          </button>
        </div>
      )}
    </div>
  );
}
