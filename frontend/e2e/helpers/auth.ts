import type { Page } from "@playwright/test";

export interface AccessFixture {
  access: {
    authenticate: (page: Page) => Promise<void>;
  };
}

export const createAccessFixture = [
  async ({}, use: (value: { authenticate: (page: Page) => Promise<void> }) => Promise<void>) => {
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
  { scope: "test" as const },
];
