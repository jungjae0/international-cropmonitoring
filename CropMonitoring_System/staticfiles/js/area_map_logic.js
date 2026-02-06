let map, geojsonLayer;
let choroplethData = {};  // { state: { current, last, average } }
let unit = "acres";
let legendControl = null;

let percentMarkers = [];

function initMap(center = [39.8283, -98.5795], zoom = 3) {
    map = L.map("map").setView(center, zoom);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);
}

function getColor(value, min, max) {
    const ratio = (value - min) / (max - min || 1);
    if (ratio < 0.33) return "#ffffb2";
    if (ratio < 0.66) return "#78c679";
    return "#238443";
}

function normalizeStateName(name) {
    return name.replace(/_/g, "");
}

function styleFeature(feature) {
    const stateName = feature.properties.NAME_1;
    const matchedKey = Object.keys(choroplethData).find(
        k => normalizeStateName(k) === stateName
    );
    const data = matchedKey ? choroplethData[matchedKey] : null;
    const current = data?.current ?? 0;

    const values = Object.values(choroplethData)
        .map(d => d.current ?? 0)
        .filter(v => v > 0);
    const min = Math.min(...values);
    const max = Math.max(...values);

    if (current <= 0) {
        return {
            fillColor: "#cdcdcd",
            color: "#000000",
            weight: 0.5,
            fillOpacity: 0.3,
            opacity: 1
        };
    }

    return {
        fillColor: getColor(current, min, max),
        color: "blue",
        weight: 2,
        fillOpacity: 0.6,
        opacity: 1
    };
}

function renderGeoLayer(geojson) {
    if (geojsonLayer) geojsonLayer.remove();

    geojsonLayer = L.geoJson(geojson, {
        style: styleFeature,
        onEachFeature: (feature, layer) => {
            const name = feature.properties.NAME_1;
            const data = choroplethData[name];
            if (data) {
                const convert = unit === "hectares" ? v => v * 0.4047 : v => v;
                const suffix = unit === "hectares" ? "ha" : "acres";
                const html = `
          <strong>${name}</strong><br>
          평년: ${convert(data.average ?? 0).toLocaleString()} ${suffix}<br>
          전년: ${convert(data.last ?? 0).toLocaleString()} ${suffix}<br>
          올해: ${convert(data.current ?? 0).toLocaleString()} ${suffix}
        `;
                layer.bindPopup(html);
            }
        }
    }).addTo(map);
}

function addLegend(min, max) {
    if (legendControl) {
        legendControl.remove();
        legendControl = null;
    }

    const thresholds = [
        {min: min, max: min + (max - min) / 3, color: "#c7f0a3"},
        {min: min + (max - min) / 3, max: min + (max - min) * 2 / 3, color: "#41b84d"},
        {min: min + (max - min) * 2 / 3, max: max, color: "#005a32"}
    ];

    legendControl = L.control({position: "bottomright"});

    legendControl.onAdd = function () {
        const div = L.DomUtil.create("div", "info legend");
        div.style.background = "white";
        div.style.padding = "8px";
        div.style.borderRadius = "6px";
        div.style.boxShadow = "0 0 4px rgba(0,0,0,0.3)";
        div.style.fontSize = "13px";

        // ✅ 제목 추가
        div.innerHTML += `<div style="font-weight:bold; margin-bottom:6px;">재배 면적 범위(acre)</div>`;

        thresholds.forEach(entry => {
            div.innerHTML += `
        <div style="display:flex; align-items:center; margin-bottom:4px;">
          <div style="width:20px; height:20px; background:${entry.color}; border:1px solid #aaa; margin-right:6px;"></div>
          <span>${Math.round(entry.min).toLocaleString()} – ${Math.round(entry.max).toLocaleString()}</span>
        </div>
      `;
        });

        return div;
    };

    legendControl.addTo(map);
}

