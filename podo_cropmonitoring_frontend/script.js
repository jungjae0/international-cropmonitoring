const controller = new AbortController();

document.addEventListener('DOMContentLoaded', () => {
  const menuButton = document.getElementById('menu-button');
  const navLinks = document.getElementById('nav-links');
  const navDropdown = document.getElementById('nav-dropdown');
  const navOverlay = document.getElementById('nav-overlay');
  const dropdownItems = document.querySelectorAll('.dropdown-item');
  const countryItems = document.querySelectorAll('.country-item');
  const cropsColumn = document.getElementById('crops-column');
  const backButton = document.getElementById('back-button');

  // 국가별 작물 데이터 (작물명과 링크 포함)
  const countryCrops = {
    '미국': [
      { name: '옥수수', href: '/country-crop/america/america-corn.html' },
      { name: '콩', href: '/country-crop/america/america-soybean.html' },
      { name: '밀', href: '/country-crop/america/america-wheat.html' }
    ],
    '브라질': [
      { name: '옥수수', href: '#' }
    ],
    '우크라이나': [
      { name: '콩', href: '#' }
    ],
    '아르헨티나': [
      { name: '콩', href: '#' },
      { name: '밀', href: '#' }
    ],
    '호주': [
      { name: '옥수수', href: '#' },
      { name: '밀', href: '#' }
    ]
  };

  // 현재 페이지 경로
  const currentPath = window.location.pathname;

  let isMenuOpen = false;
  let openedByClick = false;
  let closeTimeout = null;
  let cropsTimeout = null;

  // 드롭다운 위치 조정 (국가별 보기 메뉴 아래에 배치)
  const positionDropdown = () => {
    const hasDropdownItem = navLinks.querySelector('li.has-dropdown');
    if (hasDropdownItem) {
      const rect = hasDropdownItem.getBoundingClientRect();
      navDropdown.style.paddingLeft = `${rect.left}px`;
    }
  };

  // 드롭다운 열기
  const openDropdown = () => {
    // 닫기 타이머가 있으면 취소
    if (closeTimeout) {
      clearTimeout(closeTimeout);
      closeTimeout = null;
    }
    positionDropdown();
    navDropdown.classList.add('active');
    navOverlay.classList.add('active');
    isMenuOpen = true;
  };

  // 드롭다운 닫기
  const closeDropdown = () => {
    navDropdown.classList.remove('active');
    navOverlay.classList.remove('active');
    isMenuOpen = false;
    openedByClick = false;
    closeTimeout = null;
  };

  // 딜레이를 두고 닫기 (margin 영역 통과 시간 확보)
  const closeDropdownWithDelay = () => {
    if (closeTimeout) {
      clearTimeout(closeTimeout);
    }
    closeTimeout = setTimeout(() => {
      closeDropdown();
    }, 300); // 300ms 딜레이
  };

  // hover 이벤트: nav-links에 마우스 올렸을 때
  navLinks.addEventListener(
    'mouseenter',
    () => {
      if (!openedByClick) {
        openDropdown();
      }
    },
    { signal: controller.signal }
  );

  // hover 이벤트: nav-links에서 마우스가 나갔을 때
  navLinks.addEventListener(
    'mouseleave',
    () => {
      if (openedByClick) return;
      closeDropdownWithDelay();
    },
    { signal: controller.signal }
  );

  // hover 이벤트: nav-dropdown에 마우스가 들어왔을 때
  navDropdown.addEventListener(
    'mouseenter',
    () => {
      // 닫기 타이머 취소
      if (closeTimeout) {
        clearTimeout(closeTimeout);
        closeTimeout = null;
      }
    },
    { signal: controller.signal }
  );

  // hover 이벤트: nav-dropdown에서 마우스가 나갔을 때
  navDropdown.addEventListener(
    'mouseleave',
    () => {
      if (openedByClick) return;
      closeDropdownWithDelay();
    },
    { signal: controller.signal }
  );

  // click 이벤트: menu-button 클릭
  const handleMenuClick = (e) => {
    e.stopPropagation();

    if (isMenuOpen && openedByClick) {
      closeDropdown();
    } else {
      openDropdown();
      openedByClick = true;
    }
  };

  menuButton.addEventListener('click', handleMenuClick, {
    signal: controller.signal,
  });

  // overlay 클릭 시 닫기
  navOverlay.addEventListener(
    'click',
    () => {
      closeDropdown();
    },
    { signal: controller.signal }
  );

  // 뒤로가기 버튼 클릭 시 닫기
  backButton.addEventListener(
    'click',
    () => {
      closeDropdown();
    },
    { signal: controller.signal }
  );

  // 모바일 국가 토글 클릭 이벤트
  const countryToggles = document.querySelectorAll('.country-toggle');
  countryToggles.forEach((toggle) => {
    toggle.addEventListener(
      'click',
      (e) => {
        e.stopPropagation();
        const countryName = toggle.dataset.country;
        const cropSubmenu = document.querySelector(`.crop-submenu[data-country="${countryName}"]`);

        // 다른 열린 메뉴 닫기
        countryToggles.forEach((otherToggle) => {
          if (otherToggle !== toggle) {
            otherToggle.classList.remove('active');
            const otherCountry = otherToggle.dataset.country;
            const otherSubmenu = document.querySelector(`.crop-submenu[data-country="${otherCountry}"]`);
            if (otherSubmenu) {
              otherSubmenu.classList.remove('active');
            }
          }
        });

        // 현재 메뉴 토글
        toggle.classList.toggle('active');
        if (cropSubmenu) {
          cropSubmenu.classList.toggle('active');
        }
      },
      { signal: controller.signal }
    );
  });

  // dropdown 내부 항목 클릭 시 닫기
  dropdownItems.forEach((item) => {
    item.addEventListener(
      'click',
      () => {
        closeDropdown();
      },
      { signal: controller.signal }
    );
  });

  // 작물 컬럼 보이기 (국가별 작물 동적 생성)
  const showCrops = (countryName) => {
    if (cropsTimeout) {
      clearTimeout(cropsTimeout);
      cropsTimeout = null;
    }

    // 해당 국가의 작물 목록 가져오기
    const crops = countryCrops[countryName] || [];

    // 기존 작물 항목 모두 제거
    cropsColumn.innerHTML = '';

    // 해당 국가의 작물만 동적으로 생성
    crops.forEach((crop) => {
      const link = document.createElement('a');
      link.href = crop.href;
      link.className = 'dropdown-item';
      link.textContent = crop.name;

      // 현재 페이지와 일치하면 active 클래스 추가
      if (currentPath === crop.href) {
        link.classList.add('active');
      }

      // 클릭 시 드롭다운 닫기
      link.addEventListener('click', () => {
        closeDropdown();
      }, { signal: controller.signal });

      cropsColumn.appendChild(link);
    });

    cropsColumn.classList.add('active');
  };

  // 작물 컬럼 숨기기 (딜레이)
  const hideCropsWithDelay = () => {
    if (cropsTimeout) {
      clearTimeout(cropsTimeout);
    }
    cropsTimeout = setTimeout(() => {
      cropsColumn.classList.remove('active');
    }, 200);
  };

  // 국가 hover 이벤트
  countryItems.forEach((item) => {
    item.addEventListener(
      'mouseenter',
      () => {
        const countryName = item.textContent.trim();
        showCrops(countryName);
      },
      { signal: controller.signal }
    );

    item.addEventListener(
      'mouseleave',
      () => {
        hideCropsWithDelay();
      },
      { signal: controller.signal }
    );
  });

  // 작물 컬럼 hover 이벤트 (컬럼에 있으면 유지)
  cropsColumn.addEventListener(
    'mouseenter',
    () => {
      if (cropsTimeout) {
        clearTimeout(cropsTimeout);
        cropsTimeout = null;
      }
    },
    { signal: controller.signal }
  );

  cropsColumn.addEventListener(
    'mouseleave',
    () => {
      hideCropsWithDelay();
    },
    { signal: controller.signal }
  );

  // 정리
  window.addEventListener('beforeunload', () => {
    controller.abort();
  });
});
