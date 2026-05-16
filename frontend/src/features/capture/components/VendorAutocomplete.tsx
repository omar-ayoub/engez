import { useState, useMemo, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useLiveQuery } from "dexie-react-hooks";
import { db, type OfflineVendor } from "@/lib/db";
import { useAuthStore } from "@/lib/auth";

interface VendorAutocompleteProps {
  value: string;
  onChange: (value: string, vendor?: OfflineVendor) => void;
}

export default function VendorAutocomplete({ onChange }: VendorAutocompleteProps) {
  const { t } = useTranslation("capture");
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const user = useAuthStore((s) => s.user);
  const companyId = user?.company_id ?? "";

  const vendors = useLiveQuery(
    () => db.vendorCache.where("companyId").equals(companyId).toArray(),
    [companyId],
    [] as OfflineVendor[]
  );

  const filtered = useMemo(() => {
    if (!query || query.length < 1) return [];
    const q = query.toLowerCase();
    return vendors.filter(
      (v) =>
        v.name.toLowerCase().startsWith(q) ||
        (v.nameAr && v.nameAr.includes(query))
    ).slice(0, 8);
  }, [query, vendors]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (vendor: OfflineVendor) => {
    const displayName = vendor.nameAr || vendor.name;
    setQuery(displayName);
    onChange(displayName, vendor);
    setIsOpen(false);
    setSelectedIndex(-1);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || filtered.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && selectedIndex >= 0) {
      e.preventDefault();
      handleSelect(filtered[selectedIndex]);
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  return (
    <div ref={wrapperRef} className="relative">
      <input
        id="vendor"
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          onChange(e.target.value);
          setIsOpen(true);
          setSelectedIndex(-1);
        }}
        onFocus={() => setIsOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={t("form.vendorPlaceholder")}
        role="combobox"
        aria-expanded={isOpen && filtered.length > 0}
        aria-autocomplete="list"
        aria-controls="vendor-listbox"
        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30 md:text-sm"
      />
      {isOpen && filtered.length > 0 && (
        <ul id="vendor-listbox" role="listbox" aria-live="polite" className="absolute inset-x-0 top-full z-50 mt-1 max-h-48 overflow-y-auto rounded-lg border border-border bg-popover shadow-lg">
          {filtered.map((vendor, i) => (
            <li key={vendor.id} role="option" aria-selected={i === selectedIndex}>
              <button
                type="button"
                onClick={() => handleSelect(vendor)}
                className={`flex w-full items-center gap-2 px-3 py-2.5 text-sm transition-colors ${
                  i === selectedIndex ? "bg-accent" : "hover:bg-accent/50"
                }`}
              >
                <span className="flex-1 text-start">
                  {vendor.nameAr || vendor.name}
                </span>
                {vendor.nameAr && vendor.nameAr !== vendor.name && (
                  <span className="text-xs text-muted-foreground">{vendor.name}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
