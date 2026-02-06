document.addEventListener("DOMContentLoaded", () => {
    const cropSel = document.getElementById("crop");
    const yearSel = document.getElementById("year");
    const loadBtn = document.getElementById("load-btn");
    const grid = document.getElementById("multi-nirv-grid");
    const zgrid = document.getElementById("multi-zscore-grid");

    cropSel.addEventListener("change", () => {
        const crop = cropSel.value;
        if (!crop) return;

        fetch(`/nirv/api/years/?crop=${crop}`)
            .then(res => res.json())
            .then(data => {
                yearSel.innerHTML = "<option value=''>연도 선택</option>";
                data.years.forEach(y => {
                    const opt = document.createElement("option");
                    opt.value = y;
                    opt.textContent = y;
                    yearSel.appendChild(opt);
                });
            });
    });

    loadBtn.addEventListener("click", () => {
        const crop = cropSel.value;
        const year = yearSel.value;

        if (!crop || !year) {
            alert("작물과 연도를 선택해주세요.");
            return;
        }

        fetch(`/nirv/api/multi-graph/?crop=${crop}&year=${year}`)
            .then(res => res.json())
            .then(data => {
                grid.innerHTML = "";
                zgrid.innerHTML = "";

                data.forEach(d => {
                    // NIRv 카드
                    const id = `nirv-${d.state.replace(/\s+/g, "-")}`;
                    const container = document.createElement("div");
                    container.className = "border rounded shadow bg-white p-2";
                    container.innerHTML = `
            <div class="text-center font-semibold mb-1">${d.state}</div>
            <div id="${id}" class="min-h-[330px] w-full"></div>
          `;
                    grid.appendChild(container);

                    const traces = [];

                    if (d.lower.length && d.upper.length) {
                        traces.push({
                            x: [...d.x, ...d.x.slice().reverse()],
                            y: [...d.upper, ...d.lower.slice().reverse()],
                            fill: "toself",
                            fillcolor: "rgba(150,150,150,0.2)",
                            line: {color: "transparent"},
                            name: "평년 범위 (95%)",
                            type: "scatter",
                            showlegend: false
                        });
                    }

                    if (d.mean.length) {
                        traces.push({
                            x: d.x,
                            y: d.mean,
                            mode: "lines",
                            line: {color: "gray", width: 2},
                            name: "평년 평균"
                        });
                    }

                    if (d.last.length) {
                        traces.push({
                            x: d.x,
                            y: d.last,
                            mode: "lines",
                            line: {color: "orange", width: 2},
                            name: "전년도"
                        });
                    }

                    if (d.current.length) {
                        traces.push({
                            x: d.x,
                            y: d.current,
                            mode: "lines",
                            line: {color: "blue", width: 3},
                            name: "올해"
                        });
                    }

                    Plotly.newPlot(id, traces, {
                        margin: {t: 20, b: 40, l: 40, r: 10},
                        xaxis: {title: "Day of Year", tickfont: {size: 10}},
                        yaxis: {title: "NIRv", tickfont: {size: 10}},
                        showlegend: false
                    }, {responsive: true});

                    // Z-score 카드
                    if (d.zscore_doy?.length && d.zscore_class_num?.length) {
                        const zid = `zscore-${d.state.replace(/\s+/g, "-")}`;
                        const zcontainer = document.createElement("div");
                        zcontainer.className = "border rounded shadow bg-white p-2";
                        zcontainer.innerHTML = `
              <div class="text-center font-semibold mb-1">${d.state}</div>
              <div id="${zid}" class="min-h-[300px] w-full"></div>
            `;
                        zgrid.appendChild(zcontainer);

                        const zscoreTrace = {
                            x: d.zscore_doy,
                            y: d.zscore_class_num,
                            type: "scatter",
                            mode: "markers",
                            marker: {
                                color: d.zscore_class_num,
                                colorscale: "YlGn",
                                size: 7,
                                cmin: 1,
                                cmax: 7,

                            },
                            name: "Z-score Class"
                        };

                        const layout = {
                            height: 350,
                            margin: {t: 60, b: 50, l: 90, r: 80},  // ✅ 모든 방향 여백 충분히
                            title: {
                                text: "Z-score 등급",
                                font: {size: 16},
                                x: 0.5,
                                xanchor: "center"
                            },
                            xaxis: {title: "Day of Year"},
                            yaxis: {
                                title: {
                                    text: "Z-Class",
                                },
                                tickvals: [1, 2, 3, 4, 5, 6, 7],
                                ticktext: [
                                    "Extremely bad", "Bad", "Poor", "Slightly below",
                                    "Slightly above", "Good", "Extremely good"
                                ],
                                tickfont: {size: 10},
                                automargin: true
                            }
                        };

                        Plotly.newPlot(zid, [zscoreTrace], layout, {responsive: true});
                    }
                });
            })
            .catch(err => {
                console.error("불러오기 실패:", err);
                alert("데이터를 불러오지 못했습니다.");
            });
    });
});
