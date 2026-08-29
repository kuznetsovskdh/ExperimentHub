import { chromium } from "playwright";

const routes = ["/", "/guide", "/experiments", "/experiments/2", "/new", "/tools", "/glossary"];
const browser = await chromium.launch();
let bad = 0;

for (const r of routes) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push("PAGEERROR: " + e.message));

  await page.goto("http://localhost:3002" + r, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForTimeout(1200);

  const text = (await page.locator("body").innerText()).trim();
  const h1 = await page.locator("h1").first().innerText().catch(() => "(нет h1)");
  const scrollW = await page.evaluate(() => document.documentElement.scrollWidth);
  const clientW = await page.evaluate(() => document.documentElement.clientWidth);

  const ok = text.length > 200;
  if (!ok || errors.length) bad++;
  console.log(`${ok ? "OK " : "ПУСТО"} ${r.padEnd(18)} h1="${h1.replace(/\n/g, " ").slice(0, 48)}" текст=${text.length} симв. ${scrollW > clientW ? "⚠ ГОРИЗОНТАЛЬНЫЙ СКРОЛЛ" : ""}`);
  if (errors.length) errors.slice(0, 4).forEach((e) => console.log("     ошибка: " + e.slice(0, 160)));
  await ctx.close();
}

// мобильная ширина
const ctx = await browser.newContext({ viewport: { width: 375, height: 812 } });
const page = await ctx.newPage();
await page.goto("http://localhost:3002/guide", { waitUntil: "networkidle" });
const sw = await page.evaluate(() => document.documentElement.scrollWidth);
console.log(`\n375px: scrollWidth=${sw} ${sw > 375 ? "⚠ горизонтальный скролл" : "✓ без горизонтального скролла"}`);
await browser.close();
process.exit(bad ? 1 : 0);
