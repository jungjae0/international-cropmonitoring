// 주요 작황 정보 차트 데이터
// TODO: 실제 데이터 매핑 필요
const temperature = {
  미국: [0, 2, 7, 13, 18, 23, 26, 25, 20, 14, 8, 2],
  우크라이나: [-5, -3, 2, 10, 16, 20, 22, 21, 15, 9, 3, -2],
  호주: [24, 25, 23, 20, 17, 15, 13, 14, 16, 18, 20, 23],
  브라질: [26, 26, 25, 24, 23, 22, 22, 23, 24, 25, 26, 26],
  아르헨티나: [23, 24, 22, 18, 15, 12, 11, 12, 14, 17, 20, 22],
};
const rainfall = {
  미국: [60, 55, 70, 80, 95, 100, 95, 90, 85, 75, 65, 60],
  우크라이나: [45, 40, 50, 55, 70, 85, 90, 80, 65, 55, 50, 45],
  호주: [30, 28, 35, 40, 50, 60, 65, 60, 50, 45, 40, 35],
  브라질: [250, 230, 210, 150, 90, 50, 40, 45, 60, 130, 200, 240],
  아르헨티나: [110, 100, 90, 75, 60, 50, 45, 50, 65, 85, 100, 120],
};
const solar = {
  미국: [2.0, 3.0, 4.2, 5.1, 6.0, 6.8, 7.2, 6.9, 5.9, 4.3, 2.8, 2.1],
  우크라이나: [1.2, 2.1, 3.5, 4.8, 5.5, 6.2, 6.6, 6.1, 4.7, 3.2, 1.8, 1.1],
  호주: [7.8, 7.5, 6.8, 5.3, 4.3, 3.4, 3.0, 3.2, 4.1, 5.2, 6.5, 7.6],
  브라질: [5.5, 5.4, 5.3, 5.0, 4.8, 4.6, 4.7, 4.9, 5.1, 5.3, 5.4, 5.5],
  아르헨티나: [7.2, 6.9, 6.0, 5.1, 4.0, 3.0, 2.8, 3.1, 4.2, 5.3, 6.3, 7.0],
};

const base = {
  temperature,
  rainfall,
  solar,
};

const labels = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];
// TODO: 실제 데이터 매핑 필요
const countries = ['미국', '호주', '우크라이나', '브라질', '아르헨티나'];
const colors = ['#2458FF', '#03A9F4', '#8E24AA', '#F4511E', '#43A047'];

function generateSeasonalTemps(base) {
  const temps = [];

  for (let i = 0; i < 12; i++) {
    // 랜덤 노이즈 추가
    const noise = Math.random() * 4 - 2;
    temps.push(Math.round(base[i] + noise));
  } // 12월 데이터 끊김 처리 → null

  temps[11] = null;

  return temps;
}

function generateChartConfig(base) {
  const datasets = countries.map((country, index) => ({
    label: country,
    data: generateSeasonalTemps(base[country]),
    fill: false,
    borderColor: colors[index],
    backgroundColor: colors[index],
    tension: 0.3,
    spanGaps: false,
    pointRadius: 0,
    pointHoverRadius: 0,
  }));

  return {
    type: 'line',
    data: {
      labels,
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: 'index',
      },
      plugins: {
        legend: {
          display: true,
        },
      },
      scales: {
        x: {
          ticks: { color: '#767676' },
        },
        y: {
          ticks: { color: '#767676' },
        },
      },
    },
  };
}
const lineChartList = document.querySelectorAll('.line-chart-container');
lineChartList.forEach((container) => {
  const chart = container.querySelector('#lineChart').getContext('2d');
  const config = generateChartConfig(base[container.id]);
  new Chart(chart, config);
});

// period
// TODO: 실제 데이터 매핑 필요
const periods = ['Last 10year', 'Last 5year', 'Last year', 'Current Year'];
const periodColors = ['#2458FF', '#03A9F4', '#8E24AA', '#F4511E'];

// TODO: 실제 데이터 매핑 필요
const seasonalBase = {
  'Last 10year': [5, 6, 7, 9, 12, 15, 17, 16, 14, 10, 7, 5],
  'Last 5year': [6, 7, 9, 10, 13, 16, 18, 17, 15, 11, 8, 6],
  'Last year': [7, 8, 10, 12, 15, 18, 20, 19, 16, 12, 9, 7],
  'Current Year': [8, 9, 11, 13, 17, 19, 22, 21, 17, 13, 10, 8],
};

function generatePeriodTemps(period) {
  const base = seasonalBase[period];
  const temps = [];

  for (let i = 0; i < 12; i++) {
    const noise = Math.random() * 4 - 2;
    temps.push(Math.round(base[i] + noise));
  }

  temps[11] = null; // 12월 끊김 처리
  return temps;
}

