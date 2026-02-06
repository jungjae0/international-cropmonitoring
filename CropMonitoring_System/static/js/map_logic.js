// map_logic.js

document.addEventListener("DOMContentLoaded", () => {
  const cropSelect    = document.getElementById("crop");
  const yearSelect    = document.getElementById("year");
  const countrySelect = document.getElementById("country");
  const stateSelect   = document.getElementById("state");
  const variantSelect = document.getElementById("variant");

  const tileLayers         = [];
  let tileLayersData       = [];
  let currentCountryCenter = null;

  window.map = L.map("map").setView([20, 0], 3, { maxZoom: 12 });
// ✅ 기본 배경지도 정의
const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '© OpenStreetMap contributors'
});

const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
  maxZoom: 19,
  attribution: 'Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye'
});

// ✅ 배경 지도 선택 메뉴 추가
const baseMaps = {
  "OpenStreetMap": osm,
  "Satellite": satellite
};

osm.addTo(map);  // 기본 지도 추가

L.control.layers(baseMaps, null, { position: 'topright', collapsed: false }).addTo(map);
const legend = L.control({ position: "bottomleft" });


function updateLegend(crop) {
  const div = document.getElementById("map-legend");
  if (!div) return;

  const legends = {
    Wheat: [
      { label: "Spring Wheat", color: "#e63946", value: "봄밀" },
      { label: "Winter Wheat", color: "#235cff", value: "겨울밀" }
    ],
    Soybean: [
      { label: "Soybean", color: "#04bc00", value: "대두" }
    ],
    Corn: [
      { label: "Corn", color: "#f4a261", value: "옥수수" }
    ]
  };

  const items = legends[crop] || [];
  div.innerHTML = items.map(item => `
    <div style="display: flex; align-items: center; margin-bottom: 4px;">
      <span style="width: 14px; height: 14px; background-color: ${item.color}; display: inline-block; margin-right: 8px; border: 1px solid #666;"></span>
      ${item.label} (${item.value})
    </div>
  `).join("");
}

  function fetchAndPopulate(url, selectEl, key, placeholder) {
    safeFetchJson(url)
      .then(json => {
        json = sanitizeObject(json);
        selectEl.innerHTML = "";
        const ph = document.createElement("option");
        ph.value = "";
        ph.text  = placeholder;
        selectEl.add(ph);
        (json[key] || []).forEach(v => {
          const o = document.createElement("option");
          o.value = v;
          o.text  = v;
          selectEl.add(o);
        });
        if (selectEl === variantSelect) {
          variantSelect.dispatchEvent(new Event("change"));
        }
      })
      .catch(e => console.error(`${key} load error:`, e));
  }

  cropSelect.addEventListener("change", () => {
    const crop = cropSelect.value;
    fetchAndPopulate(`/maps/api/options/?crop=${crop}`, yearSelect, "years", "Select Year");
    countrySelect.innerHTML = `<option value="">Select Country</option>`;
    stateSelect.innerHTML   = `<option value="">전체</option>`;
    variantSelect.innerHTML = `<option value="">전체</option>`;
    variantSelect.style.display = crop === "Wheat" ? "inline-block" : "none";
    updateLegend(crop);
  });

  yearSelect.addEventListener("change", () => {
    const crop = cropSelect.value, year = yearSelect.value;
    fetchAndPopulate(`/maps/api/options/?crop=${crop}&year=${year}`, countrySelect, "countries", "Select Country");
    stateSelect.innerHTML   = `<option value="">전체</option>`;
    variantSelect.innerHTML = `<option value="">전체</option>`;
  });

  countrySelect.addEventListener("change", () => {
    const crop = cropSelect.value;
    const year = yearSelect.value;
    const country = countrySelect.value;

    fetchAndPopulate(`/maps/api/options/?crop=${crop}&year=${year}&country=${country}`, stateSelect, "states", "전체");

    if (crop === "Wheat") {
      variantSelect.style.display = "inline-block";
      setTimeout(() => {
        const state = "";  // 전체
        fetchAndPopulate(
          `/maps/api/options/?crop=${crop}&year=${year}&country=${country}&state=${state}`,
          variantSelect,
          "variants",
          "전체"
        );
      }, 300);
    } else {
      variantSelect.innerHTML = `<option value="">(Not Applicable)</option>`;
      variantSelect.style.display = "none";
    }
  });

  stateSelect.addEventListener("change", () => {
    const crop    = cropSelect.value;
    const year    = yearSelect.value;
    const country = countrySelect.value;
    const state   = stateSelect.value === "전체" ? "" : stateSelect.value;

    if (crop === "Wheat") {
      fetchAndPopulate(
        `/maps/api/options/?crop=${crop}&year=${year}&country=${country}&state=${state}`,
        variantSelect,
        "variants",
        "전체"
      );
    } else {
      variantSelect.innerHTML = `<option value="">(Not Applicable)</option>`;
      variantSelect.style.display = "none";
    }
  });

  variantSelect.addEventListener("change", () => {
    const crop    = cropSelect.value;
    const year    = yearSelect.value;
    const country = countrySelect.value;
    const state   = stateSelect.value === "전체" ? "" : stateSelect.value;
    const variant = variantSelect.value || "";

    tileLayers.forEach(l => map.removeLayer(l));
    tileLayers.length = 0;

    safeFetchJson(`/maps/api/country-zoom/?crop=${crop}&year=${year}&country=${country}&variant=${variant}`)
      .then(json => {
        json = sanitizeObject(json);
        currentCountryCenter = json.country_center;
        tileLayersData = json.tiles;
        json.tiles.forEach(t => {
          const layer = L.tileLayer(t.tile_url, { maxZoom: 13, opacity: 1, tms: true   ,zIndex: 500  // ✅ 배경보다 위에 오도록 설정
});
          layer.addTo(map);
          tileLayers.push(layer);

        });
          // ✅ 여기에 국가 중심으로 줌 인 추가
  if (currentCountryCenter) {
    map.setView([currentCountryCenter.lat, currentCountryCenter.lng], 6);
  }

        // stateSelect 유지
        const currentState = stateSelect.value;
        stateSelect.innerHTML = `<option value="">전체</option>`;
        json.states.forEach(s => {
          const opt = document.createElement("option");
          opt.value = s;
          opt.text  = s;
          stateSelect.add(opt);
          if (s === currentState) opt.selected = true;
        });

        fetchAreaSummary(crop, year, country, state, variant);
      })
      .catch(err => console.error("Tile load failed:", err));
  });


  legend.onAdd = function (map) {
  const div = L.DomUtil.create('div', 'info legend');
  div.innerHTML = `
    <div id="map-legend" style="
      padding: 6px 10px;
      background: white;
      border: 1px solid #ccc;
      border-radius: 5px;
      font-size: 14px;
      box-shadow: 0 0 5px rgba(0,0,0,0.3);
    ">
      <!-- legend content will be inserted here -->
    </div>
  `;
  return div;
};

legend.addTo(map);

});
