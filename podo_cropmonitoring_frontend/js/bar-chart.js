// TODO: 실제 데이터 매핑 필요
const barChartLabels = ['미국', '호주', '브라질', '아르헨티나', '우크라이나'];
const values = barChartLabels.map(() => Math.floor(Math.random() * 100));

const sorted = [...values].sort((a, b) => a - b);
const minRangeEnd = sorted[Math.floor(sorted.length / 3)];
const midRangeEnd = sorted[Math.floor((2 * sorted.length) / 3)];

const barColors = values.map((v) => {
  if (v <= minRangeEnd) return '#DDEAFD';
  if (v <= midRangeEnd) return '#91BCFF';
  return '#2458FF';
});

const data = {
  labels: barChartLabels,
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
  data,
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
    },
    scales: {
      x: {
        ticks: {
          color: '#767676',
        },
      },
      y: {
        ticks: {
          color: '#767676',
        },
      },
    },
  },
};

const barChartList = document.querySelectorAll('#barChart');
barChartList.forEach((chart) => {
  const newChart = new Chart(chart, config);
  window.addEventListener('resize', () => {
    newChart.resize();
  });
});
