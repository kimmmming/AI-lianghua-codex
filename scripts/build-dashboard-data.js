const fs = require("fs");
const path = require("path");

const projectRoot = path.resolve(__dirname, "..");
const selectedPath = path.join(projectRoot, "outputs", "core600_fundamental_proxy_2026-06-06.csv");
const excludedPath = path.join(projectRoot, "outputs", "excluded_fundamental_proxy_2026-06-06.csv");
const reportPath = path.join(projectRoot, "outputs", "core600_fundamental_proxy_report_2026-06-06.json");
const outDir = path.join(projectRoot, "web", "data");
const outPath = path.join(outDir, "core600-dashboard.json");
const jsOutPath = path.join(outDir, "core600-dashboard-data.js");

function parseCsv(content) {
  const rows = [];
  let cell = "";
  let row = [];
  let quoted = false;
  for (let i = 0; i < content.length; i += 1) {
    const char = content[i];
    const next = content[i + 1];
    if (char === '"' && quoted && next === '"') {
      cell += '"';
      i += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(cell);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  if (cell || row.length) {
    row.push(cell);
    rows.push(row);
  }
  const [headers, ...records] = rows;
  return records.map((record) => {
    const object = {};
    headers.forEach((header, index) => {
      object[header.replace(/^\uFEFF/, "")] = record[index] ?? "";
    });
    return object;
  });
}

function numberValue(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function countBy(rows, key) {
  const counts = new Map();
  for (const row of rows) {
    const value = row[key] || "UNKNOWN";
    counts.set(value, (counts.get(value) || 0) + 1);
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, "zh-CN"));
}

function quantile(values, q) {
  const sorted = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (!sorted.length) return null;
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sorted[base + 1] === undefined) return sorted[base];
  return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
}

const selected = parseCsv(fs.readFileSync(selectedPath, "utf-8"));
const excluded = parseCsv(fs.readFileSync(excludedPath, "utf-8"));
const report = JSON.parse(fs.readFileSync(reportPath, "utf-8"));

const selectedWithNumbers = selected.map((row, index) => ({
  rank: index + 1,
  ts_code: row.ts_code,
  name: row.name,
  industry: row.industry || "UNKNOWN",
  score: numberValue(row.fundamental_proxy_score),
  quality: numberValue(row.quality_score),
  growth: numberValue(row.growth_score),
  market: numberValue(row.market_proxy_score),
  amount: numberValue(row.average_amount_60d),
  return6m: numberValue(row.return_6m),
  volatility: numberValue(row.annualized_volatility_60d),
  drawdown: numberValue(row.max_drawdown_120d),
  roe: numberValue(row.profit_roeAvg),
  netMargin: numberValue(row.profit_npMargin),
  announcementDate: row.announcement_date,
  reportPeriod: row.report_period,
}));

const scores = selectedWithNumbers.map((row) => row.score).filter(Number.isFinite);
const amounts = selectedWithNumbers.map((row) => row.amount).filter(Number.isFinite);
const industries = countBy(selectedWithNumbers, "industry");
const exclusions = countBy(excluded, "exclusion_reason");

const payload = {
  generatedAt: new Date().toISOString(),
  asOfDate: report.as_of_date,
  version: report.selection_version,
  summary: {
    selected: selectedWithNumbers.length,
    uniqueSelected: new Set(selectedWithNumbers.map((row) => row.ts_code)).size,
    excluded: excluded.length,
    industryCount: industries.length,
    maxIndustryCount: Math.max(...industries.map((item) => item.count)),
    scoreMedian: quantile(scores, 0.5),
    scoreP90: quantile(scores, 0.9),
    amountMedian: quantile(amounts, 0.5),
    maxAnnouncementDate: report.max_announcement_date,
  },
  industries,
  exclusions,
  companies: selectedWithNumbers,
  topCompanies: selectedWithNumbers.slice(0, 80),
  scatter: selectedWithNumbers.map((row) => ({
    code: row.ts_code,
    name: row.name,
    industry: row.industry,
    x: row.amount,
    y: row.score,
    return6m: row.return6m,
    quality: row.quality,
    growth: row.growth,
  })),
  limitations: report.limitations || [],
};

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(payload, null, 2), "utf-8");
fs.writeFileSync(
  jsOutPath,
  `window.CORE600_DASHBOARD_DATA = ${JSON.stringify(payload, null, 2)};\n`,
  "utf-8"
);
console.log(`Dashboard data written to ${outPath}`);
