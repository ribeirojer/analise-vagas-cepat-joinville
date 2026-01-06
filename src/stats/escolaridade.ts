import type { Job } from "../utils/parse";

export function escolaridade(rows: Job[]) {
  return rows.reduce((acc, r) => {
    const esc = (r.Escolaridade || "Não informado").trim();
    acc[esc] = (acc[esc] ?? 0) + 1;
    return acc;
  }, {} as Record<string, number>);
}
