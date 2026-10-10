const recipeNotesDemo = document.querySelector('.recipe-notes');

if (recipeNotesDemo) {
  const notesList = recipeNotesDemo.querySelector('[data-notes-list]');
  const noteForm = recipeNotesDemo.querySelector('[data-note-form]');
  const newNoteField = noteForm.querySelector('textarea');
  const emptyNotesMessage = recipeNotesDemo.querySelector('[data-notes-empty]');
  const confirmationModal = document.querySelector('[data-confirmation-modal]');
  const confirmationTitle = confirmationModal.querySelector('[data-confirmation-title]');
  const confirmationSubmit = confirmationModal.querySelector('[data-confirmation-submit]');
  const dialog = confirmationModal.querySelector('[role="dialog"]');
  let pendingDeletion = null;
  let lastFocusedElement = null;

  const updateEmptyState = () => {
    emptyNotesMessage.hidden = notesList.querySelector('[data-note]') !== null;
  };

  const currentDate = () => new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric'
  }).format(new Date());
  const buildOwnerActions = () => {
    const actions = document.createElement('div');
    actions.className = 'note-owner-actions';
    actions.setAttribute('aria-label', 'Управление заметкой');

    [['edit', 'Редактировать'], ['delete', 'Удалить']].forEach(([action, label]) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.noteAction = action;
      button.textContent = label;
      if (action === 'delete') button.dataset.confirmDelete = 'note';
      actions.append(button);
    });

    return actions;
  };
  const createNote = (text) => {
    const note = document.createElement('article');
    const meta = document.createElement('p');
    const content = document.createElement('p');

    note.className = 'recipe-note';
    note.dataset.note = '';
    meta.className = 'note-meta';
    meta.textContent = `Маша · ${currentDate()}`;
    content.className = 'note-content';
    content.textContent = text;
    note.append(meta, content, buildOwnerActions());
    return note;
  };
  const closeConfirmation = () => {
    confirmationModal.hidden = true;
    pendingDeletion = null;
    lastFocusedElement?.focus();
  };

  const openConfirmation = (type, note, trigger) => {
    pendingDeletion = { type, note };
    lastFocusedElement = trigger;
    confirmationTitle.textContent = type === 'recipe' ? 'Удалить рецепт?' : 'Удалить заметку?';
    confirmationModal.hidden = false;
    dialog.focus();
  };
  const startEditing = (note) => {
    const content = note.querySelector('.note-content');
    const actions = note.querySelector('.note-owner-actions');
    const editor = document.createElement('textarea');
    const editActions = document.createElement('div');
    const save = document.createElement('button');
    const cancel = document.createElement('button');

    editor.className = 'note-edit-field';
    editor.setAttribute('aria-label', 'Текст заметки');
    editor.value = content.textContent;
    save.type = cancel.type = 'button';
    save.textContent = 'Сохранить';
    cancel.textContent = 'Отмена';
    editActions.className = 'note-edit-actions';
    editActions.append(save, cancel);
    content.replaceWith(editor);
    actions.replaceWith(editActions);
    editor.focus();
    const restore = (text) => {
      const nextContent = document.createElement('p');
      nextContent.className = 'note-content';
      nextContent.textContent = text;
      editor.replaceWith(nextContent);
      editActions.replaceWith(buildOwnerActions());
    };

    save.addEventListener('click', () => {
      const nextText = editor.value.trim();
      if (nextText) restore(nextText);
      else editor.focus();
    });
    cancel.addEventListener('click', () => restore(content.textContent));
  };

  updateEmptyState();
}

(() => {
  const root = document.querySelector('.recipe-notes');
  if (!root) return;
  const list = root.querySelector('[data-notes-list]');
  const form = root.querySelector('[data-note-form]');
  const field = form.querySelector('textarea');
  const empty = root.querySelector('[data-notes-empty]');
  const modal = document.querySelector('[data-confirmation-modal]');
  const title = modal.querySelector('[data-confirmation-title]');
  const dialog = modal.querySelector('[role="dialog"]');
  let target = null;
  let trigger = null;
  const sync = () => { empty.hidden = Boolean(list.querySelector('[data-note]')); };
  const actions = () => '<button type="button" data-note-action="edit">Редактировать</button><button type="button" data-note-action="delete" data-confirm-delete="note">Удалить</button>';
  const close = () => { modal.hidden = true; target = null; trigger?.focus(); };
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const text = field.value.trim();
    if (!text) return;
    const note = document.createElement('article');
    note.className = 'recipe-note'; note.dataset.note = '';
    note.innerHTML = `<p class="note-meta">Маша · ${new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'long',year:'numeric'}).format(new Date())}</p><p class="note-content"></p><div class="note-owner-actions" aria-label="Управление заметкой">${actions()}</div>`;
    note.querySelector('.note-content').textContent = text;
    list.append(note); field.value = ''; sync();
  });

  sync();
})();

(()=>{document.addEventListener('click',e=>{const b=e.target.closest('[data-note-action="edit"]');if(!b)return;const n=b.closest('[data-note]'),p=n.querySelector('.note-content'),a=n.querySelector('.note-owner-actions'),t=document.createElement('textarea'),x=document.createElement('div');t.className='note-edit-field';t.setAttribute('aria-label','Текст заметки');t.value=p.textContent;x.className='note-edit-actions';x.innerHTML='<button type="button" data-note-save>Сохранить</button><button type="button" data-note-cancel>Отмена</button>';p.replaceWith(t);a.replaceWith(x);t.focus()})})();

(()=>{document.addEventListener('click',e=>{const b=e.target.closest('[data-note-save],[data-note-cancel]');if(!b)return;const n=b.closest('[data-note]'),t=n.querySelector('.note-edit-field'),text=b.hasAttribute('data-note-save')?t.value.trim():t.defaultValue;if(!text){t.focus();return}const p=document.createElement('p'),a=document.createElement('div');p.className='note-content';p.textContent=text;a.className='note-owner-actions';a.setAttribute('aria-label','Управление заметкой');a.innerHTML='<button type="button" data-note-action="edit">Редактировать</button><button type="button" data-confirm-delete="note">Удалить</button>';t.replaceWith(p);n.querySelector('.note-edit-actions').replaceWith(a)})})();

(()=>{const m=document.querySelector('[data-confirmation-modal]');if(!m)return;const h=m.querySelector('[data-confirmation-title]'),d=m.querySelector('[role="dialog"]'),l=document.querySelector('[data-notes-list]'),z=document.querySelector('[data-notes-empty]');let x,f;const close=()=>{m.hidden=true;x=null;f?.focus()};document.addEventListener('click',e=>{const b=e.target.closest('[data-confirm-delete]');if(b){x=b;f=b;h.textContent=b.dataset.confirmDelete==='recipe'?'Удалить рецепт?':'Удалить заметку?';m.hidden=false;d.focus()}if(e.target.closest('[data-modal-close]'))close();if(e.target.closest('[data-confirmation-submit]')&&x){if(x.dataset.confirmDelete==='note'){x.closest('[data-note]').remove();z.hidden=!!l.querySelector('[data-note]')}else console.info('Recipe deletion demo confirmed');close()}});document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!m.hidden)close()})})();
