import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import Login from './components/Login';
import Sidebar from './components/Sidebar';
import ProtectedRoute from './components/ProtectedRoute';
import Dashboard from './components/Dashboard';
import OrdenCompra from './components/OrdenCompra';
import Ingresos from './components/Ingresos';
import OrdenesPago from './components/OrdenesPago';
import ProveedoresPage from './components/ProveedoresPage';
import ProyectosPage from './components/ProyectosPage';
import MaterialesPage from './components/MaterialesPage';
import Items from './components/Items';
import Trabajadores from './components/Trabajadores';
import Usuarios from './components/Usuarios';
import ChangePassword from './components/ChangePassword';
import Presupuestos from './components/Presupuestos';
import Pagos from './components/Pagos';
import DocumentosPendientes from './components/DocumentosPendientes';
import EstadoPresupuesto from './components/EstadoPresupuesto';
import GastosDirectos from './components/GastosDirectos';
import OrdenesNoRecepcionadas from './components/OrdenesNoRecepcionadas';
import { isTokenValid, removeAuthToken } from './utils/auth';
import './App.css';

// Componentes placeholder para cada sección
function OrdenesCompra() {
  return <OrdenCompra />;
}

function IngresosRecepciones() {
  return <Ingresos />;
}

function OrdenesPagoView() {
  return <OrdenesPago />;
}

function FacturacionPendiente() {
  return <DocumentosPendientes />;
}

function InformePagos() {
  return <Pagos />;
}

function PlanificacionPresupuestaria() {
  return <div className="content"><h1>Planificación Presupuestaria</h1><p>Definición de presupuestos por proyecto/centro de costo.</p></div>;
}

function RegistroGastosDirectos() {
  return <GastosDirectos />;
}

// EstadoPresupuesto component is imported from ./components/EstadoPresupuesto

// Usamos el componente real `OrdenesNoRecepcionadas` importado arriba

function Proyectos() {
  return <ProyectosPage />;
}

function Proveedores() {
  return <ProveedoresPage />;
}

function Materiales() {
  return <MaterialesPage />;
}

function MaterialesServicios() {
  return <MaterialesPage />;
}

function ItemsPresupuestarios() {
  return <Items />;
}

function TrabajadoresSolicitantes() {
  return <Trabajadores />;
}

function GestionUsuarios() {
  return <Usuarios />;
}

