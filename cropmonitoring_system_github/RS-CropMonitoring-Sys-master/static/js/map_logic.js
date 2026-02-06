document.addEventListener("DOMContentLoaded", () => {
  const cropSelect = document.getElementById("crop");
  const yearSelect = document.getElementById("year");
  const countrySelect = document.getElementById("country");
  const stateSelect = document.getElementById("state");

  const tileLayers = [];
  let tileLayersData = [];
  let currentCountryCenter = null;

  window.map = L.map("map").setView([20, 0], 3, {maxZoom: 12});
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 12,
    attribution: "© OpenStreetMap contributors"
  }).addTo(map);

  // ✅ 범례 컨트롤 추가
  const legend = L.control({ position: "bottomleft" });
  legend.onAdd = function () {
    const div = L.DomUtil.create("div", "info legend");
    div.id = "map-legend";
    div.innerHTML = "";
    return div;
  };
  legend.addTo(map);

  function updateLegend(crop) {
    const div = document.getElementById("map-legend");
    if (!div) return;

    const legends = {
      Wheat: [
        { label: "Spring Wheat", color: "#e63946" },
        { label: "Winter Wheat", color: "#235cff" }
      ],
      Soybean: [
        { label: "Soybean", color: "#04bc00" }
      ],
      Corn: [
        { label: "Corn", color: "#f4a261" }
      ]
    };

    if (!legends[crop]) {
      div.innerHTML = "";
      return;
    }

    const html = legends[crop]
      .map(item =>
        `<div><span style="display:inline-block;width:12px;height:12px;background:${item.color};margin-right:6px;border-radius:2px;"></span>${item.label}</div>`
      )
      .join("");

    div.innerHTML = `<strong>${crop}</strong><br>${html}`;
  }

  function fetchAndPopulate(url, selectElement, dataKey) {
    fetch(url)
      .then(res => res.json())
      .then(data => {
        selectElement.innerHTML = "";
        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.text = "Select " + dataKey;
        selectElement.add(defaultOption);

        if (data[dataKey]) {
          data[dataKey].forEach(item => {
            const opt = document.createElement("option");
            opt.value = item;
            opt.text = item;
            selectElement.add(opt);
          });
        }
      })
      .catch(err => console.error("Fetch error:", err));
  }

  cropSelect.addEventListener("change", () => {
    fetchAndPopulate(`/maps/api/options/?crop=${cropSelect.value}`, yearSelect, "years");
    countrySelect.innerHTML = '<option value="">Select Country</option>';
    stateSelect.innerHTML = '<option value="전체">전체</option>';

    // ✅ 범례 갱신
    updateLegend(cropSelect.value);
  });

  yearSelect.addEventListener("change", () => {
    fetchAndPopulate(`/maps/api/options/?crop=${cropSelect.value}&year=${yearSelect.value}`, countrySelect, "countries");
    stateSelect.innerHTML = '<option value="전체">전체</option>';
  });

  countrySelect.addEventListener("change", () => {
    const url = `/maps/api/country-zoom/?crop=${cropSelect.value}&year=${yearSelect.value}&country=${countrySelect.value}`;
    fetch(url)
      .then(res => res.json())
      .then(data => {
        currentCountryCenter = data.country_center;
        map.setView([currentCountryCenter.lat, currentCountryCenter.lng], 5);

        tileLayers.forEach(layer => map.removeLayer(layer));
        tileLayers.length = 0;
        tileLayersData = data.tiles;

        data.tiles.forEach(t => {
          const layer = L.tileLayer(t.tile_url, { maxZoom: 13, opacity: 1, tms: true });
          layer.addTo(map);
          tileLayers.push(layer);
        });

        stateSelect.innerHTML = '<option value="전체">전체</option>';
        data.tiles.forEach(t => {
          const opt = document.createElement("option");
          opt.value = t.state;
          opt.text = t.state;
          stateSelect.add(opt);
        });
        fetchAreaSummary(cropSelect.value, yearSelect.value, countrySelect.value, "전체");
      });
  });

  stateSelect.addEventListener("change", () => {
    const selectedState = stateSelect.value;

    if (selectedState === "전체" || selectedState === "") {
      if (currentCountryCenter) {
        map.setView([currentCountryCenter.lat, currentCountryCenter.lng], 5);
      }
    } else {
      const selected = tileLayersData.find(t => t.state === selectedState);
      if (selected) {
        map.setView([selected.center_lat, selected.center_lng], 6);
      }
    }

    const crop = cropSelect.value;
    const year = yearSelect.value;
    const country = countrySelect.value;
    if (crop && year && country) {
      fetchAreaSummary(crop, year, country, selectedState);
    }
  });
});
