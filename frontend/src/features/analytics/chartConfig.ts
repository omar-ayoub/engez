// Shared Recharts theme constants matching @theme tokens from index.css.
// SVG attributes can't resolve CSS custom properties, so hex equivalents are used.

export const chartTheme = {
  grid: "#373737",       // --color-border: oklch(0.25 0 0)
  tick: "#8c8c8c",       // --color-muted-foreground: oklch(0.6 0 0)
  legendText: "#8c8c8c", // --color-muted-foreground: oklch(0.6 0 0)
};

// Tooltip is rendered as HTML, so CSS custom properties work here
export const chartTooltipStyle = {
  contentStyle: {
    backgroundColor: "var(--color-card)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
  },
  labelStyle: { color: "var(--color-foreground)" },
};
