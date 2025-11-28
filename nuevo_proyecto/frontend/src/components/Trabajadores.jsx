import React, { useState, useEffect } from 'react';
import './Trabajadores.css';
import { getAuthToken } from '../utils/auth';

const Trabajadores = () => {
  const [trabajadores, setTrabajadores] = useState([]);
  const [filteredTrabajadores, setFilteredTrabajadores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mensaje, setMensaje] = useState({ tipo: '', texto: '' });
  
  // Estado del formulario
  const [formData, setFormData] = useState({
    nombre: '',
    correo: '',
    id: null
  });
  
  const [formErrors, setFormErrors] = useState({
    nombre: '',
    correo: ''
  });
  
  const [searchTerm, setSearchTerm] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  // Cargar trabajadores al montar
  useEffect(() => {
    cargarTrabajadores();
  }, []);

  // Filtrar cuando cambie el término de búsqueda
  useEffect(() => {
    filtrarTrabajadores();
  }, [searchTerm, trabajadores]);

  const cargarTrabajadores = async () => {
    setLoading(true);
    try {
      const token = getAuthToken();
      const response = await fetch('/api/trabajadores/todos', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setTrabajadores(data.data || []);
        setFilteredTrabajadores(data.data || []);
      } else {
        mostrarMensaje('error', 'Error al cargar trabajadores');
      }
    } catch (error) {
      console.error('Error:', error);
      mostrarMensaje('error', 'Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const filtrarTrabajadores = () => {
    if (!searchTerm.trim()) {
      setFilteredTrabajadores(trabajadores);
      return;
    }

    const term = searchTerm.toLowerCase();
    const filtered = trabajadores.filter(trabajador =>
      String(trabajador.nombre || '').toLowerCase().includes(term) ||
      String(trabajador.correo || '').toLowerCase().includes(term)
    );
    setFilteredTrabajadores(filtered);
  };

  const validarEmail = (email) => {
    const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return pattern.test(email);
  };

  const validarFormulario = () => {
    const errors = {};
    let isValid = true;

    // Validar nombre
    if (!formData.nombre.trim()) {
      errors.nombre = 'El nombre es obligatorio';
      isValid = false;
    } else if (formData.nombre.trim().length < 2) {
      errors.nombre = 'El nombre debe tener al menos 2 caracteres';
      isValid = false;
    } else if (formData.nombre.trim().length > 100) {
      errors.nombre = 'El nombre no puede exceder 100 caracteres';
      isValid = false;
    }

    // Validar correo
    if (!formData.correo.trim()) {
      errors.correo = 'El correo es obligatorio';
      isValid = false;
    } else if (!validarEmail(formData.correo)) {
      errors.correo = 'El formato del correo no es válido';
      isValid = false;
    }

    setFormErrors(errors);
    return isValid;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validarFormulario()) {
      mostrarMensaje('error', 'Por favor corrija los errores del formulario');
      return;
    }

    try {
      const token = getAuthToken();
      const url = isEditing 
        ? `/api/trabajadores/edit/${formData.id}`
        : '/api/trabajadores/new';

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          nombre: formData.nombre.toUpperCase(),
          correo: formData.correo.toLowerCase()
        })
      });

      const data = await response.json();

      if (data.success) {
        mostrarMensaje('success', data.message || 
          (isEditing ? 'Trabajador actualizado exitosamente' : 'Trabajador creado exitosamente'));
        limpiarFormulario();
        cargarTrabajadores();
      } else {
        mostrarMensaje(data.warning ? 'warning' : 'error', data.message || 'Error al guardar trabajador');
        if (data.success === true) { // Mensaje de advertencia pero se creó
          cargarTrabajadores();
        }
      }
    } catch (error) {
      console.error('Error:', error);
      mostrarMensaje('error', 'Error de conexión');
    }
  };

  const handleEdit = (trabajador) => {
    setFormData({
      nombre: trabajador.nombre,
      correo: trabajador.correo,
      id: trabajador.id
    });
    setFormErrors({ nombre: '', correo: '' });
    setIsEditing(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const limpiarFormulario = () => {
    setFormData({ nombre: '', correo: '', id: null });
    setFormErrors({ nombre: '', correo: '' });
    setIsEditing(false);
  };

  const mostrarMensaje = (tipo, texto) => {
    setMensaje({ tipo, texto });
    setTimeout(() => setMensaje({ tipo: '', texto: '' }), 5000);
  };

  return (
    <div className="trabajadores-container">
      {/* Header */}
      <div className="trabajadores-header">
        <h1>
          <i className="bi bi-people icon-trabajador"></i>
          Gestión de Trabajadores
        </h1>
      </div>

      {/* Estadísticas */}
      <div className="stats-container">
        <div className="stat-card">
          <div className="stat-number">{trabajadores.length}</div>
          <div className="stat-label">Total Trabajadores</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{filteredTrabajadores.length}</div>
          <div className="stat-label">Resultados</div>
        </div>
      </div>

      {/* Mensajes */}
      {mensaje.texto && (
        <div className={`mensaje mensaje-${mensaje.tipo}`}>
          <i className={`bi bi-${
            mensaje.tipo === 'success' ? 'check-circle' : 
            mensaje.tipo === 'warning' ? 'exclamation-triangle' : 
            'exclamation-triangle'
          }`}></i>
          {mensaje.texto}
        </div>
      )}

      {/* Búsqueda */}
      <div className="search-section">
        <div className="search-input-wrapper">
          <i className="bi bi-search search-icon"></i>
          <input
            type="text"
            placeholder="Buscar por nombre o correo..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* Formulario */}
      <div className="form-section">
        <h2>
          <i className={`bi bi-${isEditing ? 'pencil-square' : 'person-plus'}`}></i>
          {isEditing ? 'Editar Trabajador' : 'Nuevo Trabajador'}
        </h2>
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="nombre">Nombre Completo *</label>
              <input
                type="text"
                id="nombre"
                className={formErrors.nombre ? 'invalid' : formData.nombre ? 'valid' : ''}
                value={formData.nombre}
                onChange={(e) => {
                  setFormData({ ...formData, nombre: e.target.value.toUpperCase() });
                  setFormErrors({ ...formErrors, nombre: '' });
                }}
                placeholder="Ej: JUAN PÉREZ GARCÍA"
              />
              {formErrors.nombre && (
                <span className="error-message">{formErrors.nombre}</span>
              )}
            </div>
            <div className="form-group">
              <label htmlFor="correo">Correo Electrónico *</label>
              <input
                type="email"
                id="correo"
                className={formErrors.correo ? 'invalid' : formData.correo ? 'valid' : ''}
                value={formData.correo}
                onChange={(e) => {
                  setFormData({ ...formData, correo: e.target.value.toLowerCase() });
                  setFormErrors({ ...formErrors, correo: '' });
                }}
                placeholder="ejemplo@empresa.com"
              />
              {formErrors.correo && (
                <span className="error-message">{formErrors.correo}</span>
              )}
            </div>
          </div>
          <div className="btn-group">
            <button type="submit" className={`btn ${isEditing ? 'btn-success' : 'btn-primary'}`}>
              <i className={`bi bi-${isEditing ? 'check-lg' : 'plus-lg'}`}></i>
              {isEditing ? 'Actualizar' : 'Crear'} Trabajador
            </button>
            {isEditing && (
              <button type="button" className="btn btn-secondary" onClick={limpiarFormulario}>
                <i className="bi bi-x-lg"></i>
                Cancelar
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Tabla */}
      <div className="table-section">
        <div className="table-header">
          <h2>
            <i className="bi bi-list-ul"></i>
            Trabajadores Registrados
            {filteredTrabajadores.length > 0 && (
              <span className="table-count">{filteredTrabajadores.length}</span>
            )}
          </h2>
          {loading && <span className="loading">Cargando...</span>}
        </div>
        <div className="table-wrapper">
          {filteredTrabajadores.length > 0 ? (
            <table className="trabajadores-table">
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Correo Electrónico</th>
                  <th className="actions-cell">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filteredTrabajadores.map((trabajador) => (
                  <tr key={trabajador.id}>
                    <td>
                      <span className="trabajador-nombre">{trabajador.nombre}</span>
                    </td>
                    <td>
                      <div className="trabajador-correo">
                        <i className="bi bi-envelope"></i>
                        <a href={`mailto:${trabajador.correo}`}>{trabajador.correo}</a>
                      </div>
                    </td>
                    <td className="actions-cell">
                      <button
                        className="btn btn-warning"
                        onClick={() => handleEdit(trabajador)}
                      >
                        <i className="bi bi-pencil"></i>
                        Editar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="no-results">
              <div className="no-results-icon">
                <i className="bi bi-inbox"></i>
              </div>
              <p>No se encontraron trabajadores</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Trabajadores;
