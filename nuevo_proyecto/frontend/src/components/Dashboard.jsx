import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import API_BASE_URL from '../config/api';
import { getAuthToken } from '../utils/auth';
import './Dashboard.css';

function Dashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [error, setError] = useState(null);
  const [showModalDocumentos, setShowModalDocumentos] = useState(false);
  const [documentosDetalle, setDocumentosDetalle] = useState(null);
  const [loadingDocumentos, setLoadingDocumentos] = useState(false);
  
  // Estados para modal de proveedor
  const [showModalProveedor, setShowModalProveedor] = useState(false);
  const [proveedorSeleccionado, setProveedorSeleccionado] = useState(null);
  const [ordenesProveedor, setOrdenesProveedor] = useState([]);
  const [loadingOrdenesProveedor, setLoadingOrdenesProveedor] = useState(false);

  useEffect(() => {
    fetchDashboardData();
  }, []);
  
  useEffect(() => {
    if (showModalDocumentos && !documentosDetalle) {
      fetchDocumentosDetalle();
    }
  }, [showModalDocumentos]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const token = getAuthToken();
      const response = await axios.get(`${API_BASE_URL}/dashboard/`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.data.success) {
        setDashboardData(response.data.data);
        console.log('Dashboard data:', response.data.data);
      }
    } catch (err) {
      console.error('Error al cargar dashboard:', err);
      setError('Error al cargar los datos del dashboard');
    } finally {
      setLoading(false);
    }
  };

  const fetchDocumentosDetalle = async () => {
    try {
      setLoadingDocumentos(true);
      const token = getAuthToken();
      const response = await axios.get(`${API_BASE_URL}/dashboard/documentos-pendientes-detalle`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.data.success) {
        setDocumentosDetalle(response.data.data);
      }
    } catch (err) {
      console.error('Error al cargar detalle de documentos:', err);
    } finally {
      setLoadingDocumentos(false);
    }
  };
  
  const descargarPDFDocumentos = async () => {
    try {
      const token = getAuthToken();
      const response = await axios.get(`${API_BASE_URL}/dashboard/documentos-pendientes-pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'  // Importante para recibir archivo binario
      });

      // Crear URL temporal para el blob
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Generar nombre de archivo con fecha
      const fecha = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      link.setAttribute('download', `documentos_pendientes_${fecha}.pdf`);
      
      // Descargar
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      // Limpiar URL temporal
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error al descargar PDF:', err);
      alert('Error al generar el PDF. Por favor intenta nuevamente.');
    }
  };
  
  const verOrdenesProveedor = async (proveedor) => {
    try {
      setProveedorSeleccionado(proveedor);
      setShowModalProveedor(true);
      setLoadingOrdenesProveedor(true);
      
      const token = getAuthToken();
      // Llamar al endpoint de pagos filtrando por proveedor
      const response = await axios.get(`${API_BASE_URL}/pagos/list`, {
        headers: { Authorization: `Bearer ${token}` },
        params: {
          proveedor: proveedor.proveedor,
          estado: 'pendiente',
          per_page: 1000
        }
      });

      if (response.data.success) {
        setOrdenesProveedor(response.data.data.pagos || []);
      }
    } catch (err) {
      console.error('Error al cargar órdenes del proveedor:', err);
      alert('Error al cargar las órdenes del proveedor');
    } finally {
      setLoadingOrdenesProveedor(false);
    }
  };
  
  const cerrarModalProveedor = () => {
    setShowModalProveedor(false);
    setProveedorSeleccionado(null);
    setOrdenesProveedor([]);
  };

  const formatCurrency = (value) => {
    if (!value && value !== 0) return '$0';
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatNumber = (value) => {
    if (!value && value !== 0) return '0';
    return new Intl.NumberFormat('es-CL').format(value);
  };

  const getEstadoBadge = (estado) => {
    const badges = {
      'riesgo': { icon: '🔴', text: 'Riesgo', class: 'badge-riesgo' },
      'alerta': { icon: '🟡', text: 'Alerta', class: 'badge-alerta' },
      'ok': { icon: '🟢', text: 'OK', class: 'badge-ok' }
    };
    return badges[estado] || badges['ok'];
  };

  if (loading) {
    return (
      <div className="content">
        <div className="loading-dashboard">
          <i className="fas fa-spinner fa-spin"></i>
          <p>Cargando Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="content">
        <div className="error-dashboard">
          <i className="fas fa-exclamation-triangle"></i>
          <p>{error}</p>
          <button onClick={fetchDashboardData} className="btn-retry">
            <i className="fas fa-redo"></i> Reintentar
          </button>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return <div className="content">No hay datos disponibles</div>;
  }

  const { kpis, top_proveedores, top_proyectos, oc_sin_recepcionar, evolucion_deuda, distribucion_deuda, ejecucion_presupuestaria } = dashboardData;

  return (
    <div className="content dashboard-container">
      <div className="dashboard-header">
        <h1><i className="fas fa-chart-line"></i> Dashboard - Gestión de Compras</h1>
      </div>

      {/* SECCIÓN 1: KPIs PRINCIPALES */}
      <div className="kpis-grid">
        {/* Montos Pendientes de Pago - IGUAL QUE INFORME DE PAGOS */}
        <div className="kpi-card kpi-danger">
          <div className="kpi-icon">
            <i className="fas fa-hand-holding-usd"></i>
          </div>
          <div className="kpi-content">
            <h3>Montos Pendientes de Pago</h3>
            <div className="kpi-detail" style={{marginTop: '10px', gap: '12px'}}>
              <div style={{padding: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '6px'}}>
                <span style={{fontSize: '0.85em', opacity: 0.9}}>💵 Pendientes</span>
                <div style={{fontSize: '1.3em', fontWeight: 'bold', marginTop: '4px'}}>
                  {formatCurrency(kpis.monto_pendiente || 0)}
                </div>
                <span style={{fontSize: '0.75em', opacity: 0.8}}>{kpis.pendientes || 0} órdenes</span>
              </div>
              <div style={{padding: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '6px'}}>
                <span style={{fontSize: '0.85em', opacity: 0.9}}>💳 Saldo de Abonos</span>
                <div style={{fontSize: '1.3em', fontWeight: 'bold', marginTop: '4px'}}>
                  {formatCurrency(kpis.saldo_abonos || 0)}
                </div>
                <span style={{fontSize: '0.75em', opacity: 0.8}}>{kpis.con_abonos || 0} órdenes</span>
              </div>
              <div style={{padding: '10px', background: 'rgba(255,255,255,0.15)', borderRadius: '6px', borderTop: '2px solid rgba(255,255,255,0.3)'}}>
                <span style={{fontSize: '0.9em', fontWeight: 'bold'}}>🎯 TOTAL GENERAL</span>
                <div style={{fontSize: '1.6em', fontWeight: 'bold', marginTop: '4px'}}>
                  {formatCurrency(kpis.total_general || 0)}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Documentos Pendientes - CON MODAL */}
        <div className="kpi-card kpi-warning" onClick={() => setShowModalDocumentos(true)} style={{cursor: 'pointer'}}>
          <div className="kpi-icon">
            <i className="fas fa-bell"></i>
          </div>
          <div className="kpi-content">
            <h3>Documentos Pendientes</h3>
            <div className="kpi-value">{kpis.documentos_pendientes}</div>
            <div className="kpi-detail">
              <span><i className="fas fa-clock"></i> Pagos vencidos: {kpis.pagos_vencidos}</span>
              <span style={{fontSize: '12px', opacity: 0.8, marginTop: '5px'}}>Click para ver detalle</span>
            </div>
          </div>
        </div>
      </div>

      {/* SECCIÓN 2: PROVEEDORES CON DEUDA */}
      <div className="rankings-grid">
        {/* Todos los Proveedores con Deuda */}
        <div className="ranking-card">
          <div className="ranking-header">
            <h2><i className="fas fa-users"></i> Proveedores con Deuda Pendiente</h2>
            <span className="badge-count">{top_proveedores ? top_proveedores.length : 0} proveedores</span>
          </div>
          <div className="ranking-table-container">
            {top_proveedores && top_proveedores.length > 0 ? (
              <table className="ranking-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Proveedor</th>
                    <th>Deuda</th>
                    <th>N° OP</th>
                    <th>Ver</th>
                  </tr>
                </thead>
                <tbody>
                  {top_proveedores.map((prov, index) => (
                    <tr key={index}>
                      <td className="rank-number">{index + 1}</td>
                      <td className="proveedor-name">{prov.proveedor}</td>
                      <td className="deuda-amount">{formatCurrency(prov.deuda)}</td>
                      <td className="op-count">{prov.num_op} OP</td>
                      <td>
                        <button 
                          className="btn-ver-detalle"
                          onClick={() => verOrdenesProveedor(prov)}
                          title="Ver órdenes de pago"
                        >
                          <i className="fas fa-eye"></i> Ver
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="no-data">No hay datos de proveedores</p>
            )}
          </div>
        </div>
      </div>

      {/* SECCIÓN 3: ÓRDENES SIN RECEPCIONAR */}
      {oc_sin_recepcionar && oc_sin_recepcionar.length > 0 && (
        <div className="oc-pendientes-section">
          <div className="section-header">
            <h2><i className="fas fa-clock"></i> Órdenes de Compra sin Recepcionar (+15 días)</h2>
            <span className="badge-count">{oc_sin_recepcionar.length} órdenes</span>
          </div>
          <div className="oc-pendientes-grid">
            {oc_sin_recepcionar.slice(0, 6).map((oc, index) => (
              <div key={index} className="oc-pendiente-card">
                <div className="oc-header">
                  <span className="oc-numero">OC #{oc.numero_orden}</span>
                  <span className={`oc-dias ${oc.dias_pendiente > 30 ? 'dias-critico' : 'dias-alerta'}`}>
                    {oc.dias_pendiente} días
                  </span>
                </div>
                <div className="oc-body">
                  <p><strong>Proveedor:</strong> {oc.proveedor}</p>
                  <p><strong>Proyecto:</strong> {oc.proyecto}</p>
                  <p><strong>Monto:</strong> {formatCurrency(oc.monto_total)}</p>
                </div>
                <button 
                  className="btn-recepcionar"
                  onClick={() => navigate('/ingresos')}
                >
                  <i className="fas fa-truck-loading"></i> Recepcionar
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECCIÓN 4: GRÁFICOS */}
      <div className="charts-section">
        {/* Ejecución Presupuestaria */}
        {ejecucion_presupuestaria && ejecucion_presupuestaria.length > 0 && (
          <div className="chart-card chart-full">
            <div className="chart-header">
              <h2><i className="fas fa-chart-bar"></i> Ejecución Presupuestaria por Proyecto</h2>
            </div>
            <div className="chart-body">
              <div className="budget-bars">
                {ejecucion_presupuestaria.slice(0, 8).map((proyecto, index) => (
                  <div key={index} className="budget-bar-row">
                    <div className="budget-proyecto-name">{proyecto.proyecto}</div>
                    <div className="budget-bar-container">
                      <div 
                        className="budget-bar budget-bar-presupuesto"
                        style={{ width: '100%' }}
                      >
                        <span className="budget-label">Ppto: {formatCurrency(proyecto.presupuesto)}</span>
                      </div>
                      <div 
                        className={`budget-bar budget-bar-real ${proyecto.porcentaje_ejecutado > 100 ? 'over-budget' : ''}`}
                        style={{ width: `${Math.min(proyecto.porcentaje_ejecutado, 100)}%` }}
                      >
                        <span className="budget-label">Real: {formatCurrency(proyecto.real)} ({proyecto.porcentaje_ejecutado}%)</span>
                      </div>
                    </div>
                    <div className={`budget-saldo ${proyecto.saldo < 0 ? 'saldo-negativo' : 'saldo-positivo'}`}>
                      {formatCurrency(proyecto.saldo)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* MODAL DE DOCUMENTOS PENDIENTES */}
      {showModalDocumentos && (
        <div className="modal-overlay" onClick={() => setShowModalDocumentos(false)}>
          <div className="modal-content-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2><i className="fas fa-file-invoice"></i> Documentos Pendientes</h2>
              <button className="modal-close" onClick={() => setShowModalDocumentos(false)}>
                <i className="fas fa-times"></i>
              </button>
            </div>
            
            <div className="modal-body">
              {loadingDocumentos ? (
                <div className="loading-modal">
                  <i className="fas fa-spinner fa-spin"></i> Cargando detalle...
                </div>
              ) : documentosDetalle && documentosDetalle.stats ? (
                <>
                  <div className="modal-actions">
                    <button className="btn btn-primary" onClick={descargarPDFDocumentos}>
                      <i className="fas fa-file-pdf"></i> Descargar PDF
                    </button>
                    <div className="modal-summary">
                      <strong>Total documentos pendientes:</strong> {documentosDetalle.stats.total} 
                      <span style={{marginLeft: '15px', fontSize: '13px'}}>
                        ({documentosDetalle.stats.pendientes} pendientes + {documentosDetalle.stats.con_abonos} con abonos)
                      </span>
                    </div>
                  </div>
                  
                  {/* Todos los Documentos Pendientes */}
                  {documentosDetalle.documentos && documentosDetalle.documentos.length > 0 ? (
                    <div className="documentos-section">
                      <h3 style={{marginBottom: '15px'}}>
                        <i className="fas fa-list"></i> Todos los Documentos Pendientes
                        <span style={{marginLeft: '10px', fontSize: '14px', color: '#666'}}>
                          ({documentosDetalle.stats.vencidos} vencidos)
                        </span>
                      </h3>
                      <table className="modal-table">
                        <thead>
                          <tr>
                            <th>OP #</th>
                            <th>Fecha OP</th>
                            <th>Fecha Vencimiento</th>
                            <th>Proveedor</th>
                            <th>Proyecto</th>
                            <th>Factura</th>
                            <th>Monto Total</th>
                            <th>Abonado</th>
                            <th>Saldo</th>
                            <th>Días Atraso</th>
                            <th>Estado</th>
                          </tr>
                        </thead>
                        <tbody>
                          {documentosDetalle.documentos.map((doc, idx) => (
                            <tr key={idx} className={
                              doc.dias_atraso > 30 ? 'row-critical' : 
                              doc.dias_atraso > 0 ? 'row-warning' : 
                              ''
                            }>
                              <td><strong>{doc.orden_numero}</strong></td>
                              <td style={{fontSize: '12px'}}>{doc.fecha_op || '---'}</td>
                              <td style={{fontSize: '12px', fontWeight: '500'}}>{doc.fecha_vencimiento || '---'}</td>
                              <td>{doc.proveedor}</td>
                              <td>{doc.proyecto}</td>
                              <td>{doc.factura}</td>
                              <td>{formatCurrency(doc.monto_total)}</td>
                              <td>{formatCurrency(doc.total_abonado)}</td>
                              <td className="monto-destacado">{formatCurrency(doc.saldo)}</td>
                              <td className="dias-vencido">
                                {doc.dias_atraso > 0 ? (
                                  <span className={doc.dias_atraso > 30 ? 'badge-critical' : 'badge-warning-strong'}>
                                    {doc.dias_atraso} días
                                  </span>
                                ) : (
                                  <span style={{color: '#28a745'}}>✓ Al día</span>
                                )}
                              </td>
                              <td>
                                <span className={
                                  doc.estado === 'vencido' ? 'badge badge-danger' : 
                                  doc.total_abonado > 0 ? 'badge badge-info' : 
                                  'badge badge-warning'
                                }>
                                  {doc.total_abonado > 0 ? 'Con Abonos' : doc.tipo}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                        <tfoot>
                          <tr className="totales-row">
                            <td colSpan="6" className="totales-label"><strong>TOTAL</strong></td>
                            <td className="totales-value">
                              <strong>{formatCurrency(documentosDetalle.documentos.reduce((sum, p) => sum + p.monto_total, 0))}</strong>
                            </td>
                            <td className="totales-value">
                              <strong>{formatCurrency(documentosDetalle.documentos.reduce((sum, p) => sum + p.total_abonado, 0))}</strong>
                            </td>
                            <td className="totales-value">
                              <strong>{formatCurrency(documentosDetalle.documentos.reduce((sum, p) => sum + p.saldo, 0))}</strong>
                            </td>
                            <td colSpan="2"></td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  ) : (
                    <div className="no-data">
                      <i className="fas fa-check-circle"></i>
                      <p>No hay pagos vencidos</p>
                    </div>
                  )}
                </>
              ) : (
                <div className="no-data">No hay datos disponibles</div>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* MODAL DE ÓRDENES DEL PROVEEDOR */}
      {showModalProveedor && (
        <div className="modal-overlay" onClick={cerrarModalProveedor}>
          <div className="modal-content-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                <i className="fas fa-file-invoice-dollar"></i> Órdenes de Pago - {proveedorSeleccionado?.proveedor}
              </h2>
              <button className="modal-close" onClick={cerrarModalProveedor}>
                <i className="fas fa-times"></i>
              </button>
            </div>
            
            <div className="modal-body">
              {loadingOrdenesProveedor ? (
                <div className="loading-modal">
                  <i className="fas fa-spinner fa-spin"></i> Cargando órdenes...
                </div>
              ) : ordenesProveedor && ordenesProveedor.length > 0 ? (
                <>
                  <div className="modal-summary">
                    <strong>Total de órdenes:</strong> {ordenesProveedor.length}
                    <span style={{marginLeft: '20px'}}>
                      <strong>Deuda total:</strong> {formatCurrency(ordenesProveedor.reduce((sum, op) => sum + op.saldo_pendiente, 0))}
                    </span>
                  </div>
                  
                  <div className="table-responsive" style={{maxHeight: '500px', overflowY: 'auto'}}>
                    <table className="modal-table">
                      <thead style={{position: 'sticky', top: 0, backgroundColor: '#fff', zIndex: 10}}>
                        <tr>
                          <th>OP</th>
                          <th>OC</th>
                          <th>Proyecto</th>
                          <th>Detalle</th>
                          <th>Factura</th>
                          <th>Monto Total</th>
                          <th>Abonado</th>
                          <th>Saldo</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ordenesProveedor.map((orden, index) => (
                          <tr key={index}>
                            <td>{orden.orden_numero}</td>
                            <td>{orden.orden_compra || '---'}</td>
                            <td>{orden.proyecto_nombre}</td>
                            <td title={orden.detalle_compra} style={{maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                              {orden.detalle_compra}
                            </td>
                            <td>{orden.factura || '---'}</td>
                            <td className="text-right"><strong>{formatCurrency(orden.total_pago)}</strong></td>
                            <td className="text-right">{formatCurrency(orden.total_abonado)}</td>
                            <td className="text-right"><strong>{formatCurrency(orden.saldo_pendiente)}</strong></td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="totales-row" style={{position: 'sticky', bottom: 0, backgroundColor: '#f8f9fa'}}>
                          <td colSpan="5" className="totales-label"><strong>TOTALES</strong></td>
                          <td className="totales-value">
                            <strong>{formatCurrency(ordenesProveedor.reduce((sum, p) => sum + p.total_pago, 0))}</strong>
                          </td>
                          <td className="totales-value">
                            <strong>{formatCurrency(ordenesProveedor.reduce((sum, p) => sum + p.total_abonado, 0))}</strong>
                          </td>
                          <td className="totales-value">
                            <strong>{formatCurrency(ordenesProveedor.reduce((sum, p) => sum + p.saldo_pendiente, 0))}</strong>
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </>
              ) : (
                <div className="no-data">
                  <i className="fas fa-inbox"></i>
                  <p>No hay órdenes de pago pendientes para este proveedor</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
