// boundary_logic.js

let countryBoundaryLayer = null;
let stateHighlightLayer = null;

const baseStyle = {
  color: "#666",
  weight: 1,
  fill: false
};

const highlightStyle = {
  color: "#e63946",
  weight: 3,
  fill: false
};

// 국가 선택 시 전체 경계 표시
document.getElementById("country").addEventListener("change", () => {
  const country = document.getElementById("country").value;
  if (!country) return;

  safeFetchJson(`/maps/api/boundaries/?country=${country}`)
    .then(data => {
      data = sanitizeObject(data);
      return fetch(data.geojson_url);
    })
    .then(res => res.json())
    .then(geojson => {
      console.log("국가 geojson:", geojson);

      if (!geojson || geojson.type !== "FeatureCollection" || !Array.isArray(geojson.features)) {
        console.error("유효하지 않은 GeoJSON 형식입니다.");
        return;
      }

      if (countryBoundaryLayer) {
        map.removeLayer(countryBoundaryLayer);
      }

      const layer = L.geoJSON(geojson, { style: baseStyle });
      layer.addTo(map);
      map.fitBounds(layer.getBounds());
      countryBoundaryLayer = layer;

      if (stateHighlightLayer) {
        map.removeLayer(stateHighlightLayer);
        stateHighlightLayer = null;
      }
    })
    .catch(err => console.error("국가 경계 로딩 실패:", err));
});

// 주(state) 선택 시 해당 주 강조 표시
document.getElementById("state").addEventListener("change", () => {
  const state = document.getElementById("state").value;
  const country = document.getElementById("country").value;

  if (stateHighlightLayer) {
    map.removeLayer(stateHighlightLayer);
    stateHighlightLayer = null;
  }

  if (state === "전체" || !state) return;

  safeFetchJson(`/maps/api/state-boundary/?country=${country}&state=${state}`)
    .then(data => {
      data = sanitizeObject(data);
      return fetch(data.geojson_url);
    })
    .then(res => res.json())
    .then(geojson => {
      console.log("주별 geojson:", geojson);

      if (!geojson || geojson.type !== "FeatureCollection" || !Array.isArray(geojson.features)) {
        console.error("유효하지 않은 GeoJSON 형식입니다.");
        return;
      }

      const feature = geojson.features.find(f =>
        f.properties && f.properties.NAME_1 === state
      );

      if (feature) {
        const layer = L.geoJSON(feature, { style: highlightStyle });
        layer.addTo(map);
        map.fitBounds(layer.getBounds());
        stateHighlightLayer = layer;
      } else {
        console.warn(`${state} 경계를 GeoJSON에서 찾을 수 없습니다.`);
      }
    })
    .catch(err => console.error("주 경계 로딩 실패:", err));
});