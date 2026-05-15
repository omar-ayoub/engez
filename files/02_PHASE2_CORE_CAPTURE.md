# Phase 2: Core Capture — Weeks 4–7

## Spec-Kit Commands for Phase 2

```bash
/speckit.specify
```

> **Specification Prompt for Phase 2:**
>
> Build the core expense capture features that replace the WhatsApp + Spreadsheet workflow for Egyptian field workers.
>
> Four capture modes, in priority order:
> 1. Voice capture: field worker speaks in Egyptian Arabic dialect. AI transcribes and extracts structured expense data (amount, currency, category, vendor, project hint) as JSON. Pre-fills the form. Target: under 2 seconds from recording end to pre-filled form.
> 2. Receipt photo capture: field worker photographs a receipt. AI extracts text (Arabic and English) via GPT-4o vision. If an ETA-compliant QR code is present, decode it to auto-fill vendor tax registration, amount, date, and UUID — zero typing required.
> 3. Combined: voice + photo together. AI merges both extraction results, preferring ETA QR data when available.
> 4. Manual: fallback form entry with Arabic autocomplete for vendor names from cached vendor database.
>
> All capture modes must work fully offline. Data saves to IndexedDB via Dexie.js immediately. Blobs (voice recordings, receipt photos) queue for upload. Background Sync API replays submissions when connectivity returns.
>
> The form must auto-save drafts every 5 seconds. Submit = one large button tap. Total time from app open to expense submitted: under 15 seconds.

```bash
/speckit.clarify
/speckit.plan
```

> **Plan Prompt for Phase 2:**
>
> Voice capture uses the browser MediaRecorder API (webm/opus format, max 60 seconds). Audio blob is sent to FastAPI backend which calls OpenAI gpt-4o-mini-transcribe with a system prompt tailored for Egyptian Arabic expense extraction. Few-shot examples from the correction_feedback table (per company_id) are injected into the prompt.
>
> Receipt capture uses the HTML5 input[type=file][capture=environment] element for native camera access. Client-side compression with canvas: max 1200px longest edge, JPEG quality 0.85. Compressed image sent to FastAPI which calls GPT-4o vision for text extraction. Separately, pyzbar decodes any ETA QR code from the image.
>
> Offline sync uses Dexie.js for IndexedDB storage and the Background Sync API via the service worker (injectManifest strategy in vite-plugin-pwa). Sync queue items have retry logic with exponential backoff.

```bash
/speckit.tasks
/speckit.analyze
/speckit.implement
```

---

## Task 2.1: Voice Capture — Main Differentiator (Days 1–5)

### Frontend: Voice Recording Component

Create `frontend/src/features/field/hooks/useVoiceCapture.ts`:

```typescript
import { useState, useRef, useCallback } from "react";

interface VoiceResult {
  blob: Blob;
  duration: number;
}

export function useVoiceCapture(maxDurationMs = 60_000) {
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval>>();
  const startTimeRef = useRef<number>(0);

  const start = useCallback(async (): Promise<void> => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 16000, // Optimal for Whisper
      },
    });

    // Prefer opus codec for smaller file size
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

    const recorder = new MediaRecorder(stream, { mimeType });
    chunksRef.current = [];

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.start(250); // Collect chunks every 250ms
    mediaRecorderRef.current = recorder;
    startTimeRef.current = Date.now();
    setIsRecording(true);

    // Duration counter
    timerRef.current = setInterval(() => {
      setDuration(Date.now() - startTimeRef.current);
    }, 100);

    // Auto-stop at max duration
    setTimeout(() => {
      if (mediaRecorderRef.current?.state === "recording") {
        stop();
      }
    }, maxDurationMs);
  }, [maxDurationMs]);

  const stop = useCallback((): Promise<VoiceResult> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state !== "recording") {
        throw new Error("Not recording");
      }

      clearInterval(timerRef.current);

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType,
        });
        const finalDuration = Date.now() - startTimeRef.current;
        setIsRecording(false);
        setDuration(0);

        // Stop all tracks to release microphone
        recorder.stream.getTracks().forEach((t) => t.stop());

        resolve({ blob, duration: finalDuration });
      };

      recorder.stop();
    });
  }, []);

  return { isRecording, duration, start, stop };
}
```

