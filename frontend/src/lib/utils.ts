import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Доля → проценты с фиксированной точностью. 0.261 → «26,1%» */
export function pct(v: number, digits = 1) {
  return `${(v * 100).toFixed(digits).replace(".", ",")}%`;
}

/** Эффект в процентных пунктах со знаком. 0.3106 → «+31,1 пп» */
export function pp(v: number, digits = 1) {
  const s = (v * 100).toFixed(digits).replace(".", ",");
  return `${v > 0 ? "+" : ""}${s} пп`;
}

/** p-value: очень малые значения не показываем как 0,000000. */
export function fmtP(p: number) {
  if (p < 0.0001) return "< 0,0001";
  return p.toFixed(4).replace(".", ",");
}

export function num(v: number, digits = 2) {
  return v.toFixed(digits).replace(".", ",");
}
