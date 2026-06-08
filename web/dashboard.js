const state = { data: null, companies: [], selectedIndustry: "ALL", query: "", scatterPoints: [] };

const formatNumber = new Intl.NumberFormat("zh-CN");
const formatCompact = new Intl.NumberFormat("zh-CN", {
  notation: "compact",
  maximumFractionDigits: 1,
});
const formatPercent = new Intl.NumberFormat("zh-CN", {
  style: "percent",
  maximumFractionDigits: 1,
});

const exclusionLabels = {
  recent_st: "最近60日出现ST",
  missing_financial_records: "缺少可用财务数据",
  insufficient_trading_days: "交易天数不足",
  missing_market_features: "缺少行情特征",
  insufficient_liquidity: "流动性不足",
  invalid_pb: "PB无效或小于等于0",
};

function byId(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const node = byId(id);
  if (node) node.textContent = value;
}

function formatIndustryName(name) {
  const match = String(name).match(/^([A-Z]\d{2})(.+)$/);
  if (!match) return name;
  return `${match[2]}（${match[1]}）`;
}

function formatExclusionName(name) {
  return exclusionLabels[name] || name;
}

function renderBars(containerId, rows, limit = 18, formatter = (value) => value) {
  const container = byId(containerId);
  const max = Math.max(...rows.slice(0, limit).map((row) => row.count));
  container.innerHTML = rows
    .slice(0, limit)
    .map((row) => {
      const width = max ? (row.count / max) * 100 : 0;
      const label = formatter(row.name);
      return `
        <div class="bar-row" title="${label}">
          <div class="bar-label">${label}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
          <div class="bar-value">${row.count}</div>
        </div>
      `;
    })
    .join("");
}

function drawScatter(rows) {
  const canvas = byId("scatterCanvas");
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const pad = { left: 70, right: 24, top: 24, bottom: 54 };
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fbfdfc";
  ctx.fillRect(0, 0, width, height);

  const usable = rows.filter((row) => Number.isFinite(row.x) && Number.isFinite(row.y));
  const xs = usable.map((row) => Math.log10(Math.max(row.x, 1)));
  const ys = usable.map((row) => row.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  function sx(value) {
    const x = Math.log10(Math.max(value, 1));
    return pad.left + ((x - minX) / (maxX - minX || 1)) * (width - pad.left - pad.right);
  }
  function sy(value) {
    return height - pad.bottom - ((value - minY) / (maxY - minY || 1)) * (height - pad.top - pad.bottom);
  }
  state.scatterPoints = [];

  ctx.strokeStyle = "#d5ded9";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, height - pad.bottom);
  ctx.lineTo(width - pad.right, height - pad.bottom);
  ctx.stroke();

  ctx.fillStyle = "#5d6f78";
  ctx.font = "16px Microsoft YaHei, Arial";
  ctx.fillText("综合分", 18, 28);
  ctx.fillText("60日平均成交额（对数）", width / 2 - 90, height - 16);

  for (const row of usable) {
    const positive = row.return6m >= 0;
    const x = sx(row.x);
    const y = sy(row.y);
    ctx.beginPath();
    ctx.fillStyle = positive ? "rgba(31,107,87,0.58)" : "rgba(156,63,76,0.52)";
    ctx.arc(x, y, 4.2, 0, Math.PI * 2);
    ctx.fill();
    state.scatterPoints.push({ ...row, px: x, py: y });
  }
}

function setupScatterHover() {
  const canvas = byId("scatterCanvas");
  const tooltip = byId("chartTooltip");
  canvas.addEventListener("mousemove", (event) => {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = (event.clientX - rect.left) * scaleX;
    const y = (event.clientY - rect.top) * scaleY;
    let nearest = null;
    let nearestDistance = Infinity;
    for (const point of state.scatterPoints) {
      const distance = Math.hypot(point.px - x, point.py - y);
      if (distance < nearestDistance) {
        nearest = point;
        nearestDistance = distance;
      }
    }
    if (!nearest || nearestDistance > 12) {
      tooltip.hidden = true;
      return;
    }
    tooltip.hidden = false;
    tooltip.style.left = `${event.clientX + 14}px`;
    tooltip.style.top = `${event.clientY + 14}px`;
    tooltip.innerHTML = `
      <strong>${nearest.name} ${nearest.code}</strong><br>
      综合分：${nearest.y?.toFixed(2) ?? "-"}<br>
      60日成交额：${formatCompact.format(nearest.x ?? 0)}<br>
      6月收益：${Number.isFinite(nearest.return6m) ? formatPercent.format(nearest.return6m) : "-"}
    `;
  });
  canvas.addEventListener("mouseleave", () => {
    tooltip.hidden = true;
  });
}

