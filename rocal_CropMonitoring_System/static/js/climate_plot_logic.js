const cropSelect = document.getElementById('crop');
const yearSelect = document.getElementById('year');
const countrySelect = document.getElementById('country');
const stateSelect = document.getElementById('state');
const variantSelect = document.getElementById('variant');
const modeSelect = document.getElementById('mode');
const variableGroupSelect = document.getElementById('variable-group');
const plotDiv = document.getElementById('climate-plot');

const tempVars = ['tmmx_daily', 'tmmn_daily', 'tmean_daily'];
const prVars = ['pr_daily', 'pr_cumul'];

function fillOptions(selectElement, options) {
    selectElement.innerHTML = '<option value="">Select</option>';
    options.forEach(option => {
        const opt = document.createElement('option');
        opt.value = option;
        opt.textContent = option;
        selectElement.appendChild(opt);
    });
}

function fetchOptions(params, callback) {
    const query = new URLSearchParams(params).toString();
    safeFetchJson(`/climate/api/options/?${query}`)
        .then(data => {
            data = sanitizeObject(data);
            callback(data);
        })
        .catch(err => console.error('Option fetch error:', err));
}

function clearSelects(...selects) {
    selects.forEach(select => select.innerHTML = '<option value="">Select</option>');
}
function plotTemperatureGraph(dataGroup, variable) {
    const traces = [];

    // 🔧 'tmmx_daily' → 'tmmx'
    const shortVar = variable.replace('_daily', '');

    console.log('plotTemperatureGraph', dataGroup, variable);

    ['average', 'previous', 'current'].forEach((key, idx) => {
        const data = dataGroup[key];
        if (!data.date || !data[`${shortVar}mean`]) return;

        traces.push({
            x: data.date,
            y: data[`${shortVar}_mean`],
            mode: 'lines',
            name: `${key} ${shortVar}mean`.toUpperCase(),
            line: { color: ['black', 'gold', 'red'][idx] }
        });

        if (key === 'current') {
            traces.push({
                x: data.date,
                y: data[`${shortVar}_min`],
                mode: 'lines',
                line: { width: 0 },
                showlegend: false
            });
            traces.push({
                x: data.date,
                y: data[`${shortVar}_max`],
                fill: 'tonexty',
                fillcolor: 'rgba(173,216,230,0.5)',
                mode: 'lines',
                name: `${shortVar} 범위`
            });
        }
    });

    Plotly.newPlot(plotDiv, traces, {
        title: {
            text: `${variable.toUpperCase()} 비교`,
            font: { size: 18, weight: 'bold' }
        },
        xaxis: {
            title: 'Month-Day (MM-DD)',
            type: 'category',
            gridcolor: '#e5e7eb'
        },
        yaxis: {
            title: shortVar.toUpperCase(),
            gridcolor: '#e5e7eb'
        },
        legend: {
            orientation: 'h',
            x: 0.5,
            xanchor: 'center',
            y: -0.15
        },
        margin: { t: 60, b: 80, l: 60, r: 40 },
        plot_bgcolor: '#fafafa',
        paper_bgcolor: 'white'
    }, { responsive: true });
}

function plotSimpleLine(dataGroup, variable) {
    const currentDates = dataGroup.current.date.map(d => d.slice(5));
    const previousDates = dataGroup.previous.date.map(d => d.slice(5));

    const allDates = Array.from(new Set([...currentDates, ...previousDates])).sort();
    const mapA = Object.fromEntries(currentDates.map((d, i) => [d, dataGroup.current.value[i]]));
    const mapB = Object.fromEntries(previousDates.map((d, i) => [d, dataGroup.previous.value[i]]));

    Plotly.newPlot(plotDiv, [
        {
            x: allDates,
            y: allDates.map(d => mapB[d] ?? null),
            mode: 'lines',
            name: `Previous`,
            line: { dash: 'dot', width: 2, color: '#fbbf24' }
        },
        {
            x: allDates,
            y: allDates.map(d => mapA[d] ?? null),
            mode: 'lines',
            name: `Current`,
            line: { width: 3, color: '#3b82f6' }
        }
    ], {
        title: {
            text: `${variable.toUpperCase()} 비교`,
            font: { size: 18, weight: 'bold' }
        },
        xaxis: {
            title: 'Month-Day (MM-DD)',
            type: 'category',
            gridcolor: '#e5e7eb'
        },
        yaxis: {
            title: variable.toUpperCase(),
            gridcolor: '#e5e7eb'
        },
        legend: {
            orientation: 'h',
            x: 0.5,
            xanchor: 'center',
            y: -0.15
        },
        margin: { t: 60, b: 80, l: 60, r: 40 },
        plot_bgcolor: '#fafafa',
        paper_bgcolor: 'white'
    }, { responsive: true });
}

