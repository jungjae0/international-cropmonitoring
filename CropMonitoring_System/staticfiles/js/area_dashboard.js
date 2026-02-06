document.addEventListener("DOMContentLoaded", () => {
    const unitSelector = document.querySelectorAll("input[name='unit']");
    const cropSelect = document.getElementById("crop");
    const yearSelect = document.getElementById("year");
    const stateSelect = document.getElementById("state");

    // 단위 변환 함수
    const getUnitSettings = () => {
        const unit = document.querySelector("input[name='unit']:checked").value;
        return {
            convert: v => unit === "hectares" ? v * 0.4047 : v,
            suffix: unit === "hectares" ? "ha" : "acres"
        };
    };

    // 작물 선택 시 연도 / 주 옵션 동적 갱신
    cropSelect.addEventListener("change", () => {
        const crop = cropSelect.value;
        if (!crop) return;

        safeFetchJson(`/area/api/crop-info/?crop=${crop}`)
            .then(data => {
                data = sanitizeObject(data);
                // ✅ 연도 리스트 내림차순 정렬
                const sortedYears = data.years.sort((a, b) => b - a);

                // 연도 드롭다운 갱신
                yearSelect.innerHTML = "";
                sortedYears.forEach(y => {
                    const opt = document.createElement("option");
                    opt.value = y;
                    opt.textContent = y;
                    yearSelect.appendChild(opt);
                });

                // 주 드롭다운 갱신
                stateSelect.innerHTML = '<option value="">전체</option>';
                data.states.forEach(s => {
                    const opt = document.createElement("option");
                    opt.value = s;
                    opt.textContent = s;
                    stateSelect.appendChild(opt);
                });

                fetchAndRender(); // 초기 값 자동 렌더
            });
    });

    // 차트 요청 및 렌더
    function fetchAndRender() {
        const crop = cropSelect.value;
        const year = yearSelect.value;
        const state = stateSelect.value;
        if (!crop || !year) return;

        safeFetchJson(`/area/api/compare/?crop=${crop}&year=${year}&state=${state}`)
            .then(data => {
                data = sanitizeObject(data);
                const {convert, suffix} = getUnitSettings();
                const current = convert(data.current);
                const last = convert(data.last_year);
                const avg = convert(data.average);

                // 면적 비교 막대 차트
                Plotly.newPlot("area-chart", [{
                    x: ["평년", "전년도", "올해"],
                    y: [avg, last, current],
                    type: "bar",
                    marker: {color: ["gray", "orange", "blue"]}
                }], {
                    title: "면적 비교",
                    yaxis: {title: `면적 (${suffix})`},
                    margin: {t: 30}
                });

                // 시계열 그래프
                const years = data.trend.map(d => d.year);
                const areas = data.trend.map(d => convert(d.area));

                Plotly.newPlot("trend-chart", [{
                    x: years,
                    y: areas,
                    type: "scatter",
                    mode: "lines+markers",
                    marker: {color: "green"}
                }], {
                    title: "연도별 면적 추이",
                    yaxis: {title: `면적 (${suffix})`},
                    margin: {t: 30}
                });
            });
    }

    // 모든 필터 변경 시 렌더링 재요청
    [cropSelect, yearSelect, stateSelect, ...unitSelector].forEach(el => {
        el.addEventListener("change", fetchAndRender);
    });

    // 페이지 초기 로드시 렌더 (필요시)
    if (cropSelect.value) {
        fetchAndRender();
    }
});
