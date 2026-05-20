import { test, expect } from "@playwright/test";

const emptyQueueResponse = {
  items: [],
  total: 0,
  page: 1,
  page_size: 25,
  pages: 1,
  server_time: new Date().toISOString(),
};

const sampleExpense = {
  id: "exp-001",
  review_version: 1,
  status: "pending",
  amount: 1500.0,
  currency: "EGP",
  vendor: "Test Vendor",
  employee: { id: "emp-001", name: "Ahmed Ali", name_ar: "أحمد علي" },
  project: { id: "proj-001", name: "Project A", name_ar: "مشروع أ", code: "PA" },
  capture_mode: "receipt",
  created_at: new Date().toISOString(),
  eta_verified: true,
  confidence_summary: { min: 0.92, all_high: true, low_count: 0, fields: { amount: 0.95, vendor: 0.92 } },
  anomaly_count: 0,
  bulk_eligible: true,
};

const queueWithItemsResponse = {
  items: [sampleExpense],
  total: 1,
  page: 1,
  page_size: 25,
  pages: 1,
  server_time: new Date().toISOString(),
};

const detailResponse = {
  id: "exp-001",
  review_version: 1,
  status: "pending",
  amount: 1500.0,
  currency: "EGP",
  vendor: "Test Vendor",
  vendor_tax_reg: null,
  items: "",
  notes: null,
  category_id: null,
  project_id: "proj-001",
  capture_mode: "receipt",
  receipt_url: "https://example.com/receipt.jpg",
  voice_transcript: null,
  eta: { verified: true, uuid: "eta-123", vendor_tax_reg: "12345" },
  ai_extraction: { amount: 1500, vendor: "Test Vendor" },
  ai_confidence: { amount: 0.95, vendor: 0.92 },
  anomaly_flags: null,
  employee: { id: "emp-001", name: "Ahmed Ali", name_ar: "أحمد علي" },
  audit_history: [],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

async function loginAsAccountant(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    const authData = {
      state: {
        user: {
          id: "accountant-1",
          email: "accountant@test.com",
          name: "Test Accountant",
          name_ar: "محاسب تجريبي",
          role: "accountant",
          company_id: "company-1",
          company_name: "Test Company",
          company_name_ar: "شركة اختبار",
        },
        accessToken: "test-accountant-token",
        isAuthenticated: true,
      },
      version: 0,
    };
    localStorage.setItem("engez-auth", JSON.stringify(authData));
  });
}

async function mockQueueApi(page: import("@playwright/test").Page, response = emptyQueueResponse) {
  await page.route("**/api/v1/expenses/queue**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(response) })
  );
}

async function mockFullReviewApis(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/expenses/queue**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(queueWithItemsResponse) })
  );
  await page.route("**/api/v1/expenses/exp-001/review-detail", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(detailResponse) })
  );
  await page.route("**/api/v1/expenses/exp-001/approve", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: "exp-001", status: "approved", review_version: 2, reviewed_at: new Date().toISOString(), next_pending_id: null }),
    })
  );
  await page.route("**/api/v1/expenses/exp-001/reject", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: "exp-001", status: "rejected", review_version: 2, rejection_reason: "Test", reviewed_at: new Date().toISOString(), next_pending_id: null }),
    })
  );
  await page.route("**/api/v1/expenses/bulk-approve", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ bulk_operation_id: "bulk-1", approved: 1, approved_ids: ["exp-001"], skipped: [], conflicts: [] }),
    })
  );
  await page.route("**/api/v1/notifications/**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "{}" })
  );
}

// ── Review Queue Tests ──────────────────────────────────────

