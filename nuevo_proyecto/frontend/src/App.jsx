import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
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

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

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

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
    
    // Redirigir a la página que intentaba acceder antes del login
    const redirectPath = sessionStorage.getItem('redirectAfterLogin');
    if (redirectPath && redirectPath !== '/login') {
      sessionStorage.removeItem('redirectAfterLogin');
      window.location.href = redirectPath;
    }
  };

  const handleLogout = () => {
    removeAuthToken();
    setIsAuthenticated(false);
  };

  const handleSidebarToggle = (collapsed) => {
    setSidebarCollapsed(collapsed);
  };

  return (
    <Router>
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
                    <Route path="/gestion-usuarios" element={<GestionUsuarios />} />
                  </Routes>
                </div>
              </div>
            </ProtectedRoute>
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;