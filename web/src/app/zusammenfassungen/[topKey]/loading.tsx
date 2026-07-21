"use client";

import { useEffect, useState } from "react";
import { useLocale, MessageKey } from "@/lib/i18n";

const STEPS: { icon: string; label: MessageKey; desc: MessageKey }[] = [
  { icon: "📄", label: "loadingStepProtocol", desc: "loadingStepProtocolDesc" },
  { icon: "🗣",  label: "loadingStepSpeeches", desc: "loadingStepSpeechesDesc" },
  { icon: "⚡",  label: "loadingStepVectors",  desc: "loadingStepVectorsDesc" },
  { icon: "🤖",  label: "loadingStepAi",       desc: "loadingStepAiDesc" },
];

function FlowDots({ active, done }: { active: boolean; done: boolean }) {
  return (
    <div className="flex items-center gap-1 mx-2 mb-6">
      {[0, 1, 2].map((d) => (
        <div
          key={d}
          className={`w-1.5 h-1.5 rounded-full transition-colors duration-500 ${
            done ? "bg-[#219EBC]" : active ? "bg-[#219EBC] animate-pulse" : "bg-zinc-200 dark:bg-zinc-700"
          }`}
          style={{ animationDelay: `${d * 180}ms` }}
        />
      ))}
    </div>
  );
}

export default function Loading() {
  const { t } = useLocale();
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setActiveStep((s) => (s + 1) % STEPS.length), 2200);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 flex flex-col items-center justify-center px-4 gap-10">
      {/* Pipeline */}
      <div className="flex items-center">
        {STEPS.map((step, i) => (
          <div key={step.label} className="flex items-center">
            <div className={`flex flex-col items-center gap-2 transition-all duration-500 ${
              i === activeStep ? "opacity-100" : i < activeStep ? "opacity-50" : "opacity-20"
            }`}>
              <div className={`w-11 h-11 rounded-full flex items-center justify-center text-lg border-2 transition-all duration-500 ${
                i === activeStep
                  ? "border-[#219EBC] bg-[#219EBC]/10 scale-110"
                  : "border-zinc-200 dark:border-zinc-700"
              }`}>
                {step.icon}
              </div>
              <span className={`text-xs font-medium transition-colors duration-500 ${
                i === activeStep ? "text-[#219EBC]" : "text-zinc-400"
              }`}>
                {t(step.label)}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <FlowDots active={i === activeStep} done={i < activeStep} />
            )}
          </div>
        ))}
      </div>

      {/* Status */}
      <div className="text-center space-y-2">
        <p className="text-sm font-medium text-zinc-600 dark:text-zinc-300">
          {t(STEPS[activeStep].desc)}…
        </p>
        <p className="text-xs text-zinc-400">
          {t("loadingColdStart")}
        </p>
      </div>
    </div>
  );
}
