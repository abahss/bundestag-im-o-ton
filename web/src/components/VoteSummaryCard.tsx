import { VoteResult } from "@/lib/api";

export default function VoteSummaryCard({ vote }: { vote: VoteResult }) {
  return (
    <div className="bg-zinc-50 dark:bg-zinc-900 rounded-xl p-4 self-start">
      <div className="flex items-center gap-2 mb-3">
        <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">
          Abstimmung
        </h2>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${
            vote.angenommen
              ? "bg-green-50 text-green-700 dark:bg-green-500/10 dark:text-green-400"
              : "bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400"
          }`}
        >
          <span>{vote.angenommen ? "✓ Angenommen" : "✗ Abgelehnt"}</span>
          <span className="text-zinc-400 dark:text-zinc-500 font-normal">
            {vote.ja} Ja · {vote.nein} Nein{vote.enthalten > 0 ? ` · ${vote.enthalten} Enth.` : ""}
          </span>
        </span>
      </div>
      {vote.label && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-2">
          <span className="font-medium text-zinc-700 dark:text-zinc-200">Titel:</span> {vote.label}
        </p>
      )}
      {vote.beschreibung && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-2 leading-relaxed">
          {vote.beschreibung}
        </p>
      )}
      {vote.abgeordnetenwatch_url && (
        <a
          href={vote.abgeordnetenwatch_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-[#FB8500] hover:underline mt-2 block text-right"
        >
          Quelle: abgeordnetenwatch.de →
        </a>
      )}
    </div>
  );
}