function renderCompanies(rows) {
  const tbody = byId("companyRows");
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="9">没有匹配的公司。可以清空搜索或重置行业筛选。</td></tr>`;
    return;
  }
  tbody.innerHTML = rows
    .map((row) => {
      const scoreClass = row.score >= 75 ? "high" : row.score >= 70 ? "mid" : "";
      return `
      <tr>
        <td>${row.rank}</td>
        <td>${row.ts_code}</td>
        <td>${row.name}</td>
        <td>${formatIndustryName(row.industry)}</td>
        <td class="numeric"><span class="score-pill ${scoreClass}">${row.score?.toFixed(2) ?? "-"}</span></td>
        <td class="numeric">${row.quality?.toFixed(2) ?? "-"}</td>
        <td class="numeric">${row.growth?.toFixed(2) ?? "-"}</td>
        <td class="numeric">${row.market?.toFixed(2) ?? "-"}</td>
        <td class="numeric">${Number.isFinite(row.return6m) ? formatPercent.format(row.return6m) : "-"}</td>
      </tr>
    `;
    })
    .join("");
}

function applyFilters() {
  const query = state.query.trim().toLowerCase();
  const filtered = state.companies.filter((row) => {
    const industryMatch = state.selectedIndustry === "ALL" || row.industry === state.selectedIndustry;
    const textMatch = !query || `${row.ts_code} ${row.name} ${row.industry}`.toLowerCase().includes(query);
    return industryMatch && textMatch;
  });
  const limited = query || state.selectedIndustry !== "ALL" ? filtered : filtered.slice(0, 80);
  renderCompanies(limited);
  setText("tableStatus", `当前匹配 ${filtered.length} 只，正在显示 ${limited.length} 只。可用行业和搜索缩小范围。`);
}

function renderIndustryFilter(data) {
  const select = byId("industryFilter");
  const options = [
    `<option value="ALL">全部行业</option>`,
    ...data.industries.map((item) => `<option value="${item.name}">${formatIndustryName(item.name)}（${item.count}）</option>`),
  ];
  select.innerHTML = options.join("");
}

async function init() {
  let data = window.CORE600_DASHBOARD_DATA;
  if (!data) {
    const response = await fetch("./data/core600-dashboard.json");
    data = await response.json();
  }
  state.data = data;
  state.companies = data.companies || data.topCompanies;

  setText("asOfDate", data.asOfDate);
  setText("version", data.version);
  setText("selectedCount", formatNumber.format(data.summary.selected));
  setText("excludedCount", formatNumber.format(data.summary.excluded));
  setText("industryCount", formatNumber.format(data.summary.industryCount));
  setText("maxIndustry", `${data.summary.maxIndustryCount}只`);
  setText("scoreMedian", data.summary.scoreMedian?.toFixed(2) ?? "-");
  setText("scoreP90", data.summary.scoreP90?.toFixed(2) ?? "-");
  setText("amountMedian", formatCompact.format(data.summary.amountMedian ?? 0));
  setText("maxAnnouncement", data.summary.maxAnnouncementDate);
  renderBars("industryBars", data.industries, 18, formatIndustryName);
  renderBars("exclusionBars", data.exclusions, 8, formatExclusionName);
  drawScatter(data.scatter);
  setupScatterHover();
  renderIndustryFilter(data);
  applyFilters();
  byId("limitations").innerHTML = data.limitations.map((item) => `<li>${item}</li>`).join("");
}

byId("densityToggle")?.addEventListener("click", (event) => {
  const active = document.body.classList.toggle("large");
  event.currentTarget.setAttribute("aria-pressed", String(active));
});
byId("companySearch")?.addEventListener("input", (event) => {
  state.query = event.currentTarget.value;
  applyFilters();
});
byId("industryFilter")?.addEventListener("change", (event) => {
  state.selectedIndustry = event.currentTarget.value;
  applyFilters();
});
byId("resetFilters")?.addEventListener("click", () => {
  state.selectedIndustry = "ALL";
  state.query = "";
  byId("industryFilter").value = "ALL";
  byId("companySearch").value = "";
  applyFilters();
});

init().catch((error) => {
  console.error(error);
  document.body.insertAdjacentHTML(
    "beforeend",
    `<div style="margin:24px;padding:16px;background:#fff3f3;border:1px solid #c44">数据加载失败：${error.message}</div>`
  );
});
