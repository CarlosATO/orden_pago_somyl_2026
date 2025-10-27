import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './Sidebar.css';

function Sidebar({ onLogout, onToggle }) {
  // isCollapsed controla si el sidebar está reducido (solo íconos)
  const [isCollapsed, setIsCollapsed] = useState(false);
  // activeMenu almacena la clave del submenu abierto; null = ninguno
  const [activeMenu, setActiveMenu] = useState(null);

  // NUEVO: Notificar al padre cuando cambie isCollapsed
  useEffect(() => {
    if (onToggle) {
      onToggle(isCollapsed);
    }
  }, [isCollapsed, onToggle]);

  const toggleCollapse = () => {
    setIsCollapsed(prev => !prev);
    // al colapsar cerramos cualquier submenu
    setActiveMenu(null);
  };

  const toggleMenu = (menu) => {
    setActiveMenu(prev => (prev === menu ? null : menu));
  };

  const menuClass = isCollapsed ? 'sidebar collapsed' : 'sidebar';

  return (
    <div className={menuClass}>
      <div className="sidebar-header">
        <div className="brand">
          {!isCollapsed && <h2>Sistema de Gestión</h2>}
        </div>
        <button className="collapse-btn" onClick={toggleCollapse} aria-label="Toggle sidebar">
          {isCollapsed ? '›' : '‹'}
        </button>
      </div>

      <nav className="sidebar-nav">
        <ul>
          <li>
            <Link to="/dashboard" className="nav-link">
              <span className="icon">📊</span>
              {!isCollapsed && <span className="label">Dashboard / Inicio</span>}
            </Link>
          </li>

          <li className="has-sub">
            <div className="menu-item" onClick={() => toggleMenu('adquisiciones')}>
              <div>
                <span className="icon">🛒</span>
                {!isCollapsed && <span className="label">Adquisiciones</span>}
              </div>
              {!isCollapsed && <span className="arrow">{activeMenu === 'adquisiciones' ? '▾' : '▸'}</span>}
            </div>
            {activeMenu === 'adquisiciones' && (
              <ul className={isCollapsed ? 'submenu overlay' : 'submenu'}>
                <li><Link to="/ordenes-compra">Órdenes de Compra</Link></li>
                <li><Link to="/ingresos-recepciones">Ingresos / Recepciones</Link></li>
              </ul>
            )}
          </li>

          <li className="has-sub">
            <div className="menu-item" onClick={() => toggleMenu('pagos')}>
              <div>
                <span className="icon">💰</span>
                {!isCollapsed && <span className="label">Gestión de Pagos</span>}
              </div>
              {!isCollapsed && <span className="arrow">{activeMenu === 'pagos' ? '▾' : '▸'}</span>}
            </div>
            {activeMenu === 'pagos' && (
              <ul className={isCollapsed ? 'submenu overlay' : 'submenu'}>
                <li><Link to="/ordenes-pago">Órdenes de Pago</Link></li>
                <li><Link to="/facturacion-pendiente">Facturación Pendiente</Link></li>
                <li><Link to="/informe-pagos">Informe de Pagos</Link></li>
              </ul>
            )}
          </li>

          <li className="has-sub">
            <div className="menu-item" onClick={() => toggleMenu('presupuesto')}>
              <div>
                <span className="icon">📉</span>
                {!isCollapsed && <span className="label">Control Presupuestario</span>}
              </div>
              {!isCollapsed && <span className="arrow">{activeMenu === 'presupuesto' ? '▾' : '▸'}</span>}
            </div>
            {activeMenu === 'presupuesto' && (
              <ul className={isCollapsed ? 'submenu overlay' : 'submenu'}>
                <li><Link to="/presupuestos">Planificación Presupuestaria</Link></li>
                <li><Link to="/registro-gastos-directos">Registro de Gastos Directos</Link></li>
                <li><Link to="/estado-presupuesto">Estado de Presupuesto</Link></li>
              </ul>
            )}
          </li>

          <li className="has-sub">
            <div className="menu-item" onClick={() => toggleMenu('informes')}>
              <div>
                <span className="icon">📈</span>
                {!isCollapsed && <span className="label">Informes y Análisis</span>}
              </div>
              {!isCollapsed && <span className="arrow">{activeMenu === 'informes' ? '▾' : '▸'}</span>}
            </div>
            {activeMenu === 'informes' && (
              <ul className={isCollapsed ? 'submenu overlay' : 'submenu'}>
                <li><Link to="/ordenes-no-recepcionadas">Órdenes No Recepcionadas</Link></li>
                <li><Link to="/pagos">Informe Pagos</Link></li>
              </ul>
            )}
          </li>

          <li className="has-sub">
            <div className="menu-item" onClick={() => toggleMenu('configuracion')}>
              <div>
                <span className="icon">⚙️</span>
                {!isCollapsed && <span className="label">Configuración</span>}
              </div>
              {!isCollapsed && <span className="arrow">{activeMenu === 'configuracion' ? '▾' : '▸'}</span>}
            </div>
            {activeMenu === 'configuracion' && (
              <ul className={isCollapsed ? 'submenu overlay' : 'submenu'}>
                <li><Link to="/proyectos">Proyectos</Link></li>
                <li><Link to="/proveedores">Proveedores</Link></li>
                <li><Link to="/materiales">Materiales / Servicios</Link></li>
                <li><Link to="/items-presupuestarios">Ítems Presupuestarios</Link></li>
                <li><Link to="/trabajadores-solicitantes">Trabajadores / Solicitantes</Link></li>
              </ul>
            )}
          </li>

          <li className="has-sub">
            <div className="menu-item" onClick={() => toggleMenu('administracion')}>
              <div>
                <span className="icon">👤</span>
                {!isCollapsed && <span className="label">Administración del Sistema</span>}
              </div>
              {!isCollapsed && <span className="arrow">{activeMenu === 'administracion' ? '▾' : '▸'}</span>}
            </div>
            {activeMenu === 'administracion' && (
              <ul className={isCollapsed ? 'submenu overlay' : 'submenu'}>
                <li><Link to="/gestion-usuarios">Gestión de Usuarios</Link></li>
              </ul>
            )}
          </li>
        </ul>
      </nav>
      <div className="sidebar-footer">
        <button className="sidebar-logout-btn" onClick={onLogout}>
          <span className="icon">🔒</span>
          {!isCollapsed && <span className="label">Cerrar Sesión</span>}
        </button>
      </div>
    </div>
  );
}

export default Sidebar;