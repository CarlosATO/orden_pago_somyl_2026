import React, { useState, useEffect } from 'react';
import './Pagos.css';

const Pagos = () => {
  // ========= ESTADOS =========
  const [pagos, setPagos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mensaje, setMensaje] = useState({ tipo: '', texto: '' });
  
  // Paginación
  const [page, setPage] = useState(1);
  const [perPage] = useState(100); // Aumentado a 100 para mostrar más filas
  const [totalPages, setTotalPages] = useState(1);
  const [totalRegistros, setTotalRegistros] = useState(0);
  
  // Filtros
  const [filtros, setFiltros] = useState({
    proveedor: '',
    proyecto: '',
    estado: '',
    fecha_desde: '',
    fecha_hasta: '',
    orden_numero: ''
  });
  
  // Datos para filtros
  const [proveedores, setProveedores] = useState([]);
  const [proyectos, setProyectos] = useState([]);
  
  // Estadísticas
  const [stats, setStats] = useState({
    total_ordenes: 0,
    pagadas: 0,
    pendientes: 0,
    total_pendiente: 0,
    saldo_por_proyecto: {}
  });
  
  // Modal de abonos
  const [modalAbonos, setModalAbonos] = useState({
    visible: false,
    orden_numero: null,
    abonos: [],
    nuevoAbono: {
      monto_abono: '',
      fecha_abono: new Date().toISOString().split('T')[0],
      observacion: ''
    }
  });
  
  // ========= EFECTOS =========
  
  useEffect(() => {
    cargarFiltros();
  }, []);
  
  useEffect(() => {
    cargarPagos();
    cargarEstadisticas();
  }, [page, filtros]);
  
  // ========= FUNCIONES DE CARGA =========
  
  const cargarFiltros = async () => {
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch('/api/pagos/filters', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      if (data.success) {
        setProveedores(data.data.proveedores);
        setProyectos(data.data.proyectos);
      }
    } catch (error) {
      console.error('Error cargando filtros:', error);
    }
  };
  
  const cargarPagos = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      
      // Construir query params
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
        ...Object.fromEntries(
          Object.entries(filtros).filter(([_, v]) => v !== '')
        )
      });
      
      const response = await fetch(`/api/pagos/list?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      
      if (data.success) {
        setPagos(data.data.pagos);
        setTotalPages(data.data.pagination.total_pages);
        setTotalRegistros(data.data.pagination.total);
      } else {
        setMensaje({ tipo: 'error', texto: data.message });
      }
    } catch (error) {
      console.error('Error cargando pagos:', error);
      setMensaje({ tipo: 'error', texto: 'Error al cargar pagos' });
    } finally {
      setLoading(false);
    }
  };
  
  const cargarEstadisticas = async () => {
    try {
      const token = localStorage.getItem('authToken');
      
      const params = new URLSearchParams(
        Object.fromEntries(
          Object.entries(filtros).filter(([_, v]) => v !== '')
        )
      );
      
      const response = await fetch(`/api/pagos/stats?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      if (data.success) {
        setStats(data.data);
      }
    } catch (error) {
      console.error('Error cargando estadísticas:', error);
    }
  };
  
  // ========= MANEJADORES DE FILTROS =========
  
  const handleFiltroChange = (campo, valor) => {
    setFiltros(prev => ({ ...prev, [campo]: valor }));
    setPage(1); // Resetear a página 1 al filtrar
  };
  
  const limpiarFiltros = () => {
    setFiltros({
      proveedor: '',
      proyecto: '',
      estado: '',
      fecha_desde: '',
      fecha_hasta: '',
      orden_numero: ''
    });
    setPage(1);
  };
  
  // ========= FUNCIONES DE FECHA DE PAGO =========
  
  const handleFechaPagoChange = async (orden_numero, fecha_pago) => {
    try {
      const token = localStorage.getItem('authToken');
      
      const response = await fetch('/api/pagos/fecha', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ orden_numero, fecha_pago })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMensaje({ tipo: 'success', texto: data.message });
        cargarPagos();
        cargarEstadisticas();
      } else {
        setMensaje({ tipo: 'error', texto: data.message });
      }
    } catch (error) {
      console.error('Error actualizando fecha:', error);
      setMensaje({ tipo: 'error', texto: 'Error al actualizar fecha' });
    }
  };
  
  // ========= FUNCIONES DE ABONOS =========
  
  const abrirModalAbonos = async (orden_numero) => {
    try {
      const token = localStorage.getItem('authToken');
      
      const response = await fetch(`/api/pagos/abonos/${orden_numero}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      
      if (data.success) {
        setModalAbonos({
          visible: true,
          orden_numero,
          abonos: data.data,
          nuevoAbono: {
            monto_abono: '',
            fecha_abono: new Date().toISOString().split('T')[0],
            observacion: ''
          }
        });
      }
    } catch (error) {
      console.error('Error cargando abonos:', error);
    }
  };
  
  const cerrarModalAbonos = () => {
    setModalAbonos({
      visible: false,
      orden_numero: null,
      abonos: [],
      nuevoAbono: {
        monto_abono: '',
        fecha_abono: new Date().toISOString().split('T')[0],
        observacion: ''
      }
    });
  };
  
  const crearAbono = async () => {
    try {
      const token = localStorage.getItem('authToken');
      
      const response = await fetch('/api/pagos/abono', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          orden_numero: modalAbonos.orden_numero,
          ...modalAbonos.nuevoAbono
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMensaje({ tipo: 'success', texto: data.message });
        abrirModalAbonos(modalAbonos.orden_numero); // Recargar abonos
        cargarPagos();
        cargarEstadisticas();
      } else {
        setMensaje({ tipo: 'error', texto: data.message });
      }
    } catch (error) {
      console.error('Error creando abono:', error);
      setMensaje({ tipo: 'error', texto: 'Error al crear abono' });
    }
  };
  
  const eliminarAbono = async (abono_id) => {
    if (!confirm('¿Estás seguro de eliminar este abono?')) return;
    
    try {
      const token = localStorage.getItem('authToken');
      
      const response = await fetch(`/api/pagos/abono/${abono_id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMensaje({ tipo: 'success', texto: data.message });
        abrirModalAbonos(modalAbonos.orden_numero); // Recargar abonos
        cargarPagos();
        cargarEstadisticas();
      } else {
        setMensaje({ tipo: 'error', texto: data.message });
      }
    } catch (error) {
      console.error('Error eliminando abono:', error);
      setMensaje({ tipo: 'error', texto: 'Error al eliminar abono' });
    }
  };
  
  // ========= FUNCIONES DE FORMATO =========
  
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0
    }).format(value);
  };
  
  const getEstadoBadge = (estado) => {
    const badges = {
      pagado: 'badge-success',
      pendiente: 'badge-danger',
      abono: 'badge-warning'
    };
    return badges[estado] || 'badge-secondary';
  };
  
  // ========= RENDER =========
  
  return (
    <div className="pagos-container">
      {/* Mensajes */}
      {mensaje.texto && (
        <div className={`alert alert-${mensaje.tipo === 'error' ? 'danger' : 'success'}`}>
          {mensaje.texto}
          <button 
            type="button" 
            className="btn-close" 
            onClick={() => setMensaje({ tipo: '', texto: '' })}
          >×</button>
        </div>
      )}
      
      {/* Header */}
      <div className="pagos-header">
        <h1>Órdenes de Pago</h1>
        <button className="btn btn-secondary" onClick={limpiarFiltros}>
          Limpiar Filtros
        </button>
      </div>
      
      {/* Layout Superior: Estadísticas (Izq) + Proyectos Pendientes (Der) */}
      <div className="pagos-top-section">
        {/* TABLA DE ESTADÍSTICAS 2x2 - IZQUIERDA */}
        <div className="stats-table-container">
          <h3>Resumen General</h3>
          <table className="stats-table">
            <tbody>
              <tr>
                <td>
                  <div className="stat-value-compact">{stats.total_ordenes}</div>
                  <div className="stat-label-compact">Total Órdenes</div>
                </td>
                <td>
                  <div className="stat-value-compact">{stats.pagadas}</div>
                  <div className="stat-label-compact">Pagadas</div>
                </td>
              </tr>
              <tr>
                <td>
                  <div className="stat-value-compact">{stats.pendientes}</div>
                  <div className="stat-label-compact">Pendientes</div>
                </td>
                <td>
                  <div className="stat-value-compact">{formatCurrency(stats.total_pendiente)}</div>
                  <div className="stat-label-compact">Monto Pendiente</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        
        {/* TABLA DE PROYECTOS PENDIENTES - DERECHA */}
        <div className="proyectos-table-container">
          <h3>Proyectos con Saldo Pendiente</h3>
          {Object.keys(stats.saldo_por_proyecto || {}).length === 0 ? (
            <div className="no-proyectos">
              No hay proyectos con saldo pendiente
            </div>
          ) : (
            <table className="proyectos-table">
              <thead>
                <tr>
                  <th>Proyecto</th>
                  <th>Monto Pendiente</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(stats.saldo_por_proyecto)
                  .sort((a, b) => b[1] - a[1]) // Ordenar por monto descendente
                  .map(([proyecto, monto]) => (
                  <tr key={proyecto}>
                    <td title={proyecto}>{proyecto}</td>
                    <td>{formatCurrency(monto)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      
      {/* Filtros */}
      <div className="filtros-container">
        <div className="filtros-header">
          <h3>Filtros de Búsqueda</h3>
        </div>
        <div className="filtros-row">
          <input
            type="text"
            className="form-control"
            placeholder="Buscar proveedor..."
            value={filtros.proveedor}
            onChange={(e) => handleFiltroChange('proveedor', e.target.value)}
          />
          
          <input
            type="text"
            className="form-control"
            placeholder="N° Orden..."
            value={filtros.orden_numero}
            onChange={(e) => handleFiltroChange('orden_numero', e.target.value)}
          />
          
          <select
            className="form-select"
            value={filtros.proyecto}
            onChange={(e) => handleFiltroChange('proyecto', e.target.value)}
          >
            <option value="">Todos los proyectos</option>
            {proyectos.map(p => (
              <option key={p.id} value={p.id}>{p.nombre}</option>
            ))}
          </select>
          
          <select
            className="form-select"
            value={filtros.estado}
            onChange={(e) => handleFiltroChange('estado', e.target.value)}
          >
            <option value="">Todos los estados</option>
            <option value="pendiente">Pendientes</option>
            <option value="pagado">Pagados</option>
            <option value="abono">Con Abonos</option>
          </select>
          
          <input
            type="date"
            className="form-control"
            value={filtros.fecha_desde}
            onChange={(e) => handleFiltroChange('fecha_desde', e.target.value)}
          />
          
          <input
            type="date"
            className="form-control"
            value={filtros.fecha_hasta}
            onChange={(e) => handleFiltroChange('fecha_hasta', e.target.value)}
          />
        </div>
      </div>
      
      {/* Tabla Principal */}
      <div className="tabla-container">
        {loading ? (
          <div className="loading">Cargando...</div>
        ) : (
          <table className="tabla-pagos">
            <colgroup>
              <col /><col /><col /><col /><col /><col /><col /><col />
              <col /><col /><col /><col /><col /><col /><col />
            </colgroup>
            <thead>
              <tr>
                <th>OP</th>
                <th>Fecha</th>
                <th>Proveedor</th>
                <th>RUT</th>
                <th>Detalle</th>
                <th>Factura</th>
                <th>Total</th>
                <th>Proyecto</th>
                <th>Item</th>
                <th>OC</th>
                <th>Fecha Pago</th>
                <th>Abonos</th>
                <th>Saldo</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {pagos.length === 0 ? (
                <tr>
                  <td colSpan="15" className="no-registros">
                    No hay registros para mostrar
                  </td>
                </tr>
              ) : (
                pagos.map(pago => (
                  <tr key={pago.orden_numero}>
                    <td>{pago.orden_numero}</td>
                    <td>{pago.fecha}</td>
                    <td title={pago.proveedor_nombre}>{pago.proveedor_nombre}</td>
                    <td>{pago.rut_proveedor}</td>
                    <td title={pago.detalle_compra}>{pago.detalle_compra}</td>
                    <td>{pago.factura}</td>
                    <td className="text-right">
                      <strong>{formatCurrency(pago.total_pago)}</strong>
                    </td>
                    <td title={pago.proyecto_nombre}>{pago.proyecto_nombre}</td>
                    <td>{pago.item}</td>
                    <td>{pago.orden_compra}</td>
                    <td>
                      <div className="fecha-input-wrapper">
                        <input
                          type="date"
                          className="form-control-sm"
                          placeholder="Seleccionar fecha"
                          value={pago.fecha_pago || ''}
                          onChange={(e) => handleFechaPagoChange(pago.orden_numero, e.target.value)}
                          title="Haz clic para seleccionar fecha de pago"
                        />
                        <svg className="calendar-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                          <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5zM1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4H1z"/>
                        </svg>
                      </div>
                    </td>
                    <td className="text-right">{formatCurrency(pago.total_abonado)}</td>
                    <td className="text-right">
                      <strong>{formatCurrency(pago.saldo_pendiente)}</strong>
                    </td>
                    <td>
                      <span className={`badge ${getEstadoBadge(pago.estado)}`}>
                        {pago.estado}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={() => abrirModalAbonos(pago.orden_numero)}
                      >
                        Abonos
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
      
      {/* Paginación */}
      <div className="paginacion">
        <div className="paginacion-info">
          Mostrando {((page - 1) * perPage) + 1} - {Math.min(page * perPage, totalRegistros)} de {totalRegistros}
        </div>
        <div className="paginacion-botones">
          <button
            className="btn btn-sm btn-secondary"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            Anterior
          </button>
          <span className="page-info">Página {page} de {totalPages}</span>
          <button
            className="btn btn-sm btn-secondary"
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            Siguiente
          </button>
        </div>
      </div>
      
      {/* Modal de Abonos (mantener igual) */}
      {modalAbonos.visible && (
        <div className="modal-overlay" onClick={cerrarModalAbonos}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Abonos - Orden #{modalAbonos.orden_numero}</h2>
              <button className="btn-close" onClick={cerrarModalAbonos}>×</button>
            </div>
            
            <div className="modal-body">
              <div className="abonos-list">
                <h3>Abonos Registrados</h3>
                {modalAbonos.abonos.length === 0 ? (
                  <p className="no-registros">No hay abonos registrados</p>
                ) : (
                  <table className="tabla-abonos">
                    <thead>
                      <tr>
                        <th>Fecha</th>
                        <th>Monto</th>
                        <th>Observación</th>
                        <th>Acción</th>
                      </tr>
                    </thead>
                    <tbody>
                      {modalAbonos.abonos.map(abono => (
                        <tr key={abono.id}>
                          <td>{abono.fecha_abono}</td>
                          <td>{formatCurrency(abono.monto_abono)}</td>
                          <td>{abono.observacion}</td>
                          <td>
                            <button
                              className="btn btn-sm btn-danger"
                              onClick={() => eliminarAbono(abono.id)}
                            >
                              Eliminar
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
              
              <div className="nuevo-abono">
                <h3>Registrar Nuevo Abono</h3>
                <div className="form-row">
                  <div className="form-group">
                    <label>Monto</label>
                    <input
                      type="number"
                      className="form-control"
                      value={modalAbonos.nuevoAbono.monto_abono}
                      onChange={(e) => setModalAbonos(prev => ({
                        ...prev,
                        nuevoAbono: { ...prev.nuevoAbono, monto_abono: e.target.value }
                      }))}
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>Fecha</label>
                    <input
                      type="date"
                      className="form-control"
                      value={modalAbonos.nuevoAbono.fecha_abono}
                      onChange={(e) => setModalAbonos(prev => ({
                        ...prev,
                        nuevoAbono: { ...prev.nuevoAbono, fecha_abono: e.target.value }
                      }))}
                    />
                  </div>
                </div>
                
                <div className="form-group">
                  <label>Observación</label>
                  <textarea
                    className="form-control"
                    rows="2"
                    value={modalAbonos.nuevoAbono.observacion}
                    onChange={(e) => setModalAbonos(prev => ({
                      ...prev,
                      nuevoAbono: { ...prev.nuevoAbono, observacion: e.target.value }
                    }))}
                  />
                </div>
                
                <button className="btn btn-primary" onClick={crearAbono}>
                  Guardar Abono
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Pagos;