### Backend: Voice Extraction Endpoint

Create `backend/app/services/ai_voice.py`:

```python
"""Egyptian Arabic voice-to-expense extraction using OpenAI Whisper + GPT."""

import json
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def get_few_shot_examples(
    db_session, company_id: str, limit: int = 10
) -> str:
    """Fetch recent correction feedback as few-shot examples.
    THIS IS THE COMPOUNDING MOAT — accuracy improves per-tenant over time."""
    from sqlalchemy import select, desc
    from app.models.expense import CorrectionFeedback

    stmt = (
        select(CorrectionFeedback)
        .where(CorrectionFeedback.company_id == company_id)
        .order_by(desc(CorrectionFeedback.created_at))
        .limit(limit)
    )
    result = await db_session.execute(stmt)
    corrections = result.scalars().all()

    if not corrections:
        return ""

    examples = "\n".join(
        f'- When AI extracted "{c.ai_value}" for {c.field_name}, '
        f'the correct value was "{c.corrected_value}"'
        for c in corrections
    )
    return f"\n\nHistorical corrections for this company:\n{examples}\n"


async def transcribe_and_extract(
    audio_bytes: bytes,
    audio_format: str,
    company_id: str,
    db_session,
    project_names: Optional[list[str]] = None,
) -> dict:
    """Transcribe Egyptian Arabic voice and extract expense fields."""

    # Step 1: Transcribe with Whisper
    transcription = await client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=("voice.webm", audio_bytes, f"audio/{audio_format}"),
        language="ar",
        prompt=(
            "Egyptian Arabic dialect expense report. "
            "Common words: مصاريف، إيصال، فاتورة، مشروع، موقع، "
            "أسمنت، حديد، نقل، بنزين، أكل، عدد"
        ),
    )

    transcript = transcription.text

    # Step 2: Get few-shot examples from correction history
    few_shot = await get_few_shot_examples(db_session, company_id)

    # Step 3: Extract structured data with GPT
    project_hint = ""
    if project_names:
        project_hint = (
            f"\nActive projects: {', '.join(project_names)}\n"
            "Match the project_hint to the closest project name.\n"
        )

    extraction = await client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expense data extractor for Egyptian companies. "
                    "Extract structured expense data from Egyptian Arabic transcripts.\n"
                    "Return JSON with these fields:\n"
                    "- amount: number (in EGP unless stated otherwise)\n"
                    "- currency: string (default 'EGP')\n"
                    "- category: string (one of: materials, transport, fuel, "
                    "food, equipment, permits, maintenance, other)\n"
                    "- vendor: string (vendor/shop name if mentioned)\n"
                    "- project_hint: string (project name if mentioned)\n"
                    "- confidence: object with 0-1 score per field\n"
                    f"{project_hint}"
                    f"{few_shot}"
                    "\nIf a field cannot be determined, set it to null. "
                    "Never guess amounts — if unclear, set amount to null."
                ),
            },
            {
                "role": "user",
                "content": f"Transcript: {transcript}",
            },
        ],
    )

    extracted = json.loads(extraction.choices[0].message.content)

    return {
        "transcript": transcript,
        "extraction": extracted,
        "confidence": extracted.get("confidence", {}),
    }
```

Create `backend/app/api/v1/voice.py`:

```python
"""Voice capture API endpoint."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.expense import User
from app.services.ai_voice import transcribe_and_extract

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/extract")
async def extract_from_voice(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept voice recording, transcribe, and extract expense data."""
    if audio.size and audio.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(413, "Audio file too large (max 10MB)")

    audio_bytes = await audio.read()
    audio_format = "webm"  # From MediaRecorder

    # Get active project names for matching
    from sqlalchemy import select
    from app.models.expense import Project

    stmt = select(Project.name_ar, Project.name).where(
        Project.company_id == current_user.company_id,
        Project.is_active == True,
    )
    result = await db.execute(stmt)
    projects = result.all()
    project_names = [f"{p.name_ar} ({p.name})" for p in projects]

    extraction = await transcribe_and_extract(
        audio_bytes=audio_bytes,
        audio_format=audio_format,
        company_id=current_user.company_id,
        db_session=db,
        project_names=project_names,
    )

    return extraction
```

