export function clean(v: string | undefined): string {
    if (!v) return "";
    return v.replace(/\s+/g, " ").trim();
  }
  
export function parseMoney(str: string): number | null {
  if (!str) return null;

  const raw = str.toLowerCase().trim();

  // ignorar "não informado"
  if (raw.includes("não informado") || raw === "-" || raw === "") return null;

  // detectar salário por hora
  const isHourly =
    raw.includes("/h") ||
    raw.includes(" por hora") ||
    raw.endsWith(" h") ||
    /hora/.test(raw);

  // extrair número da string
  const num = Number(
    raw
      .replace(/[^\d,.-]/g, "") // remove tudo exceto dígitos ., -
      .replace(/\.(?=\d{3})/g, "") // remove separador de milhares
      .replace(",", ".")
      .trim()
  );

  if (isNaN(num)) return null;

  // heurística extra → valores abaixo de 60 provavelmente são hora
  const maybeHour = num > 0 && num < 60;

  if (isHourly || maybeHour) {
    const estimatedMonthly = num * 198; // 44h * 4.5 semanas
    return Math.round(estimatedMonthly * 100) / 100;
  }

  return num;
}
