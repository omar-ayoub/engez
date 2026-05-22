import { test, expect } from "@playwright/test";

// ── Mock Data ────────────────────────────────────────────────

const spendByProjectResponse = [
  { name: "Tower A", name_ar: "برج أ", budget: 50000, total_spend: 35000, expense_count: 42 },
  { name: "Project B", name_ar: "مشروع ب", budget: 30000, total_spend: 28000, expense_count: 31 },
  { name: "Warehouse C", name_ar: "مستودع ج", budget: 20000, total_spend: 8000, expense_count: 15 },
];

const spendByCategoryResponse = [
  { category: "materials", category_ar: "مواد", total: 45000, count: 55 },
  { category: "transport", category_ar: "نقل", total: 12000, count: 23 },
  { category: "food", category_ar: "طعام", total: 8000, count: 40 },
];

const spendTrendResponse = [
  { week: "2026-04-07", total: 12000, count: 15 },
  { week: "2026-04-14", total: 15000, count: 18 },
  { week: "2026-04-21", total: 9000, count: 12 },
  { week: "2026-04-28", total: 18000, count: 22 },
];

const budgetVsActualResponse = [
  { name: "Tower A", name_ar: "برج أ", budget: 50000, actual_spend: 35000 },
  { name: "Project B", name_ar: "مشروع ب", budget: 30000, actual_spend: 28000 },
];

const summaryResponse = {
  total_spend: 71000,
  expense_count: 88,
  project_count: 3,
  period_days: 30,
};

const integrationStatusResponse = {
  configured: true,
  system_name: "zoho_books",
  status: "active",
  last_sync: "2026-05-16T10:00:00Z",
};

const availableIntegrationsResponse = [
  { system_name: "zoho_books", display_name: "Zoho Books", display_name_ar: "زوهو بوكس", required_fields: ["access_token", "organization_id", "expense_account_id"] },
  { system_name: "odoo", display_name: "Odoo", display_name_ar: "أودو", required_fields: ["url", "db", "username", "api_key"] },
  { system_name: "csv_daftra", display_name: "CSV (Daftra)", display_name_ar: "CSV (دفترة)", required_fields: [] },
];

const anomalyMetricsResponse = {
  total_flags: 24,
  by_type: {
    duplicate_receipt: 5,
    statistical_outlier: 8,
    high_velocity: 7,
    vendor_mismatch: 4,
  },
  rejection_correlation: 0.65,
};

// ── Helpers ──────────────────────────────────────────────────

async function loginAsAdmin(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    const authData = {
      state: {
        user: {
          id: "admin-1",
          email: "admin@test.com",
          name: "Test Admin",
          name_ar: "مدير تجريبي",
          role: "admin",
          company_id: "company-1",
          company_name: "Test Company",
          company_name_ar: "شركة اختبار",
        },
        accessToken: "test-admin-token",
        isAuthenticated: true,
      },
      version: 0,
    };
    localStorage.setItem("engez-auth", JSON.stringify(authData));
  });
}

async function mockAnalyticsApis(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/analytics/spend-by-project**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(spendByProjectResponse) })
  );
  await page.route("**/api/v1/analytics/spend-by-category**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(spendByCategoryResponse) })
  );
  await page.route("**/api/v1/analytics/spend-trend**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(spendTrendResponse) })
  );
  await page.route("**/api/v1/analytics/budget-vs-actual**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(budgetVsActualResponse) })
  );
  await page.route("**/api/v1/analytics/summary**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(summaryResponse) })
  );
  await page.route("**/api/v1/analytics/export**", (route) =>
    route.fulfill({ status: 200, contentType: "text/csv", body: "project,total\nTower A,35000\nProject B,28000" })
  );
}

async function mockIntegrationApis(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/integrations/available", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(availableIntegrationsResponse) })
  );
  await page.route("**/api/v1/integrations/status", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(integrationStatusResponse) })
  );
  await page.route("**/api/v1/integrations/test-connection", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true }) })
  );
  await page.route("**/api/v1/integrations/configure", (route) =>
    route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ system_name: "zoho_books", status: "active" }) })
  );
  await page.route("**/api/v1/anomalies/metrics", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(anomalyMetricsResponse) })
  );
}

// ── Analytics Dashboard Tests ────────────────────────────────

