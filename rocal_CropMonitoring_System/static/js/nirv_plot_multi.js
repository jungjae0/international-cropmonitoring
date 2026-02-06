function fetchAndRenderNIRV(crop, year) {
    // 오늘의 DOY 계산 (1~366)
    const todayDOY = (() => {
        const now = new Date();
        const start = new Date(now.getFullYear(), 0, 0);
        const diff = now - start;
        const oneDay = 1000 * 60 * 60 * 24;
        return Math.floor(diff / oneDay);
    })();
    const grid = document.getElementById("multi-nirv-grid");
    const zgrid = document.getElementById("multi-zscore-grid");
    grid.innerHTML = "";
    zgrid.innerHTML = "";

    // 그래프를 그리기 위해 두 그리드 모두 일시적으로 표시
    grid.classList.remove("hidden");
    zgrid.classList.remove("hidden");

    safeFetchJson(`/nirv/api/multi-graph/?crop=${crop}&year=${year}`)
        .then(data => {
            // NaN 값 안전 처리
            data = data.map(d => sanitizeObject(d));
            data.forEach(d => {
                // 데이터 유효성 검증
                if (!d || !d.state || !d.x || !Array.isArray(d.x) || d.x.length === 0) {
                    return; // 유효하지 않은 데이터는 건너뛰기
                }

                const safeId = d.state.replace(/\s+/g, "-");

                // 먼저 traces를 구성하여 데이터가 있는지 확인
                const traces = [];
                // 현재 연도의 마지막 유효 센싱 DOY (백엔드 제공 우선, 없으면 프런트 계산)
                const lastSensingDOY = (() => {
                    console.log(`[${d.state}] 디버깅 시작:`, {
                        last_sensing_doy: d.last_sensing_doy,
                        current_length: d.current?.length,
                        zscore_doy_length: d.zscore_doy?.length
                    });
                    // 1. 백엔드에서 제공한 값 우선
                    if (d.last_sensing_doy !== null && d.last_sensing_doy !== undefined) {
                        return d.last_sensing_doy;
                    }

                    // 2. NIRv current 데이터에서 찾기
                    if (d.current && Array.isArray(d.current) && d.current.length > 0) {
                        for (let i = d.current.length - 1; i >= 0; i--) {
                            const v = d.current[i];
                            if (v !== null && v !== undefined && !Number.isNaN(v)) {
                                return d.x[i];
                            }
                        }
                    }

                    // 3. Z-score 데이터에서 찾기
                    if (d.zscore_doy && Array.isArray(d.zscore_doy) && d.zscore_doy.length > 0) {
                        // zscore_doy의 마지막 유효 값 반환
                        for (let i = d.zscore_doy.length - 1; i >= 0; i--) {
                            const v = d.zscore_doy[i];
                            if (v !== null && v !== undefined && !Number.isNaN(v)) {
                                return v;
                            }
                        }
                    }

                    return null;
                })();
                console.log(`[${d.state}] lastSensingDOY 계산 결과:`, lastSensingDOY);
                if (Array.isArray(d.lower) && d.lower.length > 0 && Array.isArray(d.upper) && d.upper.length > 0) {
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

                if (Array.isArray(d.mean) && d.mean.length > 0) {
                    traces.push({
                        x: d.x,
                        y: d.mean,
                        mode: "lines",
                        line: {color: "gray", width: 2},
                        name: "평년 평균"
                    });
                }

                if (Array.isArray(d.last) && d.last.length > 0) {
                    traces.push({
                        x: d.x,
                        y: d.last,
                        mode: "lines",
                        line: {color: "orange", width: 2},
                        name: "전년도"
                    });
                }

                if (Array.isArray(d.current) && d.current.length > 0) {
                    traces.push({
                        x: d.x,
                        y: d.current,
                        mode: "lines",
                        line: {color: "blue", width: 3},
                        name: "올해"
                    });
                }

                // traces가 비어있지 않을 때만 NIRv 카드 생성 및 그래프 렌더링
                if (traces.length > 0) {
                    const nid = `nirv-${safeId}`;
                    const nContainer = document.createElement("div");
                    nContainer.className = "border rounded shadow bg-white p-2";
                    nContainer.innerHTML = `
                        <div class="text-center font-semibold mb-1">${d.state}</div>
                        <div id="${nid}" class="min-h-[330px] w-full"></div>
                    `;
                    grid.appendChild(nContainer);

                    Plotly.newPlot(nid, traces, {
                        margin: {t: 20, b: 40, l: 50, r: 10},
                        xaxis: {
                            title: "Day of Year",
                            tickfont: {size: 10},
                            gridcolor: '#e5e7eb'
                        },
                        yaxis: {
                            title: "NIRv",
                            tickfont: {size: 10},
                            gridcolor: '#e5e7eb'
                        },
                        showlegend: false,
                        plot_bgcolor: '#fafafa',
                        paper_bgcolor: 'white'
                    }, {responsive: true});

                    // 오늘 DOY + 마지막 센싱 DOY 세로선 및 라벨 추가
                    const nirvShapes = [
                        {
                            type: 'line',
                            x0: todayDOY,
                            x1: todayDOY,
                            y0: 0,
                            y1: 1,
                            xref: 'x',
                            yref: 'paper',
                            line: {color: 'red', width: 2}
                        }
                    ];
                    const nirvAnnotations = [
                        {
                            x: todayDOY,
                            y: 1.02,
                            xref: 'x',
                            yref: 'paper',
                            text: `DOY ${todayDOY}`,
                            showarrow: false,
                            font: {color: 'red', size: 11},
                            xanchor: 'center',
                            align: 'center'
                        }
                    ];

                    if (lastSensingDOY !== null && lastSensingDOY !== undefined) {
                        nirvShapes.push({
                            type: 'line',
                            x0: lastSensingDOY,
                            x1: lastSensingDOY,
                            y0: 0,
                            y1: 1,
                            xref: 'x',
                            yref: 'paper',
                            line: {color: 'green', width: 2, dash: 'dot'}
                        });
                        nirvAnnotations.push({
                            x: lastSensingDOY,
                            y: 0.96,
                            xref: 'x',
                            yref: 'paper',
                            text: `Last sensing<br>DOY ${lastSensingDOY}`,
                            showarrow: false,
                            font: {color: 'green', size: 11},
                            xanchor: 'center',
                            align: 'center'
                        });
                    }

                    Plotly.relayout(nid, {
                        shapes: nirvShapes,
                        annotations: nirvAnnotations
                    });
                }

                // === Z-score 카드 ===
                if (Array.isArray(d.zscore_doy) && d.zscore_doy.length > 0 &&
                    Array.isArray(d.zscore_class_num) && d.zscore_class_num.length > 0) {
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
                        margin: {t: 20, b: 40, l: 110, r: 10},
                        title: {
                            text: d.state,
                            font: {size: 16, weight: 'bold'},
                            x: 0.5
                        },
                        xaxis: {
                            title: "Day of Year",
                            tickfont: {size: 10},
                            gridcolor: '#e5e7eb'
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
                            fixedrange: true,
                            gridcolor: '#e5e7eb'
                        },
                        plot_bgcolor: '#fafafa',
                        paper_bgcolor: 'white'
                    };

                    Plotly.newPlot(zid, [zscoreTrace], layout, {responsive: true});

                    // 오늘 DOY + 마지막 센싱 DOY 세로선 및 라벨 추가
                    const zscoreShapes = [
                        {
                            type: 'line',
                            x0: todayDOY,
                            x1: todayDOY,
                            y0: 0,
                            y1: 1,
                            xref: 'x',
                            yref: 'paper',
                            line: {color: 'red', width: 2}
                        }
                    ];
                    const zscoreAnnotations = [
                        {
                            x: todayDOY,
                            y: 1.04,
                            xref: 'x',
                            yref: 'paper',
                            text: `DOY ${todayDOY}`,
                            showarrow: false,
                            font: {color: 'red', size: 11},
                            xanchor: 'center',
                            align: 'center'
                        }
                    ];

                    if (lastSensingDOY !== null && lastSensingDOY !== undefined) {
                        console.log(`[${d.state}] Z-score에 초록색 점선 추가, lastSensingDOY:`, lastSensingDOY);
                        zscoreShapes.push({
                            type: 'line',
                            x0: lastSensingDOY,
                            x1: lastSensingDOY,
                            y0: 0,
                            y1: 1,
                            xref: 'x',
                            yref: 'paper',
                            line: {color: 'green', width: 2, dash: 'dot'}
                        });
                        zscoreAnnotations.push({
                            x: lastSensingDOY,
                            y: 0.96,
                            xref: 'x',
                            yref: 'paper',
                            text: `Last sensing<br>DOY ${lastSensingDOY}`,
                            showarrow: false,
                            font: {color: 'green', size: 11},
                            xanchor: 'center',
                            align: 'center'
                        });
                    }

                    Plotly.relayout(zid, {
                        shapes: zscoreShapes,
                        annotations: zscoreAnnotations
                    });
                }
            });

            // 그래프 그리기 완료 후, NIRv 탭을 기본으로 표시하고 Z-score는 숨김
            setTimeout(() => {
                zgrid.classList.add("hidden");
                grid.classList.remove("hidden");
            }, 200);
        })
        .catch(err => {
            console.error("❌ NIRv multi-graph load error:", err);
            alert(`NIRv 데이터 로딩 실패: ${err.message}\n브라우저 콘솔을 확인하세요.`);
        });
}




