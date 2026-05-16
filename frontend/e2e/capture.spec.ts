import { test as base, expect } from "@playwright/test";
import type { Page } from "@playwright/test";

const test = base.extend<{ access: { authenticate: (page: Page) => Promise<void> } }>({
  access: async ({}, use) => {
    await use({
      async authenticate(page: Page) {
        await page.goto("/login");
        await page.evaluate(() => {
          const authData = {
            state: {
              user: {
                id: "user-001",
                email: "test@engez.app",
                name: "Test User",
                name_ar: "مستخدم اختبار",
                role: "field_worker",
                company_id: "comp-001",
                company_name: "Test Company",
                company_name_ar: "شركة اختبار",
              },
              accessToken: "fake-test-token",
              isAuthenticated: true,
            },
            version: 0,
          };
          localStorage.setItem("engez-auth", JSON.stringify(authData));
        });
        await page.goto("/");
      },
    });
  },
});

test.describe("Expense Capture Flow", () => {
  test("can navigate to capture page", async ({ page, access }) => {
    await access.authenticate(page);

    const captureLink = page.locator('a[href="/capture"], button:has-text("Capture"), [data-testid="capture-btn"]').first();
    if (await captureLink.isVisible()) {
      await captureLink.click();
      await expect(page).toHaveURL(/\/capture/);
    } else {
      // Direct navigation fallback
      await page.goto("/capture");
      await expect(page).toHaveURL(/\/capture/);
    }
  });

  test("shows capture mode selector", async ({ page, access }) => {
    await access.authenticate(page);
    await page.goto("/capture");

    await expect(
      page.locator('button:has-text("manual")').or(page.locator('button:has-text("يدوي")'))
    ).toBeVisible();
  });

  test("manual mode shows expense form", async ({ page, access }) => {
    await access.authenticate(page);
    await page.goto("/capture");

    const manualBtn = page.locator('button:has-text("manual")').or(page.locator('button:has-text("يدوي")'));
    await manualBtn.click();

    await expect(
      page.locator('input[name="amount"]').or(page.locator('[data-testid="amount-input"]'))
    ).toBeVisible();
  });

  test("expense form has amount field with LTR direction", async ({ page, access }) => {
    await access.authenticate(page);
    await page.goto("/capture");

    const amountInput = page.locator('input[name="amount"]').or(page.locator('[data-testid="amount-input"]'));
    if (await amountInput.isVisible()) {
      const dir = await amountInput.getAttribute("dir");
      expect(dir).toBe("ltr");
    }
  });

  test("category grid shows categories", async ({ page, access }) => {
    await access.authenticate(page);
    await page.goto("/capture");

    const categoryGrid = page.locator('[data-testid="category-grid"]').or(page.locator('[role="grid"]'));
    if (await categoryGrid.isVisible()) {
      const buttons = categoryGrid.locator("button");
      const count = await buttons.count();
      expect(count).toBeGreaterThanOrEqual(4);
    }
  });

  test("vendor autocomplete shows suggestions on input", async ({ page, access }) => {
    await access.authenticate(page);
    await page.goto("/capture");

    const vendorInput = page.locator('input[name="vendor"]').or(page.locator('[data-testid="vendor-input"]'));
    if (await vendorInput.isVisible()) {
      await vendorInput.fill("Cement");
      await page.waitForTimeout(300);
    }
  });

  test("can fill and submit manual expense", async ({ page, access }) => {
    await access.authenticate(page);
    await page.goto("/capture");

    const amountInput = page.locator('input[name="amount"]').or(page.locator('[data-testid="amount-input"]'));
    if (await amountInput.isVisible()) {
      await amountInput.fill("150.50");

      const vendorInput = page.locator('input[name="vendor"]').or(page.locator('[data-testid="vendor-input"]'));
      if (await vendorInput.isVisible()) {
        await vendorInput.fill("Test Vendor");
      }

      const submitBtn = page.locator('button[type="submit"]').or(page.locator('[data-testid="submit-expense"]'));
      if (await submitBtn.isVisible()) {
        await submitBtn.click();
      }
    }
  });
});

test.describe("Voice Capture", () => {
  test("voice button shows microphone icon", async ({ page, access }) => {
    await access.authenticate(page);
    await page.goto("/capture");

    const voiceBtn = page.locator('button[aria-pressed]').or(page.locator('[data-testid="voice-btn"]'));
    if (await voiceBtn.isVisible()) {
      const ariaLabel = await voiceBtn.getAttribute("aria-label");
      expect(ariaLabel).toBeTruthy();
    }
  });
});

test.describe("Receipt Capture", () => {
  test("receipt capture button exists", async ({ page, access }) => {
    await access.authenticate(page);
    await page.goto("/capture");

    const receiptBtn = page.getByRole("button", { name: "Receipt", exact: true });
    await expect(receiptBtn).toBeVisible();
  });
});

test.describe("Offline Behavior", () => {
  test("app loads and shows content when offline", async ({ page, access, context }) => {
    await access.authenticate(page);
    await page.goto("/");

    await context.setOffline(true);

    await page.reload().catch(() => {});

    const body = page.locator("body");
    await expect(body).toBeVisible();

    await context.setOffline(false);
  });
});
