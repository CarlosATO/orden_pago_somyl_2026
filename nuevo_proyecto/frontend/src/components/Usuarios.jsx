import React, { useState, useEffect } from 'react';
import './Usuarios.css';
import { getAuthToken } from '../utils/auth';

const Usuarios = () => {
  const [usuarios, setUsuarios] = useState([]);
  const [modulos, setModulos] = useState([]);
  const [filteredUsuarios, setFilteredUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mensaje, setMensaje] = useState({ tipo: '', texto: '' });
  const [stats, setStats] = useState({ total: 0, activos: 0, inactivos: 0, bloqueados: 0 });
  
  // Estado del formulario
  const [formData, setFormData] = useState({
    nombre: '',
    email: '',
    password: '',
    confirmPassword: '',
    activo: true,
    modulosSeleccionados: [],
    id: null
  });
  
  const [formErrors, setFormErrors] = useState({
    nombre: '',
    email: '',
    password: '',
    confirmPassword: '',
    modulos: ''
  });
  
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('todos');
  const [isEditing, setIsEditing] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showFormModal, setShowFormModal] = useState(false);
  const [passwordTemporal, setPasswordTemporal] = useState(null);
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState(null);

  // Cargar usuarios y módulos al montar
  useEffect(() => {
    cargarUsuarios();
    cargarModulos();
  }, []);

  // Filtrar cuando cambie el término de búsqueda o el filtro
  useEffect(() => {
    filtrarUsuarios();
  }, [searchTerm, filtroEstado, usuarios]);

  const cargarUsuarios = async () => {
    setLoading(true);
    try {
      const token = getAuthToken();
      const response = await fetch('/api/usuarios/todos', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setUsuarios(data.data || []);
        setStats(data.stats || { total: 0, activos: 0, inactivos: 0, bloqueados: 0 });
      } else {
        mostrarMensaje('error', 'Error al cargar usuarios');
      }
    } catch (error) {
      console.error('Error:', error);
      mostrarMensaje('error', 'Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const cargarModulos = async () => {
    try {
      const token = getAuthToken();
      const response = await fetch('/api/usuarios/modulos', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setModulos(data.data || []);
      } else {
        console.error('Error cargando módulos');
      }
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const filtrarUsuarios = () => {
    let filtered = usuarios;

    // Filtrar por estado
    if (filtroEstado === 'activos') {
      filtered = filtered.filter(u => u.activo === true);
    } else if (filtroEstado === 'inactivos') {
      filtered = filtered.filter(u => u.activo === false);
    } else if (filtroEstado === 'bloqueados') {
      filtered = filtered.filter(u => u.bloqueado === true);
    }

    // Filtrar por búsqueda
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(usuario =>
        String(usuario.nombre || '').toLowerCase().includes(term) ||
        String(usuario.email || '').toLowerCase().includes(term)
      );
    }

    setFilteredUsuarios(filtered);
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
    }

    // Validar email
    if (!formData.email.trim()) {
      errors.email = 'El email es obligatorio';
      isValid = false;
    } else if (!validarEmail(formData.email)) {
      errors.email = 'El formato del email no es válido';
      isValid = false;
    }

    // Validar password (solo al crear)
    if (!isEditing) {
      if (!formData.password) {
        errors.password = 'La contraseña es obligatoria';
        isValid = false;
      } else if (formData.password.length < 8) {
        errors.password = 'La contraseña debe tener al menos 8 caracteres';
        isValid = false;
      }

      if (formData.password !== formData.confirmPassword) {
        errors.confirmPassword = 'Las contraseñas no coinciden';
        isValid = false;
      }

      // Validar módulos
      if (formData.modulosSeleccionados.length === 0) {
        errors.modulos = 'Debe seleccionar al menos un módulo';
        isValid = false;
      }
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
        ? `/api/usuarios/edit/${formData.id}`
        : '/api/usuarios/new';

      const body = isEditing ? {
        nombre: formData.nombre,
        email: formData.email.toLowerCase()
      } : {
        nombre: formData.nombre,
        email: formData.email.toLowerCase(),
        password: formData.password,
        activo: formData.activo,
        modulos: formData.modulosSeleccionados
      };

      const response = await fetch(url, {
        method: isEditing ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(body)
      });

      const data = await response.json();

      if (data.success) {
        mostrarMensaje('success', data.message || 
          (isEditing ? 'Usuario actualizado exitosamente' : 'Usuario creado exitosamente'));
        limpiarFormulario();
        cargarUsuarios();
      } else {
        mostrarMensaje('error', data.message || 'Error al guardar usuario');
      }
    } catch (error) {
      console.error('Error:', error);
      mostrarMensaje('error', 'Error de conexión');
    }
  };

  const handleEdit = (usuario) => {
    setFormData({
      nombre: usuario.nombre,
      email: usuario.email,
      password: '',
      confirmPassword: '',
      activo: usuario.activo,
      modulosSeleccionados: [],
      id: usuario.id
    });
    setFormErrors({});
    setIsEditing(true);
    setShowFormModal(true);
  };

  const handleToggleEstado = async (usuario) => {
    try {
      const token = getAuthToken();
      const response = await fetch(`/api/usuarios/toggle-estado/${usuario.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          activo: !usuario.activo
        })
      });

      const data = await response.json();

      if (data.success) {
        mostrarMensaje('success', data.message);
        cargarUsuarios();
      } else {
        mostrarMensaje('error', data.message || 'Error al cambiar estado');
      }
    } catch (error) {
      console.error('Error:', error);
      mostrarMensaje('error', 'Error de conexión');
    }
  };

  const handleToggleBloqueo = async (usuario) => {
    try {
      const token = getAuthToken();
      const response = await fetch(`/api/usuarios/toggle-bloqueo/${usuario.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          bloqueado: !usuario.bloqueado
        })
      });

      const data = await response.json();

      if (data.success) {
        mostrarMensaje('success', data.message);
        cargarUsuarios();
      } else {
        mostrarMensaje('error', data.message || 'Error al cambiar bloqueo');
      }
    } catch (error) {
      console.error('Error:', error);
      mostrarMensaje('error', 'Error de conexión');
    }
  };

  const handleResetPassword = async (usuario) => {
    if (!confirm(`¿Está seguro de resetear la contraseña de ${usuario.nombre}?`)) {
      return;
    }

    try {
      const token = getAuthToken();
      const response = await fetch(`/api/usuarios/reset-password/${usuario.id}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();

      if (data.success) {
        setPasswordTemporal(data.password_temporal);
        setUsuarioSeleccionado(data);
        setShowPasswordModal(true);
        cargarUsuarios();
      } else {
        mostrarMensaje('error', data.message || 'Error al resetear contraseña');
      }
    } catch (error) {
      console.error('Error:', error);
      mostrarMensaje('error', 'Error de conexión');
    }
  };

  const handleToggleModulo = (moduloId) => {
    const modulosActuales = [...formData.modulosSeleccionados];
    const index = modulosActuales.indexOf(moduloId);
    
    if (index > -1) {
      modulosActuales.splice(index, 1);
    } else {
      modulosActuales.push(moduloId);
    }
    
    setFormData({ ...formData, modulosSeleccionados: modulosActuales });
    setFormErrors({ ...formErrors, modulos: '' });
  };

  const limpiarFormulario = () => {
    setFormData({
      nombre: '',
      email: '',
      password: '',
      confirmPassword: '',
      activo: true,
      modulosSeleccionados: [],
      id: null
    });
    setFormErrors({});
    setIsEditing(false);
    setShowFormModal(false);
  };

  const mostrarMensaje = (tipo, texto) => {
    setMensaje({ tipo, texto });
    setTimeout(() => setMensaje({ tipo: '', texto: '' }), 5000);
  };

  const copiarPassword = () => {
    navigator.clipboard.writeText(passwordTemporal);
    mostrarMensaje('success', 'Contraseña copiada al portapapeles');
  };

  const abrirModalNuevoUsuario = () => {
    limpiarFormulario();
    setIsEditing(false);
    setShowFormModal(true);
  };

  return (
    <div className="usuarios-container">
      {/* Header */}
      <div className="usuarios-header">
        <h1>
          <i className="bi bi-people-fill icon-usuario"></i>
          Gestión de Usuarios
        </h1>
      </div>

      {/* Estadísticas */}
      <div className="stats-container">
        <div className="stat-card stat-total">
          <div className="stat-number">{stats.total}</div>
          <div className="stat-label">Total Usuarios</div>
        </div>
        <div className="stat-card stat-activos">
          <div className="stat-number">{stats.activos}</div>
          <div className="stat-label">Activos</div>
        </div>
        <div className="stat-card stat-inactivos">
          <div className="stat-number">{stats.inactivos}</div>
          <div className="stat-label">Inactivos</div>
        </div>
        <div className="stat-card stat-bloqueados">
          <div className="stat-number">{stats.bloqueados}</div>
          <div className="stat-label">Bloqueados</div>
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

      {/* Barra de Acciones */}
      <div className="actions-bar">
        <button className="btn-nuevo-usuario" onClick={abrirModalNuevoUsuario}>
          <i className="bi bi-person-plus-fill"></i>
          Nuevo Usuario
        </button>
        
        <div className="filters-group">
          <div className="filter-select-wrapper">
            <i className="bi bi-funnel-fill"></i>
            <select 
              className="filter-select"
              value={filtroEstado}
              onChange={(e) => setFiltroEstado(e.target.value)}
            >
              <option value="todos">Todos los usuarios</option>
              <option value="activos">Activos</option>
              <option value="inactivos">Inactivos</option>
              <option value="bloqueados">Bloqueados</option>
            </select>
          </div>
          
          <div className="search-input-wrapper">
            <i className="bi bi-search search-icon"></i>
            <input
              type="text"
              placeholder="Buscar por nombre o email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Tabla */}
      <div className="table-section">
        <div className="table-header">
          <h2>
            <i className="bi bi-list-ul"></i>
            Usuarios Registrados
            {filteredUsuarios.length > 0 && (
              <span className="table-count">{filteredUsuarios.length}</span>
            )}
          </h2>
          {loading && <span className="loading">Cargando...</span>}
        </div>
        <div className="table-wrapper">
          {filteredUsuarios.length > 0 ? (
            <table className="usuarios-table">
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Email</th>
                  <th>Módulos</th>
                  <th>Estado</th>
                  <th className="actions-cell">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsuarios.map((usuario) => (
                  <tr key={usuario.id}>
                    <td>
                      <div className="usuario-nombre">
                        <i className="bi bi-person-circle"></i>
                        <span>{usuario.nombre}</span>
                      </div>
                    </td>
                    <td>
                      <div className="usuario-email">
                        <i className="bi bi-envelope"></i>
                        <a href={`mailto:${usuario.email}`}>{usuario.email}</a>
                      </div>
                    </td>
                    <td>
                      <div className="modulos-list-minimal">
                        {usuario.modulos && usuario.modulos.length > 0 ? (
                          <>
                            <span className="modulos-count">{usuario.modulos.length}</span>
                            <span className="modulos-tooltip">
                              {usuario.modulos.join(', ')}
                            </span>
                          </>
                        ) : (
                          <span className="sin-modulos-minimal">0</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <div className="estado-badges">
                        {usuario.bloqueado ? (
                          <span className="badge badge-bloqueado">
                            <i className="bi bi-shield-lock"></i> Bloqueado
                          </span>
                        ) : usuario.activo ? (
                          <span className="badge badge-activo">
                            <i className="bi bi-check-circle"></i> Activo
                          </span>
                        ) : (
                          <span className="badge badge-inactivo">
                            <i className="bi bi-x-circle"></i> Inactivo
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="actions-cell">
                      <div className="action-buttons-minimal">
                        <button
                          className="action-btn action-edit"
                          onClick={() => handleEdit(usuario)}
                          title="Editar usuario"
                        >
                          <i className="bi bi-pencil-fill"></i>
                          <span>Editar</span>
                        </button>
                        <button
                          className={`action-btn ${usuario.activo ? 'action-pause' : 'action-play'}`}
                          onClick={() => handleToggleEstado(usuario)}
                          title={usuario.activo ? 'Desactivar usuario' : 'Activar usuario'}
                        >
                          <i className={`bi bi-${usuario.activo ? 'pause-fill' : 'play-fill'}`}></i>
                          <span>{usuario.activo ? 'Pausar' : 'Activar'}</span>
                        </button>
                        <button
                          className={`action-btn ${usuario.bloqueado ? 'action-unlock' : 'action-lock'}`}
                          onClick={() => handleToggleBloqueo(usuario)}
                          title={usuario.bloqueado ? 'Desbloquear usuario' : 'Bloquear usuario'}
                        >
                          <i className={`bi bi-${usuario.bloqueado ? 'unlock-fill' : 'lock-fill'}`}></i>
                          <span>{usuario.bloqueado ? 'Desbloquear' : 'Bloquear'}</span>
                        </button>
                        <button
                          className="action-btn action-key"
                          onClick={() => handleResetPassword(usuario)}
                          title="Resetear contraseña"
                        >
                          <i className="bi bi-key-fill"></i>
                          <span>Reset</span>
                        </button>
                      </div>
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
              <p>No se encontraron usuarios</p>
            </div>
          )}
        </div>
      </div>

      {/* Modal de Formulario (Crear/Editar) */}
      {showFormModal && (
        <div className="modal-overlay" onClick={() => setShowFormModal(false)}>
          <div className="modal-content modal-form" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>
                <i className={`bi bi-${isEditing ? 'pencil-square' : 'person-plus-fill'}`}></i>
                {isEditing ? 'Editar Usuario' : 'Nuevo Usuario'}
              </h3>
              <button className="btn-close" onClick={() => setShowFormModal(false)}>
                <i className="bi bi-x-lg"></i>
              </button>
            </div>
            <div className="modal-body">
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
                        setFormData({ ...formData, nombre: e.target.value });
                        setFormErrors({ ...formErrors, nombre: '' });
                      }}
                      placeholder="Ej: Juan Pérez"
                    />
                    {formErrors.nombre && (
                      <span className="error-message">{formErrors.nombre}</span>
                    )}
                  </div>
                  <div className="form-group">
                    <label htmlFor="email">Email *</label>
                    <input
                      type="email"
                      id="email"
                      className={formErrors.email ? 'invalid' : formData.email ? 'valid' : ''}
                      value={formData.email}
                      onChange={(e) => {
                        setFormData({ ...formData, email: e.target.value.toLowerCase() });
                        setFormErrors({ ...formErrors, email: '' });
                      }}
                      placeholder="usuario@empresa.com"
                    />
                    {formErrors.email && (
                      <span className="error-message">{formErrors.email}</span>
                    )}
                  </div>
                </div>

                {!isEditing && (
                  <>
                    <div className="form-grid">
                      <div className="form-group">
                        <label htmlFor="password">Contraseña *</label>
                        <input
                          type="password"
                          id="password"
                          className={formErrors.password ? 'invalid' : formData.password ? 'valid' : ''}
                          value={formData.password}
                          onChange={(e) => {
                            setFormData({ ...formData, password: e.target.value });
                            setFormErrors({ ...formErrors, password: '' });
                          }}
                          placeholder="Mínimo 8 caracteres"
                        />
                        {formErrors.password && (
                          <span className="error-message">{formErrors.password}</span>
                        )}
                      </div>
                      <div className="form-group">
                        <label htmlFor="confirmPassword">Confirmar Contraseña *</label>
                        <input
                          type="password"
                          id="confirmPassword"
                          className={formErrors.confirmPassword ? 'invalid' : formData.confirmPassword ? 'valid' : ''}
                          value={formData.confirmPassword}
                          onChange={(e) => {
                            setFormData({ ...formData, confirmPassword: e.target.value });
                            setFormErrors({ ...formErrors, confirmPassword: '' });
                          }}
                          placeholder="Repita la contraseña"
                        />
                        {formErrors.confirmPassword && (
                          <span className="error-message">{formErrors.confirmPassword}</span>
                        )}
                      </div>
                    </div>

                    <div className="form-group">
                      <label className="checkbox-label">
                        <input
                          type="checkbox"
                          checked={formData.activo}
                          onChange={(e) => setFormData({ ...formData, activo: e.target.checked })}
                        />
                        Usuario Activo
                      </label>
                    </div>

                    <div className="form-group modulos-section">
                      <label>Módulos Asignados *</label>
                      <div className="modulos-grid">
                        {modulos.map(modulo => (
                          <label key={modulo.id} className="modulo-item">
                            <input
                              type="checkbox"
                              checked={formData.modulosSeleccionados.includes(modulo.id)}
                              onChange={() => handleToggleModulo(modulo.id)}
                            />
                            <span>{modulo.nombre_modulo}</span>
                          </label>
                        ))}
                      </div>
                      {formErrors.modulos && (
                        <span className="error-message">{formErrors.modulos}</span>
                      )}
                    </div>
                  </>
                )}

                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={() => setShowFormModal(false)}>
                    <i className="bi bi-x-lg"></i>
                    Cancelar
                  </button>
                  <button type="submit" className={`btn ${isEditing ? 'btn-success' : 'btn-primary'}`}>
                    <i className={`bi bi-${isEditing ? 'check-lg' : 'plus-lg'}`}></i>
                    {isEditing ? 'Actualizar' : 'Crear'} Usuario
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Contraseña Temporal */}
      {showPasswordModal && (
        <div className="modal-overlay" onClick={() => setShowPasswordModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>
                <i className="bi bi-key-fill"></i>
                Contraseña Temporal Generada
              </h3>
              <button className="btn-close" onClick={() => setShowPasswordModal(false)}>
                <i className="bi bi-x-lg"></i>
              </button>
            </div>
            <div className="modal-body">
              <div className="password-info">
                <p><strong>Usuario:</strong> {usuarioSeleccionado?.usuario}</p>
                <p><strong>Email:</strong> {usuarioSeleccionado?.email}</p>
              </div>
              <div className="password-display">
                <label>Contraseña Temporal:</label>
                <div className="password-value">
                  <code>{passwordTemporal}</code>
                  <button className="btn btn-sm btn-copy" onClick={copiarPassword}>
                    <i className="bi bi-clipboard"></i> Copiar
                  </button>
                </div>
              </div>
              <div className="password-note">
                <i className="bi bi-exclamation-triangle"></i>
                <p>Esta contraseña solo se mostrará una vez. El usuario deberá cambiarla en su próximo inicio de sesión.</p>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={() => setShowPasswordModal(false)}>
                Entendido
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Usuarios;
