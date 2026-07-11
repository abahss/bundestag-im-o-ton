"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function FeedbackButton() {
  const pathname = usePathname();
  if (pathname === "/feedback") return null;

  return (
    <Link
      href={`/feedback?from=${encodeURIComponent(pathname)}`}
      className="fixed bottom-14 right-4 z-40 flex items-center gap-1.5 bg-[#219EBC] text-white rounded-full shadow-lg px-3 py-2 text-sm font-medium hover:bg-[#1a7fa0] transition-colors"
    >
      <span>💬</span>
      <span className="hidden sm:inline">Feedback</span>
    </Link>
  );
}
