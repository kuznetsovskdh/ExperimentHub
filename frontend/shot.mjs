import { chromium } from "playwright";
import fs from "fs";

const out = "/Users/ilakuznecov/experimenthub/docs/ui";
fs.mkdirSync(out, { recursive: true });

const shots = [
  { r: "/", n: "01-home", full: false },
  { r: "/guide", n: "02-guide", full: false },
  { r: "/experiments/2", n: "03-result", full: false },
  { r: "/new", n: "04-wizard", full: false },
  { r: "/tools", n: "05-tools", full: false },
  { r: "/glossary", n: "06-glossary", full: false },
];

const b = await chromium.launch();
const ctx = await b.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
});
const p = await ctx.newPage();

for (const s of shots) {
  await p.goto("http://localhost:3002" + s.r, { waitUntil: "networkidle" });
  await p.waitForTimeout(2200); // дать анимациям встать
  await p.screenshot({ path: `${out}/${s.n}.png`, fullPage: s.full });
  console.log("снят", s.n);
}

// подсказка термина — главное в задаче про понятность
await p.goto("http://localhost:3002/guide", { waitUntil: "networkidle" });
await p.waitForTimeout(1500);
const term = p.locator("button.term-underline").first();
await term.scrollIntoViewIfNeeded();
await term.hover();
await p.waitForTimeout(900);
await p.screenshot({ path: `${out}/07-tooltip.png` });
console.log("снят 07-tooltip");

await b.close();
