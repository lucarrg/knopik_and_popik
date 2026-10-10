(() => {
  document.querySelectorAll('[data-add-form]').forEach((button) => {
    button.addEventListener('click', () => {
      const prefix = button.dataset.addForm;
      const totalForms = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
      const template = document.getElementById(`${prefix}-empty-form`);
      const container = document.querySelector(`[data-formset="${prefix}"]`);
      if (!totalForms || !template || !container) return;

      const index = totalForms.value;
      const fragment = template.content.cloneNode(true);
      fragment.querySelectorAll('[name], [id], label[for]').forEach((element) => {
        ['name', 'id', 'for'].forEach((attribute) => {
          if (element.hasAttribute(attribute)) {
            element.setAttribute(attribute, element.getAttribute(attribute).replace(/__prefix__/g, index));
          }
        });
      });
      container.append(fragment);
      totalForms.value = Number(index) + 1;
    });
  });
})();