---

## Task 2.2: Receipt OCR + ETA QR Decode (Days 6–10)

### Client-Side Image Compression

Create `frontend/src/lib/image-compress.ts`:

```typescript
/**
 * Compress receipt image before upload.
 * Critical for: reducing upload size on slow Egyptian mobile networks,
 * and preventing SAP Concur's fatal flaw of uncompressed receipt uploads.
 */
export async function compressReceiptImage(
  file: File,
  maxDimension = 1200,
  quality = 0.85
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");

    img.onload = () => {
      let { width, height } = img;

      // Scale down to max dimension while preserving aspect ratio
      if (width > maxDimension || height > maxDimension) {
        if (width > height) {
          height = (height / width) * maxDimension;
          width = maxDimension;
        } else {
          width = (width / height) * maxDimension;
          height = maxDimension;
        }
      }

      canvas.width = width;
      canvas.height = height;
      ctx?.drawImage(img, 0, 0, width, height);

      canvas.toBlob(
        (blob) => {
          if (blob) resolve(blob);
          else reject(new Error("Compression failed"));
        },
        "image/jpeg",
        quality
      );
    };

    img.onerror = () => reject(new Error("Image load failed"));
    img.src = URL.createObjectURL(file);
  });
}
```

### Backend: Receipt + ETA QR Processing

Create `backend/app/services/qr_decode.py`:

```python
"""ETA e-invoice QR code decoding.
Available NOWHERE ELSE in the Egyptian market.

ETA QR Format:
{portal_url}/receipts/search/{UUID}/share/{DateTime}#Total:{Total},IssuerRIN:{TaxRegNumber}
"""

import re
from io import BytesIO
from typing import Optional
from dataclasses import dataclass

from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode


@dataclass
class ETAQRData:
    uuid: str
    total: float
    issuer_rin: str  # Tax Registration Number
    datetime: str
    raw_url: str


def decode_eta_qr(image_bytes: bytes) -> Optional[ETAQRData]:
    """Decode ETA-compliant QR code from receipt image.

    Returns structured tax data or None if no valid QR found.
    """
    img = Image.open(BytesIO(image_bytes))

    # Attempt decode at original resolution
    decoded = pyzbar_decode(img)

    if not decoded:
        # Retry with grayscale + contrast enhancement for thermal receipts
        img_gray = img.convert("L")
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(img_gray)
        img_enhanced = enhancer.enhance(2.0)
        decoded = pyzbar_decode(img_enhanced)

    for barcode in decoded:
        data = barcode.data.decode("utf-8", errors="ignore")

        # Match ETA QR pattern
        # Format: .../receipts/search/{UUID}/share/{DateTime}#Total:{Total},IssuerRIN:{RIN}
        pattern = (
            r"receipts/search/([a-f0-9]{64})/share/"
            r"(\d{4}-\d{2}-\d{2}T[\d:]+Z?)"
            r"#Total:([\d.]+),IssuerRIN:(\d+)"
        )
        match = re.search(pattern, data)

        if match:
            return ETAQRData(
                uuid=match.group(1),
                total=float(match.group(2) if match.group(3) else match.group(3)),
                # Fix: group indices
                datetime=match.group(2),
                total=float(match.group(3)),
                issuer_rin=match.group(4),
                raw_url=data,
            )

    return None
```

Create `backend/app/services/ai_receipt.py`:

