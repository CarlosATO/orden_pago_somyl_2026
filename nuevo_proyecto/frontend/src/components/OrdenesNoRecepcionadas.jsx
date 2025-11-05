// frontend/src/components/OrdenesNoRecepcionadas.jsx

import { useState, useEffect } from 'react';
import axios from 'axios';
import API_BASE_URL from '../config/api';
import { getAuthToken } from '../utils/auth';
import './OrdenesNoRecepcionadas.css';

const API_URL = API_BASE_URL;

function OrdenesNoRecepcionadas() {
  const [ordenesPendientes, setOrdenesPendientes] = useState([]);
  const [ordenFiltradas, setOrdenFiltradas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mensaje, setMensaje] = useState({ tipo: '', texto: '' });
  
  // KPIs
  const [totalOC, setTotalOC] = useState(0);
  const [totalMonto, setTotalMonto] = useState(0);
  
  // Modal
  const [mostrarModal, setMostrarModal] = useState(false);
  const [detalleOC, setDetalleOC] = useState(null);
  const [loadingDetalle, setLoadingDetalle] = useState(false);
  
  // Filtros
  const [busqueda, setBusqueda] = useState('');
  
  useEffect(() => {
    cargarOrdenesPendientes();
  }, []);
  
  useEffect(() => {
    filtrarOrdenes();
  }, [busqueda, ordenesPendientes]);
  
  const cargarOrdenesPendientes = async () => {
    try {
      setLoading(true);
      const token = getAuthToken();
      
      const response = await axios.get(`${API_URL}/ordenes-no-recepcionadas/lista`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.data.success) {
        setOrdenesPendientes(response.data.data);
        setTotalOC(response.data.total_oc);
        setTotalMonto(response.data.total_monto);
      }
    } catch (error) {
      mostrarMensaje('error', 'Error al cargar órdenes pendientes');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };
  
  const filtrarOrdenes = () => {
    if (!busqueda.trim()) {
      setOrdenFiltradas(ordenesPendientes);
      return;
    }
    
    const termino = busqueda.toLowerCase();
    const filtradas = ordenesPendientes.filter(orden => 
      orden.orden_compra.toLowerCase().includes(termino) ||
      orden.proveedor.toLowerCase().includes(termino)
    );
    
    setOrdenFiltradas(filtradas);
  };
  
  const verDetalle = async (ocNumero) => {
    try {
      setLoadingDetalle(true);
      setMostrarModal(true);
      setDetalleOC(null);
      
      const token = getAuthToken();
      const response = await axios.get(
        `${API_URL}/ordenes-no-recepcionadas/detalle/${ocNumero}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data.success) {
        setDetalleOC(response.data.data);
      }
    } catch (error) {
      mostrarMensaje('error', 'Error al cargar detalle');
      setMostrarModal(false);
    } finally {
      setLoadingDetalle(false);
    }
  };
  
  const sacarDelInforme = async (ocNumero) => {
    if (!confirm(`¿Está seguro de sacar la OC ${ocNumero} del informe?\n\nEsta acción ocultará la orden en este reporte.`)) {
      return;
    }
    
    try {
      setLoading(true);
      const token = getAuthToken();
      
      const response = await axios.post(
        `${API_URL}/ordenes-no-recepcionadas/sacar-informe/${ocNumero}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data.success) {
        mostrarMensaje('success', response.data.message);
        setMostrarModal(false);
        cargarOrdenesPendientes();
      }
    } catch (error) {
      mostrarMensaje('error', error.response?.data?.message || 'Error al sacar del informe');
    } finally {
      setLoading(false);
    }
  };
  
  const eliminarOrden = async (ocNumero) => {
    if (!confirm(`⚠️ ¿Está COMPLETAMENTE SEGURO de eliminar la OC ${ocNumero}?\n\n¡Esta acción NO se puede revertir!`)) {
      return;
    }
    
    try {
      setLoading(true);
      const token = getAuthToken();
      
      const response = await axios.delete(
        `${API_URL}/ordenes-no-recepcionadas/eliminar/${ocNumero}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data.success) {
        mostrarMensaje('success', response.data.message);
        setMostrarModal(false);
        cargarOrdenesPendientes();
      }
    } catch (error) {
      mostrarMensaje('error', error.response?.data?.message || 'Error al eliminar orden');
    } finally {
      setLoading(false);
    }
  };
  
  const mostrarMensaje = (tipo, texto) => {
    setMensaje({ tipo, texto });
    setTimeout(() => setMensaje({ tipo: '', texto: '' }), 5000);
  };
  
  const cerrarModal = () => {
    setMostrarModal(false);
    setDetalleOC(null);
  };
  
  return (
    <div className="ordenes-pendientes-container">
      <div className="ordenes-header">
        <h1>📊 Órdenes de Compra No Recepcionadas</h1>
      </div>
      
      {mensaje.texto && (
        <div className={`alert alert-${mensaje.tipo}`}>
          {mensaje.texto}
        </div>
      )}
      
      {/* KPIs */}
      <div className="kpis-container">
        <div className="kpi-card kpi-orders">
          <div className="kpi-icon">📦</div>
          <div className="kpi-content">
            <div className="kpi-value">{totalOC}</div>
            <div className="kpi-label">Órdenes Pendientes</div>
          </div>
        </div>
        
        <div className="kpi-card kpi-monto">
          <div className="kpi-icon">💰</div>
          <div className="kpi-content">
            <div className="kpi-value">$ {totalMonto.toLocaleString('es-CL')}</div>
            <div className="kpi-label">Monto Total con IVA</div>
          </div>
        </div>
      </div>
      
      {/* Filtros */}
      <div className="filtros-container">
        <div className="busqueda-box">
          <input
            type="text"
            placeholder="🔍 Buscar por OC o Proveedor..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="form-control"
          />
        </div>
      </div>
      
      {/* Tabla */}
      <div className="tabla-container">
        <h3>📋 Detalle de Órdenes Pendientes</h3>
        
        {loading ? (
          <div className="loading">⏳ Cargando órdenes...</div>
        ) : ordenFiltradas.length === 0 ? (
          <div className="empty-state">
            <p>🎉 No hay órdenes pendientes de recepción</p>
            {busqueda && <small>Intenta con otro término de búsqueda</small>}
          </div>
        ) : (
          <div className="table-responsive">
            <table className="ordenes-table">
              <thead>
                <tr>
                  <th>OC</th>
                  <th>Proveedor</th>
                  <th>Fecha de Solicitud</th>
                  <th>Monto Total (con IVA)</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {ordenFiltradas.map((orden) => (
                  <tr key={orden.orden_compra}>
                    <td className="oc-number">{orden.orden_compra}</td>
                    <td>{orden.proveedor}</td>
                    <td>{new Date(orden.fecha).toLocaleDateString('es-CL')}</td>
                    <td className="monto">$ {orden.monto_total.toLocaleString('es-CL')}</td>
                    <td>
                      <span className="badge badge-pendiente">{orden.estado}</span>
                    </td>
                    <td>
                      <button
                        className="btn-ver-detalle"
                        onClick={() => verDetalle(orden.orden_compra)}
                        title="Ver detalle"
                      >
                        👁️ Ver
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      
      {/* Modal de Detalle */}
      {mostrarModal && (
        <div
          className="modal-overlay"
          onClick={(e) => {
            // Cerrar solo si se clickeó directamente el overlay (evita que el click
            // original que abrió el modal lo cierre inmediatamente por bubbling)
            if (e.target === e.currentTarget) cerrarModal();
          }}
        >
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📄 Detalle de Orden de Compra</h2>
              <button className="modal-close" onClick={(e) => { e.stopPropagation(); cerrarModal(); }}>✕</button>
            </div>
            
            <div className="modal-body">
              {loadingDetalle ? (
                <div className="loading">⏳ Cargando detalle...</div>
              ) : detalleOC ? (
                <>
                  <div className="detalle-header-info">
                    <div className="info-row">
                      <strong>OC:</strong> <span>{detalleOC.orden_compra}</span>
                    </div>
                    <div className="info-row">
                      <strong>Proveedor:</strong> <span>{detalleOC.proveedor}</span>
                    </div>
                    <div className="info-row">
                      <strong>Fecha:</strong> <span>{new Date(detalleOC.fecha).toLocaleDateString('es-CL')}</span>
                    </div>
                  </div>
                  
                  <h4 className="lineas-titulo">Líneas de la Orden ({detalleOC.total_lineas})</h4>
                  
                  <div className="table-responsive">
                    <table className="detalle-table">
                      <thead>
                        <tr>
                          <th>Código</th>
                          <th>Descripción</th>
                          <th>Cantidad</th>
                          <th>Precio Unit.</th>
                          <th>Total</th>
                          <th>Tipo</th>
                          <th>Art. Corr.</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detalleOC.lineas.map((linea, idx) => (
                          <tr key={idx}>
                            <td>{linea.codigo}</td>
                            <td>{linea.descripcion}</td>
                            <td>{linea.cantidad}</td>
                            <td>$ {linea.precio_unitario.toLocaleString('es-CL')}</td>
                            <td>$ {linea.total.toLocaleString('es-CL')}</td>
                            <td>{linea.tipo}</td>
                            <td>{linea.art_corr}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <div className="error-state">Error al cargar detalle</div>
              )}
            </div>
            
            <div className="modal-footer">
              <button className="btn-secondary" onClick={cerrarModal}>
                Cerrar
              </button>
              {detalleOC && (
                <>
                  <button 
                    className="btn-warning"
                    onClick={() => sacarDelInforme(detalleOC.orden_compra)}
                    disabled={loading}
                  >
                    👁️‍🗨️ Sacar del Informe
                  </button>
                  <button 
                    className="btn-danger"
                    onClick={() => eliminarOrden(detalleOC.orden_compra)}
                    disabled={loading || !detalleOC.puede_eliminar}
                    title={!detalleOC.puede_eliminar ? "No se puede eliminar porque tiene ingresos asociados" : "Eliminar orden"}
                  >
                    🗑️ Eliminar Orden
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default OrdenesNoRecepcionadas;