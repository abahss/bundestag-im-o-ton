"use client";

import { useRouter } from "next/navigation";
import { useLocale } from "@/lib/i18n";

export default function BackButton() {
  const router = useRouter();
  const { t } = useLocale();
  return (
    <button
      onClick={() => router.back()}
      className="text-sm text-[#219EBC] hover:underline"
    >
      {t("back")}
    </button>
  );
}