function renderStateLabels(data) {
    // 기존 마커 제거
    percentMarkers.forEach(m => m.remove());
    percentMarkers = [];

    Object.entries(data).forEach(([state, d]) => {
        const percent = d.percent ?? 0;
        const lat = d.center_lat;
        const lng = d.center_lng;

        if (lat !== undefined && lng !== undefined && percent > 0) {
            const label = `${state}<br>${percent.toFixed(1)}%`;

            const marker = L.marker([lat, lng], {
                icon: L.divIcon({
                    className: "label-icon",
                    html: `<div style="
              font-weight:bold;
              font-size:13px;
              color:#fff;
              text-shadow: 1px 1px 2px black;
              text-align:center;
          ">${label}</div>`,
                    iconSize: [100, 40],
                    iconAnchor: [50, 20]
                })
            });

            marker.addTo(map);
            percentMarkers.push(marker);
        }
    });
}


function renderBarChart(data) {
    const convert = unit === "hectares" ? v => v * 0.4047 : v => v;
    const suffix = unit === "hectares" ? "ha" : "acres";

    const sorted = Object.entries(data)
        .filter(([_, d]) => (d.current ?? 0) > 0 || (d.last ?? 0) > 0 || (d.average ?? 0) > 0)
        .map(([state, d]) => ({
            state,
            current: d.current ?? 0,
            last: d.last ?? 0,
            average: d.average ?? 0
        }))
        .sort((a, b) => b.current - a.current);

    const x = sorted.map(d => d.state);
    const yCurrent = sorted.map(d => convert(d.current));
    const yLast = sorted.map(d => convert(d.last));
    const yAvg = sorted.map(d => convert(d.average));

    const traces = [
        {
            name: "평년",
            x,
            y: yAvg,
            type: "bar",
            marker: {color: "gray"}
        },
        {
            name: "전년도",
            x,
            y: yLast,
            type: "bar",
            marker: {color: "orange"}
        },
        {
            name: "올해",
            x,
            y: yCurrent,
            type: "bar",
            marker: {color: "blue"}
        }
    ];

    Plotly.newPlot("area-bar", traces, {
        barmode: "group",
        title: "주별 재배 면적 비교",
        yaxis: {title: `면적 (${suffix})`},
        margin: {t: 40}
    });
}


function renderAreaTable(data) {
    const convert = unit === "hectares" ? v => v * 0.4047 : v => v;
    const suffix = unit === "hectares" ? "ha" : "acres";
    const tbody = document.querySelector("#area-table tbody");
    tbody.innerHTML = "";

    Object.entries(data)
        .filter(([_, d]) => (d.current ?? 0) > 0 || (d.last ?? 0) > 0 || (d.average ?? 0) > 0)
        .sort((a, b) => b[1].current - a[1].current)
        .forEach(([state, d]) => {
            const avg = convert(d.average ?? 0);
            const last = convert(d.last ?? 0);
            const current = convert(d.current ?? 0);

            let diffPercent = last > 0 ? ((current - last) / last) * 100 : 0;
            const triangle = diffPercent > 0
                ? `<span style="color:red;">▲</span>`
                : (diffPercent < 0 ? `<span style="color:blue;">▼</span>` : '');

            const row = document.createElement("tr");
            row.innerHTML = `
                <td class="border p-2">${state}</td>
                <td class="border p-2">${avg.toLocaleString(undefined, {maximumFractionDigits: 1})}</td>
                <td class="border p-2">${last.toLocaleString(undefined, {maximumFractionDigits: 1})}</td>
                <td class="border p-2">${current.toLocaleString(undefined, {maximumFractionDigits: 1})}</td>
                <td class="border p-2">${triangle} ${Math.abs(diffPercent).toFixed(1)}%</td>
            `;
            tbody.appendChild(row);
        });
}


