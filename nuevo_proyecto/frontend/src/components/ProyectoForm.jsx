import React, { useEffect, useState } from 'react';
import './Proyectos.css';

const ProyectoForm = ({ proyecto, onClose, onSaved }) => {
  const [form, setForm] = useState({
    proyecto: '',
    venta: '',
    observacion: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState('success');

  useEffect(() => {
    if (proyecto && proyecto.id) {
      setForm({
        proyecto: proyecto.proyecto || '',
        venta: proyecto.venta || '',
        observacion: proyecto.observacion || ''
      });
    }
  }, [proyecto]);

  const token = localStorage.getItem('authToken');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ 
      ...prev, 
      [name]: value 
    }));
    if (message) setMessage(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      const url = proyecto && proyecto.id 
        ? `/api/proyectos/edit/${proyecto.id}` 
        : '/api/proyectos/new';
      
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
      
      setMessage(proyecto && proyecto.id ? '✓ Actualizado correctamente' : '✓ Creado correctamente');
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
            {proyecto && proyecto.id ? '✏️ Editar Proyecto' : '➕ Nuevo Proyecto'}
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

            {/* Información del Proyecto */}
            <div className="form-section">
              <div className="form-section-title">📝 Información del Proyecto</div>
              
              <div className="form-row">
                <label className="form-label">
                  Nombre del Proyecto <span className="required">*</span>
                </label>
                <input 
                  className="form-input uppercase"
                  name="proyecto" 
                  value={form.proyecto} 
                  onChange={handleChange} 
                  required 
                  maxLength={100}
                  placeholder="Ingrese el nombre del proyecto" 
                />
              </div>

              <div className="form-row">
                <label className="form-label">
                  Valor de Venta
                </label>
                <input 
                  className="form-input uppercase"
                  name="venta" 
                  value={form.venta} 
                  onChange={handleChange} 
                  maxLength={50}
                  placeholder="Ej: $50.000.000" 
                />
              </div>

              <div className="form-row">
                <label className="form-label">
                  Observación
                </label>
                <textarea 
                  className="form-textarea uppercase"
                  name="observacion" 
                  value={form.observacion} 
                  onChange={handleChange} 
                  maxLength={200}
                  placeholder="Notas adicionales sobre el proyecto"
                  rows={4}
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
              {loading ? '⏳ Guardando...' : (proyecto && proyecto.id ? '💾 Guardar Cambios' : '➕ Crear Proyecto')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProyectoForm;
