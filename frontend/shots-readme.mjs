/**
 * Набор изображений для README: десктоп, мобильный и ключевые состояния.
 * Запуск: node shots-readme.mjs
 */
import { chromium } from "playwright";
import fs from "fs";

const OUT = "/Users/ilakuznecov/experimenthub/docs/ui";
fs.mkdirSync(OUT, { recursive: true });
const BASE = "http://localhost:3002";

const browser = await chromium.launch();

// ── Десктоп ───────────────────────────────────────────────────────────
const ctx = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
});
const p = await ctx.newPage();

const desktop = [
  ["/", "01-home"],
  ["/guide", "02-guide"],
  ["/experiments", "03-experiments"],
  ["/experiments/2", "04-result"],
  ["/new", "05-wizard"],
  ["/tools", "06-tools"],
  ["/glossary", "07-glossary"],
];

for (const [route, name] of desktop) {
  await p.goto(BASE + route, { waitUntil: "networkidle" });
  await p.waitForTimeout(2200);
  await p.screenshot({ path: `${OUT}/${name}.png` });
  console.log("✓", name);
}

// Подсказка к термину — ключевая фича «понятно даже ребёнку»
await p.goto(BASE + "/guide", { waitUntil: "networkidle" });
await p.waitForTimeout(1600);
const term = p.locator("button.term-underline").first();
await term.scrollIntoViewIfNeeded();
await p.waitForTimeout(400);
await term.hover();
await p.waitForTimeout(900);
await p.screenshot({ path: `${OUT}/08-tooltip.png` });
console.log("✓ 08-tooltip");

// Сломанная метрика: без восполнения знаменателя конверсия 100% в обеих группах
await p.goto(BASE + "/experiments/2", { waitUntil: "networkidle" });
await p.waitForTimeout(1800);
await p.locator('input[type="checkbox"]').first().uncheck();
await p.waitForTimeout(2000);
await p.screenshot({ path: `${OUT}/09-broken-metric.png` });
console.log("✓ 09-broken-metric");

// Инструкция подключения продукта.
// Берём существующий эксперимент без данных, а не создаём новый:
// скрипт скриншотов не должен оставлять следов в базе.
const all = await fetch(BASE + "/api/experiments/").then((r) => r.json());
let emptyId = null;
for (const e of all) {
  const res = await fetch(
    `${BASE}/api/experiments/${e.id}/results?metric_name=completion`
  );
  if (res.status === 400) { emptyId = e.id; break; }
}

if (emptyId) {
  await p.setViewportSize({ width: 1440, height: 1250 });
  await p.goto(`${BASE}/experiments/${emptyId}`, { waitUntil: "networkidle" });
  await p.waitForTimeout(2200);
  await p.screenshot({ path: `${OUT}/11-integration.png` });
  console.log("✓ 11-integration");
  await p.setViewportSize({ width: 1440, height: 900 });
} else {
  console.log("· 11-integration пропущен: нет эксперимента без данных");
}

await p.goto(BASE + "/api/docs", { waitUntil: "networkidle" });
await p.waitForTimeout(2600);
await p.screenshot({ path: `${OUT}/12-api-docs.png` });
console.log("✓ 12-api-docs");

// Ключевые кадры для README: сработавшая защита и польза CUPED.
const list = await fetch(BASE + "/api/experiments/").then((r) => r.json());
const byName = Object.fromEntries(list.map((e) => [e.name, e.id]));

if (byName["demo-srm-broken"]) {
  await p.setViewportSize({ width: 1440, height: 1150 });
  await p.goto(`${BASE}/experiments/${byName["demo-srm-broken"]}`, { waitUntil: "networkidle" });
  await p.waitForTimeout(2500);
  await p.locator('input[placeholder="completion"]').fill("activation");
  await p.waitForTimeout(2600);
  await p.screenshot({ path: `${OUT}/13-srm-detected.png` });
  console.log("✓ 13-srm-detected");
}

if (byName["demo-onboarding-cuped"]) {
  await p.goto(`${BASE}/experiments/${byName["demo-onboarding-cuped"]}`, { waitUntil: "networkidle" });
  await p.waitForTimeout(2200);
  await p.locator('input[placeholder="completion"]').fill("sessions_per_week");
  await p.waitForTimeout(2000);
  await p.locator('input[type="checkbox"]').nth(1).check();   // применить CUPED
  await p.waitForTimeout(2600);
  await p.screenshot({ path: `${OUT}/14-cuped.png` });
  console.log("✓ 14-cuped");
  await p.setViewportSize({ width: 1440, height: 900 });
}

// Демо-режим
await p.route("**/api/**", (r) => r.fulfill({ status: 503, body: "{}" }));
await p.goto(BASE + "/experiments/2", { waitUntil: "networkidle" });
await p.waitForTimeout(2000);
await p.screenshot({ path: `${OUT}/10-demo-mode.png` });
console.log("✓ 10-demo-mode");
await ctx.close();

// ── Мобильный ─────────────────────────────────────────────────────────
const mctx = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true,
});
const mp = await mctx.newPage();
for (const [route, name] of [["/", "m1-home"], ["/guide", "m2-guide"], ["/experiments/2", "m3-result"]]) {
  await mp.goto(BASE + route, { waitUntil: "networkidle" });
  await mp.waitForTimeout(2000);
  await mp.screenshot({ path: `${OUT}/${name}.png` });
  console.log("✓", name);
}
await mctx.close();

await browser.close();
console.log("\nготово:", OUT);
