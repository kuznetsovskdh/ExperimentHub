import { chromium } from "playwright";
const b = await chromium.launch();
for (const r of ["/", "/guide", "/experiments/2", "/new", "/tools"]) {
  const ctx = await b.newContext({ viewport: { width: 375, height: 812 } });
  const p = await ctx.newPage();
  await p.goto("http://localhost:3002" + r, { waitUntil: "networkidle" });
  await p.waitForTimeout(600);
  const res = await p.evaluate(() => {
    const out = [];
    document.querySelectorAll("*").forEach((el) => {
      const rect = el.getBoundingClientRect();
      if (rect.right > 376 || rect.left < -1) {
        out.push({
          tag: el.tagName.toLowerCase(),
          cls: (el.className || "").toString().slice(0, 70),
          right: Math.round(rect.right),
          w: Math.round(rect.width),
        });
      }
    });
    return out.slice(0, 6);
  });
  console.log(`\n${r}  scrollWidth=${await p.evaluate(() => document.documentElement.scrollWidth)}`);
  res.forEach((x) => console.log(`   <${x.tag}> right=${x.right} w=${x.w}  ${x.cls}`));
  await ctx.close();
}
await b.close();
