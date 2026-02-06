// area_chart_logic.js

function formatNumber(n) {
  return n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

let stateData = [];

function fetchAreaSummary(crop, year, country, state, variant) {
  const stateParam   = state || "";
  const variantParam = variant || "";

  safeFetchJson(`/maps/api/area-summary/?crop=${crop}&year=${year}&country=${country}&state=${stateParam}&variant=${variantParam}`)
    .then(data => {
      // NaN 값 안전 처리
      data = sanitizeObject(data);
      const unit    = document.querySelector('input[name="unit"]:checked').value;
      const convert = v => unit === "hectares" ? v * 0.4047 : v;
      const suffix  = unit === "hectares" ? " ha" : " acres";

      if (data.mode === "summary") {
        document.getElementById("area-total").innerText =
          `총 면적: ${formatNumber(convert(data.total_area))}${suffix}`;
        document.getElementById("area-ranking-controls").style.display = "block";
        document.getElementById("download-btn").style.display = "inline-block";
        document.getElementById("time-series-chart").innerHTML = "";

        stateData = data.by_state;
        renderRankingList(stateData, convert, suffix);
        renderPlotlyBarChart(stateData, convert, suffix);
      }

      else if (data.mode === "state_summary") {
        document.getElementById("area-ranking-controls").style.display = "none";
        document.getElementById("download-btn").style.display = "none";
        document.getElementById("area-ranking-list").innerHTML = "";

        const total = data.areas.reduce((sum, d) => sum + d.area, 0);
        const parts = data.areas.map(a =>
          `${a.variant}: ${formatNumber(convert(a.area))}${suffix}`
        ).join(" / ");

        document.getElementById("area-total").innerText =
          `면적 (${data.state}): ${parts} (총 ${formatNumber(convert(total))}${suffix})`;

       renderPlotlyBarChart(
  data.areas.map(d => ({
    state: data.state,
    variant: d.variant,
    area: d.area,
    last_year_area: d.last_year_area ?? 0
  })),
  convert,
  suffix
);

        document.getElementById("time-series-chart").innerHTML = "";
      }

      else if (data.mode === "single") {
        const areaNow  = data.area !== null ? convert(data.area) : null;
        const areaLast = data.last_year_area !== null ? convert(data.last_year_area) : null;

        const nowText  = areaNow !== null ? formatNumber(areaNow) + suffix : "없음";
        const lastText = areaLast !== null ? formatNumber(areaLast) + suffix : "없음";

        document.getElementById("area-total").innerText =
          `면적 (${data.state} - ${data.variant}): ${nowText} (전년도: ${lastText})`;

        document.getElementById("area-ranking-controls").style.display = "none";
        document.getElementById("download-btn").style.display = "none";
        document.getElementById("area-ranking-list").innerHTML = "";

        renderPlotlyBarChart([
          {
            state: data.state,
            variant: data.variant,
            area: data.area ?? 0,
            last_year_area: data.last_year_area ?? 0
          }
        ], convert, suffix);

        safeFetchJson(`/maps/api/area-summary/?mode=time_series&crop=${crop}&year=${year}&country=${country}&state=${state}&variant=${variant}`)
          .then(json => {
            json = sanitizeObject(json);
            if (json.mode === "time_series") {
              renderTimeSeriesChart(json.series);
            }
          })
          .catch(err => console.error("Time series load failed:", err));
      }
    })
    .catch(err => console.error("Area summary load failed:", err));
}

function renderRankingList(data, convert, suffix) {
  const list = document.getElementById("area-ranking-list");
  list.innerHTML = "";

  data.forEach(d => {
    const li = document.createElement("li");
    const val = formatNumber(convert(d.area));
    const diff = d.diff !== undefined ? convert(d.diff) : null;
    const pct  = d.percent_change;

    let changeText = "";
    if (pct !== null && !isNaN(pct)) {
      const sign = pct > 0 ? "↑" : pct < 0 ? "↓" : "-";
      const pctText = `${sign} ${Math.abs(pct).toFixed(1)}%`;
      changeText = ` (${pctText})`;
    }

    li.textContent = `${d.state} - ${d.variant}: ${val}${suffix}${changeText}`;
    list.appendChild(li);
  });
}

function renderPlotlyBarChart(data, convert, suffix) {
  const xLabels = data.map(d => `${d.state} - ${d.variant}`);
  const yCurrent = data.map(d => convert(d.area));
  const yLast    = data.map(d => convert(d.last_year_area ?? 0));

  const traceCurrent = {
    x: xLabels,
    y: yCurrent,
    name: "당해년도",
    type: "bar",
    marker: { color: "blue" }
  };

  const traceLast = {
    x: xLabels,
    y: yLast,
    name: "전년도",
    type: "bar",
    marker: { color: "orange" }
  };

  const layout = {
    barmode: 'group',
    title: "면적 비교 (당해 vs 전년)",
    xaxis: { title: "State - Variant" },
    yaxis: { title: `면적 (${suffix.trim()})` }
  };

  Plotly.newPlot("plotly-bar", [traceLast, traceCurrent], layout);
}

function renderTimeSeriesChart(series) {
  if (!series || series.length === 0) return;

  const years = series.map(d => d.year);
  const areas = series.map(d => d.area);

  const layout = {
    title: "연도별 면적 추이",
    xaxis: { title: "Year" },
    yaxis: { title: "면적 (acres)" },
    margin: { t: 30 }
  };

  const trace = {
    x: years,
    y: areas,
    type: "scatter",
    mode: "lines+markers",
    marker: { color: "orange" },
    line: { shape: "linear" }
  };

  Plotly.newPlot("time-series-chart", [trace], layout);
}

document.getElementById("area-sort-asc").addEventListener("click", () => {
  stateData.sort((a, b) => a.area - b.area);
  const unit    = document.querySelector('input[name="unit"]:checked').value;
  const convert = v => unit === "hectares" ? v * 0.4047 : v;
  const suffix  = unit === "hectares" ? " ha" : " acres";
  renderRankingList(stateData, convert, suffix);
  renderPlotlyBarChart(stateData, convert, suffix);
});

document.getElementById("area-sort-desc").addEventListener("click", () => {
  stateData.sort((a, b) => b.area - a.area);
  const unit    = document.querySelector('input[name="unit"]:checked').value;
  const convert = v => unit === "hectares" ? v * 0.4047 : v;
  const suffix  = unit === "hectares" ? " ha" : " acres";
  renderRankingList(stateData, convert, suffix);
  renderPlotlyBarChart(stateData, convert, suffix);
});

document.querySelectorAll('input[name="unit"]').forEach(radio => {
  radio.addEventListener("change", () => {
    const crop    = document.getElementById("crop").value;
    const year    = document.getElementById("year").value;
    const country = document.getElementById("country").value;
    const state   = document.getElementById("state").value === "전체"
                    ? "" : document.getElementById("state").value;
    const variant = document.getElementById("variant").value;
    if (crop && year && country) {
      fetchAreaSummary(crop, year, country, state, variant);
    }
  });
});

document.getElementById("download-btn").addEventListener("click", () => {
  if (!stateData.length) return;

  const rows = [
    ["State", "Variant", "Area", "Last Year Area", "Diff", "Percent Change"]
  ];

  stateData.forEach(d => {
    rows.push([
      d.state,
      d.variant,
      d.area,
      d.last_year_area !== undefined ? d.last_year_area : "",
      d.diff !== undefined ? d.diff : "",
      d.percent_change !== undefined ? `${d.percent_change}%` : ""
    ]);
  });

  const csv = rows.map(r => r.join(",")).join("\\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = "area_summary.csv";
  a.click();

  URL.revokeObjectURL(url);
});
