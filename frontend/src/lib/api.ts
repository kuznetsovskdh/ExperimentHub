/**
 * Клиент ExperimentHub.
 *
 * Все запросы идут на /api и переписываются прокси (nginx в контейнере,
 * vite в разработке), поэтому CORS в бэкенде не нужен.
 *
 * Если API недоступен, чтение переключается на демо-данные и интерфейс
 * поднимает флаг: страницу можно открыть и показать без поднятого стека,
 * но подмена данных никогда не происходит молча.
 */
import {
  demoAchievedPower,
  demoExperiments,
  demoResult,
  demoSampleSize,
} from "./demo";
import type {
  AchievedPower,
  Experiment,
  MultipleTesting,
  ResultPayload,
  SampleSize,
} from "./types";

const BASE = "/api";

/** Ошибка, донёсшая до интерфейса текст `detail` из FastAPI. */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

let demoMode = false;
const listeners = new Set<(v: boolean) => void>();

export const isDemoMode = () => demoMode;

export function onDemoModeChange(fn: (v: boolean) => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function setDemoMode(v: boolean) {
  if (demoMode === v) return;
  demoMode = v;
  listeners.forEach((fn) => fn(v));
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    let detail = `Запрос завершился с кодом ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail))
        detail = body.detail
          .map((d: { loc?: string[]; msg?: string }) =>
            `${d.loc?.slice(1).join(".") ?? ""}: ${d.msg ?? ""}`.trim()
          )
          .join("; ");
    } catch {
      /* тело не JSON — оставляем сообщение по коду */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

/**
 * Чтение с откатом на демо.
 *
 * Откат делается только при недоступности сети или 5xx. Ошибка 4xx — это
 * осмысленный ответ сервиса (не найдено, недостаточно данных), и подменять
 * её демо-данными значило бы врать пользователю.
 */
async function readWithFallback<T>(path: string, fallback: T): Promise<T> {
  try {
    const data = await request<T>(path);
    setDemoMode(false);
    return data;
  } catch (e) {
    if (e instanceof ApiError && e.status < 500) {
      setDemoMode(false);
      throw e;
    }
    setDemoMode(true);
    return fallback;
  }
}

export const api = {
  listExperiments: () =>
    readWithFallback<Experiment[]>("/experiments/", demoExperiments),

  getExperiment: (id: number) =>
    readWithFallback<Experiment>(
      `/experiments/${id}`,
      demoExperiments.find((e) => e.id === id) ?? demoExperiments[0]
    ),

  createExperiment: (body: {
    name: string;
    entity_type: string;
    variants: { name: string; allocation_pct: number }[];
  }) =>
    request<Experiment>("/experiments/", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  stopExperiment: (id: number) =>
    request<Experiment>(`/experiments/${id}/stop`, { method: "POST" }),

  resumeExperiment: (id: number) =>
    request<Experiment>(`/experiments/${id}/resume`, { method: "POST" }),

  getResults: (
    id: number,
    params: {
      metric_name: string;
      method?: string;
      aggregation?: string;
      fill_missing?: number | null;
      use_cuped?: boolean;
      alpha?: number;
    }
  ) => {
    const q = new URLSearchParams();
    q.set("metric_name", params.metric_name);
    if (params.method) q.set("method", params.method);
    if (params.aggregation) q.set("aggregation", params.aggregation);
    if (params.fill_missing !== null && params.fill_missing !== undefined)
      q.set("fill_missing", String(params.fill_missing));
    if (params.use_cuped) q.set("use_cuped", "true");
    if (params.alpha) q.set("alpha", String(params.alpha));
    return readWithFallback<ResultPayload>(
      `/experiments/${id}/results?${q}`,
      demoResult
    );
  },

  sampleSize: (p: {
    baseline_rate: number;
    mde: number;
    alpha?: number;
    power?: number;
  }) => {
    const q = new URLSearchParams({
      baseline_rate: String(p.baseline_rate),
      mde: String(p.mde),
      alpha: String(p.alpha ?? 0.05),
      power: String(p.power ?? 0.8),
    });
    return readWithFallback<SampleSize>(
      `/stats/sample-size?${q}`,
      demoSampleSize
    );
  },

  achievedPower: (p: {
    n: number;
    baseline_rate: number;
    observed_effect: number;
    alpha?: number;
  }) => {
    const q = new URLSearchParams({
      n: String(p.n),
      baseline_rate: String(p.baseline_rate),
      observed_effect: String(p.observed_effect),
      alpha: String(p.alpha ?? 0.05),
    });
    return readWithFallback<AchievedPower>(
      `/stats/achieved-power?${q}`,
      demoAchievedPower
    );
  },

  multipleTesting: (body: {
    p_values: number[];
    method: string;
    alpha?: number;
    labels?: string[];
  }) =>
    request<MultipleTesting>("/stats/multiple-testing", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
