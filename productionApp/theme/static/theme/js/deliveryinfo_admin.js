(function() {
  function findRow(el) {
    // Django >=3 usa .form-row (ou .fieldBox em algumas versões/temas)
    return el.closest('.form-row') || el.closest('.fieldBox') || el.closest('.form-group');
  }

  function toggleEntityField() {
    var typeSelect = document.getElementById('id_deliveryType');
    var entityInput = document.getElementById('id_deliveryEntity');

    if (!typeSelect || !entityInput) return;

    var row = findRow(entityInput);
    var selectedText = '';
    if (typeSelect.tagName === 'SELECT') {
      selectedText = (typeSelect.options[typeSelect.selectedIndex] || {}).text || typeSelect.value || '';
    } else {
      selectedText = typeSelect.value || '';
    }
    var isCustomer = selectedText.trim().toLowerCase() === 'customer';

    // Esconde e desativa quando Customer
    if (row) row.style.display = isCustomer ? 'none' : '';
    entityInput.disabled = isCustomer;
  }

  document.addEventListener('DOMContentLoaded', function() {
    toggleEntityField();
    var typeSelect = document.getElementById('id_deliveryType');
    if (typeSelect) {
      typeSelect.addEventListener('change', toggleEntityField);
    }
  });
})();
