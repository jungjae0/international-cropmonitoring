/**
 * 미국 주(State) 데이터 로더
 * america.json에서 주 데이터를 불러와 country-states 컨테이너에 렌더링합니다.
 */
function initStatesLoader() {
  const currentPath = window.location.pathname;
  const fileName = currentPath.split('/').pop();
  const stateAbbr = fileName.split('-')[0];

  // TODO: 실제 데이터 매핑 필요
  fetch('/assets/json/america.json')
    .then((res) => res.json())
    .then((data) => {
      const statesData = data.states;
      const statesContainer = document.querySelectorAll('.country-states');

      if (statesContainer.length === 0) return;

      const selectedState = statesData.find(
        (state) => state.abbreviation.toLowerCase() === stateAbbr
      );
      const otherStates = statesData.filter(
        (state) => state.abbreviation.toLowerCase() !== stateAbbr
      );

      // 현재 페이지의 작물 종류 추출 (예: america-corn.html -> corn)
      const cropMatch = fileName.match(/-(corn|soybean|wheat)\.html$/);

      // 실제 작물 종류를 사용 필요
      // const currentCrop = cropMatch ? cropMatch[1] : 'corn';
      const currentCrop = 'corn';

      statesContainer.forEach((container) => {
        let html = '';

        // 선택된 주 표시 (X 버튼 포함)
        if (selectedState) {
          html += `<a href="/country-crop/america/america-${currentCrop}.html" class="state-item active"><span>${selectedState.nameKo}</span><span>X</span></a>`;
        }

        // 데이터가 있는 주들
        html += otherStates
          .filter((state) => state.hasData)
          .map((state) => {
            const isActive = state.abbreviation.toLowerCase() === stateAbbr;
            // tx 대신에 주소를 넣어주세요
            const abbr = 'tx'; // 예시) state.abbreviation.toLowerCase()
            return `<a href="/country-crop/america/states/${abbr}-${currentCrop}.html" class="state-item${
              isActive ? ' active' : ''
            }">${state.nameKo}</a>`;
          })
          .join('');

        // 데이터가 없는 주들 (비활성화)
        html += otherStates
          .filter((state) => !state.hasData)
          .map((state) => {
            return `<span class="state-item" aria-disabled="true">${state.nameKo}</span>`;
          })
          .join('');

        container.innerHTML = html;
      });
    })
    .catch((error) => {
      console.error('States data loading error:', error);
    });
}

// DOM 로드 시 자동 실행
document.addEventListener('DOMContentLoaded', initStatesLoader);
