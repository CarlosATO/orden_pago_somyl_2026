import { useState, useEffect, useCallback, Fragment } from 'react';
import './EstadoPresupuesto.css';
import ChartsPresupuesto from './ChartsPresupuesto';
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
  const [resumen, setResumen] = useState({
    presupuesto_inicial: { venta: 0, gasto: 0, saldo: 0 },
    estado_actual: { produccion: 0, gasto: 0, saldo: 0 },
    indicadores: { ejecucion_presupuesto: 0, avance_produccion: 0, variacion_saldo: 0, meses_analizados: 0 }
  });
  const [loading, setLoading] = useState(false);
  const [loadingProyectos, setLoadingProyectos] = useState(true); // Nuevo: loading separado para proyectos
  const [mensaje, setMensaje] = useState(null);
  
  // Filtros
  const [proyectoSeleccionado, setProyectoSeleccionado] = useState(''); // Cambiado de 'todos' a '' para no cargar nada
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

  // Funciones de carga de datos
  const fetchProyectos = useCallback(async () => {
    console.log('🔄 Iniciando carga de proyectos...');
    setLoadingProyectos(true);
    try {
      const token = getAuthToken();
      if (!token) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
        return;
      }

      const response = await fetch('/api/proyectos/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          console.log('✅ Proyectos cargados:', data.data?.length || 0);
          console.log('📋 Lista de proyectos:', data.data);
          setProyectos(data.data || []);
        } else {
          console.error('❌ Error en respuesta:', data.message);
        }
      } else if (response.status === 401) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
      } else {
        console.error('❌ Error HTTP:', response.status, response.statusText);
        setMensaje({ tipo: 'error', texto: `Error ${response.status} al cargar proyectos` });
      }
    } catch (error) {
      console.error('❌ Error al cargar proyectos:', error);
      setMensaje({ tipo: 'error', texto: 'Error al cargar lista de proyectos' });
    } finally {
      console.log('✅ Carga de proyectos finalizada');
      setLoadingProyectos(false);
    }
  }, []);

  const fetchEstadoPresupuesto = useCallback(async () => {
    setLoading(true);
    try {
      const token = getAuthToken();
      if (!token) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
        return;
      }

      // Solo permitir IDs específicos, NO "todos"
      if (!proyectoSeleccionado || proyectoSeleccionado === '') {
        setLoading(false);
        return;
      }

      // Construir URL con filtro de proyecto (siempre con ID específico)
      const url = `/api/estado-presupuesto/?proyecto_id=${proyectoSeleccionado}`;

      const response = await fetch(url, {
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
          console.log('✅ Resumen:', data.data.resumen);
          setMatriz(data.data.matriz);
          
          // NO actualizar la lista de proyectos aquí
          // La lista de proyectos se carga solo con fetchProyectos()
          
          setItems(data.data.items);
          setTotales(data.data.totales);
          setResumen(data.data.resumen || {
            presupuesto_inicial: { venta: 0, gasto: 0, saldo: 0 },
            estado_actual: { produccion: 0, gasto: 0, saldo: 0 },
            indicadores: { ejecucion_presupuesto: 0, avance_produccion: 0, variacion_saldo: 0, meses_analizados: 0 }
          });
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
  }, [proyectoSeleccionado]);

  useEffect(() => {
    // Cargar lista de proyectos al montar el componente
    fetchProyectos();
  }, [fetchProyectos]);

  useEffect(() => {
    // Cargar datos SOLO si hay un proyecto seleccionado Y no es vacío
    if (proyectoSeleccionado && proyectoSeleccionado !== '') {
      fetchEstadoPresupuesto();
    } else {
      // Limpiar datos si no hay selección
      setMatriz({});
      setItems([]);
      setTotales({
        presupuesto_total: 0,
        real_total: 0,
        diferencia_total: 0
      });
      setResumen({
        presupuesto_inicial: { venta: 0, gasto: 0, saldo: 0 },
        estado_actual: { produccion: 0, gasto: 0, saldo: 0 },
        indicadores: { ejecucion_presupuesto: 0, avance_produccion: 0, variacion_saldo: 0, meses_analizados: 0 }
      });
    }
  }, [proyectoSeleccionado, fetchEstadoPresupuesto]);

  useEffect(() => {
    if (mensaje) {
      const timer = setTimeout(() => setMensaje(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [mensaje]);

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

  const descargarPDF = async () => {
    if (!modalDetalle) return;
    
    try {
      const token = getAuthToken();
      const { proyectoId, itemId, mes } = modalDetalle;
      
      const response = await fetch(
        `/api/estado-presupuesto/detalle/pdf?proyecto_id=${proyectoId}&item_id=${itemId}&mes=${mes}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `detalle_gastos_${proyectoId}_${itemId}_${mes}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        console.error('Error al descargar PDF');
      }
    } catch (error) {
      console.error('Error:', error);
    }
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
        return false;
      }

      if (vistaActual === 'comparativa') {
        const tieneData = itemData.total_presupuesto > 0 || itemData.total_real > 0;
        if (tieneData) {
          console.log(`✅ Item incluido: ${item.item} (P: ${itemData.total_presupuesto}, R: ${itemData.total_real})`);
        }
        return tieneData;
      }
      
      if (vistaActual === 'presupuesto') {
        return itemData.total_presupuesto > 0;
      }
      
      if (vistaActual === 'real') {
        return itemData.total_real > 0;
      }
      
      return false;
    });
    
    console.log(`🔢 Total items filtrados para ${proyectoData.nombre}: ${itemsFiltrados.length} de ${items.length} totales`);
    console.log(`📋 Items mostrados:`, itemsFiltrados.map(i => i.item).join(', '));
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
  </div>

  {/* Filtros */}
      {mensaje && (
        <div className={`alert alert-${mensaje.tipo === 'error' ? 'danger' : 'success'}`}>
          {mensaje.texto}
        </div>
      )}

      {/* Stats Cards - Nuevo formato */}
      <div className="presupuesto-section">
        {/* Columna Izquierda - Presupuesto Inicial */}
        <div className="presupuesto-inicial">
          <div className="section-header-blue">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M9 7H7C5.89543 7 5 7.89543 5 9V19C5 20.1046 5.89543 21 7 21H17C18.1046 21 19 20.1046 19 19V9C19 7.89543 18.1046 7 17 7H15M9 7V5C9 3.89543 9.89543 3 11 3H13C14.1046 3 15 3.89543 15 5V7M9 7H15" stroke="currentColor" strokeWidth="2"/>
            </svg>
            PRESUPUESTO INICIAL
          </div>
          <div className="presupuesto-content">
            <div className="presupuesto-row">
              <span className="label">Venta presupuestada</span>
              <span className="value value-blue">{formatMonto(resumen.presupuesto_inicial?.venta || 0)}</span>
            </div>
            <div className="presupuesto-row">
              <span className="label">Gasto presupuestado</span>
              <span className="value value-red">{formatMonto(resumen.presupuesto_inicial?.gasto || 0)}</span>
            </div>
            <div className="presupuesto-row presupuesto-saldo">
              <span className="label-saldo">Saldo presupuestado</span>
              <span className="value value-green">{formatMonto(resumen.presupuesto_inicial?.saldo || 0)}</span>
            </div>
          </div>
        </div>

        {/* Columna Derecha - Estado Actual */}
        <div className="estado-actual">
          <div className="section-header-green">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M3 3V21H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <path d="M7 16L12 11L16 15L21 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            ESTADO ACTUAL
          </div>
          <div className="estado-content">
            <div className="estado-row">
              <span className="label">Producción actual</span>
              <span className="value value-green-border">{formatMonto(resumen.estado_actual?.produccion || 0)}</span>
            </div>
            <div className="estado-row">
              <span className="label">Gasto actual</span>
              <span className="value value-red">{formatMonto(resumen.estado_actual?.gasto || 0)}</span>
            </div>
            <div className="estado-row estado-saldo">
              <span className="label-saldo">Saldo actual</span>
              <span className={`value ${(resumen.estado_actual?.saldo || 0) >= 0 ? 'value-green' : 'value-red'}`}>
                {formatMonto(resumen.estado_actual?.saldo || 0)}
              </span>
            </div>
          </div>
        </div>
  </div>

  {/* Gráficos comparativos: SOLO si hay proyecto seleccionado */}
  {proyectoSeleccionado && proyectoSeleccionado !== '' && (
    <ChartsPresupuesto proyectoId={proyectoSeleccionado} />
  )}

  {/* Stats Cards Inferiores */}
      <div className="stats-grid-bottom">
        <div className="stat-card-small">
          <div className="stat-value-large stat-blue">
            {resumen.indicadores?.ejecucion_presupuesto?.toFixed(1) || '0.0'}%
          </div>
          <div className="stat-label-small">EJECUCIÓN PRESUPUESTO</div>
        </div>

        <div className="stat-card-small">
          <div className="stat-value-large stat-yellow">
            {resumen.indicadores?.avance_produccion?.toFixed(1) || '0.0'}%
          </div>
          <div className="stat-label-small">AVANCE PRODUCCIÓN</div>
        </div>

        <div className="stat-card-small">
          <div className="stat-value-large stat-green">
            {formatMonto(resumen.indicadores?.variacion_saldo || 0)}
          </div>
          <div className="stat-label-small">VARIACIÓN SALDO</div>
        </div>

        <div className="stat-card-small">
          <div className="stat-value-large stat-cyan">
            {resumen.indicadores?.meses_analizados || 0}
          </div>
          <div className="stat-label-small">MESES ANALIZADOS</div>
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
          <select 
            value={proyectoSeleccionado} 
            onChange={(e) => {
              console.log('📋 Proyecto seleccionado:', e.target.value);
              setProyectoSeleccionado(e.target.value);
            }}
            disabled={loadingProyectos}
          >
            <option value="">
              {loadingProyectos ? 'Cargando proyectos...' : 'Seleccione un proyecto...'}
            </option>
            {console.log('🔍 Proyectos en estado para renderizar:', proyectos.length, proyectos)}
            {proyectos.map(p => (
              <option key={p.id} value={p.id}>{p.proyecto}</option>
            ))}
          </select>
          {loading && <span className="loading-indicator">Cargando datos...</span>}
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
        ) : !proyectoSeleccionado ? (
          <div className="empty-state">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
              <path d="M21 16V8C20.9996 7.64928 20.9071 7.30481 20.7315 7.00116C20.556 6.69751 20.3037 6.44536 20 6.27L13 2.27C12.696 2.09446 12.3511 2.00205 12 2.00205C11.6489 2.00205 11.304 2.09446 11 2.27L4 6.27C3.69626 6.44536 3.44398 6.69751 3.26846 7.00116C3.09294 7.30481 3.00036 7.64928 3 8V16C3.00036 16.3507 3.09294 16.6952 3.26846 16.9988C3.44398 17.3025 3.69626 17.5546 4 17.73L11 21.73C11.304 21.9055 11.6489 21.9979 12 21.9979C12.3511 21.9979 12.696 21.9055 13 21.73L20 17.73C20.3037 17.5546 20.556 17.3025 20.7315 16.9988C20.9071 16.6952 20.9996 16.3507 21 16Z" stroke="#94a3b8" strokeWidth="2"/>
            </svg>
            <p>Seleccione un proyecto para ver el estado del presupuesto</p>
          </div>
        ) : proyectosFiltrados.length === 0 ? (
          <div className="empty-state">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
              <rect x="3" y="3" width="18" height="18" rx="2" stroke="#cbd5e1" strokeWidth="2"/>
              <path d="M3 9H21" stroke="#cbd5e1" strokeWidth="2"/>
              <path d="M9 3V21" stroke="#cbd5e1" strokeWidth="2"/>
            </svg>
            <p>No hay datos disponibles para este proyecto</p>
          </div>
        ) : (
          <div className="table-scroll-matriz">
            <div className={`tabla-matriz vista-${vistaActual}`}>
              {/* Header Principal */}
              <div className="tabla-header-matriz">
                <div className="header-cell sticky-col-item">Item</div>
                {meses.map(m => (
                  <div key={m.num} className="header-mes">
                    {m.nombre}
                  </div>
                ))}
                <div className="header-mes">Total</div>
              </div>

              {/* Sub-header para vista comparativa - SOLO DIFERENCIA */}
              {vistaActual === 'comparativa' && (
                <div className="tabla-subheader-matriz">
                  <div className="subheader-spacer sticky-col-item"></div>
                  {meses.map(m => (
                    <div key={`dif-${m.num}`} className="subheader-cell">Dif.</div>
                  ))}
                  <div key="total-dif" className="subheader-cell">Dif.</div>
                </div>
              )}

              {/* Body - Filas de datos */}
              <div className="tabla-body-matriz">
                {proyectosFiltrados.map(proyecto => {
                  const proyectoData = matriz[proyecto.id];
                  if (!proyectoData) {
                    console.log(`❌ No se encontró proyectoData para proyecto ${proyecto.id}`);
                    return null;
                  }

                  const itemsFiltrados = getItemsFiltrados(proyectoData);
                  
                  console.log(`📋 Proyecto ${proyectoData.nombre}: ${itemsFiltrados.length} items filtrados`);
                  
                  if (itemsFiltrados.length === 0) {
                    console.log(`⚠️ No hay items para mostrar en proyecto ${proyectoData.nombre}`);
                    return null;
                  }

                  return (
                    <Fragment key={proyecto.id}>
                      {/* Fila de encabezado de proyecto */}
                      <div className="tabla-row-proyecto">
                        <div className="proyecto-header-cell">
                          {proyectoData.nombre}
                        </div>
                      </div>

                      {/* Filas de items */}
                      {itemsFiltrados.map((item, itemIndex) => {
                        const itemData = proyectoData.items[item.id];
                        
                        if (!itemData) {
                          console.log(`❌ No itemData para item ${item.id}`);
                          return null;
                        }

                        console.log(`✅ Renderizando fila: ${proyectoData.nombre} - ${itemData.nombre}`);

                        return (
                          <div key={`${proyecto.id}-${item.id}`} className="tabla-row-matriz">
                            <div className="data-cell sticky-col-item item-cell">{itemData.nombre}</div>
                            
                            {meses.flatMap(m => {
                              const datos = itemData.meses[m.num] || { presupuesto: 0, real: 0, diferencia: 0 };
                          
                              if (vistaActual === 'comparativa') {
                                // SOLO MOSTRAR DIFERENCIA en comparativa
                                return (
                                  <div key={`dif-${proyecto.id}-${item.id}-${m.num}`} className={`data-cell monto-cell diferencia ${getColorClass(datos.diferencia)}`}>
                                    {datos.presupuesto > 0 || datos.real > 0 ? formatMonto(datos.diferencia) : '-'}
                                  </div>
                                );
                              } else if (vistaActual === 'presupuesto') {
                                return (
                                  <div key={`${proyecto.id}-${item.id}-${m.num}`} className="data-cell monto-cell">
                                    {datos.presupuesto > 0 ? formatMonto(datos.presupuesto) : '-'}
                                  </div>
                                );
                              } else {
                                return (
                                  <div 
                                    key={`${proyecto.id}-${item.id}-${m.num}`}
                                    className={`data-cell monto-cell ${datos.real > 0 ? 'clickable' : ''}`}
                                    onClick={() => datos.real > 0 && handleCellClick(proyecto.id, item.id, m.num, datos)}
                                  >
                                    {datos.real > 0 ? formatMonto(datos.real) : '-'}
                                  </div>
                                );
                              }
                            })}

                            {/* Total por fila */}
                            {vistaActual === 'comparativa' ? (
                              <div key={`total-dif-${proyecto.id}-${item.id}`} className={`data-cell monto-cell total-cell diferencia ${getColorClass(itemData.total_presupuesto - itemData.total_real)}`}>
                                {formatMonto(itemData.total_presupuesto - itemData.total_real)}
                              </div>
                            ) : vistaActual === 'presupuesto' ? (
                              <div className="data-cell monto-cell total-cell">{formatMonto(itemData.total_presupuesto)}</div>
                            ) : (
                              <div className="data-cell monto-cell total-cell">{formatMonto(itemData.total_real)}</div>
                            )}
                          </div>
                        );
                      })}
                    </Fragment>
                  );
                })}

                {/* Fila de totales */}
                <div className="tabla-row-matriz total-row">
                  <div className="data-cell sticky-col-item total-label">TOTALES</div>
                  {meses.map(m => {
                    const totalesMes = totalesPorMes[m.num] || { presupuesto: 0, real: 0, diferencia: 0 };
                    
                    if (vistaActual === 'comparativa') {
                      return (
                        <div key={`total-dif-${m.num}`} className={`data-cell monto-cell total-cell diferencia ${getColorClass(totalesMes.diferencia)}`}>
                          {formatMonto(totalesMes.diferencia)}
                        </div>
                      );
                    } else if (vistaActual === 'presupuesto') {
                      return (
                        <div key={`total-${m.num}`} className="data-cell monto-cell total-cell">
                          {formatMonto(totalesMes.presupuesto)}
                        </div>
                      );
                    } else {
                      return (
                        <div key={`total-${m.num}`} className="data-cell monto-cell total-cell">
                          {formatMonto(totalesMes.real)}
                        </div>
                      );
                    }
                  })}
                  {vistaActual === 'comparativa' ? (
                    <div key="total-final-dif" className={`data-cell monto-cell total-cell diferencia ${getColorClass(totales.diferencia_total)}`}>
                      {formatMonto(totales.diferencia_total)}
                    </div>
                  ) : vistaActual === 'presupuesto' ? (
                    <div className="data-cell monto-cell total-cell">{formatMonto(totales.presupuesto_total)}</div>
                  ) : (
                    <div className="data-cell monto-cell total-cell">{formatMonto(totales.real_total)}</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modal de Detalle */}
      {modalDetalle && (
        <div className="modal-overlay" onClick={cerrarModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Detalle de Gastos</h3>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button 
                  className="btn-pdf" 
                  onClick={descargarPDF}
                  title="Descargar PDF"
                  style={{
                    backgroundColor: '#dc2626',
                    color: 'white',
                    border: 'none',
                    padding: '8px 16px',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '14px',
                    fontWeight: '500',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" strokeWidth="2"/>
                    <polyline points="14 2 14 8 20 8" strokeWidth="2"/>
                    <line x1="12" y1="18" x2="12" y2="12" strokeWidth="2"/>
                    <line x1="9" y1="15" x2="15" y2="15" strokeWidth="2"/>
                  </svg>
                  PDF
                </button>
                <button className="btn-close" onClick={cerrarModal}>×</button>
              </div>
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
                          <th>Proveedor</th>
                          <th>Descripción</th>
                          <th>Monto</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detalleData.ordenes_pago.map(op => (
                          <tr key={op.id}>
                            <td>{op.orden_numero}</td>
                            <td>{op.orden_compra}</td>
                            <td>{op.proveedor || '-'}</td>
                            <td>{op.descripcion || '-'}</td>
                            <td className="text-right">{formatMonto(op.monto)}</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr>
                          <td colSpan="4"><strong>Total Órdenes</strong></td>
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