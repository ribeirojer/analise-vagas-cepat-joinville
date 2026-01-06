import fs from "fs";
import path from "path";

export function readCSVFiles(dir: string): string[] {
  return fs.readdirSync(dir)
    .filter(f => f.endsWith(".csv"))
    .map(f => path.join(dir, f));
}

export function readText(file: string) {
  return fs.readFileSync(file, "utf8");
}
