import type { ReactNode } from "react";

/** Turn `foo **bar** baz` into React nodes with <strong> around bar. Used to render
 *  the inline **bold** lead-ins in the "Variante D" general-summary format
 *  (**Verlauf:** line + bullet points). */
export function inlineBold(s: string): ReactNode {
  return s.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={j} className="font-semibold text-zinc-700 dark:text-zinc-300">
        {part.slice(2, -2)}
      </strong>
    ) : (
      part
    ),
  );
}
