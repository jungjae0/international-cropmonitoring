function formatNumber(n) {
    return n.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

let stateData = [];

function fetchAreaSummary(crop, year, country, state) {
    // ✅ "전체"를 정확히 넘기되, 쿼리에서는 ""로 해석되므로 명시적으로 처리
    const stateParam = (state === "전체" || !state) ? "" : state;

    fetch(`/maps/api/area-summary/?crop=${crop}&year=${year}&country=${country}&state=${stateParam}`)
        .then(res => res.json())
        .then(data => {
            // console.log("응답 데이터:", data);
            const unit = document.querySelector('input[name="unit"]:checked').value;
            const convert = (v) => unit === "hectares" ? v * 0.4047 : v;
            const suffix = unit === "hectares" ? " ha" : " acres";

            if (data.mode === "summary") {
                document.getElementById("area-total").innerText =
                    `총 면적: ${formatNumber(convert(data.total_area))}${suffix}`;

                document.getElementById("area-ranking-controls").style.display = 'block';
                stateData = data.by_state;
                renderRankingList(stateData, convert, suffix);
                renderPlotlyBarChart(stateData, convert, suffix);
            } else if (data.mode === "single") {
                document.getElementById("area-total").innerText =
                    data.area !== null
                        ? `면적 (${data.state}): ${(convert(data.area))}${suffix}`
                        : `${data.state}에 대한 면적 정보가 없습니다.`;

                document.getElementById("area-ranking-controls").style.display = 'none';
                document.getElementById("area-ranking-list").innerHTML = "";
                renderPlotlyBarChart([], convert, suffix);
            }
        });
}

function renderRankingList(data, convert, suffix) {
    const list = document.getElementById("area-ranking-list");
    list.innerHTML = "";
    data.forEach(entry => {
        const li = document.createElement("li");
        li.innerHTML = `
      <span>${entry.state}</span>
      <span>${formatNumber(convert(entry.area))}${suffix}</span>
    `;
        list.appendChild(li);
    });
}

function renderPlotlyBarChart(data, convert, suffix) {
    const states = data.map(d => d.state);
    const values = data.map(d => convert(d.area));

    const layout = {
        title: '주별 재배 면적',
        xaxis: {title: 'State'},
        yaxis: {title: `면적 (${suffix.trim()})`},
        margin: {t: 40, l: 60, r: 20, b: 60},
        responsive: true
    };

    const trace = {
        x: states,
        y: values,
        type: 'bar',
        marker: {color: '#457b9d'}
    };

    Plotly.newPlot('area-chart', [trace], layout);
}

// ✅ 단위 전환 시 다시 렌더링
const unitRadios = document.querySelectorAll('input[name="unit"]');
unitRadios.forEach(radio => {
    radio.addEventListener('change', () => {
        const crop = document.getElementById("crop").value;
        const year = document.getElementById("year").value;
        const country = document.getElementById("country").value;
        const state = document.getElementById("state").value;
        if (crop && year && country) {
            fetchAreaSummary(crop, year, country, state);
        }
    });
});

// ✅ 정렬 버튼 작동 (현재 stateData 기준)
const ascBtn = document.getElementById("sort-asc");
const descBtn = document.getElementById("sort-desc");

ascBtn.addEventListener("click", () => {
    stateData.sort((a, b) => a.area - b.area);
    const unit = document.querySelector('input[name="unit"]:checked').value;
    const convert = (v) => unit === "hectares" ? v * 0.4047 : v;
    const suffix = unit === "hectares" ? " ha" : " acres";
    renderRankingList(stateData, convert, suffix);
    renderPlotlyBarChart(stateData, convert, suffix);
});

descBtn.addEventListener("click", () => {
    stateData.sort((a, b) => b.area - a.area);
    const unit = document.querySelector('input[name="unit"]:checked').value;
    const convert = (v) => unit === "hectares" ? v * 0.4047 : v;
    const suffix = unit === "hectares" ? " ha" : " acres";
    renderRankingList(stateData, convert, suffix);
    renderPlotlyBarChart(stateData, convert, suffix);
});
