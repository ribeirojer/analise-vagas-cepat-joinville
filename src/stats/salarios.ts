import type { Job } from "../utils/parse";

export function salaryStats(rows: Job[]) {
  const values = rows.map(r => r.Salario).filter((v): v is number => v != null);
  if (!values.length) return null;

  const sorted = [...values].sort((a, b) => a - b);
  const sum = values.reduce((a, b) => a + b, 0);
  const avg = sum / values.length;
  const median = sorted[Math.floor(sorted.length / 2)];
  const min = sorted[0];
  const max = sorted[sorted.length - 1];

  // Quartis
  const Q1 = sorted[Math.floor(sorted.length * 0.25)];
  const Q3 = sorted[Math.floor(sorted.length * 0.75)];
  const IQR = Q3 != null && Q1 != null ? Q3 - Q1 : null;

  // Desvio padrão
  const variance = values.reduce((acc, v) => acc + Math.pow(v - avg, 2), 0) / values.length;
  const std = Math.sqrt(variance);

  // Faixas sugeridas
  const ranges = {
    "Até 1.500": pct(values.filter(v => v <= 1500).length, values.length),
    "1.501 – 2.000": pct(values.filter(v => v > 1500 && v <= 2000).length, values.length),
    "2.001 – 3.000": pct(values.filter(v => v > 2000 && v <= 3000).length, values.length),
    "3.001 – 4.000": pct(values.filter(v => v > 3000 && v <= 4000).length, values.length),
    "4.001+": pct(values.filter(v => v > 4000).length, values.length),
  };

  // Top 10 salários
  const top10 = [...sorted.slice(-10)].reverse();

  // Possíveis erros / outliers (OCR capturou números absurdos)
  const outliers = Q1 != null && Q3 != null 
    ? IQR != null 
      ? values.filter(v => v > Q3 + 1.5 * IQR || v < Q1 - 1.5 * IQR) 
      : []
    : [];

  return {
    total: values.length,
    min,
    max,
    avg,
    median,
    Q1,
    Q3,
    IQR,
    std,
    ranges,
    top10,
    outliersCount: outliers.length,
  };
}

function pct(a: number, total: number) {
  return { count: a, pct: Number(((a / total) * 100).toFixed(2)) };
}

export interface ParsedSalary {
  value: number | null;
  type: "mensal" | "hora" | "desconhecido";
  estimadoMensal?: number;
}
