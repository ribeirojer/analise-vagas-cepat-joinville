import { clean, parseMoney } from "./clean";
import { normalizeBairro, normalizeEscolaridade } from "./normalize";

export interface Job {
  Codigo?: string;
  CBO?: string;
  Nome?: string;
  Vagas?: number;
  Escolaridade?: string;
  ExpMeses?: string | number | null;
  Salario?: number | null;
  SalarioRaw?: string;
  SalarioTipo?: "mensal" | "hora" | "desconhecido";
  SalarioHoraOriginal?: number; // se veio por hora
  Bairro?: string | string[];
}

export function parseHeader(line: string) {
  return line.split("|").map(clean);
}

export function parseRow(cols: string[], line: string): Job | null {
  if (!line.trim() || /Código|------/.test(line)) return null;

  const values = line.split("|").map(clean);
  if (values.length < cols.length) return null;

return {
  Codigo: values[0],
  CBO: values[1],
  Nome: clean(values[2]),
  Vagas: Number(values[3] || 0),
  Escolaridade: normalizeEscolaridade(values[4] || ""),
  ExpMeses: values[5],
  Salario: parseMoney(values[6] || ""),
  Bairro: normalizeBairro(values[7] || "Indefinido")
};
}

