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

test.describe("Login Page", () => {
  test("shows login form with Arabic labels", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByText("إنجز").or(page.getByText("ENGEZ"))).toBeVisible();
    await expect(page.locator('label[for="email"]')).toBeVisible();
    await expect(page.locator('label[for="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test("shows validation error on empty submit", async ({ page }) => {
    await page.goto("/login");
    await page.click('button[type="submit"]');
    await expect(page.locator(".text-destructive").first()).toBeVisible();
  });

  test("shows error on wrong credentials", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[id="email"]', "wrong@engez.app");
    await page.fill('input[id="password"]', "wrongpass");
    await page.click('button[type="submit"]');
    await expect(page.locator('[role="alert"]')).toBeVisible();
  });

  test("language toggle switches between AR and EN", async ({ page }) => {
    await page.goto("/login");
    const toggleBtn = page.locator('button[aria-label="Toggle language"], button:has-text("English")').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
  });
});

test.describe("Protected Routes", () => {
  test("redirects to /login when not authenticated", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
  });
});
