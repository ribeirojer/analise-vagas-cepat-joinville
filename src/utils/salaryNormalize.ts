
export interface ParsedSalary {
    value: number | null;
    type: "mensal" | "hora" | "desconhecido";
    estimadoMensal?: number | null;
    }
    
export function normalizeSalary(raw: string | number | null): ParsedSalary {
  if (raw == null) return { value: null, type: "desconhecido" };

  const txt = String(raw).trim();

  // Detectar se parece "15/h" ou "15 por hora"
  const horaRegex = /(\/h|hora|hr)/i;
  const value = Number(txt.replace(/\D/g, ""));

  if (!value) return { value: null, type: "desconhecido" };

  if (horaRegex.test(txt)) {
    // Ex: 12/h → normalizar para mensal
    const estimadoMensal = value * 8 * 22; // 8h/dia * 22 dias úteis
    return { value, type: "hora", estimadoMensal };
  }

  return { value, type: "mensal" };
}
