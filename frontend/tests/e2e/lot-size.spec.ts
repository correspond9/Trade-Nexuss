import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173/trade';
const CREDENTIALS = { email: 'admin@example.com', password: 'admin123' };

async function tryLogin(page) {
  const emailInput = page.locator('input[type="email"], input[name="email"]');
  if (await emailInput.count()) {
    await emailInput.first().fill(CREDENTIALS.email);
    const pwdInput = page.locator('input[type="password"], input[name="password"]');
    await pwdInput.first().fill(CREDENTIALS.password);
    const submit = page.locator('button:has-text("Login"), button:has-text("Sign In"), button[type="submit"]');
    await submit.first().click();
    await page.waitForLoadState('networkidle');
  }
}

async function openModalFromTab(page, tabText: string) {
  await page.locator(`text=${tabText}`).first().click();
  await page.waitForTimeout(500);
  const buyBtn = page.locator('button:has-text("BUY")').first();
  await buyBtn.click();
  const modal = page.locator('div:has-text("Total Qty")').first();
  await expect(modal).toBeVisible({ timeout: 5000 });
  const text = await modal.textContent();
  return text || '';
}

function extractTotalQty(text: string): number {
  const match = text.match(/Total Qty:\s*([0-9]+)/i);
  return match ? Number(match[1]) : NaN;
}

test('modal lot size uses configured values for indices', async ({ page }) => {
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  await tryLogin(page);

  // Ensure Straddle page
  const straddleTab = page.locator('text=Straddle').first();
  if (await straddleTab.count()) {
    await straddleTab.click();
  }

  // NIFTY
  const niftyText = await openModalFromTab(page, 'NIFTY 50');
  const niftyQty = extractTotalQty(niftyText);
  expect(niftyQty).toBe(65);
  await page.keyboard.press('Escape');

  // BANKNIFTY
  const bankText = await openModalFromTab(page, 'NIFTY BANK');
  const bankQty = extractTotalQty(bankText);
  expect(bankQty).toBe(30);
  await page.keyboard.press('Escape');

  // SENSEX
  const sensexText = await openModalFromTab(page, 'SENSEX');
  const sensexQty = extractTotalQty(sensexText);
  expect(sensexQty).toBe(20);
});
