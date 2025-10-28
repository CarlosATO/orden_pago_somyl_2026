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

function OrdenesPago() {
  return <div className="content"><h1>Órdenes de Pago</h1><p>Autorizaciones de pago a proveedores (basadas en ingresos/facturas).</p></div>;
}

function FacturacionPendiente() {
  return <div className="content"><h1>Facturación Pendiente</h1><p>Seguimiento de ingresos/OCs que aún no tienen factura asociada.</p></div>;
}

function InformePagos() {
  return <div className="content"><h1>Informe de Pagos</h1><p>Historial y estado de los pagos efectuados.</p></div>;
}

function PlanificacionPresupuestaria() {
  return <div className="content"><h1>Planificación Presupuestaria</h1><p>Definición de presupuestos por proyecto/centro de costo.</p></div>;
}

function RegistroGastosDirectos() {
  return <div className="content"><h1>Registro de Gastos Directos</h1><p>Entrada de gastos sin OC que afectan al presupuesto.</p></div>;
}

function EstadoPresupuesto() {
  return <div className="content"><h1>Estado de Presupuesto</h1><p>Visualización comparativa del presupuesto vs. gastos (incluye OCs, pagos y gastos directos).</p></div>;
}

function OrdenesNoRecepcionadas() {
  return <div className="content"><h1>Órdenes No Recepcionadas</h1><p>Reporte específico.</p></div>;
}

function Proyectos() {
  return <div className="content"><h1>Proyectos</h1></div>;
}

function Proveedores() {
  return <div className="content"><h1>Proveedores</h1></div>;
}

function MaterialesServicios() {
  return <div className="content"><h1>Materiales / Servicios</h1></div>;
}

function ItemsPresupuestarios() {
  return <div className="content"><h1>Ítems Presupuestarios</h1></div>;
}

function TrabajadoresSolicitantes() {
  return <div className="content"><h1>Trabajadores / Solicitantes</h1></div>;
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
                <Route path="/ordenes-pago" element={<OrdenesPago />} />
                <Route path="/facturacion-pendiente" element={<FacturacionPendiente />} />
                <Route path="/informe-pagos" element={<InformePagos />} />
                <Route path="/planificacion-presupuestaria" element={<PlanificacionPresupuestaria />} />
                <Route path="/registro-gastos-directos" element={<RegistroGastosDirectos />} />
                {/* EstadoPresupuesto route removed (module deleted) */}
                <Route path="/ordenes-no-recepcionadas" element={<OrdenesNoRecepcionadas />} />
                <Route path="/proyectos" element={<Proyectos />} />
                <Route path="/proveedores" element={<Proveedores />} />
                <Route path="/materiales-servicios" element={<MaterialesServicios />} />
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