function generateChartConfigByPeriod() {
  const datasets = periods.map((period, index) => ({
    label: period,
    data: generatePeriodTemps(period),
    fill: false,
    borderColor: periodColors[index],
    backgroundColor: periodColors[index],
    tension: 0.3,
    spanGaps: false,
    pointRadius: 0,
    pointHoverRadius: 0,
  }));

  return {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: 'index',
      },
      plugins: {
        legend: { display: true },
      },
      scales: {
        x: { ticks: { color: '#767676' } },
        y: { ticks: { color: '#767676' } },
      },
    },
  };
}
// 이미지가 모두 로드된 후 차트 생성
window.addEventListener('load', () => {
  const periodChartList = document.querySelectorAll('#lineChartPeriod');

  periodChartList.forEach((chartElement) => {
    // 같은 chart-group 내의 이미지 찾기
    const chartGroup = chartElement.closest('.chart-group');
    const referenceImage = chartGroup.querySelector('.chart-content img');

    if (referenceImage) {
      const chartContent = chartElement.closest('.chart-content');

      // 높이 업데이트 함수
      const updateHeight = () => {
        chartContent.style.height = referenceImage.offsetHeight + 'px';
      };

      // 초기 높이 설정
      updateHeight();

      // 이미지 크기 변화 감지 및 자동 조절
      const resizeObserver = new ResizeObserver(() => {
        updateHeight();
      });

      resizeObserver.observe(referenceImage);
    }

    const ctx = chartElement.getContext('2d');
    const config = generateChartConfigByPeriod();
    new Chart(ctx, config);
  });
});

// NIRV 차트
function generateNirvConfig() {
  // TODO: 실제 데이터 매핑 필요
  const monthlyData = [
    0.0582,
    0.05809,
    0.05876,
    0.05995,
    0.06237,
    0.06731,
    0.07819,
    0.12205,
    0.22999,
    0.31848,
    null,
    null,
  ];

  const data = {
    labels,
    datasets: [
      {
        label: 'NIRV Index',
        data: monthlyData,
        fill: false,
        borderColor: '#43A047',
        backgroundColor: '#43A047',
        tension: 0.3,
        spanGaps: false,
        pointRadius: 0,
        pointHoverRadius: 0,
      },
    ],
  };

  // 식생지수
  return {
    type: 'line',
    data,
    options: {
      responsive: true, // ← CSS 크기 적용
      maintainAspectRatio: false,

      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          enabled: true,
          mode: 'index',
          intersect: false,
        },
      },

      scales: {
        x: {
          ticks: { color: '#666' },
        },
        y: {
          ticks: { color: '#666' },
        },
      },
    },
  };
}

window.addEventListener('load', () => {
  const nirvChartElements = document.querySelectorAll('#nirvChart');
  if (nirvChartElements.length === 0) return;
  nirvChartElements.forEach((chartElement) => {
    const ctx = chartElement.getContext('2d');
    const config = generateNirvConfig();

    new Chart(ctx, config);
  });
});

function createSingleChart(data, canvas) {
  const labels = data.map((item) => item.label);
  const values = data.map((item) => item.value);

  const ctx = canvas.getContext('2d');

  const sorted = [...values].sort((a, b) => a - b);
  const minRangeEnd = sorted[Math.floor(sorted.length / 3)];
  const midRangeEnd = sorted[Math.floor((sorted.length * 2) / 3)];

  const barColors = values.map((v) => {
    if (v <= minRangeEnd) return '#DDEAFD'; // 하위 구간
    if (v <= midRangeEnd) return '#91BCFF'; // 중간 구간
    return '#2458FF'; // 상위 구간
  });

  const chartData = {
    labels,
    datasets: [
      {
        data: values,
        backgroundColor: barColors,
        borderWidth: 1,
      },
    ],
  };

  const config = {
    type: 'bar',
    data: chartData,
    options: {
      responsive: true, // ← CSS 크기 적용
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          ticks: { color: '#767676' },
        },
        y: {
          ticks: { color: '#767676' },
          beginAtZero: true,
        },
      },
    },
  };

  new Chart(ctx, config);
}

function generateStateData(seed) {
  // TODO: 실제 데이터 매핑 필요
  const base = [
    0.03,
    0.045,
    0.06,
    0.08,
    0.12,
    0.19,
    0.27,
    0.31,
    0.28,
    0.23,
    0.18,
    null,
  ];

  const data = [];

  for (let i = 0; i < 12; i++) {
    if (i === 11) {
      data.push(null); // DEC 끊김
    } else {
      // 주별로 패턴을 다르게 하기 위해 seed 반영
      const seedShift = seed * 0.005; // 랜덤 노이즈: 월별로 ±0.005~0.02 자연스러운 변화

      const noise = Math.random() * 0.02 - 0.01;

      data.push(Number((base[i] + seedShift + noise).toFixed(4)));
    }
  }

  return data;
}

