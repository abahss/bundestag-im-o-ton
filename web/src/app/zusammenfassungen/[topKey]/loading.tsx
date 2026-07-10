export default function Loading() {
  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 flex items-center justify-center">
      <div className="text-center space-y-3">
        <div className="w-8 h-8 border-2 border-[#219EBC] border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-sm text-zinc-400">Zusammenfassungen werden geladen…</p>
      </div>
    </div>
  );
}
