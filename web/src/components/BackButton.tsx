"use client";

import { useRouter } from "next/navigation";
import { usePdfSplitScreen } from "@/components/PdfSplitScreenProvider";

export default function BackButton() {
  const router = useRouter();
  const { open, hide } = usePdfSplitScreen();
  return (
    <button
      onClick={() => (open ? hide() : router.back())}
      className="text-sm text-[#3e3ac6] dark:text-[#ceec97] hover:underline"
    >
      ← Zurück
    </button>
  );
}
