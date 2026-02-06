document.addEventListener("DOMContentLoaded", () => {
    const cropSel = document.getElementById("crop");
    const yearSel = document.getElementById("year");
    const stateSel = document.getElementById("state");
    const loadBtn = document.getElementById("load-btn");

    // 작물 선택 → 연도 목록 가져오기
    cropSel.addEventListener("change", () => {
        const crop = cropSel.value;
        if (!crop) return;

        safeFetchJson(`/nirv/api/years/?crop=${crop}`)
            .then(data => {
                yearSel.innerHTML = "<option value=''>연도 선택</option>";
                stateSel.innerHTML = "<option value=''>주 선택</option>";
                data.years.forEach(y => {
                    const opt = document.createElement("option");
                    opt.value = y;
                    opt.textContent = y;
                    yearSel.appendChild(opt);
                });
            });
    });

    // 연도 선택 → 주 목록 가져오기
    yearSel.addEventListener("change", () => {
        const crop = cropSel.value;
        const year = yearSel.value;
        if (!crop || !year) return;

        safeFetchJson(`/nirv/api/states/?crop=${crop}&year=${year}`)
            .then(data => {
                stateSel.innerHTML = "<option value=''>주 선택</option>";
                data.states.forEach(s => {
                    const opt = document.createElement("option");
                    opt.value = s;
                    opt.textContent = s;
                    stateSel.appendChild(opt);
                });
            });
    });

    // "업데이트" 버튼 클릭 → 그래프 그리기
    loadBtn.addEventListener("click", () => {
        const crop = cropSel.value;
        const year = yearSel.value;
        const state = stateSel.value;

        if (!crop || !year || !state) {
            alert("모든 항목을 선택해주세요.");
            return;
        }

        // 그래프를 그리기 위해 두 컨테이너 모두 일시적으로 표시
        const nirvContainer = document.getElementById('nirv-container');
        const zscoreContainer = document.getElementById('zscore-container');
        nirvContainer.classList.remove('hidden');
        zscoreContainer.classList.remove('hidden');

        safeFetchJson(`/nirv/api/graph/?crop=${crop}&year=${year}&state=${state}`)
            .then(data => {
                // NaN 값 안전 처리
                data = sanitizeObject(data);
                const x = data.x;

                // === NIRv 그래프 ===
                const nirvTraces = [];

                if (data.lower.length && data.upper.length) {
                    nirvTraces.push({
                        x: [...x, ...x.slice().reverse()],
                        y: [...data.upper, ...data.lower.slice().reverse()],
                        fill: "toself",
                        fillcolor: "rgba(150,150,150,0.2)",
                        line: {color: "transparent"},
                        name: "평년 범위 (95%)",
                        type: "scatter",
                        showlegend: false
                    });
                }

                if (data.mean.length) {
                    nirvTraces.push({
                        x,
                        y: data.mean,
                        mode: "lines",
                        line: {color: "gray", width: 2},
                        name: "평년 평균"
                    });
                }

                if (data.last.length) {
                    nirvTraces.push({
                        x,
                        y: data.last,
                        mode: "lines",
                        line: {color: "orange", width: 2},
                        name: `전년도 (${parseInt(year) - 1})`
                    });
                }

                if (data.current.length) {
                    nirvTraces.push({
                        x,
                        y: data.current,
                        mode: "lines",
                        line: {color: "blue", width: 3},
                        name: `올해 (${year})`
                    });
                }

                Plotly.newPlot("nirv-plot", nirvTraces, {
                    margin: {t: 60, b: 60, l: 60, r: 20},
                    title: {
                        text: `${state} - ${crop} (${year})`,
                        font: {size: 18, weight: 'bold'},
                        x: 0.5
                    },
                    xaxis: {
                        title: "Day of Year",
                        gridcolor: '#e5e7eb'
                    },
                    yaxis: {
                        title: "NIRv",
                        gridcolor: '#e5e7eb'
                    },
                    legend: {
                        orientation: 'h',
                        x: 0.5,
                        xanchor: 'center',
                        y: -0.15
                    },
                    plot_bgcolor: '#fafafa',
                    paper_bgcolor: 'white'
                }, {responsive: true});

                // === Z-score 그래프 ===
                if (data.zscore_doy?.length && data.zscore_class_num?.length) {
                    const zTrace = {
                        x: data.zscore_doy,
                        y: data.zscore_class_num,
                        type: "scatter",
                        mode: "markers",
                        marker: {
                            color: data.zscore_class_num,
                            colorscale: [
                                [0, 'rgb(255,105,105)'],    // 빨강 - 낮은 값
                                [0.5, 'rgb(108,121,255)'],  // 파랑 - 중간값
                                [1, 'rgb(22,170,22)']       // 초록 - 높은 값
                            ],
                            size: 8,
                            cmin: 1,
                            cmax: 7,
                            colorbar: {
                                title: "Z-Class",
                                orientation: "v",
                                x: 1.02,
                                y: 0.5,
                                xanchor: "left",
                                len: 0.7,
                                thickness: 15,
                                tickvals: [1, 2, 3, 4, 5, 6, 7],
                                ticktext: [
                                    "Extremely bad", "Bad", "Poor", "Slightly below",
                                    "Slightly above", "Good", "Extremely good"
                                ]
                            }
                        },
                        name: "Z-Class"
                    };

                    const zLayout = {
                        height: 450,
                        margin: {t: 60, b: 60, l: 110, r: 100},
                        title: {
                            text: `${state} - ${crop} (${year}) Z-score`,
                            font: {size: 18, weight: 'bold'},
                            x: 0.5
                        },
                        xaxis: {
                            title: "Day of Year",
                            gridcolor: '#e5e7eb'
                        },
                        yaxis: {
                            title: "Z-Class",
                            tickvals: [1, 2, 3, 4, 5, 6, 7],
                            ticktext: [
                                "Extremely bad", "Bad", "Poor", "Slightly below",
                                "Slightly above", "Good", "Extremely good"
                            ],
                            tickfont: {size: 10},
                            automargin: true,
                            gridcolor: '#e5e7eb'
                        },
                        plot_bgcolor: '#fafafa',
                        paper_bgcolor: 'white'
                    };

                    Plotly.newPlot("zscore-plot", [zTrace], zLayout, {responsive: true});
                }

                // 그래프 그리기 완료 후, NIRv 탭을 기본으로 표시하고 Z-score는 숨김
                setTimeout(() => {
                    zscoreContainer.classList.add('hidden');
                    nirvContainer.classList.remove('hidden');
                }, 100);
            })
            .catch(err => {
                console.error("그래프 로딩 오류:", err);
                alert("데이터를 불러오지 못했습니다.");

                // 에러 발생 시에도 컨테이너 상태 복원
                const nirvContainer = document.getElementById('nirv-container');
                const zscoreContainer = document.getElementById('zscore-container');
                zscoreContainer.classList.add('hidden');
                nirvContainer.classList.remove('hidden');
            });
    });

    // ========= 탭 전환 로직 =========
    const tabNirv = document.getElementById('tab-nirv');
    const tabZscore = document.getElementById('tab-zscore');
    const nirvContainer = document.getElementById('nirv-container');
    const zscoreContainer = document.getElementById('zscore-container');

    if (tabNirv && tabZscore) {
        tabNirv.addEventListener('click', () => {
            // NIRv 탭 활성화
            tabNirv.classList.add('border-blue-500', 'text-blue-500', 'font-semibold');
            tabNirv.classList.remove('border-transparent', 'text-gray-500');

            // Z-score 탭 비활성화
            tabZscore.classList.remove('border-blue-500', 'text-blue-500', 'font-semibold');
            tabZscore.classList.add('border-transparent', 'text-gray-500');

            // 컨테이너 표시/숨김
            nirvContainer.classList.remove('hidden');
            zscoreContainer.classList.add('hidden');

            // NIRv 그래프 크기 재조정
            setTimeout(() => {
                Plotly.Plots.resize(document.getElementById('nirv-plot'));
            }, 100);
        });

        tabZscore.addEventListener('click', () => {
            // Z-score 탭 활성화
            tabZscore.classList.add('border-blue-500', 'text-blue-500', 'font-semibold');
            tabZscore.classList.remove('border-transparent', 'text-gray-500');

            // NIRv 탭 비활성화
            tabNirv.classList.remove('border-blue-500', 'text-blue-500', 'font-semibold');
            tabNirv.classList.add('border-transparent', 'text-gray-500');

            // 컨테이너 표시/숨김
            zscoreContainer.classList.remove('hidden');
            nirvContainer.classList.add('hidden');

            // Z-score 그래프 크기 재조정
            setTimeout(() => {
                Plotly.Plots.resize(document.getElementById('zscore-plot'));
            }, 100);
        });
    }
});