function tryFetchAndPlot() {
    const crop = cropSelect.value;
    const year = yearSelect.value;
    const country = countrySelect.value;
    const state = stateSelect.value;
    const variant = variantSelect.value;
    const mode = modeSelect.value;
    const variableGroup = variableGroupSelect.value;

    if (!crop || !year || !country || !state || !variableGroup) return;

    const variables = variableGroup === 'pr' ? prVars : tempVars;
    plotDiv.innerHTML = '';

if ((mode === 'static') && (variableGroup === 'temp' || variableGroup === 'pr')) {
    const container = document.createElement('div');
    container.style.display = 'flex';
    container.style.flexDirection = 'column';  // ✅ 세로 정렬
    container.style.alignItems = 'center';     // ✅ 가운데 정렬
    container.style.gap = '20px';

        const varTitles = {
            tmmx_daily: '최고기온',
            tmmn_daily: '최저기온',
            tmean_daily: '평균기온'
        };

        variables.forEach(variable => {
            const params = { crop, year, country, state, variable, mode };
            if (crop === 'Wheat') params.variant = variant;

            safeFetchJson(`/climate/api/data/?${new URLSearchParams(params).toString()}`)
                .then(data => {
                    data = sanitizeObject(data);
                    if (data.image_url) {
                        const block = document.createElement('div');
                        block.style.textAlign = 'center';

                        const title = document.createElement('div');
                        title.textContent = varTitles[variable] || variable;
                        title.style.fontWeight = 'bold';
                        title.style.marginBottom = '5px';

                        const img = document.createElement('img');
                        img.src = data.image_url;
                        img.alt = variable;
                        img.style.maxWidth = '800px';

                        block.appendChild(title);
                        block.appendChild(img);
                        container.appendChild(block);
                    }
                });
        });

        plotDiv.appendChild(container);
    } else {
        // 기존 동적 그래프 또는 강수량 이미지 처리
        variables.forEach(variable => {
            const params = { crop, year, country, state, variable, mode };
            if (crop === 'Wheat') params.variant = variant;

            safeFetchJson(`/climate/api/data/?${new URLSearchParams(params).toString()}`)
                .then(data => {
                    data = sanitizeObject(data);
                    if (mode === 'static' && data.image_url) {
                        const img = document.createElement('img');
                        img.src = data.image_url;
                        img.style.maxWidth = '100%';
                        img.style.marginBottom = '20px';
                        plotDiv.appendChild(img);
                    } else if (mode === 'dynamic') {
                        if (variableGroup === 'temp') {
                            plotTemperatureGraph(data.data, variable);
                        } else {
                            plotSimpleLine(data.data, variable);
                        }
                    }
                })
                .catch(err => {
                    console.error('Plot fetch error:', err);
                    alert("데이터를 불러오는데 실패했습니다.");
                });
        });
    }
}

// ========= 이벤트 등록 =========

cropSelect.addEventListener('change', () => {
    clearSelects(yearSelect, countrySelect, stateSelect);
    fillOptions(variantSelect, ['SpringWheat', 'WinterWheat']);
    variantSelect.style.display = 'none';
    document.querySelector('label[for="variant"]').style.display = 'none';

    if (cropSelect.value) {
        fetchOptions({ crop: cropSelect.value }, data => fillOptions(yearSelect, data.years));
    }
});

yearSelect.addEventListener('change', () => {
    clearSelects(countrySelect, stateSelect);
    if (cropSelect.value && yearSelect.value) {
        fetchOptions({ crop: cropSelect.value, year: yearSelect.value }, data => fillOptions(countrySelect, data.countries));
    }
});

countrySelect.addEventListener('change', () => {
    clearSelects(stateSelect);
    if (cropSelect.value && yearSelect.value && countrySelect.value) {
        fetchOptions({
            crop: cropSelect.value,
            year: yearSelect.value,
            country: countrySelect.value
        }, data => fillOptions(stateSelect, data.states));
    }
});

stateSelect.addEventListener('change', () => {
    if (!cropSelect.value || !yearSelect.value || !countrySelect.value || !stateSelect.value) return;

    fetchOptions({
        crop: cropSelect.value,
        year: yearSelect.value,
        country: countrySelect.value,
        state: stateSelect.value
    }, data => {
        if (cropSelect.value === 'Wheat') {
            if (data.variants && data.variants.length > 0) {
                fillOptions(variantSelect, data.variants);
                variantSelect.style.display = 'inline-block';
                document.querySelector('label[for="variant"]').style.display = 'inline-block';
            } else {
                variantSelect.style.display = 'none';
                document.querySelector('label[for="variant"]').style.display = 'none';
            }
        }
        tryFetchAndPlot();
    });
});

variantSelect.addEventListener('change', tryFetchAndPlot);
modeSelect.addEventListener('change', tryFetchAndPlot);
variableGroupSelect.addEventListener('change', tryFetchAndPlot);

// ========= 탭 전환 로직 =========
document.addEventListener('DOMContentLoaded', () => {
    const tabTimeseries = document.getElementById('tab-timeseries');
    const tabZscore = document.getElementById('tab-zscore');
    const timeseriesContainer = document.getElementById('timeseries-container');
    const zscoreContainer = document.getElementById('zscore-container');

    if (tabTimeseries && tabZscore) {
        tabTimeseries.addEventListener('click', () => {
            // 시계열 탭 활성화
            tabTimeseries.classList.add('border-blue-500', 'text-blue-500', 'font-semibold');
            tabTimeseries.classList.remove('border-transparent', 'text-gray-500');

            // Z-score 탭 비활성화
            tabZscore.classList.remove('border-blue-500', 'text-blue-500', 'font-semibold');
            tabZscore.classList.add('border-transparent', 'text-gray-500');

            // 컨테이너 표시/숨김
            timeseriesContainer.classList.remove('hidden');
            zscoreContainer.classList.add('hidden');
        });

        tabZscore.addEventListener('click', () => {
            // Z-score 탭 활성화
            tabZscore.classList.add('border-blue-500', 'text-blue-500', 'font-semibold');
            tabZscore.classList.remove('border-transparent', 'text-gray-500');

            // 시계열 탭 비활성화
            tabTimeseries.classList.remove('border-blue-500', 'text-blue-500', 'font-semibold');
            tabTimeseries.classList.add('border-transparent', 'text-gray-500');

            // 컨테이너 표시/숨김
            zscoreContainer.classList.remove('hidden');
            timeseriesContainer.classList.add('hidden');
        });
    }
});
