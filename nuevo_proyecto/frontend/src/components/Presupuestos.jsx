import { useState, useEffect } from 'react';
import './Presupuestos.css';

function Presupuestos() {
  // Estados para datos
  const [proyectos, setProyectos] = useState([]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Estados para navegación entre vistas
  const [vistaActual, setVistaActual] = useState('lista'); // 'lista' o 'editar'
  const [proyectoEditando, setProyectoEditando] = useState(null);
  const [mostrarModalProyecto, setMostrarModalProyecto] = useState(false);
  const [nuevoProyecto, setNuevoProyecto] = useState({ nombre: '', venta: '', observacion: '' });
  
  // Estados para formulario multi-línea
  const [lineasPresupuesto, setLineasPresupuesto] = useState([
    { item: '', detalle: '', fecha: new Date().toISOString().split('T')[0], monto: '' }
  ]);
  
  // Estados para gastos existentes
  const [gastosProyecto, setGastosProyecto] = useState([]);
  const [stats, setStats] = useState(null);

  const API_URL = '/api';

  // Cargar proyectos e items al iniciar
  useEffect(() => {
    cargarDatosIniciales();
  }, []);

  const cargarDatosIniciales = async () => {
    const token = localStorage.getItem('authToken');
    setLoading(true);
    
    try {
      // Cargar proyectos
      const resProyectos = await fetch(`${API_URL}/proyectos/api/activos`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const dataProyectos = await resProyectos.json();
      const proyectosBase = dataProyectos.data || [];

      // Cargar totales de presupuesto para cada proyecto
      const proyectosConTotales = await Promise.all(
        proyectosBase.map(async (proyecto) => {
          try {
            const resGastos = await fetch(`${API_URL}/presupuestos/gastos/${proyecto.id}`, {
              headers: { 'Authorization': `Bearer ${token}` }
            });
            const dataGastos = await resGastos.json();
            return {
              ...proyecto,
              montoTotal: dataGastos.stats?.total_amount || 0,
              cantidadRegistros: dataGastos.stats?.total_entries || 0
            };
          } catch {
            return { ...proyecto, montoTotal: 0, cantidadRegistros: 0 };
          }
        })
      );

      setProyectos(proyectosConTotales);

      // Cargar items
      const resItems = await fetch(`${API_URL}/items/todos`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const dataItems = await resItems.json();
      setItems(dataItems.data || []);
    } catch (error) {
      console.error('Error al cargar datos:', error);
      alert('Error al cargar datos iniciales');
    } finally {
      setLoading(false);
    }
  };

  // Abrir vista de edición
  const handleEditarProyecto = async (proyecto) => {
    setProyectoEditando(proyecto);
    setVistaActual('editar');
    await cargarGastosProyecto(proyecto.id);
  };

  // Volver a lista
  const handleVolverLista = () => {
    setVistaActual('lista');
    setProyectoEditando(null);
    setLineasPresupuesto([
      { item: '', detalle: '', fecha: new Date().toISOString().split('T')[0], monto: '' }
    ]);
    // Recargar proyectos para actualizar totales
    cargarDatosIniciales();
  };

  // Crear nuevo proyecto
  const handleCrearProyecto = async (e) => {
    e.preventDefault();
    
    if (!nuevoProyecto.nombre.trim()) {
      alert('El nombre del proyecto es obligatorio');
      return;
    }

    const token = localStorage.getItem('authToken');
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/proyectos`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          proyecto: nuevoProyecto.nombre.toUpperCase(),
          venta: nuevoProyecto.venta ? parseInt(nuevoProyecto.venta) : null,
          observacion: nuevoProyecto.observacion || null
        })
      });

      const data = await response.json();
      
      if (data.success) {
        alert('✓ Proyecto creado exitosamente');
        setMostrarModalProyecto(false);
        setNuevoProyecto({ nombre: '', venta: '', observacion: '' });
        await cargarDatosIniciales();
      } else {
        alert(data.message || 'Error al crear proyecto');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Error al crear proyecto');
    } finally {
      setLoading(false);
    }
  };

  // Cargar gastos del proyecto
  const cargarGastosProyecto = async (proyectoId) => {
    setLoading(true);
    const token = localStorage.getItem('authToken');
    
    try {
      const response = await fetch(`${API_URL}/presupuestos/gastos/${proyectoId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      
      if (data.success) {
        setGastosProyecto(data.gastos || []);
        setStats(data.stats || null);
      }
    } catch (error) {
      console.error('Error al cargar gastos:', error);
    } finally {
      setLoading(false);
    }
  };

  // Agregar nueva línea
  const handleAgregarLinea = () => {
    setLineasPresupuesto([
      ...lineasPresupuesto,
      { item: '', detalle: '', fecha: new Date().toISOString().split('T')[0], monto: '' }
    ]);
  };

  // Eliminar línea
  const handleEliminarLinea = (index) => {
    if (lineasPresupuesto.length === 1) {
      alert('Debe haber al menos una línea');
      return;
    }
    const nuevasLineas = lineasPresupuesto.filter((_, i) => i !== index);
    setLineasPresupuesto(nuevasLineas);
  };

  // Cambiar valor de línea
  const handleCambioLinea = (index, campo, valor) => {
    const nuevasLineas = [...lineasPresupuesto];
    nuevasLineas[index][campo] = valor;
    setLineasPresupuesto(nuevasLineas);
  };

  // Guardar todos los presupuestos
  const handleGuardarTodo = async () => {
    // Validar que haya al menos una línea completa
    const lineasValidas = lineasPresupuesto.filter(
      linea => linea.item && linea.monto && linea.fecha
    );

    if (lineasValidas.length === 0) {
      alert('Debe completar al menos una línea con ítem, monto y fecha');
      return;
    }

    const token = localStorage.getItem('authToken');
    setLoading(true);

    try {
      // Guardar cada línea
      let errores = 0;
      let exitosos = 0;

      for (const linea of lineasValidas) {
        try {
          const response = await fetch(`${API_URL}/presupuestos`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              proyecto_id: proyectoEditando.id,
              item: linea.item,
              detalle: linea.detalle || '',
              fecha: linea.fecha,
              monto: parseFloat(linea.monto)
            })
          });

          const data = await response.json();
          if (data.success) {
            exitosos++;
          } else {
            errores++;
          }
        } catch {
          errores++;
        }
      }

      if (exitosos > 0) {
        alert(`✓ Se guardaron ${exitosos} presupuesto(s) exitosamente${errores > 0 ? `. ${errores} fallaron.` : ''}`);
        // Limpiar formulario
        setLineasPresupuesto([
          { item: '', detalle: '', fecha: new Date().toISOString().split('T')[0], monto: '' }
        ]);
        // Recargar gastos
        await cargarGastosProyecto(proyectoEditando.id);
      } else {
        alert('Error: No se pudo guardar ningún presupuesto');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Error al guardar presupuestos');
    } finally {
      setLoading(false);
    }
  };

  // Eliminar gasto existente
  const handleEliminarGasto = async (gastoId) => {
    if (!confirm('¿Está seguro de eliminar este registro?')) return;

    const token = localStorage.getItem('authToken');
    
    try {
      const response = await fetch(`${API_URL}/presupuestos/${gastoId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const data = await response.json();
      
      if (data.success) {
        alert('✓ Registro eliminado exitosamente');
        await cargarGastosProyecto(proyectoEditando.id);
      } else {
        alert(data.message || 'Error al eliminar');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Error al eliminar');
    }
  };

  // Formatear moneda
  const formatMonto = (monto) => {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP'
    }).format(monto);
  };

  // Formatear fecha
  const formatFecha = (fecha) => {
    return new Date(fecha).toLocaleDateString('es-CL');
  };

  // ========== RENDER ==========
  return (
    <div className="presupuestos-container">
      {/* Header */}
      <div className="presupuestos-header">
        <h1>
          <span className="icon-presupuesto">💰</span>
          Presupuestos
        </h1>
        {vistaActual === 'lista' ? (
          <button className="btn-presupuesto btn-primary" onClick={() => setMostrarModalProyecto(true)}>
            + Nuevo Proyecto
          </button>
        ) : (
          <button className="btn-presupuesto btn-secondary" onClick={handleVolverLista}>
            ← Volver a Lista
          </button>
        )}
      </div>

      {/* VISTA: LISTA DE PROYECTOS */}
      {vistaActual === 'lista' && (
        <>
          {loading ? (
            <div className="loading visible">
              <div className="spinner"></div>
              Cargando proyectos...
            </div>
          ) : proyectos.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📋</div>
              <div className="empty-state-text">
                No hay proyectos disponibles. Crea proyectos en la sección de Configuración.
              </div>
            </div>
          ) : (
            <div className="tabla-proyectos">
              <h3>Proyectos</h3>
              <div className="tabla-wrapper">
                <table className="tabla-minimalista">
                  <thead>
                    <tr>
                      <th>Proyecto</th>
                      <th>Monto Total</th>
                      <th>Registros</th>
                      <th>Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {proyectos.map((proyecto) => (
                      <tr key={proyecto.id}>
                        <td className="proyecto-nombre">{proyecto.proyecto}</td>
                        <td className="monto">{formatMonto(proyecto.montoTotal)}</td>
                        <td>{proyecto.cantidadRegistros}</td>
                        <td>
                          <button
                            className="btn-editar"
                            onClick={() => handleEditarProyecto(proyecto)}
                          >
                            ✏️ Editar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* VISTA: EDICIÓN DE PROYECTO */}
      {vistaActual === 'editar' && proyectoEditando && (
        <>
          {/* Info del proyecto */}
          <div className="proyecto-info">
            <h2>{proyectoEditando.proyecto}</h2>
            <div className="stats-inline">
              <span>Total Presupuestado: <strong>{formatMonto(stats?.total_amount || 0)}</strong></span>
              <span>•</span>
              <span>Registros: <strong>{stats?.total_entries || 0}</strong></span>
              {lineasPresupuesto.some(l => l.monto) && (
                <>
                  <span>•</span>
                  <span>Total Nuevo: <strong className="total-nuevo">
                    {formatMonto(lineasPresupuesto.reduce((sum, l) => sum + (parseFloat(l.monto) || 0), 0))}
                  </strong></span>
                </>
              )}
            </div>
          </div>

          {/* Formulario multi-línea */}
          <div className="form-multilínea">
            <h3>Agregar Presupuestos</h3>
            
            <div className="lineas-container">
              {lineasPresupuesto.map((linea, index) => (
                <div key={index} className="linea-presupuesto">
                  <div className="linea-numero">{index + 1}</div>
                  
                  <div className="linea-campos">
                    <div className="form-field">
                      <label>Ítem *</label>
                      <select
                        value={linea.item}
                        onChange={(e) => handleCambioLinea(index, 'item', e.target.value)}
                        required
                      >
                        <option value="">-- Seleccione --</option>
                        {items.map((item) => (
                          <option key={item.id} value={item.tipo}>
                            {item.tipo}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="form-field">
                      <label>Monto *</label>
                      <input
                        type="number"
                        value={linea.monto}
                        onChange={(e) => handleCambioLinea(index, 'monto', e.target.value)}
                        placeholder="0"
                        min="0"
                        required
                      />
                    </div>

                    <div className="form-field">
                      <label>Fecha *</label>
                      <input
                        type="date"
                        value={linea.fecha}
                        onChange={(e) => handleCambioLinea(index, 'fecha', e.target.value)}
                        required
                      />
                    </div>

                    <div className="form-field form-field-detalle">
                      <label>Detalle</label>
                      <input
                        type="text"
                        value={linea.detalle}
                        onChange={(e) => handleCambioLinea(index, 'detalle', e.target.value)}
                        placeholder="Descripción opcional"
                        maxLength="200"
                      />
                    </div>
                  </div>

                  <button
                    type="button"
                    className="btn-eliminar-linea"
                    onClick={() => handleEliminarLinea(index)}
                    disabled={lineasPresupuesto.length === 1}
                  >
                    🗑️
                  </button>
                </div>
              ))}
            </div>

            <div className="form-acciones">
              <button
                type="button"
                className="btn-presupuesto btn-secondary"
                onClick={handleAgregarLinea}
              >
                + Agregar Línea
              </button>
              <button
                type="button"
                className="btn-presupuesto btn-primary"
                onClick={handleGuardarTodo}
                disabled={loading}
              >
                {loading ? 'Guardando...' : '💾 Guardar Todo'}
              </button>
            </div>
          </div>

          {/* Tabla de gastos existentes */}
          {loading ? (
            <div className="loading visible">
              <div className="spinner"></div>
              Cargando historial...
            </div>
          ) : gastosProyecto.length > 0 ? (
            <div className="tabla-gastos visible">
              <h3>Historial de Presupuestos</h3>
              <div className="tabla-wrapper">
                <table className="tabla-minimalista">
                  <thead>
                    <tr>
                      <th>Fecha</th>
                      <th>Ítem</th>
                      <th>Detalle</th>
                      <th>Monto</th>
                      <th>Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gastosProyecto.map((gasto) => (
                      <tr key={gasto.id}>
                        <td>{formatFecha(gasto.fecha)}</td>
                        <td>
                          <span className="badge-item">{gasto.item}</span>
                        </td>
                        <td>{gasto.detalle || '-'}</td>
                        <td className="monto">{formatMonto(gasto.monto)}</td>
                        <td>
                          <button
                            className="btn-eliminar"
                            onClick={() => handleEliminarGasto(gasto.id)}
                          >
                            🗑️
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">📊</div>
              <div className="empty-state-text">
                No hay presupuestos registrados para este proyecto
              </div>
            </div>
          )}
        </>
      )}

      {/* MODAL: NUEVO PROYECTO */}
      {mostrarModalProyecto && (
        <div className="modal-overlay" onClick={() => setMostrarModalProyecto(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Crear Nuevo Proyecto</h3>
              <button className="modal-close" onClick={() => setMostrarModalProyecto(false)}>×</button>
            </div>
            
            <form onSubmit={handleCrearProyecto}>
              <div className="modal-body">
                <div className="form-field">
                  <label htmlFor="nombre-proyecto">Nombre del Proyecto *</label>
                  <input
                    type="text"
                    id="nombre-proyecto"
                    value={nuevoProyecto.nombre}
                    onChange={(e) => setNuevoProyecto({...nuevoProyecto, nombre: e.target.value.toUpperCase()})}
                    placeholder="Ej: EDIFICIO CENTRAL"
                    maxLength="100"
                    required
                    autoFocus
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="venta-proyecto">Valor de Venta</label>
                  <input
                    type="number"
                    id="venta-proyecto"
                    value={nuevoProyecto.venta}
                    onChange={(e) => setNuevoProyecto({...nuevoProyecto, venta: e.target.value})}
                    placeholder="0"
                    min="0"
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="observacion-proyecto">Observación</label>
                  <textarea
                    id="observacion-proyecto"
                    value={nuevoProyecto.observacion}
                    onChange={(e) => setNuevoProyecto({...nuevoProyecto, observacion: e.target.value})}
                    placeholder="Notas adicionales..."
                    rows="3"
                    maxLength="500"
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button 
                  type="button" 
                  className="btn-presupuesto btn-secondary"
                  onClick={() => setMostrarModalProyecto(false)}
                >
                  Cancelar
                </button>
                <button 
                  type="submit" 
                  className="btn-presupuesto btn-primary"
                  disabled={loading}
                >
                  {loading ? 'Creando...' : '✓ Crear Proyecto'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Presupuestos;