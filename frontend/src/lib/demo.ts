/**
 * Демо-данные на случай недоступного API.
 *
 * Это не выдуманные цифры: здесь реальный результат эксперимента
 * rustest-hint-experiment — 6 из 23 в контроле против 16 из 28 в treatment.
 * Страницу можно открыть и показать без поднятого Docker, и она будет
 * рассказывать правду, а не витрину.
 */
import type {
  AchievedPower,
  Experiment,
  ResultPayload,
  SampleSize,
} from "./types";

export const demoExperiments: Experiment[] = [
  {
    id: 2,
    name: "rustest-hint-experiment",
    entity_type: "user",
    status: "active",
    created_at: "2026-08-21T10:12:00",
    stopped_at: null,
    variants: [
      { id: 3, name: "control", allocation_pct: 50 },
      { id: 4, name: "treatment", allocation_pct: 50 },
    ],
  },
];

export const demoResult: ResultPayload = {
  experiment_id: 2,
  experiment_status: "active",
  metric_name: "completion",
  method: "z_test",
  aggregation: "max",
  fill_missing: 0,
  control_variant: { id: 3, name: "control" },
  treatment_variant: { id: 4, name: "treatment" },
  n_control: 23,
  n_treatment: 28,
  n_assigned_control: 23,
  n_assigned_treatment: 28,
  mean_control: 0.26087,
  mean_treatment: 0.571429,
  effect_size: 0.310559,
  p_value: 0.025903,
  ci_lower: 0.054,
  ci_upper: 0.567118,
  alpha: 0.05,
  significant: true,
  cuped: null,
  srm: {
    chi2: 0.490196,
    p_value: 0.48384,
    alpha: 0.05,
    srm_detected: false,
    reliable: true,
    total_assignments: 51,
    observed_counts: [23, 28],
    observed_ratio: [45.1, 54.9],
    expected_ratio: [50, 50],
    warnings: [],
  },
  warnings: [
    "У 6 сущностей несколько событий по метрике 'completion'. Применена агрегация 'max' — по одному наблюдению на сущность.",
    "Сущностям без событий присвоено значение 0.0: control +17, treatment +12.",
  ],
};

export const demoSampleSize: SampleSize = {
  baseline_rate: 0.261,
  mde: 0.1,
  alpha: 0.05,
  power: 0.8,
  sample_size_per_variant: 336,
  sample_size_total: 672,
};

export const demoAchievedPower: AchievedPower = {
  n_per_variant: 25,
  baseline_rate: 0.261,
  observed_effect: 0.3106,
  alpha: 0.05,
  achieved_power: 0.6056,
  warnings: [],
};
