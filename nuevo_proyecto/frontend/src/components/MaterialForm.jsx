import React, { useEffect, useState } from 'react';
import './Materiales.css';
import { getAuthToken } from '../utils/auth';

const MaterialForm = ({ material, items, onClose, onSaved }) => {
  const [form, setForm] = useState({
    cod: '',
    material: '',
    tipo: '',
    item: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState('success');

  useEffect(() => {
    if (material && material.id) {
      setForm({
        cod: material.cod || '',
        material: material.material || '',
        tipo: material.tipo || '',
        item: material.item || ''
      });
    }
  }, [material]);

  const token = getAuthToken();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ 
      ...prev, 
      [name]: value.toUpperCase() 
    }));
    if (message) setMessage(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      const url = material && material.id 
        ? `/api/materiales/edit/${material.id}` 
        : '/api/materiales/new';
      
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify(form)
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.message || 'Error en servidor');
      }
      
      setMessage(material && material.id ? '✓ Actualizado correctamente' : '✓ Creado correctamente');
      setMessageType('success');
      
      setTimeout(() => {
        if (onSaved) onSaved(data.data || data);
      }, 800);
      
    } catch (err) {
      console.error(err);
      setMessage(err.message || 'Error al guardar');
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal-content">
        <div className="modal-header">
          <h3>
            {material && material.id ? '✏️ Editar Material' : '➕ Nuevo Material'}
          </h3>
          <button className="btn-close" onClick={onClose} type="button">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {message && (
              <div className={`form-message ${messageType}`}>
                {messageType === 'success' ? '✓' : '⚠️'} {message}
              </div>
            )}

            {/* Información del Material */}
            <div className="form-section">
              <div className="form-section-title">📦 Información del Material</div>
              
              <div className="form-grid-2">
                <div className="form-row">
                  <label className="form-label">
                    Código <span className="required">*</span>
                  </label>
                  <input 
                    className="form-input uppercase"
                    name="cod" 
                    value={form.cod} 
                    onChange={handleChange} 
                    required 
                    maxLength={50}
                    placeholder="Código único del material" 
                  />
                </div>

                <div className="form-row">
                  <label className="form-label">
                    Item <span className="required">*</span>
                  </label>
                  <select 
                    className="form-select"
                    name="item" 
                    value={form.item} 
                    onChange={handleChange} 
                    required
                  >
                    <option value="">Seleccione item...</option>
                    {items.map((it, idx) => (
                      <option key={idx} value={it.tipo}>
                        {it.tipo}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-row">
                <label className="form-label">
                  Nombre del Material <span className="required">*</span>
                </label>
                <input 
                  className="form-input uppercase"
                  name="material" 
                  value={form.material} 
                  onChange={handleChange} 
                  required 
                  maxLength={200}
                  placeholder="Descripción completa del material" 
                />
              </div>

              <div className="form-row">
                <label className="form-label">
                  Tipo
                </label>
                <input 
                  className="form-input uppercase"
                  name="tipo" 
                  value={form.tipo} 
                  onChange={handleChange} 
                  maxLength={100}
                  placeholder="Clasificación específica (opcional)" 
                />
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button 
              type="button" 
              className="btn-cancel" 
              onClick={onClose}
              disabled={loading}
            >
              Cancelar
            </button>
            <button 
              type="submit" 
              className="btn-submit"
              disabled={loading}
            >
              {loading ? '⏳ Guardando...' : (material && material.id ? '💾 Guardar Cambios' : '➕ Crear Material')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default MaterialForm;
