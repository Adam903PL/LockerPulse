import { cn } from "@/lib/utils";
import { scoreLabel } from "@/lib/point-display";

export function ScoreBadge({
  score,
  grade,
  className,
  compact = false,
}: {
  score: number;
  grade: string;
  className?: string;
  compact?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-md border text-center",
        compact ? "h-9 min-w-[118px] flex-row gap-1.5 px-2.5" : "h-16 w-20 flex-col",
        gradeClass(grade),
        className,
      )}
    >
      <span className={cn("font-mono font-bold leading-none", compact ? "text-base" : "text-xl")}>
        {score}
      </span>
      {compact ? (
        <span className="h-4 w-px bg-current opacity-25" aria-hidden="true" />
      ) : null}
      <span
        className={cn(
          "font-semibold uppercase leading-none",
          compact ? "whitespace-nowrap text-[10px]" : "mt-1 text-[10px]",
        )}
      >
        {scoreLabel(grade)}
      </span>
    </div>
  );
}

export function gradeClass(grade: string) {
  if (grade === "excellent") {
    return "border-[#ffd200] bg-[#ffd200] text-[#1d1d1b]";
  }
  if (grade === "good") {
    return "border-[#ffd200] bg-[#fff4b8] text-[#1d1d1b]";
  }
  if (grade === "fair") {
    return "border-amber-300 bg-amber-50 text-amber-900";
  }
  if (grade === "weak") {
    return "border-orange-300 bg-orange-50 text-orange-800";
  }
  return "border-red-300 bg-red-50 text-red-800";
}
