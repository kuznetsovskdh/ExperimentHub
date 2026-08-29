/**
 * Жёсткое тестирование UI ExperimentHub.
 * Блоки: рендеринг, данные, подсказки, формы, доступность, адаптивность,
 * демо-режим, мутации.
 */
import { chromium } from "playwright";

const BASE = "http://localhost:3002";
const ROUTES = ["/", "/guide", "/experiments", "/experiments/2", "/new", "/tools", "/glossary"];
let pass = 0, fail = 0;
const fails = [];

function check(name, ok, detail = "") {
  if (ok) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; fails.push(`${name} — ${detail}`); console.log(`  ✗ ${name}  ${detail}`); }
}

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });

// ─── Блок 1. Рендеринг и ошибки консоли ────────────────────────────────
console.log("\nБЛОК 1. Рендеринг и ошибки консоли");
for (const r of ROUTES) {
  const p = await ctx.newPage();
  const errs = [];
  p.on("console", (m) => m.type() === "error" && errs.push(m.text()));
  p.on("pageerror", (e) => errs.push("PAGEERROR " + e.message));
  await p.goto(BASE + r, { waitUntil: "networkidle", timeout: 30000 });
  await p.waitForTimeout(900);
  const txt = (await p.locator("body").innerText()).trim();
  check(`${r} рендерится`, txt.length > 200, `текста ${txt.length} симв.`);
  check(`${r} без ошибок консоли`, errs.length === 0, errs.slice(0,2).join(" | ").slice(0,140));
  await p.close();
}

// ─── Блок 2. Живые данные ──────────────────────────────────────────────
console.log("\nБЛОК 2. Живые данные на экранах");
{
  const p = await ctx.newPage();
  await p.goto(BASE + "/experiments/2", { waitUntil: "networkidle" });
  await p.waitForTimeout(1600);
  const body = await p.locator("body").innerText();
  check("карточка показывает конверсию control", /26,1\s*%/.test(body), body.match(/2\d,\d%/g)?.join(",") ?? "нет");
  check("карточка показывает конверсию treatment", /57,1\s*%/.test(body));
  check("показан эффект в пп", /\+31,1\s*пп/.test(body));
  check("показан p-value", /0,0259/.test(body));
  check("показан вердикт SRM", /перекоса нет|обнаружен перекос|выборки мало/i.test(body));
  check("предупреждения платформы выведены", /агрегация|знаменател|нескольк/i.test(body));
  await p.close();
}

// ─── Блок 3. Подсказки к терминам ──────────────────────────────────────
console.log("\nБЛОК 3. Подсказки к терминам");
{
  const p = await ctx.newPage();
  await p.goto(BASE + "/guide", { waitUntil: "networkidle" });
  await p.waitForTimeout(1200);
  const terms = p.locator("button.term-underline");
  const n = await terms.count();
  check("термины размечены на странице", n >= 8, `найдено ${n}`);

  const t = terms.first();
  await t.scrollIntoViewIfNeeded();
  await t.hover();
  await p.waitForTimeout(700);
  const tip = p.locator('[role="tooltip"]');
  const tipVisible = await tip.count() > 0 && await tip.first().isVisible();
  check("подсказка открывается по наведению", tipVisible);
  if (tipVisible) {
    const tipTxt = await tip.first().innerText();
    check("подсказка содержательна", tipTxt.length > 40, `${tipTxt.length} симв.`);
    check("подсказка помечает регистр", /простыми словами|точно/i.test(tipTxt), tipTxt.slice(0,60));
  }

  // клавиатурная доступность
  await p.keyboard.press("Escape");
  await t.focus();
  await p.waitForTimeout(600);
  const tipKb = await p.locator('[role="tooltip"]').count();
  check("подсказка доступна с клавиатуры (focus)", tipKb > 0);
  await p.close();
}

// ─── Блок 4. Переключатель «Объяснять просто» ──────────────────────────
console.log("\nБЛОК 4. Режим «Объяснять просто»");
{
  const p = await ctx.newPage();
  await p.goto(BASE + "/glossary", { waitUntil: "networkidle" });
  await p.waitForTimeout(1000);
  const before = await p.locator("body").innerText();
  const sw = p.locator('button[role="switch"]').first();
  check("переключатель присутствует", await sw.count() > 0);
  const stateBefore = await sw.getAttribute("data-state");
  await sw.click();
  await p.waitForTimeout(600);
  const after = await p.locator("body").innerText();
  const stateAfter = await sw.getAttribute("data-state");
  check("переключатель меняет состояние", stateBefore !== stateAfter, `${stateBefore}→${stateAfter}`);
  check("текст объяснений меняется", before !== after);

  // сохраняется между перезагрузками
  await p.reload({ waitUntil: "networkidle" });
  await p.waitForTimeout(800);
  const persisted = await p.locator('button[role="switch"]').first().getAttribute("data-state");
  check("выбор запоминается после перезагрузки", persisted === stateAfter, `${persisted} vs ${stateAfter}`);
  await p.close();
}

