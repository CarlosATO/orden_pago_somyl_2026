import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Login from './components/Login';
import Sidebar from './components/Sidebar';
import OrdenCompra from './components/OrdenCompra';
import Ingresos from './components/Ingresos';
import OrdenesPago from './components/ordenesPago';
import ProveedoresPage from './components/ProveedoresPage';
import ProyectosPage from './components/ProyectosPage';
import MaterialesPage from './components/MaterialesPage';
import Items from './components/Items';
import Trabajadores from './components/Trabajadores';
import Presupuestos from './components/Presupuestos';
import Pagos from './components/Pagos';
import DocumentosPendientes from './components/DocumentosPendientes';
import EstadoPresupuesto from './components/EstadoPresupuesto';
import './App.css';

// Componentes placeholder para cada sección
function Dashboard() {
  return <div className="content"><h1>📊 Dashboard / Inicio</h1><p>Visión general, KPIs, accesos rápidos.</p></div>;
}

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
  return <div className="content"><h1>Registro de Gastos Directos</h1><p>Entrada de gastos sin OC que afectan al presupuesto.</p></div>;
}

// EstadoPresupuesto component is imported from ./components/EstadoPresupuesto

function OrdenesNoRecepcionadas() {
  return <div className="content"><h1>Órdenes No Recepcionadas</h1><p>Reporte específico.</p></div>;
}

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
  return <div className="content"><h1>Gestión de Usuarios</h1><p>Crear usuarios, asignar roles/permisos.</p></div>;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('authToken'));
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    setIsAuthenticated(false);
  };

  const handleSidebarToggle = (collapsed) => {
    setSidebarCollapsed(collapsed);
  };

  return (
    <Router>
      <div className="App">
        {isAuthenticated ? (
          <div className="app-layout">
            <Sidebar onLogout={handleLogout} onToggle={handleSidebarToggle} />
            <div className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
              <Routes>
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
                <Route path="/" element={<Dashboard />} />
              </Routes>
            </div>
          </div>
        ) : (
          <Login onLoginSuccess={handleLoginSuccess} />
        )}
      </div>
    </Router>
  );
}

export default App;