import { useState, useEffect } from 'react';
import './Presupuestos.css';

function Presupuestos() {
  const [proyectos, setProyectos] = useState([]);
  const [items, setItems] = useState([]);
  const [proyectoSeleccionado, setProyectoSeleccionado] = useState('');
  const [proyectoId, setProyectoId] = useState(null);
  const [gastos, setGastos] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  
  const [formData, setFormData] = useState({
    item: '',
    detalle: '',
    fecha: new Date().toISOString().split('T')[0],
    monto: ''
  });

  // Cargar proyectos e items al iniciar
  useEffect(() => {
    cargarDatosIniciales();
  }, []);

  const cargarDatosIniciales = async () => {
    const token = localStorage.getItem('authToken');
    
    try {
      // Cargar proyectos
      const resProyectos = await fetch('/api/proyectos/api/activos', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const dataProyectos = await resProyectos.json();
      console.log('Proyectos cargados:', dataProyectos);
      setProyectos(dataProyectos.data || []);

      // Cargar items
      const resItems = await fetch('/api/items/todos', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const dataItems = await resItems.json();
      console.log('Items cargados:', dataItems);
      setItems(dataItems.data || []);
    } catch (error) {
      console.error('Error al cargar datos:', error);
      alert('Error al cargar datos iniciales. Revisa la consola.');
    }
  };

  // Cuando se selecciona un proyecto
  const handleProyectoChange = async (e) => {
    const nombreProyecto = e.target.value;
    setProyectoSeleccionado(nombreProyecto);
    
    if (!nombreProyecto) {
      setMostrarFormulario(false);
      setGastos([]);
      setStats(null);
      return;
    }

    // Buscar el ID del proyecto
    const proyecto = proyectos.find(p => p.proyecto === nombreProyecto);
    if (proyecto) {
      setProyectoId(proyecto.id);
      setMostrarFormulario(true);
      await cargarGastosProyecto(proyecto.id);
    }
  };

  // Cargar gastos del proyecto
  const cargarGastosProyecto = async (id) => {
    setLoading(true);
    const token = localStorage.getItem('authToken');
    
    try {
      const response = await fetch(`/api/presupuestos/gastos/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      
      if (data.success) {
        setGastos(data.gastos || []);
        setStats(data.stats || null);
      }
    } catch (error) {
      console.error('Error al cargar gastos:', error);
    } finally {
      setLoading(false);
    }
  };

  // Manejar cambios en el formulario
  const handleFormChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  // Enviar nuevo presupuesto
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!proyectoId || !formData.item || !formData.monto) {
      alert('Por favor complete todos los campos requeridos');
      return;
    }

    const token = localStorage.getItem('authToken');
    
    try {
      const response = await fetch('/api/presupuestos', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          proyecto_id: proyectoId,
          item: formData.item,
          detalle: formData.detalle,
          fecha: formData.fecha,
          monto: parseFloat(formData.monto)
        })
      });

      const data = await response.json();
      
      if (data.success) {
        alert('Presupuesto registrado exitosamente');
        // Limpiar formulario
        setFormData({
          item: '',
          detalle: '',
          fecha: new Date().toISOString().split('T')[0],
          monto: ''
        });
        // Recargar gastos
        await cargarGastosProyecto(proyectoId);
      } else {
        alert(data.message || 'Error al registrar presupuesto');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Error al registrar presupuesto');
    }
  };

  // Eliminar gasto
  const handleEliminar = async (gastoId) => {
    if (!confirm('¿Está seguro de eliminar este registro?')) return;

    const token = localStorage.getItem('authToken');
    
    try {
      const response = await fetch(`/api/presupuestos/${gastoId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const data = await response.json();
      
      if (data.success) {
        alert('Registro eliminado exitosamente');
        await cargarGastosProyecto(proyectoId);
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

  return (
    <div className="presupuestos-container">
      {/* Header */}
      <div className="presupuestos-header">
        <h1>
          <span className="icon-presupuesto">💰</span>
          Presupuestos
        </h1>
      </div>

      {/* Selector de Proyecto */}
      <div className="selector-proyecto">
        <label htmlFor="proyecto">Seleccione un Proyecto</label>
        <select
          id="proyecto"
          value={proyectoSeleccionado}
          onChange={handleProyectoChange}
        >
          <option value="">-- Seleccione un proyecto --</option>
          {proyectos.length === 0 && (
            <option disabled>No hay proyectos disponibles</option>
          )}
          {proyectos.map((p) => (
            <option key={p.id} value={p.proyecto}>
              {p.proyecto}
            </option>
          ))}
        </select>
        {proyectos.length === 0 && (
          <p style={{color: '#ef4444', fontSize: '0.875rem', marginTop: '0.5rem'}}>
            ⚠️ No se encontraron proyectos. Crea proyectos en la sección de Configuración.
          </p>
        )}
      </div>

      {/* Formulario de Ingreso */}
      <div className={`form-presupuesto ${mostrarFormulario ? 'visible' : ''}`}>
        <h3>Ingresar Nuevo Presupuesto</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-field">
              <label htmlFor="item">Ítem *</label>
              <select
                id="item"
                name="item"
                value={formData.item}
                onChange={handleFormChange}
                required
              >
                <option value="">-- Seleccione --</option>
                {items.length === 0 && (
                  <option disabled>No hay items disponibles</option>
                )}
                {items.map((item) => (
                  <option key={item.id} value={item.tipo}>
                    {item.tipo}
                  </option>
                ))}
              </select>
              {items.length === 0 && (
                <p style={{color: '#ef4444', fontSize: '0.75rem', marginTop: '0.25rem'}}>
                  ⚠️ No hay ítems presupuestarios. Créalos en Configuración.
                </p>
              )}
            </div>

            <div className="form-field">
              <label htmlFor="monto">Monto *</label>
              <input
                type="number"
                id="monto"
                name="monto"
                value={formData.monto}
                onChange={handleFormChange}
                placeholder="0"
                min="0"
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="fecha">Fecha *</label>
              <input
                type="date"
                id="fecha"
                name="fecha"
                value={formData.fecha}
                onChange={handleFormChange}
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="detalle">Detalle</label>
              <input
                type="text"
                id="detalle"
                name="detalle"
                value={formData.detalle}
                onChange={handleFormChange}
                placeholder="Descripción opcional"
                maxLength="200"
              />
            </div>
          </div>

          <div className="btn-group">
            <button type="button" className="btn-presupuesto btn-secondary" onClick={() => {
              setFormData({
                item: '',
                detalle: '',
                fecha: new Date().toISOString().split('T')[0],
                monto: ''
              });
            }}>
              🔄 Limpiar
            </button>
            <button type="submit" className="btn-presupuesto btn-primary">
              ✓ Registrar
            </button>
          </div>
        </form>
      </div>

      {/* Estadísticas */}
      {stats && (
        <div className={`stats-presupuesto ${stats ? 'visible' : ''}`}>
          <div className="stat-card total">
            <div className="stat-label">Monto Total</div>
            <div className="stat-value">{formatMonto(stats.total_amount)}</div>
          </div>
          <div className="stat-card registros">
            <div className="stat-label">Registros</div>
            <div className="stat-value">{stats.total_entries}</div>
          </div>
          <div className="stat-card items">
            <div className="stat-label">Ítems Únicos</div>
            <div className="stat-value">{stats.unique_items}</div>
          </div>
          <div className="stat-card fecha">
            <div className="stat-label">Último Registro</div>
            <div className="stat-value" style={{fontSize: '1rem'}}>
              {stats.last_entry || 'N/A'}
            </div>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="loading visible">
          <div className="spinner"></div>
          Cargando datos...
        </div>
      )}

      {/* Tabla de Gastos */}
      {!loading && gastos.length > 0 && (
        <div className="tabla-gastos visible">
          <h3>Historial de Presupuestos - {proyectoSeleccionado}</h3>
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
                {gastos.map((gasto) => (
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
                        onClick={() => handleEliminar(gasto.id)}
                      >
                        🗑️ Eliminar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Estado vacío */}
      {!loading && mostrarFormulario && gastos.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">📊</div>
          <div className="empty-state-text">
            No hay presupuestos registrados para este proyecto
          </div>
        </div>
      )}
    </div>
  );
}

export default Presupuestos;
