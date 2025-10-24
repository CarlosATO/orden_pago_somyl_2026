import React, { useEffect, useState } from 'react';
import './Proveedores.css';

const ProveedorForm = ({ proveedor, onSaved }) => {
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
    } else {
      setForm(prev => ({ ...prev, nombre: '', rut: '' }));
    }
  }, [proveedor]);

  const token = localStorage.getItem('authToken');

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm(prev => ({ ...prev, [name]: type === 'checkbox' ? (checked ? 1 : 0) : value }));
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
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      const url = proveedor && proveedor.id ? `/api/proveedores/edit/${proveedor.id}` : '/api/proveedores/new';
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify(form)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || 'Error en servidor');
      setMessage('Guardado correctamente');
      if (onSaved) onSaved(data.data || data);
    } catch (err) {
      console.error(err);
      setMessage(err.message || 'Error al guardar');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="proveedor-form">
      <h3>{proveedor && proveedor.id ? 'Editar proveedor' : 'Nuevo proveedor'}</h3>
      {message && <div className="form-message">{message}</div>}
      <form onSubmit={handleSubmit}>
        <div className="row">
          <label>Razón Social</label>
          <input name="nombre" value={form.nombre} onChange={handleChange} required placeholder="Nombre o razón social" />
        </div>

        <div className="grid-2">
          <div className="row">
            <label>RUT</label>
            <input name="rut" value={form.rut} onChange={handleChange} onBlur={handleBlurRut} required placeholder="12345678-9" />
          </div>
          <div className="row inline">
            <label style={{ minWidth: 110 }}>Subcontrato</label>
            <input type="checkbox" name="subcontrato" checked={!!form.subcontrato} onChange={handleChange} />
          </div>
        </div>

        <div className="grid-2">
          <div className="row">
            <label>Dirección</label>
            <input name="direccion" value={form.direccion} onChange={handleChange} placeholder="Calle, número" />
          </div>
          <div className="row">
            <label>Comuna</label>
            <input name="comuna" value={form.comuna} onChange={handleChange} placeholder="Comuna" />
          </div>
        </div>

        <div className="grid-2">
          <div className="row">
            <label>Teléfono</label>
            <input name="telefono" value={form.telefono} onChange={handleChange} placeholder="+56 9 xxxx xxxx" />
          </div>
          <div className="row">
            <label>Contacto</label>
            <input name="contacto" value={form.contacto} onChange={handleChange} placeholder="Nombre de contacto" />
          </div>
        </div>

        <div className="grid-2">
          <div className="row">
            <label>Correo</label>
            <input name="email" value={form.email} onChange={handleChange} type="email" placeholder="correo@proveedor.cl" />
          </div>
          <div className="row">
            <label>Banco</label>
            <input name="banco" value={form.banco} onChange={handleChange} placeholder="Banco" />
          </div>
        </div>

        <div className="grid-2">
          <div className="row">
            <label>Cuenta</label>
            <input name="cuenta" value={form.cuenta} onChange={handleChange} placeholder="Número cuenta" />
          </div>
          <div className="row">
            <label>Páguese a</label>
            <input name="paguese_a" value={form.paguese_a} onChange={handleChange} placeholder="Nombre para pago" />
          </div>
        </div>

        <div className="actions">
          <button type="submit" disabled={loading}>{loading ? 'Guardando...' : 'Guardar'}</button>
        </div>
      </form>
    </div>
  );
};

export default ProveedorForm;
