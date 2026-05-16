import { useTranslation } from "react-i18next";
import {
  Hammer,
  Truck,
  Fuel,
  UtensilsCrossed,
  Wrench,
  FileCheck,
  Settings,
  MoreHorizontal,
} from "lucide-react";

const CATEGORIES = [
  { id: "materials", icon: Hammer },
  { id: "transport", icon: Truck },
  { id: "fuel", icon: Fuel },
  { id: "food", icon: UtensilsCrossed },
  { id: "equipment", icon: Wrench },
  { id: "permits", icon: FileCheck },
  { id: "maintenance", icon: Settings },
  { id: "other", icon: MoreHorizontal },
] as const;

interface CategoryGridProps {
  selected: string;
  onChange: (categoryId: string) => void;
}

export default function CategoryGrid({ selected, onChange }: CategoryGridProps) {
  const { t } = useTranslation("capture");

  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    let target: number;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      target = (index + 1) % CATEGORIES.length;
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      target = (index - 1 + CATEGORIES.length) % CATEGORIES.length;
    } else {
      return;
    }
    const buttons = e.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>("[role=radio]");
    buttons?.[target]?.focus();
    onChange(CATEGORIES[target].id);
  };

  return (
    <div id="category-grid" className="grid grid-cols-4 grid-rows-2 gap-2" role="radiogroup" aria-label={t("form.category")}>
      {CATEGORIES.map(({ id, icon: Icon }, index) => (
        <button
          key={id}
          type="button"
          role="radio"
          tabIndex={selected === id || (!selected && index === 0) ? 0 : -1}
          onClick={() => onChange(id)}
          onKeyDown={(e) => handleKeyDown(e, index)}
          className={`flex min-h-touch flex-col items-center justify-center gap-1 rounded-xl p-2 transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
            selected === id
              ? "bg-brand-surface text-white"
              : "bg-secondary text-muted-foreground hover:bg-accent"
          }`}
          aria-checked={selected === id}
          aria-label={t(`categories.${id}`)}
        >
          <Icon className="size-5" />
          <span className="text-xs leading-tight">{t(`categories.${id}`)}</span>
        </button>
      ))}
    </div>
  );
}
