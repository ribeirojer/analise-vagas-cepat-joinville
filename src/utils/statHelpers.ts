export const median = (sorted: number[]) => sorted[Math.floor(sorted.length / 2)];

export function percentiles(sorted: number[]) {
  const p = (q: number) => sorted[Math.floor(sorted.length * q)];
  return {
    p10: p(0.10),
    p25: p(0.25),
    p50: p(0.50),
    p75: p(0.75),
    p90: p(0.90),
  };
}

export const std = (vals: number[], avg: number) =>
  Math.sqrt(vals.reduce((a, v) => a + Math.pow(v - avg, 2), 0) / vals.length);

export const skewness = (vals: number[]) => {
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
  const n = vals.length;
  const stdDev = std(vals, avg);
  return vals.reduce((a, v) => a + Math.pow((v - avg) / stdDev, 3), 0) / n;
};

// Coeficiente de desigualdade de renda
export function gini(sorted: number[]) {
  const n = sorted.length;
  const sum = sorted.reduce((a, b) => a + b, 0);
  return sorted.reduce((acc, v, i) => acc + (2 * (i + 1) - n - 1) * v, 0) / (n * sum);
}
