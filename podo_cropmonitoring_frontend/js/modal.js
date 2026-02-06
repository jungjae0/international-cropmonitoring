/**
 * Modal Controller
 * - showIssueModal(): 이슈 모달 표시
 * - showDataModal(type: string): 데이터 모달 표시
 *   - type: production, area, import, import_ratio, ndvi
 */

// 모달 요소 캐싱
let modal = null;
let modalOverlay = null;
let modalTitle = null;
let modalCloseButtons = null;
let modalContent = null;

// DOM 로드 후 모달 요소 초기화
document.addEventListener('DOMContentLoaded', () => {
  initModalElements();
  setupModalEventListeners();
});

/**
 * 모달 DOM 요소 초기화
 */
function initModalElements() {
  modal = document.getElementById('chart-modal');
  if (!modal) return;

  modalOverlay = modal.querySelector('.modal-overlay');
  modalTitle = document.getElementById('modal-title').querySelector('h2');
  modalCloseButtons = modal.querySelectorAll('.modal-close');
  modalContent = modal.querySelector('.modal-content');
}

/**
 * 모달 이벤트 리스너 설정
 */
function setupModalEventListeners() {
  if (!modal) return;

  // 닫기 버튼 클릭 이벤트
  modalCloseButtons.forEach((button) => {
    button.addEventListener('click', closeModal);
  });

  // 오버레이 클릭 이벤트
  if (modalOverlay) {
    modalOverlay.addEventListener('click', closeModal);
  }

  // ESC 키 이벤트
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('active')) {
      closeModal();
    }
  });
}

/**
 * 모달 열기
 */
function openModal() {
  if (!modal) return;
  modal.classList.add('active');
  document.body.classList.add('modal-open');
}

/**
 * 모달 닫기
 */
function closeModal() {
  if (!modal) return;
  modal.classList.remove('active');
  document.body.classList.remove('modal-open');
}

/**
 * 타입별 한글 제목 매핑
 */
const TYPE_TITLES = {
  production: '생산량',
  area: '재배면적',
  import: '연간 수입량',
  import_ratio: '수입비중',
  ndvi: '식생지수',
  issue: '이슈 전체 보기',
};

/**
 * 이슈 모달 표시
 */
function showIssueModal() {
  const modalHeader = modal.querySelector('.modal-header');
  const subtitle = `<p class="modal-subtitle">등록된 이슈들을 한 번에 확인할 수 있어요.</p>`;
  modalHeader.insertAdjacentHTML('beforeend', subtitle);

  // 이슈 데이터 fetch 및 표시
  // TODO: 실제 데이터 매핑 필요
  fetch('/assets/json/issue.json')
    .then((response) => response.json())
    .then((data) => {
      // 이슈 데이터를 모달 내용에 표시하는 로직 구현
      const issueList = data.issueList
        .map(
          (issue) => `
      <div class="issue-card">
                <div class="issue-header">
                  <div>
                    <h1>${issue.title}</h1>
                    <p>${issue.reportedDate}</p>
                  </div>
                </div>
                <div class="issue-content">${issue.description}</div>
              </div>
              `
        )
        .join('');
      const modalBody = modal.querySelector('.modal-body');
      modalBody.innerHTML = `
        <div class="issue-list">
          ${issueList}
        </div>
      `;
    })
    .catch((error) => {
      console.error('Error loading issue data:', error);
    });

  openModal();
}

/**
 * 식생지수 모달 표시
 * @param {string} type - ndvi
 */
function showNirModal() {
  // TODO: 타입별 데이터 로드 및 모달 바디 업데이트
  // 사용자가 내부 데이터 구현 예정
  const modalBody = modal.querySelector('.modal-body');
  modalBody.innerHTML = `
    <div class="chart-list">
      <div class="total-chart">
        <div class="total-chart-slider-wrapper">
          <div class="total-chart-slider">
            <div class="total-chart-item">
              <div class="total-chart-header">
                <h1>통합 그래프</h1>
              </div>
              <div class="total-chart-content">
                <canvas id="ndviTotalChart"></canvas>
              </div>
            </div>
            <div class="total-chart-item">
              <div class="total-chart-header">
                <h1>미국 콘벨트 옥수수 생육상황 등급 (1: 불량 → 3: 보통 → 5: 양호)</h1>
              </div>
              <div class="total-chart-content">
                <img src="/assets/corn-belt-ndvi.png" alt="NDVI Layer" />
              </div>
            </div>
          </div>
        </div>
        <div class="total-chart-carousel">
          <div class="indicator active"></div>
          <div class="indicator"></div>
        </div>
      </div>
      <div class="state-chart-list">

      </div>
    </div>
  `;

  // total-chart slider 이벤트
  const totalChartSlider = modalBody.querySelector('.total-chart-slider');
  const totalChartIndicators = modalBody.querySelectorAll(
    '.total-chart-carousel .indicator'
  );

  totalChartIndicators.forEach((indicator, index) => {
    indicator.addEventListener('click', () => {
      totalChartSlider.style.transform = `translateX(-${index * 100}%)`;
      totalChartIndicators.forEach((ind) => ind.classList.remove('active'));
      indicator.classList.add('active');
    });
  });

  // create state nirv chart
  // TODO: 실제 데이터 매핑 필요
  fetch('/assets/json/ndvi.json')
    .then((response) => response.json())
    .then((data) => {
      // create Total chart
      const totalChartCanvas = modalBody.querySelector('#ndviTotalChart');
      createTotalNirvChart(totalChartCanvas);

      // create state chart list
      const stateChartList = modalBody.querySelector('.state-chart-list');

      const ndviList = data.ndviList.map((ndvi) => {
        return {
          html: `
            <div class="state-chart-item">
              <div class="state-chart-item-header">
                <h1>${ndvi.name}</h1>
              </div>
              <div class="state-chart-item-content">
                <canvas id="ndviStateChart"></canvas>
              </div>
            </div>
          `,
          data: ndvi,
        };
      });

      stateChartList.innerHTML = ndviList.map((ndvi) => ndvi.html).join('');

      stateChartList
        .querySelectorAll('.state-chart-item')
        .forEach((item, index) => {
          const ndvi = ndviList[index];
          const canvas = item.querySelector('#ndviStateChart');
          createSingleNirvChart(ndvi.data, canvas);
        });
    });

  openModal();
}

