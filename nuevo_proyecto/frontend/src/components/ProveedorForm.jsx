import React, { useEffect, useState } from 'react';
import './Proveedores.css';
import { getAuthToken } from '../utils/auth';

const ProveedorForm = ({ proveedor, onClose, onSaved }) => {
  const [form, setForm] = useState({
    nombre: '',
    rut: '',
    subcontrato: 0,
    direccion: '',
    comuna: '',
    telefono: '',
    contacto: '',
    email: '',
    banco: '',
    cuenta: '',
    paguese_a: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState('success');

  useEffect(() => {
    if (proveedor && proveedor.id) {
      setForm({
        nombre: proveedor.nombre || '',
        rut: proveedor.rut || '',
        subcontrato: proveedor.subcontrato || 0,
        direccion: proveedor.direccion || '',
        comuna: proveedor.comuna || '',
        telefono: proveedor.telefono || '',
        contacto: proveedor.contacto || '',
        email: proveedor.email || '',
        banco: proveedor.banco || '',
        cuenta: proveedor.cuenta || '',
        paguese_a: proveedor.paguese_a || ''
      });
    }
  }, [proveedor]);

  const token = getAuthToken();

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm(prev => ({ 
      ...prev, 
      [name]: type === 'checkbox' ? (checked ? 1 : 0) : value 
    }));
    if (message) setMessage(null);
  };

  const validateRut = async (rut) => {
    try {
      const res = await fetch('/api/proveedores/api/validate_rut', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rut })
      });
      const data = await res.json();
      return { ok: res.ok && data.success, data };
    } catch {
      return { ok: false, data: { message: 'Error en validación' } };
    }
  };

  const handleBlurRut = async () => {
    if (!form.rut) return;
    const { ok, data } = await validateRut(form.rut);
    if (ok) {
      setForm(prev => ({ ...prev, rut: data.rut }));
      setMessage(null);
    } else {
      setMessage(data.message || 'RUT inválido');
      setMessageType('error');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      const url = proveedor && proveedor.id 
        ? `/api/proveedores/edit/${proveedor.id}` 
        : '/api/proveedores/new';
      
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
      
      setMessage(proveedor && proveedor.id ? '✓ Actualizado correctamente' : '✓ Creado correctamente');
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
            {proveedor && proveedor.id ? '✏️ Editar Proveedor' : '➕ Nuevo Proveedor'}
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

            {/* Información Básica */}
            <div className="form-section">
              <div className="form-section-title">📝 Información Básica</div>
              
              <div className="form-row">
                <label className="form-label">
                  Razón Social <span className="required">*</span>
                </label>
                <input 
                  className="form-input"
                  name="nombre" 
                  value={form.nombre} 
                  onChange={handleChange} 
                  required 
                  placeholder="Nombre o razón social del proveedor" 
                />
              </div>

              <div className="form-grid-proveedor">
                <div className="form-row">
                  <label className="form-label">
                    RUT <span className="required">*</span>
                  </label>
                  <input 
                    className="form-input"
                    name="rut" 
                    value={form.rut} 
                    onChange={handleChange} 
                    onBlur={handleBlurRut} 
                    required 
                    placeholder="12345678-9" 
                  />
                </div>

                <div className="form-row">
                  <label className="form-label">Selecciona si es subcontrato</label>
                  <div className="form-checkbox-wrapper">
                    <input 
                      className="form-checkbox"
                      type="checkbox" 
                      name="subcontrato" 
                      checked={!!form.subcontrato} 
                      onChange={handleChange}
                      id="subcontrato-check"
                    />
                    <label className="form-checkbox-label" htmlFor="subcontrato-check">
                      Es subcontrato
                    </label>
                  </div>
                </div>
              </div>
            </div>

            {/* Ubicación */}
            <div className="form-section">
              <div className="form-section-title">📍 Ubicación</div>
              
              <div className="form-grid-2">
                <div className="form-row">
                  <label className="form-label">Dirección</label>
                  <input 
                    className="form-input"
                    name="direccion" 
                    value={form.direccion} 
                    onChange={handleChange} 
                    placeholder="Calle y número" 
                  />
                </div>

                <div className="form-row">
                  <label className="form-label">Comuna</label>
                  <input 
                    className="form-input"
                    name="comuna" 
                    value={form.comuna} 
                    onChange={handleChange} 
                    placeholder="Comuna" 
                  />
                </div>
              </div>
            </div>

            {/* Contacto */}
            <div className="form-section">
              <div className="form-section-title">📞 Contacto</div>
              
              <div className="form-grid-2">
                <div className="form-row">
                  <label className="form-label">Teléfono</label>
                  <input 
                    className="form-input"
                    name="telefono" 
                    value={form.telefono} 
                    onChange={handleChange} 
                    placeholder="+56 9 xxxx xxxx" 
                  />
                </div>

                <div className="form-row">
                  <label className="form-label">Nombre Contacto</label>
                  <input 
                    className="form-input"
                    name="contacto" 
                    value={form.contacto} 
                    onChange={handleChange} 
                    placeholder="Nombre de contacto" 
                  />
                </div>
              </div>

              <div className="form-row">
                <label className="form-label">Correo Electrónico</label>
                <input 
                  className="form-input"
                  name="email" 
                  value={form.email} 
                  onChange={handleChange} 
                  type="email" 
                  placeholder="correo@proveedor.cl" 
                />
              </div>
            </div>

            {/* Datos Bancarios */}
            <div className="form-section">
              <div className="form-section-title">🏦 Datos Bancarios</div>
              
              <div className="form-grid-2">
                <div className="form-row">
                  <label className="form-label">Banco</label>
                  <input 
                    className="form-input"
                    name="banco" 
                    value={form.banco} 
                    onChange={handleChange} 
                    placeholder="Nombre del banco" 
                  />
                </div>

                <div className="form-row">
                  <label className="form-label">Número de Cuenta</label>
                  <input 
                    className="form-input"
                    name="cuenta" 
                    value={form.cuenta} 
                    onChange={handleChange} 
                    placeholder="Número de cuenta" 
                  />
                </div>
              </div>

              <div className="form-row">
                <label className="form-label">Páguese a</label>
                <input 
                  className="form-input"
                  name="paguese_a" 
                  value={form.paguese_a} 
                  onChange={handleChange} 
                  placeholder="Nombre para realizar el pago" 
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
              {loading ? '⏳ Guardando...' : (proveedor && proveedor.id ? '💾 Guardar Cambios' : '➕ Crear Proveedor')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProveedorForm;