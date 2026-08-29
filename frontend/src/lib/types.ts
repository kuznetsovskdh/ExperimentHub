/** Формы ответов ExperimentHub. Повторяют то, что реально отдаёт FastAPI. */

export type Variant = {
  id: number;
  name: string;
  allocation_pct: number;
};

export type Experiment = {
  id: number;
  name: string;
  entity_type: string;
  status: "active" | "stopped" | string;
  created_at?: string | null;
  stopped_at?: string | null;
  variants?: Variant[];
};

export type SrmCheck = {
  chi2: number;
  p_value: number;
  alpha: number;
  srm_detected: boolean;
  reliable: boolean;
  total_assignments: number;
  observed_counts: number[];
  observed_ratio: number[];
  expected_ratio: number[];
  warnings: string[];
};

export type ResultPayload = {
  experiment_id: number;
  experiment_status: string;
  metric_name: string;
  method: string;
  aggregation: string;
  fill_missing: number | null;
  control_variant: { id: number; name: string };
  treatment_variant: { id: number; name: string };
  n_control: number;
  n_treatment: number;
  n_assigned_control: number;
  n_assigned_treatment: number;
  mean_control: number;
  mean_treatment: number;
  effect_size: number;
  p_value: number;
  ci_lower: number;
  ci_upper: number;
  alpha: number;
  significant: boolean;
  cuped: { applied: boolean } | null;
  srm: SrmCheck;
  warnings: string[];
};

export type SampleSize = {
  baseline_rate: number;
  mde: number;
  alpha: number;
  power: number;
  sample_size_per_variant: number;
  sample_size_total: number;
};

export type AchievedPower = {
  n_per_variant: number;
  baseline_rate: number;
  observed_effect: number;
  alpha: number;
  achieved_power: number;
  warnings: string[];
};

export type MultipleTesting = {
  method: string;
  controls: string | null;
  alpha: number;
  n_tests: number;
  threshold?: number;
  p_values: number[];
  adjusted_p_values: number[];
  rejected: boolean[];
  n_rejected: number;
  warnings?: string[];
  labels?: string[];
};