async function generateImportContent() {
  // TODO: 실제 데이터 매핑 필요
  return fetch('/assets/json/import.json')
    .then((response) => response.json())
    .then((data) => {
      // 수입량 데이터 처리 및 모달 내용 업데이트 로직 구현
      return {
        html: `
        <div class="single-content-wrapper">
          <canvas id="importChart"></canvas>
        </div>
      `,
        data: data.importList,
      };
    });
}
// async function generateImportRatioContent() {}
async function generateProductionContent() {
  // TODO: 실제 데이터 매핑 필요
  return fetch('/assets/json/production.json')
    .then((response) => response.json())
    .then((data) => {
      // 생산량 데이터 처리 및 모달 내용 업데이트 로직 구현

      return {
        html: `
        <div class="single-content-wrapper">
          <canvas id="productionChart"></canvas>
        </div>
      `,
        data: data.productionList,
      };
    });
}
async function generateAreaContent() {
  // TODO: 실제 데이터 매핑 필요
  return fetch('/assets/json/area.json')
    .then((response) => response.json())
    .then((data) => {
      // 재배면적 데이터 처리 및 모달 내용 업데이트 로직 구현
      return {
        html: `
        <div class="single-content-wrapper">
          <canvas id="areaChart"></canvas>
        </div>
      `,
        data: data.areaList,
      };
    });
}

/**
 * 데이터 모달 표시
 * @param {string} type - production, area, import, import_ratio
 */
function showDataModal(type) {
  const modalBody = modal.querySelector('.modal-body');

  switch (type) {
    case 'import':
    case 'import_ratio':
      generateImportContent().then(({ html, data }) => {
        modalBody.innerHTML = html;
        const canvas = modalBody.querySelector('#importChart');
        createSingleChart(data, canvas);
      });
      break;
    case 'production':
      generateProductionContent().then(({ html, data }) => {
        modalBody.innerHTML = `
          <div class="multi-content-wrapper">
            <div class="production-content">
              <h1>미국 콘벨트 옥수수 수량 분포 추정('22)</h1>
              <div class="production-images">
                <div class="production-images-slider">
                  <img src="/assets/corn-belt-production-1.png" alt="Production Image 1" />
                  <img src="/assets/corn-belt-production-2.png" alt="Production Image 2" />
                </div>
              </div>
              <div class="production-carousel">
                  <div class="indicator active"></div>
                  <div class="indicator"></div>
                </div>
            </div>
            ${html}
          </div>
        `;
        const canvas = modalBody.querySelector('#productionChart');
        createSingleChart(data, canvas);
        const indicators = modalBody.querySelectorAll(
          '.production-carousel .indicator'
        );
        const slider = modalBody.querySelector('.production-images-slider');

        indicators.forEach((indicator, index) => {
          indicator.addEventListener('click', () => {
            slider.style.transform = `translateX(-${index * 100}%)`;
            indicators.forEach((ind) => ind.classList.remove('active'));
            indicator.classList.add('active');
          });
        });
      });
      break;
    case 'area':
      generateAreaContent().then(({ html, data }) => {
        modalBody.innerHTML = `
          <div class="multi-content-wrapper">
            <div class="area-content">
            <h1>미국 콘벨트 13개주 옥수수 작물 구분도</h1>
              <div class="area-images">
                <img src="/assets/corn-belt-area.png" alt="Area Image 1" />
              </div>
            </div>
            ${html}
          </div>
        `;
        const canvas = modalBody.querySelector('#areaChart');
        createSingleChart(data, canvas);
      });
      break;
    default:
      // 이외의 값을 주입할 때 주의해주세요!
      throw new Error('Unknown data modal type: ' + type);
  }
  openModal();
}

/**
 * 통합 핸들러 - 버튼 onclick에서 호출
 * @param {string} type - issue, production, area, import, import_ratio, ndvi
 */
function handleExpandClick(type) {
  if (!modal || !modalTitle) return;

  const title = TYPE_TITLES[type] || '데이터';
  modalTitle.textContent = title;

  modalContent.classList.remove('modal-content-ndvi', 'modal-content-data');
  if (type === 'ndvi') {
    modalContent.classList.add('modal-content-ndvi');
  } else {
    modalContent.classList.add('modal-content-data');
  }

  const modalHeader = modal.querySelector('.modal-header');
  modalHeader.querySelector('.modal-subtitle')?.remove();

  switch (type) {
    case 'issue':
      showIssueModal();
      break;
    case 'ndvi':
      showNirModal();
      break;
    case 'production':
    case 'area':
    case 'import':
    case 'import_ratio':
      showDataModal(type);
      break;
    default:
      console.warn('Unknown modal type:', type);
  }
}