document.addEventListener("DOMContentLoaded", function () {
  const cropSel = document.getElementById("crop");
  const yearSel = document.getElementById("year");
  const loadBtn = document.getElementById("load-btn");
  const nirvTab = document.getElementById("tab-nirv");
  const zscoreTab = document.getElementById("tab-zscore");
  const nirvGrid = document.getElementById("multi-nirv-grid");
  const zscoreGrid = document.getElementById("multi-zscore-grid");

  // 작물 선택 → 연도 목록 가져오기
  cropSel.addEventListener("change", () => {
    const crop = cropSel.value;
    if (!crop) {
      yearSel.innerHTML = "<option value=''>연도 선택</option>";
      return;
    }

    safeFetchJson(`/nirv/api/years/?crop=${crop}`)
      .then(data => {
        yearSel.innerHTML = "<option value=''>연도 선택</option>";
        data.years.forEach(y => {
          const opt = document.createElement("option");
          opt.value = y;
          opt.textContent = y;
          yearSel.appendChild(opt);
        });
      })
      .catch(err => {
        console.error("연도 목록 로딩 오류:", err);
        yearSel.innerHTML = "<option value=''>연도 선택</option>";
      });
  });

  // "업데이트" 버튼 클릭 → 그래프 그리기
  loadBtn.addEventListener("click", () => {
    const crop = cropSel.value;
    const year = yearSel.value;

    if (!crop || !year) {
      alert("작물과 연도를 모두 선택해주세요.");
      return;
    }

    fetchAndRenderNIRV(crop, year);
  });

  // 탭 전환 로직
  nirvTab.addEventListener("click", () => {
    nirvTab.classList.add("border-blue-500", "text-blue-500", "font-semibold");
    nirvTab.classList.remove("border-transparent");
    zscoreTab.classList.remove("border-blue-500", "text-blue-500", "font-semibold");
    zscoreTab.classList.add("text-gray-500", "border-transparent");

    nirvGrid.classList.remove("hidden");
    zscoreGrid.classList.add("hidden");

    // NIRv 그래프 크기 재조정
    setTimeout(() => {
      const nirvPlots = nirvGrid.querySelectorAll('[id^="nirv-"]');
      nirvPlots.forEach(plot => {
        if (plot && window.Plotly) {
          Plotly.Plots.resize(plot);
        }
      });
    }, 100);
  });

  zscoreTab.addEventListener("click", () => {
    zscoreTab.classList.add("border-blue-500", "text-blue-500", "font-semibold");
    zscoreTab.classList.remove("border-transparent");
    nirvTab.classList.remove("border-blue-500", "text-blue-500", "font-semibold");
    nirvTab.classList.add("text-gray-500", "border-transparent");

    zscoreGrid.classList.remove("hidden");
    nirvGrid.classList.add("hidden");

    // Z-score 그래프 크기 재조정
    setTimeout(() => {
      const zscorePlots = zscoreGrid.querySelectorAll('[id^="zscore-"]');
      zscorePlots.forEach(plot => {
        if (plot && window.Plotly) {
          Plotly.Plots.resize(plot);
        }
      });
    }, 100);
  });
});

