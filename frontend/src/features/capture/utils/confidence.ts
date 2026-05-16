export function confidenceBorderClass(score: number | undefined): string {
  if (score === undefined || score >= 0.5) return "";
  return "ring-1 ring-amber-500/50";
}