function fetchAndRenderMap(crop, year, country) {
    safeFetchJson(`/area/api/choropleth/?crop=${crop}&year=${year}&country=${country}`)
        .then(data => {
            data = sanitizeObject(data);

            if (!data || !data.area_by_state) {
                console.error("Invalid data received:", data);
                alert("데이터를 불러오는데 실패했습니다. 관리자에게 문의하세요.");
                return;
            }

            choroplethData = Object.fromEntries(
                Object.entries(data.area_by_state).filter(([_, d]) =>
                    (d.current ?? 0) > 0 || (d.last ?? 0) > 0 || (d.average ?? 0) > 0
                )
            );

            // map.setView([data.center_lat, data.center_lng], 4);

            map.setView([39.8283, -98.5795] , 4.5);

            // 서버가 boundary_geojson을 바로 내려주면 그 값을 사용하고,
            // 없으면 boundary_url 또는 /media 경로로 폴백
            const boundaryPromise = data.boundary_geojson
                ? Promise.resolve(data.boundary_geojson)
                : fetch(data.boundary_url || `/media/${country}/Layers/${country}_states.json`).then(res => {
                    if (!res.ok) throw new Error(`boundary fetch failed: ${res.status}`);
                    return res.json();
                });

            boundaryPromise
                .then(json => {
                    renderGeoLayer(json);
                    const currentValues = Object.values(choroplethData)
                        .map(d => d.current ?? 0)
                        .filter(v => v > 0);
                    if (currentValues.length > 0) {
                        addLegend(Math.min(...currentValues), Math.max(...currentValues));
                    }
                })
                .catch(err => {
                    console.error("boundary load error", err);
                    alert("경계 GeoJSON을 불러오지 못했습니다. /media 경로에 파일이 있는지 확인하세요.");
                });

            renderBarChart(choroplethData);
            renderAreaTable(choroplethData);
            renderStateLabels(choroplethData);
        })
        .catch(err => {
            console.error("❌ Area map load error:", err);
            alert(`데이터 로딩 실패: ${err.message}\n브라우저 콘솔을 확인하세요.`);
        });
}


document.addEventListener("DOMContentLoaded", () => {
    initMap();

    function loadYearsAndRender() {
        const crop = document.getElementById("crop").value;
        const country = document.getElementById("country").value;

        safeFetchJson(`/area/api/available-years/?crop=${crop}&country=${country}`)
            .then(data => {
                data = sanitizeObject(data);
                const yearSel = document.getElementById("year");
                yearSel.innerHTML = "";

                const years = data.years && data.years.length ? data.years : [];
                if (years.length === 0) {
                    return;
                }

                years.forEach(y => {
                    const opt = document.createElement("option");
                    opt.value = y;
                    opt.textContent = y;
                    yearSel.appendChild(opt);
                });

                yearSel.value = years[0];

                fetchAndRenderMap(crop, yearSel.value, country);
                fetchAndRenderNIRV(crop, yearSel.value);
            })
            .catch(err => {
                console.error("연도 불러오기 실패", err);
            });
    }

    document.getElementById("map-update-btn").addEventListener("click", () => {
        const crop = document.getElementById("crop").value;
        const year = document.getElementById("year").value;
        const country = document.getElementById("country").value;

        if (!crop || !year || !country) {
            alert("모든 항목을 선택해주세요.");
            return;
        }

        // 🗺️ 기존 지도 + 막대그래프 렌더
        fetchAndRenderMap(crop, year, country);

        // 🌱 NIRv 다중 시계열 추가 호출
        fetchAndRenderNIRV(crop, year);
    });

    document.querySelectorAll("input[name='unit']").forEach(radio => {
        radio.addEventListener("change", () => {
            unit = document.querySelector("input[name='unit']:checked").value;
            renderGeoLayer(geojsonLayer.toGeoJSON());
            renderBarChart(choroplethData);
        });
    });

    // ✅ crop 변경 시 가능한 연도만 갱신
    document.getElementById("crop").addEventListener("change", () => {
        const crop = document.getElementById("crop").value;
        const country = document.getElementById("country").value;
        if (!crop || !country) return;

        safeFetchJson(`/area/api/available-years/?crop=${crop}&country=${country}`)
            .then(data => {
                data = sanitizeObject(data);
                const yearSel = document.getElementById("year");
                yearSel.innerHTML = "";
                data.years.forEach(y => {
                    const opt = document.createElement("option");
                    opt.value = y;
                    opt.textContent = y;
                    yearSel.appendChild(opt);
                });
            });
    });

    // 최초 진입 시 최신 연도로 자동 렌더링
    loadYearsAndRender();
});
