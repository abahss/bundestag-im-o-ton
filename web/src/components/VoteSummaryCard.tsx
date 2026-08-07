import { VoteResult } from "@/lib/api";
import VoteOutcomeRing from "@/components/VoteOutcomeRing";

export default function VoteSummaryCard({ vote }: { vote: VoteResult }) {
  return (
    <div className="bg-zinc-50 dark:bg-zinc-900 rounded-xl p-4 self-start">
      <div className="mb-3">
        <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">
          Abstimmung
        </h2>
        <VoteOutcomeRing vote={vote} />
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
