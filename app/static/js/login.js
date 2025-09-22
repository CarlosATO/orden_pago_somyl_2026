// login.js
// Maneja el envío del formulario de login vía fetch, muestra loading, y procesa respuestas JSON del servidor.
(function () {
  'use strict';

  function qs(id) { return document.getElementById(id); }

  function getCsrfToken() {
    // 1) meta tag <meta name="csrf-token" content="...">
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    // 2) hidden input named csrf_token
    const hidden = document.querySelector('input[name="csrf_token"]');
    if (hidden && hidden.value) return hidden.value;
    // 3) cookie common names (XSRF-TOKEN, csrf_token)
    const cookies = document.cookie.split(';').map(c => c.trim());
    for (const c of cookies) {
      if (c.startsWith('XSRF-TOKEN=')) return decodeURIComponent(c.split('=')[1]);
      if (c.startsWith('csrf_token=')) return decodeURIComponent(c.split('=')[1]);
    }
    return null;
  }

  function showAlert(container, message, category) {
    // category: success, danger, warning, info
    const div = document.createElement('div');
    div.className = `alert alert-${category}`;
    div.setAttribute('role', 'alert');
    div.textContent = message;
    // Limpiar contenedor y mostrar
    container.innerHTML = '';
    container.appendChild(div);
    // Focus en el alert para accesibilidad
    div.tabIndex = -1;
    div.focus();
  }

  document.addEventListener('DOMContentLoaded', function () {
    const form = qs('loginForm');
    const btn = qs('btnLogin');
    const loading = qs('loginLoading');
    const alerts = qs('loginAlerts');

    if (!form) return;

    form.addEventListener('submit', async function (e) {
      // Si el botón ya está deshabilitado, prevenir reenvío
      if (btn && btn.disabled) {
        e.preventDefault();
        return;
      }

      // Solo interceptamos si fetch está disponible
      if (!window.fetch) return;

      e.preventDefault();

      // Preparar datos del formulario
      const formData = new FormData(form);
      const payload = new URLSearchParams();
      for (const pair of formData.entries()) {
        payload.append(pair[0], pair[1]);
      }

      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Conectando...';
      }
      if (loading) loading.style.display = 'block';

      try {
        const csrfToken = getCsrfToken();
        const headers = {
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        };
        if (csrfToken) headers['X-CSRFToken'] = csrfToken;

        const resp = await fetch(form.action || window.location.pathname, {
          method: 'POST',
          headers,
          body: payload.toString(),
          credentials: 'same-origin'
        });

        if (resp.headers.get('Content-Type') && resp.headers.get('Content-Type').includes('application/json')) {
          const data = await resp.json();
          if (data.success) {
            // Redirigir si el backend indica redirect
            if (data.redirect) {
              window.location.href = data.redirect;
              return;
            }
            // Si éxito sin redirect, mostrar mensaje
            if (alerts) showAlert(alerts, data.message || 'Login exitoso', 'success');
          } else {
            // Mostrar error retornado
            if (alerts) showAlert(alerts, data.message || 'Error en el login', 'danger');
          }
        } else {
          // Si no viene JSON, fallback: recargar la página para que el servidor renderice
          window.location.reload();
          return;
        }
      } catch (err) {
        if (alerts) showAlert(alerts, 'Error de red. Intenta de nuevo.', 'danger');
        console.error('Login fetch error', err);
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-box-arrow-in-right me-2"></i>Ingresar al Sistema';
        }
        if (loading) loading.style.display = 'none';
      }
    }, { passive: false });
  });
})();
