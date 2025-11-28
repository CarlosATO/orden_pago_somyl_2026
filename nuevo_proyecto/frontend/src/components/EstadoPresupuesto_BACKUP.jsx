import { useState, useEffect } from 'react';
import './EstadoPresupuesto.css';
import { getAuthToken } from '../utils/auth';

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
  const [vistaActual, setVistaActual] = useState('comparativa');
  
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
      const token = getAuthToken();
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
        console.log('📊 Datos recibidos del backend:', data);
        if (data.success) {
          console.log('✅ Matriz:', data.data.matriz);
          console.log('✅ Proyectos:', data.data.proyectos);
          console.log('✅ Items:', data.data.items);
          console.log('✅ Totales:', data.data.totales);
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
      const token = getAuthToken();
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

  // 🔧 FUNCIÓN DE FILTRADO SEGÚN VISTA
  const getItemsFiltrados = (proyectoData) => {
    if (!proyectoData || !proyectoData.items) {
      console.error('❌ ProyectoData inválido:', proyectoData);
      return [];
    }
    
    const itemsFiltrados = items.filter(item => {
      const itemData = proyectoData.items[item.id];
      
      if (!itemData) {
        console.warn(`⚠️ No se encontró itemData para item ${item.id} (${item.item})`);
        return false;
      }

      console.log(`📋 Revisando item ${item.item}:`, {
        total_presupuesto: itemData.total_presupuesto,
        total_real: itemData.total_real,
        vista: vistaActual
      });

      if (vistaActual === 'comparativa') {
        return itemData.total_presupuesto > 0 || itemData.total_real > 0;
      }
      
      if (vistaActual === 'presupuesto') {
        return itemData.total_presupuesto > 0;
      }
      
      if (vistaActual === 'real') {
        return itemData.total_real > 0;
      }
      
      return false;
    });
    
    console.log(`✅ Items filtrados para ${proyectoData.nombre}:`, itemsFiltrados.length, itemsFiltrados);
    return itemsFiltrados;
  };

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
        <button className="btn-refresh" onClick={fetchEstadoPresupuesto}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M21 10C21 10 18.995 7.26822 17.3662 5.63824C15.7373 4.00827 13.4864 3 11 3C6.02944 3 2 7.02944 2 12C2 16.9706 6.02944 21 11 21C15.1031 21 18.5649 18.2543 19.6482 14.5M21 10V4M21 10H15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          Actualizar
        </button>
      </div>

      {/* Mensaje */}
      {mensaje && (
        <div className={`alert alert-${mensaje.tipo === 'error' ? 'danger' : 'success'}`}>
          {mensaje.texto}
        </div>
      )}

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon stat-presupuesto">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M9 7H7C5.89543 7 5 7.89543 5 9V19C5 20.1046 5.89543 21 7 21H17C18.1046 21 19 20.1046 19 19V9C19 7.89543 18.1046 7 17 7H15M9 7V5C9 3.89543 9.89543 3 11 3H13C14.1046 3 15 3.89543 15 5V7M9 7H15" stroke="currentColor" strokeWidth="2"/>
            </svg>
          </div>
          <div className="stat-content">
            <div className="stat-value">{formatMonto(totales.presupuesto_total)}</div>
            <div className="stat-label">Presupuesto Total</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-real">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
              <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
              <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="stat-content">
            <div className="stat-value">{formatMonto(totales.real_total)}</div>
            <div className="stat-label">Gasto Real</div>
          </div>
        </div>

        <div className="stat-card">
          <div className={`stat-icon stat-diferencia ${totales.diferencia_total >= 0 ? 'positivo' : 'negativo'}`}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M7 10L12 15L17 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="stat-content">
            <div className={`stat-value ${totales.diferencia_total >= 0 ? 'positivo' : 'negativo'}`}>
              {formatMonto(totales.diferencia_total)}
            </div>
            <div className="stat-label">Diferencia</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-porcentaje">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
              <path d="M12 6V12L16 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
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
              <rect x="3" y="3" width="18" height="18" rx="2" stroke="#cbd5e1" strokeWidth="2"/>
              <path d="M3 9H21" stroke="#cbd5e1" strokeWidth="2"/>
              <path d="M9 3V21" stroke="#cbd5e1" strokeWidth="2"/>
            </svg>
            <p>No hay datos disponibles</p>
          </div>
        ) : (
          <div className="table-scroll-matriz">
            <table className="tabla-matriz">
              <thead>
                <tr>
                  <th className="sticky-col" rowSpan={vistaActual === 'comparativa' ? 2 : 1}>Proy.</th>
                  <th className="sticky-col-2" rowSpan={vistaActual === 'comparativa' ? 2 : 1}>Item</th>
                  {meses.map(m => (
                    <th key={m.num} colSpan={vistaActual === 'comparativa' ? 3 : 1}>
                      {m.nombre}
                    </th>
                  ))}
                  <th colSpan={vistaActual === 'comparativa' ? 3 : 1}>Total</th>
                </tr>
                {vistaActual === 'comparativa' && (
                  <tr>
                    {meses.flatMap(m => [
                      <th key={`pres-${m.num}`} className="sub-header">Pres.</th>,
                      <th key={`real-${m.num}`} className="sub-header">Real</th>,
                      <th key={`dif-${m.num}`} className="sub-header">Dif.</th>
                    ])}
                    <th key="total-pres" className="sub-header">Pres.</th>
                    <th key="total-real" className="sub-header">Real</th>
                    <th key="total-dif" className="sub-header">Dif.</th>
                  </tr>
                )}
              </thead>
              <tbody>
                {proyectosFiltrados.map(proyecto => {
                  const proyectoData = matriz[proyecto.id];
                  if (!proyectoData) return null;

                  const itemsFiltrados = getItemsFiltrados(proyectoData);
                  
                  if (itemsFiltrados.length === 0) return null;

                  return itemsFiltrados.map((item, itemIndex) => {
                    const itemData = proyectoData.items[item.id];

                    return (
                      <tr key={`${proyecto.id}-${item.id}`}>
                        {itemIndex === 0 && (
                          <td 
                            className="sticky-col proyecto-cell" 
                            rowSpan={itemsFiltrados.length}
                            title={proyectoData.nombre}
                          >
                            {proyectoData.nombre}
                          </td>
                        )}
                        <td className="sticky-col-2 item-cell">{itemData.nombre}</td>
                        
                        {meses.flatMap(m => {
                          const datos = itemData.meses[m.num] || { presupuesto: 0, real: 0, diferencia: 0 };
                          
                          if (vistaActual === 'comparativa') {
                            return [
                              <td key={`pres-${proyecto.id}-${item.id}-${m.num}`} className="monto-cell">
                                {datos.presupuesto > 0 ? formatMonto(datos.presupuesto) : '-'}
                              </td>,
                              <td 
                                key={`real-${proyecto.id}-${item.id}-${m.num}`}
                                className={`monto-cell ${datos.real > 0 ? 'clickable' : ''}`}
                                onClick={() => datos.real > 0 && handleCellClick(proyecto.id, item.id, m.num, datos)}
                              >
                                {datos.real > 0 ? formatMonto(datos.real) : '-'}
                              </td>,
                              <td key={`dif-${proyecto.id}-${item.id}-${m.num}`} className={`monto-cell diferencia ${getColorClass(datos.diferencia)}`}>
                                {datos.presupuesto > 0 || datos.real > 0 ? formatMonto(datos.diferencia) : '-'}
                              </td>
                            ];
                          } else if (vistaActual === 'presupuesto') {
                            return [
                              <td key={`${proyecto.id}-${item.id}-${m.num}`} className="monto-cell">
                                {datos.presupuesto > 0 ? formatMonto(datos.presupuesto) : '-'}
                              </td>
                            ];
                          } else {
                            return [
                              <td 
                                key={`${proyecto.id}-${item.id}-${m.num}`}
                                className={`monto-cell ${datos.real > 0 ? 'clickable' : ''}`}
                                onClick={() => datos.real > 0 && handleCellClick(proyecto.id, item.id, m.num, datos)}
                              >
                                {datos.real > 0 ? formatMonto(datos.real) : '-'}
                              </td>
                            ];
                          }
                        })}

                        {/* Totales por fila */}
                        {vistaActual === 'comparativa' ? (
                          <>
                            <td key={`total-pres-${proyecto.id}-${item.id}`} className="monto-cell total-cell">{formatMonto(itemData.total_presupuesto)}</td>
                            <td key={`total-real-${proyecto.id}-${item.id}`} className="monto-cell total-cell">{formatMonto(itemData.total_real)}</td>
                            <td key={`total-dif-${proyecto.id}-${item.id}`} className={`monto-cell total-cell diferencia ${getColorClass(itemData.total_presupuesto - itemData.total_real)}`}>
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
                  <td className="sticky-col total-label">-</td>
                  <td className="sticky-col-2 total-label">TOTALES</td>
                  {meses.flatMap(m => {
                    const totales = totalesPorMes[m.num] || { presupuesto: 0, real: 0, diferencia: 0 };
                    
                    if (vistaActual === 'comparativa') {
                      return [
                        <td key={`total-pres-${m.num}`} className="monto-cell total-cell">{formatMonto(totales.presupuesto)}</td>,
                        <td key={`total-real-${m.num}`} className="monto-cell total-cell">{formatMonto(totales.real)}</td>,
                        <td key={`total-dif-${m.num}`} className={`monto-cell total-cell diferencia ${getColorClass(totales.diferencia)}`}>
                          {formatMonto(totales.diferencia)}
                        </td>
                      ];
                    } else if (vistaActual === 'presupuesto') {
                      return [
                        <td key={`total-${m.num}`} className="monto-cell total-cell">
                          {formatMonto(totales.presupuesto)}
                        </td>
                      ];
                    } else {
                      return [
                        <td key={`total-${m.num}`} className="monto-cell total-cell">
                          {formatMonto(totales.real)}
                        </td>
                      ];
                    }
                  })}
                  {vistaActual === 'comparativa' ? (
                    <>
                      <td key="total-final-pres" className="monto-cell total-cell">{formatMonto(totales.presupuesto_total)}</td>
                      <td key="total-final-real" className="monto-cell total-cell">{formatMonto(totales.real_total)}</td>
                      <td key="total-final-dif" className={`monto-cell total-cell diferencia ${getColorClass(totales.diferencia_total)}`}>
                        {formatMonto(totales.diferencia_total)}
                      </td>
                    </>
                  ) : vistaActual === 'presupuesto' ? (
                    <td className="monto-cell total-cell">{formatMonto(totales.presupuesto_total)}</td>
                  ) : (
                    <td className="monto-cell total-cell">{formatMonto(totales.real_total)}</td>
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
              <button className="btn-close" onClick={cerrarModal}>×</button>
            </div>
            
            {loadingDetalle ? (
              <div className="loading-modal">
                <div className="spinner"></div>
                <p>Cargando detalle...</p>
              </div>
            ) : detalleData ? (
              <div className="modal-body">
                <div className="detalle-info">
                  <p><strong>Proyecto:</strong> {detalleData.proyecto}</p>
                  <p><strong>Item:</strong> {detalleData.item}</p>
                  <p><strong>Mes:</strong> {meses.find(m => m.num === parseInt(detalleData.mes))?.nombre || detalleData.mes}</p>
                </div>

                {detalleData.ordenes_pago && detalleData.ordenes_pago.length > 0 && (
                  <div className="detalle-section">
                    <h4>Órdenes de Pago</h4>
                    <table className="tabla-detalle">
                      <thead>
                        <tr>
                          <th>Orden</th>
                          <th>O.Compra</th>
                          <th>Descripción</th>
                          <th>Monto</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detalleData.ordenes_pago.map(op => (
                          <tr key={op.id}>
                            <td>{op.orden_numero}</td>
                            <td>{op.orden_compra}</td>
                            <td>{op.descripcion || '-'}</td>
                            <td className="text-right">{formatMonto(op.monto)}</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr>
                          <td colSpan="3"><strong>Total Órdenes</strong></td>
                          <td className="text-right"><strong>{formatMonto(detalleData.total_ordenes)}</strong></td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                )}

                {detalleData.gastos_directos && detalleData.gastos_directos.length > 0 && (
                  <div className="detalle-section">
                    <h4>Gastos Directos</h4>
                    <table className="tabla-detalle">
                      <thead>
                        <tr>
                          <th>Descripción</th>
                          <th>Fecha</th>
                          <th>Monto</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detalleData.gastos_directos.map(gd => (
                          <tr key={gd.id}>
                            <td>{gd.descripcion}</td>
                            <td>{gd.fecha}</td>
                            <td className="text-right">{formatMonto(gd.monto)}</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr>
                          <td colSpan="2"><strong>Total Gastos Directos</strong></td>
                          <td className="text-right"><strong>{formatMonto(detalleData.total_gastos)}</strong></td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                )}

                <div className="detalle-total">
                  <p><strong>TOTAL GENERAL:</strong> {formatMonto(detalleData.total)}</p>
                </div>
              </div>
            ) : (
              <div className="modal-body">
                <p>No se pudo cargar el detalle</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default EstadoPresupuesto;