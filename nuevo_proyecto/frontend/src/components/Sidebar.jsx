import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getCurrentUser } from '../utils/auth';
import './Sidebar.css';

function Sidebar({ onLogout, onToggle }) {
  // isCollapsed controla si el sidebar está reducido (solo íconos)
  const [isCollapsed, setIsCollapsed] = useState(false);
  // activeMenu almacena la clave del submenu abierto; null = ninguno
  const [activeMenu, setActiveMenu] = useState(null);
  // Usuario actual
  const [currentUser, setCurrentUser] = useState(null);

  // Obtener usuario al montar el componente
  useEffect(() => {
    const user = getCurrentUser();
    setCurrentUser(user);
  }, []);

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
        <button className="collapse-btn" onClick={toggleCollapse} aria-label="Toggle sidebar" title={isCollapsed ? "Expandir menú" : "Contraer menú"}>
          {isCollapsed ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          )}
        </button>
      </div>

      <nav className="sidebar-nav">
        <ul>
          {/* Dashboard - Link directo */}
          <li>
            <Link to="/dashboard" className="nav-link">
              <i className="fas fa-chart-line"></i>
              {!isCollapsed && <span className="label">Dashboard</span>}
            </Link>
          </li>

          {/* Adquisiciones - Flujo completo de compra */}
          <li className="has-sub">
            <div className="menu-item" onClick={() => toggleMenu('adquisiciones')}>
              <div className="menu-content">
                <i className="fas fa-shopping-cart"></i>
                {!isCollapsed && <span className="label">Adquisiciones</span>}
              </div>
              {!isCollapsed && (
                <i className={`arrow fas fa-chevron-${activeMenu === 'adquisiciones' ? 'down' : 'right'}`}></i>
              )}
            </div>
            {activeMenu === 'adquisiciones' && (
              <ul className={isCollapsed ? 'submenu overlay' : 'submenu'}>
                <li><Link to="/ordenes-compra"><i className="fas fa-file-alt"></i> Órdenes de Compra</Link></li>
                <li><Link to="/ingresos-recepciones"><i className="fas fa-box-open"></i> Ingresos / Recepciones</Link></li>
                <li><Link to="/ordenes-no-recepcionadas"><i className="fas fa-truck-loading"></i> Órdenes No Recepcionadas</Link></li>
                <li><Link to="/documentos-pendientes"><i className="fas fa-file-invoice"></i> Documentos Pendientes</Link></li>
              </ul>
            )}
          </li>

          {/* Pagos - Flujo completo de pago */}
          <li className="has-sub">
            <div className="menu-item" onClick={() => toggleMenu('pagos')}>
              <div className="menu-content">
                <i className="fas fa-money-check-dollar"></i>
                {!isCollapsed && <span className="label">Pagos</span>}
              </div>
              {!isCollapsed && (
                <i className={`arrow fas fa-chevron-${activeMenu === 'pagos' ? 'down' : 'right'}`}></i>
              )}
            </div>
            {activeMenu === 'pagos' && (
              <ul className={isCollapsed ? 'submenu overlay' : 'submenu'}>
                <li><Link to="/ordenes-pago"><i className="fas fa-file-invoice-dollar"></i> Órdenes de Pago</Link></li>
                <li><Link to="/pagos"><i className="fas fa-chart-bar"></i> Informe de Pagos</Link></li>
              </ul>
            )}
          </li>

          {/* Presupuestos - Control presupuestario */}
          <li className="has-sub">
            <div className="menu-item" onClick={() => toggleMenu('presupuestos')}>
              <div className="menu-content">
                <i className="fas fa-chart-pie"></i>
                {!isCollapsed && <span className="label">Presupuestos</span>}
              </div>
              {!isCollapsed && (
                <i className={`arrow fas fa-chevron-${activeMenu === 'presupuestos' ? 'down' : 'right'}`}></i>
              )}
            </div>
            {activeMenu === 'presupuestos' && (
              <ul className={isCollapsed ? 'submenu overlay' : 'submenu'}>
                <li><Link to="/presupuestos"><i className="fas fa-project-diagram"></i> Presupuestos por Proyecto</Link></li>
                <li><Link to="/registro-gastos-directos"><i className="fas fa-receipt"></i> Gastos Directos</Link></li>
                <li><Link to="/estado-presupuesto"><i className="fas fa-chart-area"></i> Estado General</Link></li>
              </ul>
            )}
          </li>

          {/* Maestros - Datos base del sistema */}
          <li className="has-sub">
            <div className="menu-item" onClick={() => toggleMenu('maestros')}>
              <div className="menu-content">
                <i className="fas fa-database"></i>
                {!isCollapsed && <span className="label">Maestros</span>}
              </div>
              {!isCollapsed && (
                <i className={`arrow fas fa-chevron-${activeMenu === 'maestros' ? 'down' : 'right'}`}></i>
              )}
            </div>
            {activeMenu === 'maestros' && (
              <ul className={isCollapsed ? 'submenu overlay' : 'submenu'}>
                <li><Link to="/proveedores"><i className="fas fa-truck"></i> Proveedores</Link></li>
                <li><Link to="/proyectos"><i className="fas fa-building"></i> Proyectos</Link></li>
                <li><Link to="/materiales"><i className="fas fa-boxes"></i> Materiales / Servicios</Link></li>
                <li><Link to="/trabajadores-solicitantes"><i className="fas fa-users"></i> Trabajadores</Link></li>
                <li><Link to="/items-presupuestarios"><i className="fas fa-list-ul"></i> Ítems Presupuestarios</Link></li>
              </ul>
            )}
          </li>

          {/* Administración - Gestión del sistema */}
          <li className="has-sub">
            <div className="menu-item" onClick={() => toggleMenu('administracion')}>
              <div className="menu-content">
                <i className="fas fa-user-shield"></i>
                {!isCollapsed && <span className="label">Administración</span>}
              </div>
              {!isCollapsed && (
                <i className={`arrow fas fa-chevron-${activeMenu === 'administracion' ? 'down' : 'right'}`}></i>
              )}
            </div>
            {activeMenu === 'administracion' && (
              <ul className={isCollapsed ? 'submenu overlay' : 'submenu'}>
                <li><Link to="/gestion-usuarios"><i className="fas fa-users-cog"></i> Gestión de Usuarios</Link></li>
              </ul>
            )}
          </li>
        </ul>
      </nav>
      <div className="sidebar-footer">
        {/* Perfil del Usuario */}
        {currentUser && (
          <div className="user-profile">
            <div className="user-avatar">
              <i className="fas fa-user-circle"></i>
            </div>
            {!isCollapsed && (
              <div className="user-info">
                <span className="user-name">{currentUser.nombre}</span>
                <span className="user-email">{currentUser.email}</span>
              </div>
            )}
          </div>
        )}
        
        {/* Botón de Cerrar Sesión */}
        <button 
          className={`sidebar-logout-btn ${isCollapsed ? 'collapsed' : ''}`} 
          onClick={onLogout}
          title="Cerrar Sesión"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
          {!isCollapsed && <span className="label">Cerrar Sesión</span>}
        </button>
      </div>
    </div>
  );
}

export default Sidebar;