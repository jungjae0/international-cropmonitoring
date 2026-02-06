function fetchAndRenderNIRV(crop, year) {
    const grid = document.getElementById("multi-nirv-grid");
    const zgrid = document.getElementById("multi-zscore-grid");
    grid.innerHTML = "";
    zgrid.innerHTML = "";

    fetch(`/nirv/api/multi-graph/?crop=${crop}&year=${year}`)
        .then(res => res.json())
        .then(data => {
            data.forEach(d => {
                const safeId = d.state.replace(/\s+/g, "-");

                // === NIRv 카드 ===
                const nid = `nirv-${safeId}`;
                const nContainer = document.createElement("div");
                nContainer.className = "border rounded shadow bg-white p-2";
                nContainer.innerHTML = `
          <div class="text-center font-semibold mb-1">${d.state}</div>
          <div id="${nid}" class="min-h-[330px] w-full"></div>
        `;
                grid.appendChild(nContainer);

                const traces = [];
                if (d.lower.length && d.upper.length) {
                    traces.push({
                        x: [...d.x, ...d.x.slice().reverse()],
                        y: [...d.upper, ...d.lower.slice().reverse()],
                        fill: "toself",
                        fillcolor: "rgba(150,150,150,0.2)",
                        line: {color: "transparent"},
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

                Plotly.newPlot(nid, traces, {
                    margin: {t: 20, b: 40, l: 40, r: 10},
                    xaxis: {title: "Day of Year", tickfont: {size: 10}},
                    yaxis: {title: "NIRv", tickfont: {size: 10}},
                    showlegend: false
                }, {responsive: true});

                // === Z-score 카드 ===
                if (d.zscore_doy?.length && d.zscore_class_num?.length) {
                    const zid = `zscore-${safeId}`;
                    const zContainer = document.createElement("div");
                    zContainer.className = "border rounded shadow bg-white p-2";
                    zContainer.innerHTML = `
            <div class="text-center font-semibold mb-1">${d.state}</div>
            <div id="${zid}" class="min-h-[300px] w-full"></div>
          `;
                    zgrid.appendChild(zContainer);

                    const zscoreTrace = {
                        x: d.zscore_doy,
                        y: d.zscore_class_num,
                        type: "scatter",
                        mode: "markers",
                        marker: {
                            color: d.zscore_class_num,
  colorscale: [
    [0, 'rgb(255,105,105)'],    // 빨강 - 낮은 값 (1)
    [0.5, 'rgb(108,121,255)'],  // 파랑 - 중간값 (4)
    [1, 'rgb(22,170,22)']     // 초록 - 높은 값 (7)
  ],
                            size: 7,
                            cmin: 1,
                            cmax: 7,
                            // colorbar: {
                            //   title: "Z-Class",
                            //   orientation: "v",
                            //   x: 1.02,
                            //   y: 1,
                            //   xanchor: "left",
                            //   len: 0.5,
                            //   thickness: 10,
                            //   tickvals: [1, 2, 3, 4, 5, 6, 7],
                            //   ticktext: [
                            //     "Extremely bad", "Bad", "Poor", "Slightly below",
                            //     "Slightly above", "Good", "Extremely good"
                            //   ]
                            // }
                        },
                        name: "Z-score Class"
                    };

                    const layout = {
                        height: 300,
                        // margin: {t: 20, b: 40, l: 40, r: 10},
                        margin: {t: 20, b: 40, l: 110, r: 0},
                        title: {
                            text: d.state,  // 예: Illinois
                            font: {size: 16},
                            x: 0.5
                        },
                        xaxis: {
                            title: "Day of Year"
                        },
                        yaxis: {
                            title: "Z-Class",
                            range: [0.5, 7.5],
                            tickvals: [1, 2, 3, 4, 5, 6, 7],
                            ticktext: [
                                "Extremely bad", "Bad", "Poor", "Slightly below",
                                "Slightly above", "Good", "Extremely good"
                            ],
                            tickfont: {size: 10},
                            automargin: true,
                            fixedrange: true
                        }
                    };

                    Plotly.newPlot(zid, [zscoreTrace], layout, {responsive: true});
                }
            });
        });
}
