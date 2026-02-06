// static/js/climate_plot_logic.js

const cropSelect = document.getElementById('crop');
const yearSelect = document.getElementById('year');
const countrySelect = document.getElementById('country');
const stateSelect = document.getElementById('state');
const variableSelect = document.getElementById('variable');

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
    fetch(`/climate/api/options/?${query}`)
        .then(res => res.json())
        .then(data => callback(data))
        .catch(err => console.error('Option fetch error:', err));
}
function alignData(datesA, valuesA, datesB, valuesB) {
    const allDates = Array.from(new Set([...datesA, ...datesB])).sort(); // MM-DD 기준 정렬
    const mapA = Object.fromEntries(datesA.map((d, i) => [d, valuesA[i]]));
    const mapB = Object.fromEntries(datesB.map((d, i) => [d, valuesB[i]]));

    return {
        x: allDates,
        yA: allDates.map(d => mapA[d] ?? null),
        yB: allDates.map(d => mapB[d] ?? null)
    };
}
function tryFetchAndPlot() {
    const crop = cropSelect.value;
    const year = yearSelect.value;
    const country = countrySelect.value;
    const state = stateSelect.value;
    const variable = variableSelect.value;

    if (!crop || !year || !country || !state || !variable) return;

    const query = new URLSearchParams({ crop, year, country, state, variable }).toString();
    fetch(`/climate/api/data/?${query}`)
        .then(res => res.json())
        .then(data => {
            const currentDates = data.data.current.date.map(d => d.slice(5));
            const previousDates = data.data.previous.date.map(d => d.slice(5));

            const aligned = alignData(
                currentDates,
                data.data.current.value,
                previousDates,
                data.data.previous.value
            );

            Plotly.newPlot('climate-plot', [
                {
                    x: aligned.x,
                    y: aligned.yB,
                    mode: 'lines',
                    name: `${data.previous_year} ${data.variable.toUpperCase()}`,
                    line: { dash: 'dot' }
                },
                {
                    x: aligned.x,
                    y: aligned.yA,
                    mode: 'lines',
                    name: `${data.current_year} ${data.variable.toUpperCase()}`
                }
            ], {
                title: `${data.variable.toUpperCase()} 비교 (${data.previous_year} vs ${data.current_year})`,
                xaxis: { title: 'Month-Day (MM-DD)', type: 'category' },
                yaxis: { title: data.variable.toUpperCase() },
                legend: { orientation: 'h' }
            });
        })
        .catch(err => {
            console.error('Plot fetch error:', err);
            alert("데이터를 불러오는데 실패했습니다.");
        });
}


cropSelect.addEventListener('change', () => {
    fillOptions(yearSelect, []);
    fillOptions(countrySelect, []);
    fillOptions(stateSelect, []);
    fillOptions(variableSelect, []);
    if (cropSelect.value) {
        fetchOptions({ crop: cropSelect.value }, data => fillOptions(yearSelect, data.years));
    }
});

yearSelect.addEventListener('change', () => {
    fillOptions(countrySelect, []);
    fillOptions(stateSelect, []);
    fillOptions(variableSelect, []);
    if (cropSelect.value && yearSelect.value) {
        fetchOptions({ crop: cropSelect.value, year: yearSelect.value }, data => fillOptions(countrySelect, data.countries));
    }
});

countrySelect.addEventListener('change', () => {
    fillOptions(stateSelect, []);
    fillOptions(variableSelect, []);
    if (cropSelect.value && yearSelect.value && countrySelect.value) {
        fetchOptions({ crop: cropSelect.value, year: yearSelect.value, country: countrySelect.value }, data => fillOptions(stateSelect, data.states));
    }
});

stateSelect.addEventListener('change', () => {
    fillOptions(variableSelect, []);
    if (cropSelect.value && yearSelect.value && countrySelect.value && stateSelect.value) {
        fetchOptions({
            crop: cropSelect.value,
            year: yearSelect.value,
            country: countrySelect.value,
            state: stateSelect.value
        }, data => fillOptions(variableSelect, data.variables));
    }
});

variableSelect.addEventListener('change', () => {
    tryFetchAndPlot();
});