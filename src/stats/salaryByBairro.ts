import type { Job } from "../utils/parse";
import { normalizeBairro } from "../utils/normalize";

export function salaryByBairro(rows: Job[]) {
  const map: Record<string, { sum: number; count: number; min: number; max: number }> = {};

  for (const r of rows) {
    if (!r.Salario) continue;
   // console.log(r.Bairro?.[0] ?? "Indefinido");
    const bairro = String(normalizeBairro(r?.Bairro?.[0] ?? "Indefinido"));
    if (!map[bairro]) {
      map[bairro] = { sum: 0, count: 0, min: r.Salario, max: r.Salario };
    }
    map[bairro].sum += r.Salario;
    map[bairro].count++;
    map[bairro].min = Math.min(map[bairro].min, r.Salario);
    map[bairro].max = Math.max(map[bairro].max, r.Salario);
  }

  const result = Object.entries(map)
    .map(([bairro, info]) => ({
      bairro,
      count: info.count,
      avg: Number((info.sum / info.count).toFixed(2)),
      min: info.min,
      max: info.max
    }))
    .sort((a, b) => b.avg - a.avg); // bairros mais bem pagos primeiro

  return result;
}
