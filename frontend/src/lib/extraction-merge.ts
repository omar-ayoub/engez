export interface ExtractionSource {
  amount?: number | null;
  currency?: string;
  category?: string | null;
  vendor?: string | null;
  items?: string | null;
  vendor_tax_reg?: string | null;
  date?: string | null;
  project_hint?: string | null;
  confidence?: Record<string, number | null> | null;
}

interface MergedExtraction {
  source: "combined";
  amount: number | null;
  amount_source: string;
  vendor: string | null;
  vendor_source: string;
  items: string | null;
  items_source: string;
  category: string | null;
  category_source: string;
  currency: string;
  project_hint: string | null;
  project_hint_source: string;
  vendor_tax_reg: string | null;
  date: string | null;
}

export function mergeExtractions(
  voice?: ExtractionSource | null,
  receipt?: {
    extraction?: ExtractionSource | null;
    qr_detected?: boolean;
    qr_data?: {
      total?: number | null;
      issuer_rin?: string | null;
      datetime?: string | null;
    } | null;
  } | null
): MergedExtraction {
  const r = receipt?.extraction;
  const qr = receipt?.qr_data;
  const qrDetected = receipt?.qr_detected ?? false;

  function pickNumber(field: "amount"): { value: number | null; source: string } {
    if (qrDetected && qr?.total != null) return { value: qr.total, source: "qr" };
    if (r && r[field] != null) return { value: r[field] as number, source: "receipt_ocr" };
    if (voice && voice[field] != null) return { value: voice[field] as number, source: "voice" };
    return { value: null, source: "none" };
  }

  function pickString(field: keyof ExtractionSource): { value: string | null; source: string } {
    if (qrDetected && field === "vendor_tax_reg" && qr?.issuer_rin) {
      return { value: qr.issuer_rin, source: "qr" };
    }
    if (qrDetected && field === "date" && qr?.datetime) {
      return { value: qr.datetime, source: "qr" };
    }
    if (r && r[field] != null) return { value: r[field] as string, source: "receipt_ocr" };
    if (voice && voice[field] != null) return { value: voice[field] as string, source: "voice" };
    return { value: null, source: "none" };
  }

  const amount = pickNumber("amount");
  const vendor = pickString("vendor");
  const items = pickString("items");
  const category = pickString("category");
  const project_hint = pickString("project_hint");
  const vendor_tax_reg = pickString("vendor_tax_reg");
  const date = pickString("date");

  return {
    source: "combined",
    amount: amount.value,
    amount_source: amount.source,
    vendor: vendor.value,
    vendor_source: vendor.source,
    items: items.value,
    items_source: items.source,
    category: category.value,
    category_source: category.source,
    currency: r?.currency || voice?.currency || "EGP",
    project_hint: project_hint.value,
    project_hint_source: project_hint.source,
    vendor_tax_reg: vendor_tax_reg.value,
    date: date.value,
  };
}