// ─── Блок 5. Калькуляторы ──────────────────────────────────────────────
console.log("\nБЛОК 5. Калькуляторы");
{
  const p = await ctx.newPage();
  await p.goto(BASE + "/tools", { waitUntil: "networkidle" });
  await p.waitForTimeout(1600);
  const body = await p.locator("body").innerText();
  check("расчёт выборки сходится с API (336)", /336/.test(body), body.match(/\d[\d\s]{2,}/g)?.slice(0,4).join(",") ?? "");

  // граничный ввод: конверсия + MDE > 100%
  const inputs = p.locator('input[type="number"]');
  await inputs.nth(0).fill("95");
  await inputs.nth(1).fill("20");
  await p.waitForTimeout(1200);
  const edge = await p.locator("body").innerText();
  check("невозможные параметры объяснены, не падают", /должны лежать|Проверьте параметры/i.test(edge), edge.slice(0,80));

  // вкладка постфактум
  await p.getByRole("tab", { name: "После" }).click();
  await p.waitForTimeout(1400);
  const after = await p.locator("body").innerText();
  check("достигнутая мощность считается", /60,6\s*%|мощность/i.test(after));
  await p.close();
}

// ─── Блок 6. Мастер создания ───────────────────────────────────────────
console.log("\nБЛОК 6. Мастер создания эксперимента");
{
  const p = await ctx.newPage();
  await p.goto(BASE + "/new", { waitUntil: "networkidle" });
  await p.waitForTimeout(900);

  const next = p.getByRole("button", { name: /Дальше/ });
  check("кнопка «Дальше» заблокирована без имени", await next.isDisabled());

  await p.locator('input[placeholder*="hint-before-test"]').fill("ui-selftest-exp");
  await p.waitForTimeout(300);
  check("кнопка разблокирована после ввода имени", !(await next.isDisabled()));
  await next.click();
  await p.waitForTimeout(600);

  // шаг 2: сумма долей
  const allocs = p.locator('input[type="number"]');
  await allocs.nth(0).fill("30");
  await p.waitForTimeout(400);
  const body2 = await p.locator("body").innerText();
  check("несумма долей помечена как ошибка", /должно быть ровно 100/.test(body2));
  const next2 = p.getByRole("button", { name: /Дальше/ });
  check("переход заблокирован при сумме ≠ 100", await next2.isDisabled());

  await allocs.nth(0).fill("50");
  await p.waitForTimeout(400);
  check("переход разблокирован при сумме 100", !(await next2.isDisabled()));
  await next2.click();
  await p.waitForTimeout(1500);

  const body3 = await p.locator("body").innerText();
  check("шаг 3 показывает нужный размер выборки", /на каждый вариант|наблюдений/i.test(body3));
  await p.close();
}

// ─── Блок 7. Адаптивность ──────────────────────────────────────────────
console.log("\nБЛОК 7. Адаптивность");
for (const [w, h, label] of [[375, 812, "375px"], [768, 1024, "768px"], [1920, 1080, "1920px"]]) {
  const c = await browser.newContext({ viewport: { width: w, height: h } });
  const p = await c.newPage();
  let worst = 0;
  for (const r of ROUTES) {
    await p.goto(BASE + r, { waitUntil: "networkidle" });
    await p.waitForTimeout(500);
    const sw = await p.evaluate(() => document.documentElement.scrollWidth);
    if (sw > worst) worst = sw;
  }
  check(`${label} без горизонтального скролла`, worst <= w + 1, `максимум scrollWidth=${worst}`);
  await c.close();
}

// ─── Блок 8. Демо-режим ────────────────────────────────────────────────
console.log("\nБЛОК 8. Демо-режим при недоступном API");
{
  const c = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await c.newPage();
  // имитируем падение бэкенда, не трогая контейнер
  await p.route("**/api/**", (route) => route.fulfill({ status: 503, body: "{}" }));
  await p.goto(BASE + "/experiments/2", { waitUntil: "networkidle" });
  await p.waitForTimeout(1800);
  const body = await p.locator("body").innerText();
  check("страница не пустая при упавшем API", body.length > 200, `${body.length} симв.`);
  check("виден бейдж демо-данных", /демо-данные/i.test(body));
  check("демо показывает реальные цифры", /26,1\s*%/.test(body) && /57,1\s*%/.test(body));
  await c.close();
}

