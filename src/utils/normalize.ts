export function normalizeBase(str: string) {
  return str
    ?.trim()
    .normalize("NFD")             // remove acentos estranhos
    .replace(/[\u0300-\u036f]/g, "") 
    .toLowerCase()
    .replace(/[^\w\s/]/g, "")     // remove símbolos tipo "ç̧U", aspas, emojis
    .replace(/\s+/g, " ");        // normaliza espaços
}

  
  // dicionário de equivalências
  export const bairroMap: Record<string, string | undefined> = {
    "saguacu": "Saguaçu",
    "saguaçu": "Saguaçu",
    "saquacu": "Saguaçu",
    "sagucau": "Saguaçu",
    "saquac u": "Saguaçu",
    "salgacu": "Saguaçu",
    "salgaçu": "Saguaçu",
  
    "america": "América",
    "ame rica": "América",
    "amercia": "América",
  
    "zona industrial norte": "Zona Industrial Norte",
    "z i norte": "Zona Industrial Norte",
  
    "paranaguamiri": "Paranaguamirim",
    "paranaguamirin": "Paranaguamirim",
    "paranagua mirim": "Paranaguamirim",
  
    "iririu": "Iririú",
    "jardim iririu": "Iririú",
  
    "fatima": "Fátima",
    "fatíma": "Fátima",
    "fá tima": "Fátima",
  
    "gloria": "Glória",
    "gló ria": "Glória",
  
    "sao marcos": "São Marcos",
  
    "jardim sofi a": "Jardim Sofia",
    "jardim pariso": "Jardim Paraíso",
  
    "itaum": "Itaum",
    "itaum america comasa": "Itaum",
  
    "bom retiro": "Bom Retiro",
    "aventurero": "Aventureiro",
  
    "comasa": "Comasa",
  
    "adhemar garcia": "Adhemar Garcia",
  
    "boa vista": "Boa Vista",
    "costa e silva": "Costa e Silva",
    "petropolis": "Petrópolis",
  
    // valores que não devem contar como bairro:
    "bairro": undefined,
    "nao informado": undefined,
    "local nao fixo": undefined,
    "indefinido": undefined,
    "estado de santa catarina": undefined,
  };

  export const escolaridadeMap: Record<string, string | undefined> = {
    "fundamental completo": "Fundamental Completo",
    "fundamental incompleto": "Fundamental Incompleto",
    "fundamental": "Fundamental Completo",
    "fundamental proprio": "Fundamental Completo",
  
    "ensino medio completo": "Ensino Médio Completo",
    "ensino medio incompleto": "Ensino Médio Incompleto",
    "ensino medio": "Ensino Médio Completo",
    "ensino medio curso tecnico": "Ensino Médio + Curso Técnico",
  
    "curso tecnico": "Curso Técnico",
    "curso tecnico superior completo": "Curso Técnico/Superior Completo",
    "curso tecnico superior incompleto": "Curso Técnico/Superior Incompleto",
    "curso tecnico ou superior": "Curso Técnico/Superior Completo",
  
    "superior completo": "Superior Completo",
    "superior incompleto": "Superior Incompleto",
    "ensino superior incompleto": "Superior Incompleto",
    "curso superior": "Superior Completo",
  
    "nao exigida": "Não exigida",
    "nao informado": "Não informado",
    "escolaridade": "Não informado",
  
    // Ruídos:
    "-": "Não informado",
    "r 71319": undefined, // salário vindo no campo – ignorar
  };
  
  export function normalizeBairro(str: string) {
    const parts = normalizeBase(str).split("/");
    const final: string[] = [];
  
    for (const p of parts) {
      const fixed = bairroMap[p];
      if (!fixed) continue;
      final.push(fixed);
    }
  
    return final.length > 0 ? final : [""];
  }
  
  export function normalizeEscolaridade(str: string) {
  const key = normalizeBase(str);
  const val = escolaridadeMap[key];

  if (!val) return "";  // ignora lixo
  return val;
}

  
  export function capitalizeWords(str: string) {
    return str.replace(/\b\w+/g, w => (w ?? "").charAt(0).toUpperCase() + (w ?? "").slice(1).toLowerCase());
  }
  