// Componente interno que tiene acceso a useNavigate
function AppContent() {
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    // Verificar SSO token en la URL al inicializar
    const params = new URLSearchParams(window.location.search);
    const ssoToken = params.get('sso_token');
    const ssoUser = params.get('sso_user');
    const referrer = params.get('referrer');
    if (ssoToken) {
      console.log("⚡️ SSO Token detectado al inicializar. Iniciando sesión...");
      try {
        setAuthToken(ssoToken);
      } catch (e) {
        sessionStorage.setItem('authToken', ssoToken);
      }
      if (ssoUser) {
        localStorage.setItem('rememberedEmail', ssoUser);
      }
      if (referrer) {
        sessionStorage.setItem('sso_referrer', referrer);
      }
      return true; // Autenticado por SSO
    }
    return isTokenValid(); // Verificar token normal
  });
  const [accessDenied, setAccessDenied] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    const ssoToken = params.get('sso_token');
    return !ssoToken && !isTokenValid();
  });
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [checkedTempPassword, setCheckedTempPassword] = useState(false);
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false);

  // ==============================================================
  // 🚀 DETECTOR DE SSO GLOBAL (para cualquier ruta)
  // ==============================================================
  // NAVEGACIÓN PARA SSO
  // ==============================================================
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const ssoToken = params.get('sso_token');
    if (ssoToken) {
      console.log("⚡️ Navegando a dashboard por SSO...");
      navigate('/dashboard', { replace: true });
    }
  }, [navigate]); // Fin de navegación SSO
  // ==============================================================

  // Verificar autenticación al montar el componente
  useEffect(() => {
    const checkAuth = () => {
      const valid = isTokenValid();
      setIsAuthenticated(valid);
      
      if (!valid) {
        removeAuthToken(); // Limpiar tokens inválidos
      }
    };
    
    checkAuth();
    
    // Verificar cada 5 minutos si el token sigue siendo válido
    const interval = setInterval(checkAuth, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, []);

  // Si el usuario está autenticado, verificar si tiene contraseña temporal
  useEffect(() => {
    const checkTemp = async () => {
      if (!isAuthenticated) return;
      if (checkedTempPassword) return; // evitar repetir

      try {
        const token = sessionStorage.getItem('authToken');
        console.log('Checking temp password with token present?', !!token);
        const resp = await fetch('/api/usuarios/check-temp-password', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        console.log('check-temp-password response status:', resp.status);
        if (resp.ok) {
          const data = await resp.json();
          console.log('check-temp-password response data:', data);
          if (data && data.temp_password) {
            console.log('Usuario con contraseña temporal - redirigiendo a cambiar contraseña');
            // Forzar a cambiar contraseña
            navigate('/cambiar-contrasena', { replace: true });
          } else {
            console.log('No es contraseña temporal');
          }
        } else {
          console.warn('check-temp-password no respondió OK');
        }
      } catch (err) {
        console.error('Error verificando contraseña temporal', err);
      } finally {
        setCheckedTempPassword(true);
      }
    };

    checkTemp();
  }, [isAuthenticated, checkedTempPassword, navigate]);

  // Si el login indicó fuerza de cambio de contraseña (bandera en sessionStorage), abrir modal
  useEffect(() => {
    if (!isAuthenticated) return;
    try {
      const forced = sessionStorage.getItem('forceChangePassword');
      if (forced) {
        console.log('Flag forceChangePassword detectada en sessionStorage -> abrir modal');
        setShowChangePasswordModal(true);
        sessionStorage.removeItem('forceChangePassword');
      }
    } catch (e) {
      // ignore
    }
  }, [isAuthenticated]);

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    // Limpiar tokens y datos locales
    try { removeAuthToken(); } catch (e) { /* ignore */ }
    try { localStorage.clear(); } catch (e) { /* ignore */ }
    try { sessionStorage.clear(); } catch (e) { /* ignore */ }
    // Redirigir directamente al referrer SSO o al portal por defecto (sin cambiar estado para evitar flash del login)
    const referrer = sessionStorage.getItem('sso_referrer') || 'https://portal.datix.cl';
    window.location.href = referrer;
  };

  const handleSidebarToggle = (collapsed) => {
    setSidebarCollapsed(collapsed);
  };

  // Componente de acceso denegado
  const AccessDenied = () => (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      backgroundColor: '#f5f5f5',
      fontFamily: 'Arial, sans-serif'
    }}>
      <h1 style={{ color: '#333', marginBottom: '20px' }}>Acceso Denegado</h1>
      <p style={{ color: '#666', textAlign: 'center', marginBottom: '30px' }}>
        Esta aplicación se ha mudado al portal. Por favor, ingrese desde el portal oficial.
      </p>
      <a 
        href="https://portal.datix.cl" 
        style={{
          backgroundColor: '#007bff',
          color: 'white',
          padding: '10px 20px',
          textDecoration: 'none',
          borderRadius: '5px',
          fontSize: '16px'
        }}
      >
        Ir al Portal
      </a>
    </div>
  );

  if (accessDenied) {
    return <AccessDenied />;
  }

  return (
    <div className="App">
      <Routes>
        {/* Ruta de login pública */}
        <Route 
          path="/login" 
          element={
            isAuthenticated ? 
              <Navigate to="/dashboard" replace /> : 
              <Login onLoginSuccess={handleLoginSuccess} />
          } 
        />
        
        {/* Rutas protegidas */}
        <Route path="/*" element={
          <ProtectedRoute>
            <div className="app-layout">
              <Sidebar onLogout={handleLogout} onToggle={handleSidebarToggle} />
              <div className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/ordenes-compra" element={<OrdenesCompra />} />
                  <Route path="/ingresos-recepciones" element={<IngresosRecepciones />} />
                  <Route path="/ordenes-pago" element={<OrdenesPagoView />} />
                  <Route path="/presupuestos" element={<Presupuestos />} />
                  <Route path="/pagos" element={<Pagos />} />
                  <Route path="/documentos-pendientes" element={<DocumentosPendientes />} />
                  <Route path="/facturacion-pendiente" element={<FacturacionPendiente />} />
                  <Route path="/informe-pagos" element={<InformePagos />} />
                  <Route path="/planificacion-presupuestaria" element={<PlanificacionPresupuestaria />} />
                  <Route path="/registro-gastos-directos" element={<RegistroGastosDirectos />} />
                  <Route path="/estado-presupuesto" element={<EstadoPresupuesto />} />
                  <Route path="/ordenes-no-recepcionadas" element={<OrdenesNoRecepcionadas />} />
                  <Route path="/proyectos" element={<Proyectos />} />
                  <Route path="/proveedores" element={<Proveedores />} />
                  <Route path="/materiales" element={<Materiales />} />
                  <Route path="/items-presupuestarios" element={<ItemsPresupuestarios />} />
                  <Route path="/trabajadores-solicitantes" element={<TrabajadoresSolicitantes />} />
                  <Route path="/cambiar-contrasena" element={<ChangePassword />} />
                  <Route path="/gestion-usuarios" element={<GestionUsuarios />} />
                </Routes>
                {/* Mostrar ChangePassword como modal si fue forzado tras el login */}
                {showChangePasswordModal && (
                  <div className="modal-overlay" onClick={() => setShowChangePasswordModal(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                      <ChangePassword onClose={() => setShowChangePasswordModal(false)} />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </ProtectedRoute>
        } />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;