import React, { useState, useEffect } from 'react';
import './Items.css';
import { getAuthToken } from '../utils/auth';

const Items = () => {
  const [items, setItems] = useState([]);
  const [filteredItems, setFilteredItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mensaje, setMensaje] = useState({ tipo: '', texto: '' });
  
  // Estado del formulario
  const [formData, setFormData] = useState({
    tipo: '',
    id: null
  });
  
  const [searchTerm, setSearchTerm] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  // Cargar items al montar
  useEffect(() => {
    cargarItems();
  }, []);

  // Filtrar cuando cambie el término de búsqueda
  useEffect(() => {
    filtrarItems();
  }, [searchTerm, items]);

  const cargarItems = async () => {
    setLoading(true);
    try {
  const token = getAuthToken();
      const response = await fetch('/api/items/todos', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setItems(data.data || []);
        setFilteredItems(data.data || []);
      } else {
        mostrarMensaje('error', 'Error al cargar items');
      }
    } catch (error) {
      console.error('Error:', error);
      mostrarMensaje('error', 'Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const filtrarItems = () => {
    if (!searchTerm.trim()) {
      setFilteredItems(items);
      return;
    }

    const term = searchTerm.toLowerCase();
    const filtered = items.filter(item =>
      String(item.tipo || '').toLowerCase().includes(term)
    );
    setFilteredItems(filtered);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.tipo.trim()) {
      mostrarMensaje('error', 'Debe ingresar un nombre de item');
      return;
    }

    try {
  const token = getAuthToken();
      const url = isEditing 
        ? `/api/items/edit/${formData.id}`
        : '/api/items/new';

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          tipo: formData.tipo.toUpperCase()
        })
      });

      const data = await response.json();

      if (data.success) {
        mostrarMensaje('success', data.message || 
          (isEditing ? 'Item actualizado exitosamente' : 'Item creado exitosamente'));
        limpiarFormulario();
        cargarItems();
      } else {
        mostrarMensaje('error', data.message || 'Error al guardar item');
      }
    } catch (error) {
      console.error('Error:', error);
      mostrarMensaje('error', 'Error de conexión');
    }
  };

  const handleEdit = (item) => {
    setFormData({
      tipo: item.tipo,
      id: item.id
    });
    setIsEditing(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const limpiarFormulario = () => {
    setFormData({ tipo: '', id: null });
    setIsEditing(false);
  };

  const mostrarMensaje = (tipo, texto) => {
    setMensaje({ tipo, texto });
    setTimeout(() => setMensaje({ tipo: '', texto: '' }), 4000);
  };

  return (
    <div className="items-container">
      {/* Header */}
      <div className="items-header">
        <h1>
          <i className="bi bi-tag icon-item"></i>
          Gestión de Items
        </h1>
      </div>

      {/* Estadísticas */}
      <div className="stats-container">
        <div className="stat-card">
          <div className="stat-number">{items.length}</div>
          <div className="stat-label">Total Items</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{filteredItems.length}</div>
          <div className="stat-label">Resultados</div>
        </div>
      </div>

      {/* Mensajes */}
      {mensaje.texto && (
        <div className={`mensaje mensaje-${mensaje.tipo}`}>
          <i className={`bi bi-${mensaje.tipo === 'success' ? 'check-circle' : 'exclamation-triangle'}`}></i>
          {mensaje.texto}
        </div>
      )}

      {/* Búsqueda */}
      <div className="search-section">
        <div className="search-input-wrapper">
          <i className="bi bi-search search-icon"></i>
          <input
            type="text"
            placeholder="Buscar por nombre..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* Formulario */}
      <div className="form-section">
        <h2>
          <i className={`bi bi-${isEditing ? 'pencil-square' : 'plus-circle'}`}></i>
          {isEditing ? 'Editar Item' : 'Nuevo Item'}
        </h2>
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="tipo">Nombre del Item *</label>
              <input
                type="text"
                id="tipo"
                value={formData.tipo}
                onChange={(e) => setFormData({ ...formData, tipo: e.target.value.toUpperCase() })}
                placeholder="Ej: MATERIALES, SERVICIOS, etc."
                required
              />
            </div>
            <div className="btn-group">
              <button type="submit" className={`btn ${isEditing ? 'btn-success' : 'btn-primary'}`}>
                <i className={`bi bi-${isEditing ? 'check-lg' : 'plus-lg'}`}></i>
                {isEditing ? 'Actualizar' : 'Crear'}
              </button>
              {isEditing && (
                <button type="button" className="btn btn-secondary" onClick={limpiarFormulario}>
                  <i className="bi bi-x-lg"></i>
                  Cancelar
                </button>
              )}
            </div>
          </div>
        </form>
      </div>

      {/* Tabla */}
      <div className="table-section">
        <div className="table-header">
          <h2>
            <i className="bi bi-list-ul"></i>
            Items Registrados
            {filteredItems.length > 0 && (
              <span className="table-count">{filteredItems.length}</span>
            )}
          </h2>
          {loading && <span className="loading">Cargando...</span>}
        </div>
        <div className="table-wrapper">
          {filteredItems.length > 0 ? (
            <table className="items-table">
              <thead>
                <tr>
                  <th>Nombre del Item</th>
                  <th className="actions-cell">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.tipo}</strong>
                    </td>
                    <td className="actions-cell">
                      <button
                        className="btn btn-warning"
                        onClick={() => handleEdit(item)}
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
              <p>No se encontraron items</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Items;