// Resizable columns for pendientesTable
(function() {
  function makeResizable(table) {
    const ths = table.querySelectorAll('th');
    ths.forEach((th, i) => {
      if (i === ths.length - 1) return; // Skip last column (actions)
      const resizer = document.createElement('div');
      resizer.className = 'resizer';
      th.style.position = 'relative';
      resizer.style.position = 'absolute';
      resizer.style.right = 0;
      resizer.style.top = 0;
      resizer.style.width = '6px';
      resizer.style.height = '100%';
      resizer.style.cursor = 'col-resize';
      resizer.style.userSelect = 'none';
      resizer.style.zIndex = 10;
      th.appendChild(resizer);
      let startX, startWidth;
      resizer.addEventListener('mousedown', function(e) {
        startX = e.pageX;
        startWidth = th.offsetWidth;
        document.body.style.cursor = 'col-resize';
        function onMove(e2) {
          const newWidth = Math.max(50, startWidth + (e2.pageX - startX));
          th.style.width = newWidth + 'px';
        }
        function onUp() {
          document.removeEventListener('mousemove', onMove);
          document.removeEventListener('mouseup', onUp);
          document.body.style.cursor = '';
        }
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
      });
    });
  }
  document.addEventListener('DOMContentLoaded', function() {
    const table = document.getElementById('pendientesTable');
    if (table) makeResizable(table);
  });
})();
