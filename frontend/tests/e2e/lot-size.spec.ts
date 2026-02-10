import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173/trade';
const CREDENTIALS = { email: 'admin@example.com', password: 'admin123' };

async function tryLogin(page) {
  // Support email or mobile-based login forms
  const emailInput = page.locator('input[type="email"], input[name="email"]');
  const mobileInput = page.locator('input[name="mobile"], input[type="tel"]');
  const pwdInput = page.locator('input[type="password"], input[name="password"]');
  if (await emailInput.count()) {
    await emailInput.first().fill(CREDENTIALS.email);
  } else if (await mobileInput.count()) {
    // backend accepts mobile param and will fallback to username/email matching
    await mobileInput.first().fill(CREDENTIALS.email);
  }
  if (await pwdInput.count()) {
    await pwdInput.first().fill(CREDENTIALS.password);
  }
  const submit = page.locator('button:has-text("Login"), button:has-text("Sign In"), button[type="submit"]');
  if (await submit.count()) {
    await submit.first().click();
    await page.waitForLoadState('networkidle');
  }
}

async function openModalFromTab(page, tabText: string, action: string = 'BUY') {
  await page.locator(`text=${tabText}`).first().click();
  await page.waitForTimeout(500);
  // Wait for action button (BUY/SELL) to appear (data may be loading); make click resilient
  await page.waitForSelector(`button:has-text("${action}")`, { timeout: 15000 });
  const actionBtn = page.locator(`button:has-text("${action}")`).first();
  await actionBtn.click();
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

  // Ensure we're on the trade page (login may redirect admins to /dashboard)
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
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

  // NIFTY - SELL
  const niftySellText = await openModalFromTab(page, 'NIFTY 50', 'SELL');
  const niftySellQty = extractTotalQty(niftySellText);
  expect(niftySellQty).toBe(65);
  await page.keyboard.press('Escape');

  // BANKNIFTY
  const bankText = await openModalFromTab(page, 'NIFTY BANK');
  const bankQty = extractTotalQty(bankText);
  expect(bankQty).toBe(30);
  await page.keyboard.press('Escape');

  // BANKNIFTY - SELL
  const bankSellText = await openModalFromTab(page, 'NIFTY BANK', 'SELL');
  const bankSellQty = extractTotalQty(bankSellText);
  expect(bankSellQty).toBe(30);
  await page.keyboard.press('Escape');

  // SENSEX
  const sensexText = await openModalFromTab(page, 'SENSEX');
  const sensexQty = extractTotalQty(sensexText);
  expect(sensexQty).toBe(20);
  await page.keyboard.press('Escape');

  // SENSEX - SELL
  const sensexSellText = await openModalFromTab(page, 'SENSEX', 'SELL');
  const sensexSellQty = extractTotalQty(sensexSellText);
  expect(sensexSellQty).toBe(20);
  await page.keyboard.press('Escape');
});