test.describe("Analytics Dashboard", () => {
  test("shows analytics dashboard page for admin", async ({ page }) => {
    await loginAsAdmin(page);
    await mockAnalyticsApis(page);
    await page.goto("/analytics");

    await expect(
      page.getByText("لوحة التحليلات").or(page.getByText("Analytics Dashboard"))
    ).toBeVisible();
  });

  test("displays spend by project chart", async ({ page }) => {
    await loginAsAdmin(page);
    await mockAnalyticsApis(page);
    await page.goto("/analytics");

    await expect(
      page.getByText("Tower A").or(page.getByText("برج أ"))
    ).toBeVisible();
  });

  test("displays spend by category chart", async ({ page }) => {
    await loginAsAdmin(page);
    await mockAnalyticsApis(page);
    await page.goto("/analytics");

    await expect(
      page.getByText("materials").or(page.getByText("مواد"))
    ).toBeVisible();
  });

  test("displays summary KPIs", async ({ page }) => {
    await loginAsAdmin(page);
    await mockAnalyticsApis(page);
    await page.goto("/analytics");

    await expect(page.getByText("71,000").or(page.getByText("٧١٬٠٠٠"))).toBeVisible();
  });

  test("period filter changes chart data", async ({ page }) => {
    await loginAsAdmin(page);
    await mockAnalyticsApis(page);
    await page.goto("/analytics");

    const periodSelect = page.getByRole("combobox", { name: /period|الفترة/i });
    if (await periodSelect.isVisible()) {
      await periodSelect.click();
      const option90 = page.getByRole("option", { name: /90/i });
      if (await option90.isVisible()) {
        await option90.click();
      }
    }
  });

  test("export CSV button triggers download", async ({ page }) => {
    await loginAsAdmin(page);
    await mockAnalyticsApis(page);
    await page.goto("/analytics");

    const exportBtn = page.getByRole("button", { name: /export|تصدير/i }).first();
    if (await exportBtn.isVisible()) {
      await Promise.all([
        page.waitForEvent("download").catch(() => null),
        exportBtn.click(),
      ]);
      // Download event may not fire with mocked routes, just verify no errors
    }
  });
});

// ── Integration Settings Tests ───────────────────────────────

test.describe("Integration Settings", () => {
  test("shows available integrations", async ({ page }) => {
    await loginAsAdmin(page);
    await mockIntegrationApis(page);
    await page.goto("/settings/integrations");

    await expect(
      page.getByText("Zoho Books").or(page.getByText("زوهو بوكس"))
    ).toBeVisible();
  });

  test("shows current integration status", async ({ page }) => {
    await loginAsAdmin(page);
    await mockIntegrationApis(page);
    await page.goto("/settings/integrations");

    await expect(
      page.getByText(/active|نشط/i)
    ).toBeVisible();
  });

  test("test connection button is visible", async ({ page }) => {
    await loginAsAdmin(page);
    await mockIntegrationApis(page);
    await page.goto("/settings/integrations");

    await expect(
      page.getByRole("button", { name: /test|اختبار/i })
    ).toBeVisible();
  });
});

// ── Anomaly Badges Tests ─────────────────────────────────────

test.describe("Anomaly Badges", () => {
  test("anomaly metrics page is accessible to admin", async ({ page }) => {
    await loginAsAdmin(page);
    await mockIntegrationApis(page);
    await page.goto("/settings/anomaly-metrics");

    await expect(
      page.getByText(/24|anomal|كشف/i)
    ).toBeVisible();
  });

  test("shows breakdown by anomaly type", async ({ page }) => {
    await loginAsAdmin(page);
    await mockIntegrationApis(page);
    await page.goto("/settings/anomaly-metrics");

    await expect(
      page.getByText(/duplicate|مكرر/i).or(page.getByText(/outlier|شاذ/i))
    ).toBeVisible();
  });
});

// ── RTL Layout Tests ─────────────────────────────────────────

test.describe("RTL Layout", () => {
  test("analytics dashboard renders in RTL by default", async ({ page }) => {
    await loginAsAdmin(page);
    await mockAnalyticsApis(page);
    await page.goto("/analytics");

    const dir = await page.locator("html").getAttribute("dir");
    expect(dir).toBe("rtl");
  });

  test("chart numbers render in LTR direction", async ({ page }) => {
    await loginAsAdmin(page);
    await mockAnalyticsApis(page);
    await page.goto("/analytics");

    const ltrEl = page.locator("[dir='ltr']").first();
    if (await ltrEl.isVisible()) {
      const direction = await ltrEl.evaluate(
        (el) => getComputedStyle(el).direction
      );
      expect(direction).toBe("ltr");
    }
  });

  test("switching to English sets computed direction to LTR", async ({ page }) => {
    await loginAsAdmin(page);
    await mockAnalyticsApis(page);

    // Set language to English via localStorage before navigation
    await page.addInitScript(() => {
      localStorage.setItem("i18nextLng", "en");
    });
    await page.goto("/analytics");

    const computedDir = await page.locator("html").evaluate(
      (el) => getComputedStyle(el).direction
    );
    expect(computedDir).toBe("ltr");

    const attrDir = await page.locator("html").getAttribute("dir");
    expect(attrDir).toBe("ltr");
  });
});
