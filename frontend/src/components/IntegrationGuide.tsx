import * as React from "react";
import { Check, Copy } from "lucide-react";
import { Term } from "@/components/Term";
import { Badge } from "@/components/ui/badge";

/**
 * Инструкция по подключению продукта к эксперименту.
 *
 * Показывается вместо ошибки, когда в эксперименте ещё нет назначений:
 * для только что созданного эксперимента «нет данных» — это не сбой,
 * а следующий шаг работы, и человеку нужен код, а не сообщение об ошибке.
 */
function CodeBlock({ code, caption }: { code: string; caption: string }) {
  const [copied, setCopied] = React.useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* буфер недоступен — код всё равно виден и выделяется мышью */
    }
  };

  return (
    <figure className="overflow-hidden rounded-lg border border-line-soft bg-[#06090d]">
      <figcaption className="flex items-center justify-between gap-3 border-b border-line-soft px-4 py-2">
        <span className="font-mono text-[11px] text-faint">{caption}</span>
        <button
          onClick={copy}
          className="flex items-center gap-1.5 rounded px-2 py-1 font-mono text-[11px] text-faint transition-colors hover:text-treatment"
        >
          {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
          {copied ? "скопировано" : "копировать"}
        </button>
      </figcaption>
      <pre className="overflow-x-auto px-4 py-3.5">
        <code className="font-mono text-[12.5px] leading-relaxed text-ink">
          {code}
        </code>
      </pre>
    </figure>
  );
}

function Step({
  n,
  title,
  children,
}: {
  n: string;
  title: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-4 border-t border-line-soft py-7 md:grid-cols-[36px_1fr]">
      <div className="num text-[12px] text-treatment">{n}</div>
      <div className="min-w-0 space-y-4">
        <h3 className="display text-[18px] font-semibold leading-snug">
          {title}
        </h3>
        {children}
      </div>
    </div>
  );
}

