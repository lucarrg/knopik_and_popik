const staticForms = document.querySelectorAll('.search, .catalog-toolbar');

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
    const canCollapse = filterBreakpoint.matches;
    const shouldOpen = canCollapse && isOpen;

    filterRegion.classList.toggle('is-open', shouldOpen);
    filtersToggle.setAttribute('aria-expanded', String(shouldOpen));
  };

  filtersToggle.addEventListener('click', () => {
    const isOpen = filtersToggle.getAttribute('aria-expanded') === 'true';
    setFiltersOpen(!isOpen);
  });

  filterBreakpoint.addEventListener('change', () => {
    setFiltersOpen(false);
  });

  setFiltersOpen(false);
}

const catalogFilterPanel = document.querySelector('.catalog-filters');
const filterReset = document.querySelector('.filters-reset');
const ingredientInput = document.querySelector('.ingredient-input');
const selectedChips = document.querySelector('.selected-chips');
const filtersToggleLabel = document.querySelector('.filters-toggle-label');

if (catalogFilterPanel && filterReset && selectedChips) {
  const filterInputs = catalogFilterPanel.querySelectorAll('input[type="checkbox"], input[type="radio"]');

  const updateResetVisibility = () => {
    const selectedControlCount = Array.from(filterInputs).filter((input) => input.checked).length;
    const selectedProductCount = selectedChips.children.length;
    const activeFilterCount = selectedControlCount + selectedProductCount;

    filterReset.hidden = activeFilterCount === 0;

    if (filtersToggleLabel) {
      filtersToggleLabel.textContent = activeFilterCount ? `Фильтры · ${activeFilterCount}` : 'Фильтры';
    }
  };

  const addProductChip = (product) => {
    const chip = document.createElement('span');
    const removeButton = document.createElement('button');

    chip.append(`${product} `);
    removeButton.type = 'button';
    removeButton.setAttribute('aria-label', `Удалить ${product}`);
    removeButton.textContent = '×';
    chip.append(removeButton);
    selectedChips.append(chip);
  };

  filterInputs.forEach((input) => {
    input.addEventListener('change', updateResetVisibility);
  });

  selectedChips.addEventListener('click', (event) => {
    const removeButton = event.target.closest('button');

    if (removeButton) {
      removeButton.closest('span')?.remove();
      updateResetVisibility();
    }
  });

  if (ingredientInput) {
    ingredientInput.addEventListener('keydown', (event) => {
      const product = ingredientInput.value.trim();

      if (event.key === 'Enter' && product) {
        event.preventDefault();
        addProductChip(product);
        ingredientInput.value = '';
        updateResetVisibility();
      }
    });
  }

  filterReset.addEventListener('click', () => {
    filterInputs.forEach((input) => {
      input.checked = false;
    });
    selectedChips.replaceChildren();

    if (ingredientInput) {
      ingredientInput.value = '';
    }

    updateResetVisibility();
  });

  updateResetVisibility();
}

const recipeNotes = document.querySelector('.recipe-notes');

if (recipeNotes) {
  const notesList = recipeNotes.querySelector('[data-notes-list]');
  const noteForm = recipeNotes.querySelector('[data-note-form]');
  const noteField = noteForm.querySelector('textarea');
  const emptyNotes = recipeNotes.querySelector('[data-notes-empty]');
  const modal = document.querySelector('[data-confirmation-modal]');
  const modalTitle = modal.querySelector('[data-confirmation-title]');
  const modalDialog = modal.querySelector('[role="dialog"]');
  let pendingDelete = null;
  let restoreFocus = null;

  const updateEmptyNotes = () => {
    emptyNotes.hidden = Boolean(notesList.querySelector('[data-note]'));
  };
  const noteDate = () => new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric'
  }).format(new Date());

  const ownerActions = () => {
    const actions = document.createElement('div');
    actions.className = 'note-owner-actions';
    actions.setAttribute('aria-label', 'Управление заметкой');
    actions.innerHTML = '<button type="button" data-note-action="edit">Редактировать</button><button type="button" data-note-action="delete" data-confirm-delete="note">Удалить</button>';
    return actions;
  };

}
