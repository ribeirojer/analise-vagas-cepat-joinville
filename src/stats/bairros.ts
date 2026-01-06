import type { Job } from "../utils/parse";

export function vagasPorBairro(rows: Job[]) {
  return rows.reduce((acc, r) => {
    const b = r.Bairro || "Indefinido";
    acc[b] = (acc[b] ?? 0) + (r.Vagas ?? 0);
    return acc;
  }, {} as Record<string, number>);
}