export function IntegrationGuide({
  experimentId,
  entityType,
  variants,
}: {
  experimentId: number;
  entityType: string;
  variants: { id: number; name: string }[];
}) {
  const treatmentName = variants[1]?.name ?? "treatment";
  const treatmentId = variants[1]?.id ?? 2;

  return (
    <div className="rounded-xl border border-line-soft bg-surface p-7">
      <Badge variant="treatment">данных пока нет</Badge>

      <h2 className="display mt-5 text-[24px] font-bold">
        Подключите продукт — и здесь появится результат
      </h2>
      <p className="mt-4 max-w-[62ch] text-[15px] leading-relaxed text-muted">
        Эксперимент создан и готов принимать данные. Осталось научить ваш
        продукт спрашивать вариант и присылать метрику. Это два HTTP-запроса.
      </p>

      <div className="mt-6">
        <Step
          n="01"
          title="Дать продукту доступ к ExperimentHub"
        >
          <p className="text-[14px] leading-relaxed text-muted">
            Если ваш сервис живёт в Docker, подключите его к общей сети — тогда
            обращаться можно по имени контейнера, без проброса портов наружу.
          </p>
          <CodeBlock
            caption="docker-compose.yml вашего продукта"
            code={`services:
  ваш-сервис:
    environment:
      EH_BASE_URL: http://experimenthub-app-1:8000
      EH_EXPERIMENT_ID: "${experimentId}"
    networks:
      - eh_network

networks:
  eh_network:
    external: true`}
          />
          <p className="text-[13px] leading-relaxed text-faint">
            Сеть создаётся один раз командой{" "}
            <code className="font-mono text-ink">
              docker network create eh_network
            </code>
            . Если продукт запущен вне Docker, используйте{" "}
            <code className="font-mono text-ink">http://localhost:8001</code> —
            по этому адресу отвечает сам сервис, а не интерфейс:{" "}
            <a
              href="/api/docs"
              target="_blank"
              rel="noreferrer"
              className="text-treatment underline decoration-dotted underline-offset-4 hover:text-ink"
            >
              открыть документацию API
            </a>
            .
          </p>
        </Step>

        <Step
          n="02"
          title={<>Спросить вариант, когда показываете изменение</>}
        >
          <p className="text-[14px] leading-relaxed text-muted">
            Передайте идентификатор{" "}
            <Term id="entity-id">сущности</Term> — здесь это{" "}
            <code className="font-mono text-ink">{entityType}</code>. Ответ{" "}
            <Term id="randomization">детерминирован</Term>: один и тот же
            идентификатор всегда получит один и тот же вариант.
          </p>
          <CodeBlock
            caption="GET /experiments/{id}/assignment"
            code={`r = requests.get(
    f"{EH_BASE_URL}/experiments/${experimentId}/assignment",
    params={"entity_id": str(${entityType}_id)},
    timeout=2,
)
variant = r.json()["variant_name"]   # "${variants[0]?.name ?? "control"}" или "${treatmentName}"

if variant == "${treatmentName}":
    показать_новую_версию()
else:
    показать_текущую_версию()`}
          />
          <p className="text-[13px] leading-relaxed text-faint">
            Оберните вызов в try/except с таймаутом: если ExperimentHub
            недоступен, продукт должен показать контрольный вариант, а не упасть.
          </p>
        </Step>

        <Step n="03" title="Присылать метрику — обязательно с нулями">
          <p className="text-[14px] leading-relaxed text-muted">
            Это место, где интеграции ломаются чаще всего. Если слать событие
            только при успехе, <Term id="fill-missing">знаменатель</Term>{" "}
            конверсии будет состоять из одних успехов, и она всегда окажется
            равна 100% в обеих группах.
          </p>
          <CodeBlock
            caption="POST /experiments/{id}/events"
            code={`def отправить_метрику(${entityType}_id, попытка_id, успех: bool):
    requests.post(
        f"{EH_BASE_URL}/experiments/${experimentId}/events",
        json={
            "entity_id": str(${entityType}_id),
            "metric_name": "conversion",
            "metric_value": 1.0 if успех else 0.0,
            # ключ идемпотентности: повтор при retry не задвоит метрику
            "event_key": f"{попытка_id}-{'finish' if успех else 'start'}",
        },
        timeout=2,
    )

# при начале — ноль в знаменатель
отправить_метрику(${entityType}_id, попытка_id, успех=False)

# при целевом действии — единица
отправить_метрику(${entityType}_id, попытка_id, успех=True)`}
          />
        </Step>

        <Step n="04" title="Проверить, что данные дошли">
          <CodeBlock
            caption="терминал"
            code={`# назначение (повторный вызов обязан вернуть тот же вариант)
curl -s "localhost:8001/experiments/${experimentId}/assignment?entity_id=test-1"

# отправка метрики
curl -s -X POST localhost:8001/experiments/${experimentId}/events \\
  -H 'Content-Type: application/json' \\
  -d '{"entity_id":"test-1","metric_name":"conversion","metric_value":1.0}'

# результат появится здесь же, на этой странице`}
          />
          <p className="text-[13px] leading-relaxed text-faint">
            Как только придут назначения хотя бы по два на вариант, страница
            начнёт показывать эффект, доверительный интервал и{" "}
            <Term id="srm">проверку деления</Term>. Вариант{" "}
            <span className="text-treatment">{treatmentName}</span> имеет id{" "}
            <span className="num text-ink">{treatmentId}</span>.
          </p>

          <p className="text-[13px] leading-relaxed text-faint">
            Все эндпоинты с формами для ручной проверки —{" "}
            <a
              href="/api/docs"
              target="_blank"
              rel="noreferrer"
              className="text-treatment underline decoration-dotted underline-offset-4 hover:text-ink"
            >
              в документации API
            </a>
            .
          </p>
        </Step>
      </div>

      <div className="mt-2 rounded-lg border border-warn/25 bg-warn/[0.04] p-5">
        <p className="text-[13.5px] leading-relaxed text-muted">
          <span className="text-warn">Перед запуском</span> посчитайте размер
          выборки на вкладке «Расчёты» и не останавливайте эксперимент раньше:{" "}
          <Term id="peeking">подглядывание</Term> с остановкой на первом
          «значимо» поднимает долю ложных открытий с 5% до 27%.
        </p>
      </div>
    </div>
  );
}
