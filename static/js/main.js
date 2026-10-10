const staticForms = document.querySelectorAll('.search');

staticForms.forEach((form) => {
  form.addEventListener('submit', (event) => {
    event.preventDefault();
  });
});

const menuToggle = document.querySelector('.menu-toggle');
const mobileMenu = document.querySelector('.mobile-nav');

if (menuToggle && mobileMenu) {
  menuToggle.addEventListener('click', () => {
    const isOpen = menuToggle.getAttribute('aria-expanded') === 'true';
    menuToggle.setAttribute('aria-expanded', String(!isOpen));
    mobileMenu.hidden = isOpen;
  });

  mobileMenu.addEventListener('click', (event) => {
    if (event.target.closest('a')) {
      menuToggle.setAttribute('aria-expanded', 'false');
      mobileMenu.hidden = true;
    }
  });
}

const filtersToggle = document.querySelector('.filters-toggle');
const filterRegion = document.querySelector('.catalog-filter-region');
const filtersPanel = document.querySelector('.catalog-filters');

if (filtersToggle && filterRegion && filtersPanel) {
  const filterBreakpoint = window.matchMedia('(max-width: 860px)');
  const setFiltersOpen = (isOpen) => {
    const shouldOpen = filterBreakpoint.matches && isOpen;
    filterRegion.classList.toggle('is-open', shouldOpen);
    filtersToggle.setAttribute('aria-expanded', String(shouldOpen));
  };

  filtersToggle.addEventListener('click', () => {
    setFiltersOpen(filtersToggle.getAttribute('aria-expanded') !== 'true');
  });
  filterBreakpoint.addEventListener('change', () => setFiltersOpen(false));
  setFiltersOpen(false);
}