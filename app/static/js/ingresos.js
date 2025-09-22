// ingresos.js - manejo asíncrono del formulario de ingresos
(function(){
  'use strict';

  function qs(sel){ return document.querySelector(sel); }
  function qsa(sel){ return Array.from(document.querySelectorAll(sel)); }

  function formatCLP(x){ return new Intl.NumberFormat('es-CL',{style:'currency',currency:'CLP'}).format(x); }

  function getCsrfToken(){
    const meta = document.querySelector('meta[name="csrf-token"]');
    if(meta && meta.content) return meta.content;
    const hidden = document.querySelector('input[name="csrf_token"]');
    if(hidden && hidden.value) return hidden.value;
    const cookies = document.cookie.split(';').map(c=>c.trim());
    for(const c of cookies){ if(c.startsWith('XSRF-TOKEN=')) return decodeURIComponent(c.split('=')[1]); if(c.startsWith('csrf_token=')) return decodeURIComponent(c.split('=')[1]); }
    return null;
  }

  function showAlert(container, message, category='danger'){
    if(!container) return;
    const div = document.createElement('div');
    div.className = `alert alert-${category}`;
    div.setAttribute('role','alert');
    div.textContent = message;
    container.innerHTML = '';
    container.appendChild(div);
    div.tabIndex = -1; div.focus();
  }

  document.addEventListener('DOMContentLoaded', function(){
    const form = qs('form[method="POST"]');
    const btnSave = qs('#btnSave');
    const modalEl = qs('#modalGuardando');
    const modal = modalEl ? new bootstrap.Modal(modalEl) : null;
    const alerts = document.getElementById('ingresosAlerts');

    function collectFormData(){
      const fd = new FormData(form);
      // Ensure we send arrays correctly
      return new URLSearchParams([...fd.entries()]);
    }

    async function submitAsync(e){
      e.preventDefault();

      // Validación mínima: al menos un recibido > 0
      const hasIngresos = qsa('input[name="recibido_linea[]"]').some(i => parseInt(i.value,10) > 0);
      if(!hasIngresos){ showAlert(alerts, 'Debe ingresar al menos una cantidad recibida antes de guardar.', 'warning'); return; }

      // Mostrar modal y bloquear UI
      if(btnSave){ btnSave.disabled = true; btnSave.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Guardando...'; }
      if(modal) modal.show();

      try{
        const csrfToken = getCsrfToken();
        const headers = {
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        };
        if(csrfToken) headers['X-CSRFToken'] = csrfToken;

        const resp = await fetch(form.action || window.location.pathname, {
          method: 'POST',
          headers,
          body: collectFormData().toString(),
          credentials: 'same-origin'
        });

        const contentType = resp.headers.get('Content-Type') || '';
        if(contentType.includes('application/json')){
          const data = await resp.json();
          if(data.success){
            showAlert(alerts, data.message || 'Ingreso guardado correctamente', 'success');
            // Si el backend devuelve redirect, recargar la vista para reflejar cambios
            if(data.redirect){ window.location.href = data.redirect; return; }
            // Opcional: limpiar inputs recibidos para reflejar que fueron guardados
            qsa('input[name="recibido_linea[]"]').forEach(i => i.value = 0);
            // Actualizar sumas y estado visual
            document.querySelectorAll('td.clp').forEach(td => {
              const val = parseFloat(td.dataset.neto || td.textContent.replace(/[^0-9.-]+/g,'')) || 0;
              td.textContent = formatCLP(val);
            });
            // Forzar recalculo
            if(typeof window.actualizarSumas === 'function') window.actualizarSumas();
            if(typeof window.checkCompleto === 'function') window.checkCompleto();
          } else {
            showAlert(alerts, data.message || 'Error al guardar', 'danger');
          }
        } else {
          // No JSON: fallback -> recarga completa
          window.location.reload();
        }
      } catch(err){
        console.error('Error en submit asíncrono:', err);
        showAlert(alerts, 'Error de red. Intenta nuevamente.', 'danger');
      } finally{
        if(modal) modal.hide();
        if(btnSave){ btnSave.disabled = false; btnSave.innerHTML = '<i class="bi bi-save me-2"></i>Guardar Ingreso'; }
      }
    }

    // Sólo usar submit asíncrono si fetch y bootstrap están disponibles
    if(form && window.fetch){
      form.addEventListener('submit', submitAsync);
    }
  });

})();