```python
"""Receipt OCR using GPT-4o vision."""

import base64
import json
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.qr_decode import decode_eta_qr, ETAQRData

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def process_receipt(
    image_bytes: bytes,
    company_id: str,
    db_session,
) -> dict:
    """Process receipt image: OCR + ETA QR decode.

    Returns merged extraction preferring QR data when available.
    """
    # Step 1: Attempt ETA QR decode (instant, no API call needed)
    qr_data: Optional[ETAQRData] = decode_eta_qr(image_bytes)

    # Step 2: GPT-4o vision for OCR (catches what QR misses: category, vendor name)
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    ocr_result = await client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an Arabic/English receipt OCR system for Egyptian businesses. "
                    "Extract all visible data from this receipt image.\n"
                    "Return JSON with:\n"
                    "- amount: number\n"
                    "- currency: string (default 'EGP')\n"
                    "- vendor: string\n"
                    "- date: string (ISO 8601)\n"
                    "- category: string (materials|transport|fuel|food|"
                    "equipment|permits|maintenance|other)\n"
                    "- line_items: array of {description, amount} if visible\n"
                    "- confidence: object with 0-1 score per field\n"
                    "\nReceipts may be thermal paper (faded/smudged), "
                    "handwritten, or printed. Arabic text is common."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        max_tokens=1000,
    )

    ocr_extraction = json.loads(ocr_result.choices[0].message.content)

    # Step 3: Merge — QR data overrides OCR where available
    merged = {**ocr_extraction}

    if qr_data:
        merged["amount"] = qr_data.total
        merged["vendor_tax_reg"] = qr_data.issuer_rin
        merged["eta_uuid"] = qr_data.uuid
        merged["eta_verified"] = True
        merged["date"] = qr_data.datetime

        # Look up vendor name from cache using tax registration
        from sqlalchemy import select
        from app.models.expense import VendorCache

        stmt = select(VendorCache).where(
            VendorCache.company_id == company_id,
            VendorCache.tax_registration == qr_data.issuer_rin,
        )
        result = await db_session.execute(stmt)
        cached_vendor = result.scalar_one_or_none()

        if cached_vendor:
            merged["vendor"] = cached_vendor.name
            if cached_vendor.category_hint:
                merged["category"] = cached_vendor.category_hint

    return {
        "extraction": merged,
        "qr_detected": qr_data is not None,
        "qr_data": {
            "uuid": qr_data.uuid,
            "total": qr_data.total,
            "issuer_rin": qr_data.issuer_rin,
        } if qr_data else None,
        "confidence": merged.get("confidence", {}),
    }
```

---

## Task 2.3: Expense Form — Critical UX (Days 11–14)

### Design Requirement

Run Impeccable before building the form:

```bash
/impeccable critique expense-form
# Then after building:
/impeccable polish expense-form
```

### Key UX Rules

1. **Pre-filled from AI** — user should rarely type anything
2. **Amount field is huge** — largest element on screen, monospace font, LTR direction
3. **Category** — visual icon grid, not a dropdown (faster for touch)
4. **Vendor** — autocomplete from cached vendor DB
5. **Project** — single tap from recent projects list
6. **Submit button** — full width, tall (56px), bottom-fixed, one tap
7. **Auto-save** — draft saves to IndexedDB every 5 seconds
8. **Arabic labels default** — English available via settings toggle

### Form Architecture

The expense form component should:
- Accept pre-filled data from voice extraction or receipt OCR
- Merge voice + receipt data when both provided (prefer QR data for amounts)
- Show confidence indicators (green/amber/red badges) on AI-filled fields
- Low-confidence fields have a subtle yellow highlight — user attention drawn there
- Save to Dexie.js `expenses` table with `status: "draft"` on every auto-save
- On submit: change status to `"pending"`, add to `syncQueue`, trigger Background Sync

---

## Task 2.4: Offline + Background Sync (Days 15–18)

### Switch to injectManifest Strategy

Update `frontend/vite.config.ts` to use `injectManifest` for custom sync logic:

```typescript
VitePWA({
  strategies: "injectManifest",
  srcDir: "src/sw",
  filename: "service-worker.ts",
  registerType: "autoUpdate",
  injectManifest: {
    globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
  },
  devOptions: {
    enabled: true,
    type: "module",
  },
})
```

### Custom Service Worker with Background Sync

Create `frontend/src/sw/service-worker.ts`:

