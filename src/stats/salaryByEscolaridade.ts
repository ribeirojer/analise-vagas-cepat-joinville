import type { Job } from "../utils/parse";
import { normalizeEscolaridade } from "../utils/normalize";

export function salaryByEscolaridade(rows: Job[]) {
  const map: Record<string, { sum: number; count: number; min: number; max: number }> = {};

  for (const r of rows) {
    if (!r.Salario) continue;
    const nivel = String(normalizeEscolaridade(r.Escolaridade ?? "Não informado"));

    if (!map[nivel]) {
      map[nivel] = { sum: 0, count: 0, min: r.Salario, max: r.Salario };
    }

    map[nivel].sum += r.Salario;
    map[nivel].count++;
    map[nivel].min = Math.min(map[nivel].min, r.Salario);
    map[nivel].max = Math.max(map[nivel].max, r.Salario);
  }

  const result = Object.entries(map)
    .map(([nivel, info]) => ({
      escolaridade: nivel,
      count: info.count,
      avg: Number((info.sum / info.count).toFixed(2)),
      min: info.min,
      max: info.max
    }))
    .sort((a, b) => b.avg - a.avg); // da maior média para a menor

  return result;
}
