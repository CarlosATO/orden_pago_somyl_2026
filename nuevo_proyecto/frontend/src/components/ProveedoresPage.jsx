import React, { useEffect, useState } from 'react';
import ProveedorForm from './ProveedorForm';
import ProveedoresTable from './ProveedoresTable';
import './Proveedores.css';

const ProveedoresPage = () => {
  const [proveedores, setProveedores] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const token = localStorage.getItem('authToken');

  const fetchTodos = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/proveedores/api/todos', {
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setProveedores(data.data || []);
      } else {
        console.error('Error cargando proveedores:', data);
      }
    } catch (err) {
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTodos();
  }, []);

  const handleEdit = (prov) => {
    setSelected(prov);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSaved = () => {
    // Refresh list after create/update
    fetchTodos();
    setSelected(null);
  };

  return (
    <div className="proveedores-page">
      <div className="proveedores-header">
        <h1>Proveedores</h1>
      </div>

      <div className="form-area">
        <ProveedorForm
          key={selected ? selected.id : 'new'}
          proveedor={selected}
          onSaved={handleSaved}
        />
      </div>

      <div className="table-area">
        <div className="table-header">
          <h2>Lista de proveedores</h2>
          {loading && <span className="loading">Cargando...</span>}
        </div>
        <ProveedoresTable proveedores={proveedores} onEdit={handleEdit} />
      </div>
    </div>
  );
};

export default ProveedoresPage;
