import { expect, test } from "@playwright/test";

test("main layout snapshot", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveScreenshot("main-layout.png", { fullPage: true });
});

