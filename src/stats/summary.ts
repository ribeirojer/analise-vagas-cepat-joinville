import type { Job } from "../utils/parse";

export function summary(rows: Job[]) {
  const totalVagas = rows.reduce((a, r) => a + (r.Vagas ?? 0), 0);
  return {
    totalRegistros: rows.length,
    totalVagas,
  };
}