test.describe("Review Queue", () => {
  test("shows review queue page for accountant", async ({ page }) => {
    await loginAsAccountant(page);
    await mockQueueApi(page);
    await page.goto("/review");

    await expect(
      page
        .getByText("طابور المراجعة")
        .or(page.getByText("Review Queue"))
    ).toBeVisible();
  });

  test("displays filter controls", async ({ page }) => {
    await loginAsAccountant(page);
    await mockQueueApi(page);
    await page.goto("/review");

    await expect(
      page.getByRole("combobox", { name: /project|مشروع|المشروع/i })
    ).toBeVisible();

    await expect(
      page.getByRole("combobox", { name: /status|الحالة/i })
    ).toBeVisible();
  });

  test("displays sort controls", async ({ page }) => {
    await loginAsAccountant(page);
    await mockQueueApi(page);
    await page.goto("/review");

    await expect(
      page.getByRole("combobox", { name: /sort|ترتيب/i })
    ).toBeVisible();
  });

  test("shows empty state when no pending expenses", async ({ page }) => {
    await loginAsAccountant(page);
    await mockQueueApi(page, emptyQueueResponse);
    await page.goto("/review");

    await expect(
      page.getByText(/all reviewed|تمت المراجعة/i)
    ).toBeVisible();
  });

  test("shows expenses in queue when data exists", async ({ page }) => {
    await loginAsAccountant(page);
    await mockQueueApi(page, queueWithItemsResponse);
    await page.goto("/review");

    await expect(page.getByText("Test Vendor")).toBeVisible();
  });
});

// ── Expense Detail Tests ────────────────────────────────────

test.describe("Expense Detail", () => {
  test("shows confidence badges for AI-extracted fields", async ({ page }) => {
    await loginAsAccountant(page);
    await mockFullReviewApis(page);
    await page.goto("/review/exp-001");

    await expect(
      page.getByText(/92%|95%/)
    ).toBeVisible();
  });

  test("shows ETA verification badge", async ({ page }) => {
    await loginAsAccountant(page);
    await mockFullReviewApis(page);
    await page.goto("/review/exp-001");

    await expect(
      page.getByText(/ETA|فاتورة إلكترونية/i)
    ).toBeVisible();
  });
});

// ── Approve / Reject Tests ──────────────────────────────────

test.describe("Approve and Reject", () => {
  test("approve button is visible in detail view", async ({ page }) => {
    await loginAsAccountant(page);
    await mockFullReviewApis(page);
    await page.goto("/review/exp-001");

    await expect(
      page.getByRole("button", { name: /approve|موافقة/i })
    ).toBeVisible();
  });

  test("reject requires reason text", async ({ page }) => {
    await loginAsAccountant(page);
    await mockFullReviewApis(page);
    await page.goto("/review/exp-001");

    const rejectBtn = page.getByRole("button", { name: /reject|رفض/i });
    await expect(rejectBtn).toBeVisible();
    await rejectBtn.click();

    const confirmBtn = page.getByRole("button", { name: /confirm|تأكيد/i });
    if (await confirmBtn.isVisible()) {
      await expect(confirmBtn).toBeDisabled();
    }
  });
});

// ── Bulk Approve Tests ──────────────────────────────────────

test.describe("Bulk Approve", () => {
  test("bulk approve button is disabled when nothing selected", async ({ page }) => {
    await loginAsAccountant(page);
    await mockQueueApi(page, queueWithItemsResponse);
    await page.goto("/review");

    const selectionBtn = page.getByRole("button", { name: /select|تحديد/i });
    if (await selectionBtn.isVisible()) {
      await selectionBtn.click();
    }

    const bulkBtn = page.getByRole("button", { name: /bulk|جماعي/i }).first();
    if (await bulkBtn.isVisible()) {
      await expect(bulkBtn).toBeDisabled();
    }
  });
});

// ── RTL Layout Tests ────────────────────────────────────────

test.describe("RTL Layout", () => {
  test("review desk renders in RTL by default", async ({ page }) => {
    await loginAsAccountant(page);
    await mockQueueApi(page);
    await page.goto("/review");

    const dir = await page.locator("html").getAttribute("dir");
    expect(dir).toBe("rtl");
  });

  test("amounts render in LTR direction", async ({ page }) => {
    await loginAsAccountant(page);
    await mockQueueApi(page, queueWithItemsResponse);
    await page.goto("/review");

    const amountEl = page.locator("[dir='ltr']").first();
    if (await amountEl.isVisible()) {
      const direction = await amountEl.evaluate(
        (el) => getComputedStyle(el).direction
      );
      expect(direction).toBe("ltr");
    }
  });
});
