import { readCSVFiles, readText } from "./utils/file";
import { parseHeader, parseRow, type Job } from "./utils/parse";

import { summary } from "./stats/summary";
import { vagasPorBairro } from "./stats/bairros";
import { salaryStats } from "./stats/salarios";
import { escolaridade } from "./stats/escolaridade";
import { salaryByBairro } from "./stats/salaryByBairro";
import { salaryByEscolaridade } from "./stats/salaryByEscolaridade";

const FOLDER = "./ok-csv";

function loadJobs(): Job[] {
  let all: Job[] = [];

  for (const file of readCSVFiles(FOLDER)) {
    const txt = readText(file);
    const lines = txt.split(/\r?\n/).filter(Boolean);
    const header = parseHeader(lines.find(l => l.includes("|"))!);

    for (const line of lines) {
      const row = parseRow(header, line);
      if (row) all.push(row);
    }
  }
  return all;
}

(function main() {
  const jobs = loadJobs();

  console.log("📌", summary(jobs));
  console.log("🏙 vagas por bairro:", vagasPorBairro(jobs));
  console.log("🎓 escolaridade:", escolaridade(jobs));
  console.log("💰 salário:", salaryStats(jobs));

  console.log(salaryByBairro(jobs));
  console.log(salaryByEscolaridade(jobs));
})();