// ─── Блок 9. Reduced motion ────────────────────────────────────────────
console.log("\nБЛОК 9. prefers-reduced-motion");
{
  const c = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
  const p = await c.newPage();
  const errs = [];
  p.on("pageerror", (e) => errs.push(e.message));
  await p.goto(BASE + "/", { waitUntil: "networkidle" });
  await p.waitForTimeout(1500);
  const txt = await p.locator("body").innerText();
  check("главная работает с отключёнными анимациями", txt.length > 200 && errs.length === 0, errs[0] ?? "");
  const split = await p.evaluate(() => {
    const c = document.querySelector("canvas");
    if (!c) return "нет canvas";
    const ctx = c.getContext("2d");
    const d = ctx.getImageData(0, 0, c.width, c.height).data;
    let painted = 0;
    for (let i = 3; i < d.length; i += 4000) if (d[i] > 0) painted++;
    return painted;
  });
  check("расщепление показано статично, а не пустым", typeof split === "number" && split > 0, String(split));
  await c.close();
}

// ─── Блок 10. Навигация ────────────────────────────────────────────────
console.log("\nБЛОК 10. Навигация");
{
  const p = await ctx.newPage();
  await p.goto(BASE + "/", { waitUntil: "networkidle" });
  await p.waitForTimeout(900);
  await p.getByRole("link", { name: "Как сделать A/B" }).first().click();
  await p.waitForTimeout(900);
  check("переход по навигации работает", p.url().endsWith("/guide"), p.url());
  const scrollY = await p.evaluate(() => window.scrollY);
  check("при переходе страница прокручена наверх", scrollY < 50, String(scrollY));
  await p.goBack();
  await p.waitForTimeout(700);
  check("кнопка «назад» браузера работает", p.url() === BASE + "/", p.url());
  await p.close();
}


// ─── Блок 11. Регрессии на исправленные дефекты ────────────────────────
console.log("\nБЛОК 11. Регрессии");
{
  const p = await ctx.newPage();

  // Подложка навигации должна совпадать с активным пунктом. Раньше она
  // считалась до загрузки шрифтов и застревала на чужих координатах.
  for (const [route, label] of [["/guide", "Как сделать A/B"], ["/tools", "Расчёты"]]) {
    await p.goto(BASE + route, { waitUntil: "networkidle" });
    await p.waitForTimeout(1600);
    const dx = await p.evaluate((lbl) => {
      const ul = document.querySelector("header ul");
      const pill = ul?.querySelector("li[aria-hidden='true']");
      const link = [...(ul?.querySelectorAll("a") ?? [])].find((a) => a.textContent.trim() === lbl);
      if (!pill || !link) return 999;
      const pr = pill.getBoundingClientRect(), lr = link.getBoundingClientRect();
      return Math.abs((pr.left + pr.right) / 2 - (lr.left + lr.right) / 2);
    }, label);
    check(`подложка навигации на «${label}»`, dx < 12, `расхождение ${Math.round(dx)}px`);
  }

  // Swagger, открытый через прокси, должен получать схему, а не index.html.
  await p.goto(BASE + "/api/docs", { waitUntil: "networkidle" });
  await p.waitForTimeout(2500);
  const docs = await p.locator("body").innerText();
  check("документация API рендерится", !/Unable to render|Parser error/.test(docs));
  check("эндпоинты перечислены", (await p.locator(".opblock").count()) > 5);

  // Эксперимент без данных — это онбординг, а не ошибка.
  const created = await fetch(BASE + "/api/experiments/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: `uitest-empty-${Date.now()}`,
      entity_type: "user",
      variants: [
        { name: "control", allocation_pct: 50 },
        { name: "treatment", allocation_pct: 50 },
      ],
    }),
  }).then((r) => r.json());

  await p.goto(`${BASE}/experiments/${created.id}`, { waitUntil: "networkidle" });
  await p.waitForTimeout(2000);
  const empty = await p.locator("body").innerText();
  check("пустой эксперимент показывает инструкцию", /Подключите продукт/.test(empty));
  check("инструкция содержит настройку docker-сети", /eh_network/.test(empty));
  check("инструкция содержит код отправки метрики", /event_key/.test(empty));
  check("сообщения «Расчёт невозможен» нет", !/Расчёт невозможен/.test(empty));
  check("id эксперимента подставлен в код", empty.includes(`"${created.id}"`), `id=${created.id}`);

  // Тест убирает за собой: иначе каждый прогон оставляет в базе пустой
  // эксперимент, и список в интерфейсе постепенно забивается мусором.
  const removed = await fetch(`${BASE}/api/experiments/${created.id}`, {
    method: "DELETE",
  }).then((r) => r.ok).catch(() => false);
  check("тестовый эксперимент удалён после проверки", removed);

  await p.close();
}

await browser.close();

console.log(`\n${"─".repeat(58)}`);
console.log(`ИТОГО: ${pass} пройдено, ${fail} провалено`);
if (fails.length) { console.log("\nПРОВАЛЫ:"); fails.forEach((f) => console.log("  • " + f)); }
process.exit(fail ? 1 : 0);
