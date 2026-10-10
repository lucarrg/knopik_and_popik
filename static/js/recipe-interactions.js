(() => {
  const notesRoot = document.querySelector('.recipe-notes');
  const modal = document.querySelector('[data-confirmation-modal]');

  if (!notesRoot || !modal) {
    return;
  }

  const dialog = modal.querySelector('[role="dialog"]');
  const title = modal.querySelector('[data-confirmation-title]');
  let deleteForm = null;
  let deleteType = null;
  let lastFocusedElement = null;

  const closeModal = () => {
    modal.hidden = true;
    deleteForm = null;
    deleteType = null;
    lastFocusedElement?.focus();
  };

  const openNoteDeleteModal = (trigger) => {
    const note = trigger.closest('[data-note]');
    deleteForm = note?.querySelector('[data-note-delete-form]');
    deleteType = 'note';

    if (!deleteForm) {
      return;
    }

    lastFocusedElement = trigger;
    if (title) {
      title.textContent = 'Удалить заметку?';
    }
    modal.hidden = false;
    dialog?.focus();
  };

  const openRecipeDeleteModal = (trigger) => {
    deleteForm = null;
    deleteType = 'recipe';
    lastFocusedElement = trigger;
    if (title) {
      title.textContent = 'Удалить рецепт?';
    }
    modal.hidden = false;
    dialog?.focus();
  };

  notesRoot.addEventListener('click', (event) => {
    const editButton = event.target.closest('[data-note-action="edit"]');
    if (editButton) {
      const note = editButton.closest('[data-note]');
      const content = note?.querySelector('.note-content');
      const actions = note?.querySelector('.note-owner-actions');
      const form = note?.querySelector('.note-edit-form');
      const textarea = form?.querySelector('textarea');

      if (!note || !content || !actions || !form) {
        return;
      }

      content.hidden = true;
      actions.hidden = true;
      form.hidden = false;
      textarea?.focus();
      return;
    }

    const cancelButton = event.target.closest('[data-note-edit-cancel]');
    if (cancelButton) {
      const note = cancelButton.closest('[data-note]');
      const content = note?.querySelector('.note-content');
      const actions = note?.querySelector('.note-owner-actions');
      const form = note?.querySelector('.note-edit-form');

      form?.reset();
      if (content) {
        content.hidden = false;
      }
      if (actions) {
        actions.hidden = false;
      }
      if (form) {
        form.hidden = true;
      }
      return;
    }

    const deleteButton = event.target.closest('[data-confirm-delete="note"]');
    if (deleteButton) {
      openNoteDeleteModal(deleteButton);
    }
  });

  document.addEventListener('click', (event) => {
    const recipeDeleteButton = event.target.closest('[data-confirm-delete="recipe"]');
    if (recipeDeleteButton) {
      openRecipeDeleteModal(recipeDeleteButton);
    }
  });

  modal.addEventListener('click', (event) => {
    if (event.target === modal || event.target.closest('[data-modal-close]')) {
      closeModal();
      return;
    }

    if (event.target.closest('[data-confirmation-submit]')) {
      if (deleteForm) {
        deleteForm.submit();
        return;
      }

      if (deleteType === 'recipe') {
        console.info('Recipe deletion demo confirmed');
      }
      closeModal();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !modal.hidden) {
      closeModal();
    }
  });
})();