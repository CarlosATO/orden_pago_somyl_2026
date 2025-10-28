import { useState, useEffect } from 'react';
import './EstadoPresupuesto.css';

function EstadoPresupuesto() {
  const [matriz, setMatriz] = useState({});
  const [proyectos, setProyectos] = useState([]);
  const [items, setItems] = useState([]);
  const [totales, setTotales] = useState({
    presupuesto_total: 0,
    real_total: 0,
    diferencia_total: 0
  });
  const [loading, setLoading] = useState(false);
  const [mensaje, setMensaje] = useState(null);
  
  // Filtros
  const [proyectoSeleccionado, setProyectoSeleccionado] = useState('todos');
  const [vistaActual, setVistaActual] = useState('comparativa'); // comparativa | presupuesto | real
  
  // Modal de detalle
  const [modalDetalle, setModalDetalle] = useState(null);
  const [detalleData, setDetalleData] = useState(null);
  const [loadingDetalle, setLoadingDetalle] = useState(false);

  const meses = [
    { num: 1, nombre: 'Ene' },
    { num: 2, nombre: 'Feb' },
    { num: 3, nombre: 'Mar' },
    { num: 4, nombre: 'Abr' },
    { num: 5, nombre: 'May' },
    { num: 6, nombre: 'Jun' },
    { num: 7, nombre: 'Jul' },
    { num: 8, nombre: 'Ago' },
    { num: 9, nombre: 'Sep' },
    { num: 10, nombre: 'Oct' },
    { num: 11, nombre: 'Nov' },
    { num: 12, nombre: 'Dic' }
  ];

  useEffect(() => {
    fetchEstadoPresupuesto();
  }, []);

  useEffect(() => {
    if (mensaje) {
      const timer = setTimeout(() => setMensaje(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [mensaje]);

  const fetchEstadoPresupuesto = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      if (!token) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
        return;
      }

      const response = await fetch('/api/estado-presupuesto/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setMatriz(data.data.matriz);
          setProyectos(data.data.proyectos);
          setItems(data.data.items);
          setTotales(data.data.totales);
        } else {
          setMensaje({ tipo: 'error', texto: data.message || 'Error al cargar datos' });
        }
      } else if (response.status === 401) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
      } else {
        setMensaje({ tipo: 'error', texto: 'Error al cargar estado de presupuesto' });
      }
    } catch (error) {
      console.error('Error:', error);
      setMensaje({ tipo: 'error', texto: 'Error de conexión' });
    } finally {
      setLoading(false);
    }
  };

  const fetchDetalle = async (proyectoId, itemId, mes) => {
    setLoadingDetalle(true);
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(
        `/api/estado-presupuesto/detalle?proyecto=${proyectoId}&item=${itemId}&mes=${mes}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setDetalleData(data.data);
        }
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoadingDetalle(false);
    }
  };

  const handleCellClick = (proyectoId, itemId, mes, datos) => {
    if (datos.real > 0) {
      setModalDetalle({ proyectoId, itemId, mes });
      fetchDetalle(proyectoId, itemId, mes);
    }
  };

  const cerrarModal = () => {
    setModalDetalle(null);
    setDetalleData(null);
  };

  const formatMonto = (monto) => {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(monto);
  };

  const getColorClass = (diferencia) => {
    if (diferencia > 0) return 'positivo';
    if (diferencia < 0) return 'negativo';
    return 'neutro';
  };

  const proyectosFiltrados = proyectoSeleccionado === 'todos' 
    ? proyectos 
    : proyectos.filter(p => p.id === parseInt(proyectoSeleccionado));

  const calcularTotalesPorMes = () => {
    const totalesMes = {};
    meses.forEach(m => {
      totalesMes[m.num] = { presupuesto: 0, real: 0, diferencia: 0 };
    });

    proyectosFiltrados.forEach(proyecto => {
      const proyectoData = matriz[proyecto.id];
      if (!proyectoData) return;

      items.forEach(item => {
        const itemData = proyectoData.items[item.id];
        if (!itemData) return;

        Object.entries(itemData.meses).forEach(([mes, datos]) => {
          const mesNum = parseInt(mes);
          if (totalesMes[mesNum]) {
            totalesMes[mesNum].presupuesto += datos.presupuesto;
            totalesMes[mesNum].real += datos.real;
            totalesMes[mesNum].diferencia += datos.diferencia;
          }
        });
      });
    });

    return totalesMes;
  };

  const totalesPorMes = calcularTotalesPorMes();

  return (
    <div className="estado-presupuesto-container">
      {/* Header */}
      <div className="estado-header">
        <div className="header-title-group">
          <div className="icon-wrapper">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path d="M3 3V21H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <path d="M7 16L12 11L16 15L21 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <h1>Estado de Presupuesto</h1>
        </div>
        <button className="btn-refresh" onClick={fetchEstadoPresupuesto} disabled={loading}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M1 4V10H7M23 20V14H17" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10M23 14L18.36 18.36A9 9 0 0 1 3.51 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          Actualizar
        </button>
      </div>

      {mensaje && (
        <div className={`mensaje mensaje-${mensaje.tipo}`}>
          {mensaje.texto}
        </div>
      )}

      {/* Stats Cards */}
      <div className="stats-grid-presupuesto">
        <div className="stat-card">
          <div className="stat-icon stat-presupuesto">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2"/>
              <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2"/>
              <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2"/>
            </svg>
          </div>
          <div className="stat-content">
            <div className="stat-value">{formatMonto(totales.presupuesto_total)}</div>
            <div className="stat-label">Presupuesto Total</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-real">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
              <path d="M12 6V12L16 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <div className="stat-content">
            <div className="stat-value">{formatMonto(totales.real_total)}</div>
            <div className="stat-label">Gasto Real</div>
          </div>
        </div>

        <div className="stat-card">
          <div className={`stat-icon stat-diferencia ${getColorClass(totales.diferencia_total)}`}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <div className="stat-content">
            <div className={`stat-value ${getColorClass(totales.diferencia_total)}`}>
              {formatMonto(totales.diferencia_total)}
            </div>
            <div className="stat-label">Diferencia</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-porcentaje">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <circle cx="7" cy="7" r="2" stroke="currentColor" strokeWidth="2"/>
              <circle cx="17" cy="17" r="2" stroke="currentColor" strokeWidth="2"/>
              <path d="M19 5L5 19" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <div className="stat-content">
            <div className="stat-value">
              {totales.presupuesto_total > 0 
                ? `${((totales.real_total / totales.presupuesto_total) * 100).toFixed(1)}%`
                : '0%'}
            </div>
            <div className="stat-label">Ejecución</div>
          </div>
        </div>
      </div>

      {/* Filtros y Controles */}
      <div className="controles-section">
        <div className="filtro-proyecto">
          <label>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M21 16V8C20.9996 7.64928 20.9071 7.30481 20.7315 7.00116C20.556 6.69751 20.3037 6.44536 20 6.27L13 2.27C12.696 2.09446 12.3511 2.00205 12 2.00205C11.6489 2.00205 11.304 2.09446 11 2.27L4 6.27C3.69626 6.44536 3.44398 6.69751 3.26846 7.00116C3.09294 7.30481 3.00036 7.64928 3 8V16C3.00036 16.3507 3.09294 16.6952 3.26846 16.9988C3.44398 17.3025 3.69626 17.5546 4 17.73L11 21.73C11.304 21.9055 11.6489 21.9979 12 21.9979C12.3511 21.9979 12.696 21.9055 13 21.73L20 17.73C20.3037 17.5546 20.556 17.3025 20.7315 16.9988C20.9071 16.6952 20.9996 16.3507 21 16Z" stroke="currentColor" strokeWidth="2"/>
            </svg>
            Proyecto
          </label>
          <select value={proyectoSeleccionado} onChange={(e) => setProyectoSeleccionado(e.target.value)}>
            <option value="todos">Todos los proyectos</option>
            {proyectos.map(p => (
              <option key={p.id} value={p.id}>{p.proyecto}</option>
            ))}
          </select>
        </div>

        <div className="vista-toggle">
          <button 
            className={vistaActual === 'comparativa' ? 'active' : ''}
            onClick={() => setVistaActual('comparativa')}
          >
            Comparativa
          </button>
          <button 
            className={vistaActual === 'presupuesto' ? 'active' : ''}
            onClick={() => setVistaActual('presupuesto')}
          >
            Solo Presupuesto
          </button>
          <button 
            className={vistaActual === 'real' ? 'active' : ''}
            onClick={() => setVistaActual('real')}
          >
            Solo Real
          </button>
        </div>

        <div className="leyenda">
          <span className="leyenda-item">
            <span className="indicador positivo"></span>
            Dentro de presupuesto
          </span>
          <span className="leyenda-item">
            <span className="indicador negativo"></span>
            Sobre presupuesto
          </span>
        </div>
      </div>

      {/* Tabla Matriz */}
      <div className="tabla-container-matriz">
        {loading ? (
          <div className="loading-overlay">
            <div className="spinner"></div>
            <p>Cargando estado de presupuesto...</p>
          </div>
        ) : proyectosFiltrados.length === 0 ? (
          <div className="empty-state">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2"/>
              <path d="M2 17L12 22L22 17M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2"/>
            </svg>
            <h3>Sin proyectos</h3>
            <p>No hay proyectos con presupuesto asignado</p>
          </div>
        ) : (
          <div className="table-scroll-matriz">
            <table className="tabla-matriz">
              <thead>
                <tr>
                  <th className="sticky-col" rowSpan="2">Proyecto</th>
                  <th className="sticky-col-2" rowSpan="2">Item</th>
                  {meses.map(m => (
                    <th key={m.num} colSpan={vistaActual === 'comparativa' ? 3 : 1}>
                      {m.nombre}
                    </th>
                  ))}
                  <th colSpan={vistaActual === 'comparativa' ? 3 : 1}>Total</th>
                </tr>
                {vistaActual === 'comparativa' && (
                  <tr>
                    {meses.map(m => (
                      <React.Fragment key={`sub-${m.num}`}>
                        <th className="sub-header">Pres.</th>
                        <th className="sub-header">Real</th>
                        <th className="sub-header">Dif.</th>
                      </React.Fragment>
                    ))}
                    <th className="sub-header">Pres.</th>
                    <th className="sub-header">Real</th>
                    <th className="sub-header">Dif.</th>
                  </tr>
                )}
              </thead>
              <tbody>
                {proyectosFiltrados.map(proyecto => {
                  const proyectoData = matriz[proyecto.id];
                  if (!proyectoData) return null;

                  return items.map((item, itemIndex) => {
                    const itemData = proyectoData.items[item.id];
                    if (!itemData) return null;

                    return (
                      <tr key={`${proyecto.id}-${item.id}`}>
                        {itemIndex === 0 && (
                          <td className="sticky-col proyecto-cell" rowSpan={items.length}>
                            {proyectoData.nombre}
                          </td>
                        )}
                        <td className="sticky-col-2 item-cell">{itemData.nombre}</td>
                        
                        {meses.map(m => {
                          const datos = itemData.meses[m.num] || { presupuesto: 0, real: 0, diferencia: 0 };
                          
                          if (vistaActual === 'comparativa') {
                            return (
                              <React.Fragment key={`${proyecto.id}-${item.id}-${m.num}`}>
                                <td className="monto-cell">{datos.presupuesto > 0 ? formatMonto(datos.presupuesto) : '-'}</td>
                                <td 
                                  className={`monto-cell ${datos.real > 0 ? 'clickable' : ''}`}
                                  onClick={() => datos.real > 0 && handleCellClick(proyecto.id, item.id, m.num, datos)}
                                >
                                  {datos.real > 0 ? formatMonto(datos.real) : '-'}
                                </td>
                                <td className={`monto-cell diferencia ${getColorClass(datos.diferencia)}`}>
                                  {datos.presupuesto > 0 || datos.real > 0 ? formatMonto(datos.diferencia) : '-'}
                                </td>
                              </React.Fragment>
                            );
                          } else if (vistaActual === 'presupuesto') {
                            return (
                              <td key={`${proyecto.id}-${item.id}-${m.num}`} className="monto-cell">
                                {datos.presupuesto > 0 ? formatMonto(datos.presupuesto) : '-'}
                              </td>
                            );
                          } else {
                            return (
                              <td 
                                key={`${proyecto.id}-${item.id}-${m.num}`}
                                className={`monto-cell ${datos.real > 0 ? 'clickable' : ''}`}
                                onClick={() => datos.real > 0 && handleCellClick(proyecto.id, item.id, m.num, datos)}
                              >
                                {datos.real > 0 ? formatMonto(datos.real) : '-'}
                              </td>
                            );
                          }
                        })}

                        {/* Totales por fila */}
                        {vistaActual === 'comparativa' ? (
                          <>
                            <td className="monto-cell total-cell">{formatMonto(itemData.total_presupuesto)}</td>
                            <td className="monto-cell total-cell">{formatMonto(itemData.total_real)}</td>
                            <td className={`monto-cell total-cell diferencia ${getColorClass(itemData.total_presupuesto - itemData.total_real)}`}>
                              {formatMonto(itemData.total_presupuesto - itemData.total_real)}
                            </td>
                          </>
                        ) : vistaActual === 'presupuesto' ? (
                          <td className="monto-cell total-cell">{formatMonto(itemData.total_presupuesto)}</td>
                        ) : (
                          <td className="monto-cell total-cell">{formatMonto(itemData.total_real)}</td>
                        )}
                      </tr>
                    );
                  });
                })}

                {/* Fila de totales */}
                <tr className="total-row">
                  <td className="sticky-col" colSpan="2">TOTAL</td>
                  {meses.map(m => {
                    const totalesMes = totalesPorMes[m.num];
                    if (vistaActual === 'comparativa') {
                      return (
                        <React.Fragment key={`total-${m.num}`}>
                          <td className="monto-cell">{formatMonto(totalesMes.presupuesto)}</td>
                          <td className="monto-cell">{formatMonto(totalesMes.real)}</td>
                          <td className={`monto-cell diferencia ${getColorClass(totalesMes.diferencia)}`}>
                            {formatMonto(totalesMes.diferencia)}
                          </td>
                        </React.Fragment>
                      );
                    } else if (vistaActual === 'presupuesto') {
                      return <td key={`total-${m.num}`} className="monto-cell">{formatMonto(totalesMes.presupuesto)}</td>;
                    } else {
                      return <td key={`total-${m.num}`} className="monto-cell">{formatMonto(totalesMes.real)}</td>;
                    }
                  })}
                  {vistaActual === 'comparativa' ? (
                    <>
                      <td className="monto-cell">{formatMonto(totales.presupuesto_total)}</td>
                      <td className="monto-cell">{formatMonto(totales.real_total)}</td>
                      <td className={`monto-cell diferencia ${getColorClass(totales.diferencia_total)}`}>
                        {formatMonto(totales.diferencia_total)}
                      </td>
                    </>
                  ) : vistaActual === 'presupuesto' ? (
                    <td className="monto-cell">{formatMonto(totales.presupuesto_total)}</td>
                  ) : (
                    <td className="monto-cell">{formatMonto(totales.real_total)}</td>
                  )}
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal de Detalle */}
      {modalDetalle && (
        <div className="modal-overlay" onClick={cerrarModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Detalle de Gastos</h3>
              <button className="btn-close-modal" onClick={cerrarModal}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </button>
            </div>
            
            <div className="modal-body">
              {loadingDetalle ? (
                <div className="loading-modal">
                  <div className="spinner"></div>
                  <p>Cargando detalle...</p>
                </div>
              ) : detalleData ? (
                <>
                  <div className="detalle-info">
                    <p><strong>Proyecto:</strong> {detalleData.proyecto}</p>
                    <p><strong>Item:</strong> {detalleData.item}</p>
                    <p><strong>Mes:</strong> {meses.find(m => m.num === parseInt(detalleData.mes))?.nombre || detalleData.mes}</p>
                  </div>

                  {detalleData.ordenes && detalleData.ordenes.length > 0 && (
                    <div className="detalle-section">
                      <h4>Órdenes de Pago ({detalleData.ordenes.length})</h4>
                      <table className="tabla-detalle">
                        <thead>
                          <tr>
                            <th>O.Pago</th>
                            <th>OC</th>
                            <th>Proveedor</th>
                            <th>Material</th>
                            <th className="text-end">Monto</th>
                          </tr>
                        </thead>
                        <tbody>
                          {detalleData.ordenes.map(orden => (
                            <tr key={orden.id}>
                              <td>{orden.orden_numero}</td>
                              <td>{orden.orden_compra}</td>
                              <td>{orden.proveedor_nombre}</td>
                              <td>{orden.material_nombre}</td>
                              <td className="text-end">{formatMonto(orden.costo_final_con_iva)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <div className="subtotal">
                        <strong>Subtotal Órdenes:</strong> {formatMonto(detalleData.totales.ordenes)}
                      </div>
                    </div>
                  )}

                  {detalleData.gastos && detalleData.gastos.length > 0 && (
                    <div className="detalle-section">
                      <h4>Gastos Directos ({detalleData.gastos.length})</h4>
                      <table className="tabla-detalle">
                        <thead>
                          <tr>
                            <th>Descripción</th>
                            <th>Fecha</th>
                            <th className="text-end">Monto</th>
                          </tr>
                        </thead>
                        <tbody>
                          {detalleData.gastos.map(gasto => (
                            <tr key={gasto.id}>
                              <td>{gasto.descripcion}</td>
                              <td>{new Date(gasto.fecha).toLocaleDateString('es-CL')}</td>
                              <td className="text-end">{formatMonto(gasto.monto)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <div className="subtotal">
                        <strong>Subtotal Gastos:</strong> {formatMonto(detalleData.totales.gastos)}
                      </div>
                    </div>
                  )}

                  <div className="total-general">
                    <strong>TOTAL GENERAL:</strong> {formatMonto(detalleData.totales.general)}
                  </div>
                </>
              ) : (
                <p>No se pudo cargar el detalle</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default EstadoPresupuesto;