/**
 * 재배달력 날짜 마커 초기화
 * 현재 날짜에 해당하는 셀에 마커를 표시합니다.
 */
function initCultivationDateMarker() {
  const tables = document.querySelectorAll('.cultivation-table');

  tables.forEach(table => {
    // 기존 마커 및 클래스 제거 (중복 방지)
    table.querySelectorAll('.has-date-marker').forEach(cell => {
      cell.classList.remove('has-date-marker');
    });
    table.querySelectorAll('.cultivation-date-marker').forEach(marker => {
      marker.remove();
    });

    // 모든 th 요소 가져오기
    const allCells = Array.from(table.querySelectorAll('th[data-date]'));
    if (allCells.length === 0) return;

    // data-date를 Date 객체로 변환하는 함수 (올해 기준)
    const currentYear = new Date().getFullYear();
    const parseDate = (dateStr) => {
      const [month, day] = dateStr.split('-').map(Number);
      return new Date(currentYear, month - 1, day);
    };

    // 셀들을 날짜순으로 정렬
    const sortedCells = [...allCells].sort((a, b) => {
      return parseDate(a.dataset.date) - parseDate(b.dataset.date);
    });

    // 현재 날짜 (시간 제외)
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // 현재 날짜가 속한 구간 찾기
    let targetCell = null;
    let ratio = 0; // 셀 내에서의 위치 비율 (0 = 왼쪽, 1 = 오른쪽)

    for (let i = 0; i < sortedCells.length; i++) {
      const cellDate = parseDate(sortedCells[i].dataset.date);

      if (i === sortedCells.length - 1) {
        // 마지막 셀 이후인 경우
        if (today >= cellDate) {
          targetCell = sortedCells[i];
          ratio = 0.5; // 셀 중간에 표시
        }
      } else {
        const nextCellDate = parseDate(sortedCells[i + 1].dataset.date);

        if (today >= cellDate && today < nextCellDate) {
          targetCell = sortedCells[i];

          // 구간 내 비율 계산 (셀 내에서의 위치)
          const totalDays = (nextCellDate - cellDate) / (1000 * 60 * 60 * 24);
          const elapsedDays = (today - cellDate) / (1000 * 60 * 60 * 24);
          ratio = elapsedDays / totalDays;
          break;
        }
      }
    }

    // 첫 번째 날짜 이전인 경우
    if (!targetCell && sortedCells.length > 0) {
      const firstDate = parseDate(sortedCells[0].dataset.date);
      if (today < firstDate) {
        targetCell = sortedCells[0];
        ratio = 0;
      }
    }

    if (!targetCell) return;

    // th에 relative 클래스 추가
    targetCell.classList.add('has-date-marker');

    // 마커 div 생성 및 th 내부에 추가
    const marker = document.createElement('div');
    marker.className = 'cultivation-date-marker';

    targetCell.appendChild(marker);
  });
}

// DOM 로드 시 자동 실행
document.addEventListener('DOMContentLoaded', initCultivationDateMarker);