```typescript
/// <reference lib="webworker" />
import { precacheAndRoute, cleanupOutdatedCaches } from "workbox-precaching";
import { registerRoute } from "workbox-routing";
import { NetworkFirst, CacheFirst } from "workbox-strategies";
import { ExpirationPlugin } from "workbox-expiration";
import { BackgroundSyncPlugin } from "workbox-background-sync";

declare let self: ServiceWorkerGlobalScope;

// Precache app shell
precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

// API calls: Network first with 5s timeout, fallback to cache
registerRoute(
  ({ url }) => url.pathname.startsWith("/api/"),
  new NetworkFirst({
    cacheName: "api-responses",
    networkTimeoutSeconds: 5,
    plugins: [
      new ExpirationPlugin({ maxEntries: 200, maxAgeSeconds: 86400 }),
    ],
  })
);

// Font files: Cache first (they don't change)
registerRoute(
  ({ request }) => request.destination === "font",
  new CacheFirst({
    cacheName: "fonts",
    plugins: [
      new ExpirationPlugin({ maxEntries: 10, maxAgeSeconds: 31536000 }),
    ],
  })
);

// Background Sync for expense submissions
const expenseSyncPlugin = new BackgroundSyncPlugin("expense-sync-queue", {
  maxRetentionTime: 7 * 24 * 60, // 7 days in minutes
  onSync: async ({ queue }) => {
    let entry;
    while ((entry = await queue.shiftRequest())) {
      try {
        await fetch(entry.request.clone());
      } catch (error) {
        // Re-add failed request back to queue
        await queue.unshiftRequest(entry);
        throw error; // Triggers retry
      }
    }
  },
});

// Register expense submission route for background sync
registerRoute(
  ({ url }) => url.pathname === "/api/v1/expenses",
  new NetworkFirst({
    plugins: [expenseSyncPlugin],
  }),
  "POST"
);

// Receipt image upload route with background sync
registerRoute(
  ({ url }) => url.pathname === "/api/v1/receipts/upload",
  new NetworkFirst({
    plugins: [
      new BackgroundSyncPlugin("receipt-upload-queue", {
        maxRetentionTime: 7 * 24 * 60,
      }),
    ],
  }),
  "POST"
);

// Listen for skip waiting message
self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});
```

### Sync Status Hook

Create `frontend/src/hooks/useSyncStatus.ts`:

```typescript
import { useState, useEffect, useCallback } from "react";
import { db } from "@/lib/db";
import { useLiveQuery } from "dexie-react-hooks";

export type SyncStatus = "idle" | "syncing" | "offline" | "error";

export function useSyncStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>("idle");

  // Live query: count of unsynced expenses
  const pendingCount = useLiveQuery(
    () => db.expenses.where("status").equals("pending").count(),
    [],
    0
  );

  const queueCount = useLiveQuery(
    () => db.syncQueue.count(),
    [],
    0
  );

  useEffect(() => {
    const onOnline = () => {
      setIsOnline(true);
      triggerSync();
    };
    const onOffline = () => {
      setIsOnline(false);
      setSyncStatus("offline");
    };

    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);

    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  const triggerSync = useCallback(async () => {
    if (!navigator.onLine) return;
    setSyncStatus("syncing");

    try {
      // Request Background Sync
      const registration = await navigator.serviceWorker.ready;
      await registration.sync?.register("expense-sync");
      setSyncStatus("idle");
    } catch {
      // Fallback: manual sync for browsers without Background Sync API
      setSyncStatus("error");
    }
  }, []);

  return {
    isOnline,
    syncStatus,
    pendingCount,
    queueCount,
    triggerSync,
  };
}
```

---

## Phase 2 Completion Checklist

- [ ] Voice recording captures audio in webm/opus format
- [ ] Backend transcribes Egyptian Arabic correctly (test with real dialect samples)
- [ ] AI extraction returns valid JSON with amount, category, vendor, confidence scores
- [ ] Few-shot examples from correction_feedback are injected into prompts
- [ ] Receipt photo compresses to under 300KB before upload
- [ ] GPT-4o vision extracts text from Arabic thermal receipts
- [ ] ETA QR codes decode correctly (test with production ETA receipt)
- [ ] QR data overrides OCR data in merged extraction
- [ ] Vendor cache lookup by tax registration number works
- [ ] Expense form pre-fills from AI extraction
- [ ] Low-confidence fields are highlighted
- [ ] Auto-save to IndexedDB works every 5 seconds
- [ ] Submit adds to sync queue and triggers Background Sync
- [ ] Offline mode: full capture flow works with airplane mode
- [ ] Reconnection: queued expenses sync automatically
- [ ] Total time from app open to submit: measured under 15 seconds
- [ ] `/impeccable polish expense-form` passes with no P0 issues

**Proceed to `03_PHASE3_REVIEW_DESK.md` →**