function createTotalNirvChart(canvas) {
  const ctx = canvas.getContext('2d'); // 12개 주(State)

  const labels = [
    'JAN',
    'FEB',
    'MAR',
    'APR',
    'MAY',
    'JUN',
    'JUL',
    'AUG',
    'SEP',
    'OCT',
    'NOV',
    'DEC',
  ];

  // TODO: 실제 데이터 매핑 필요
  const states = [
    'North Dakota',
    'Minnesota',
    'Illinois',
    'South Dakota',
    'Iowa',
    'Indiana',
    'Nebraska',
    'Missouri',
    'Ohio',
    'Kansas',
    'Wisconsin',
    'Kentucky',
  ];

  const colors = [
    '#2458FF',
    '#03A9F4',
    '#8E24AA',
    '#F4511E',
    '#43A047',
    '#795548',
    '#6A1B9A',
    '#1E88E5',
    '#D81B60',
    '#00897B',
    '#7CB342',
    '#FDD835',
  ];

  const datasets = states.map((state, index) => ({
    label: state,
    data: generateStateData(index),
    borderColor: colors[index],
    backgroundColor: colors[index],
    borderWidth: 1.2,
    tension: 0.35,
    pointRadius: 0,
  }));

  const config = {
    type: 'line',
    data: {
      labels,
      datasets,
    },

    options: {
      responsive: true,
      maintainAspectRatio: false,

      interaction: {
        mode: 'index',
        intersect: false,
      },

      plugins: {
        legend: {
          labels: { font: { size: 7 } },
        },
        tooltip: {
          enabled: true,
          mode: 'index',
          intersect: false,
        },
      },

      scales: {
        x: { ticks: { color: '#555' } },
        y: { ticks: { color: '#555' } },
      },
    },
  };

  new Chart(ctx, config);
}

function createSingleNirvChart(ndvi, canvas) {
  const ctx = canvas.getContext('2d');

  const { fiveYearMax, fiveYearMin, fiveYearAvg, lastYearAvg, currentYearAvg } =
    ndvi;

  const labels = [
    'APR',
    'MAY',
    'JUN',
    'JUL',
    'AUG',
    'SEP',
    'OCT',
    'NOV',
    'DEC',
  ];

  // TODO: 실제 데이터 매핑 필요
  const datasets = [
    {
      label: '5-yr S.E.',
      data: fiveYearMax,
      borderColor: 'rgba(0,0,0,0.001)',
      backgroundColor: 'rgba(180,180,180,0.4)',
      fill: '+1',
      tension: 0.35,
      pointRadius: 0,
      pointHitRadius: 20,
    },
    {
      label: '5-yr S.E. lower',
      data: fiveYearMin,
      borderColor: 'rgba(0,0,0,0.001)',
      backgroundColor: 'rgba(180,180,180,0.4)',
      tension: 0.35,
      pointRadius: 0,
      pointHitRadius: 20,
    },
    {
      label: '5-Yr Avg',
      data: fiveYearAvg,
      borderColor: '#21272A',
      backgroundColor: '#21272A',
      borderWidth: 2,
      tension: 0.35,
      pointRadius: 0,
      pointHitRadius: 20,
    },
    {
      label: 'JAN 2024 - DEC 2024',
      data: lastYearAvg,
      borderColor: '#2458FF',
      backgroundColor: '#2458FF',
      borderWidth: 1.5,
      tension: 0.35,
      pointRadius: 0,
      pointHitRadius: 20,
    },
    {
      label: 'JAN 2025 - NOV 2025',
      data: currentYearAvg,
      borderColor: '#F4511E',
      backgroundColor: '#F4511E',
      borderWidth: 1.5,
      tension: 0.35,
      pointRadius: 0,
      pointHitRadius: 20,
    },
  ];

  const config = {
    type: 'line',
    data: {
      labels,
      datasets,
    },

    options: {
      responsive: true,
      maintainAspectRatio: false,

      interaction: {
        mode: 'index',
        intersect: false,
      },

      plugins: {
        legend: {
          labels: { font: { size: 8 } },
        },
        tooltip: {
          enabled: true,
          mode: 'index',
          intersect: false,
        },
      },

      scales: {
        x: { ticks: { color: '#555' } },
        y: { ticks: { color: '#555' } },
      },
    },
  };

  new Chart(ctx, config);
}
