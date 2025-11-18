import React, { useEffect, useState } from 'react';
import ProveedorForm from './ProveedorForm';
import ProveedoresTable from './ProveedoresTable';
import './Proveedores.css';
import { getAuthToken } from '../utils/auth';

const ProveedoresPage = () => {
  const [proveedores, setProveedores] = useState([]);
  const [filteredProveedores, setFilteredProveedores] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [selectedProveedor, setSelectedProveedor] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const token = getAuthToken();

  const fetchProveedores = async () => {
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
        setFilteredProveedores(data.data || []);
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
    fetchProveedores();
  }, []);

  // Filtrar proveedores según búsqueda
  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredProveedores(proveedores);
      return;
    }

    const term = searchTerm.toLowerCase();
    const filtered = proveedores.filter(p => 
      p.nombre?.toLowerCase().includes(term) ||
      p.rut?.toLowerCase().includes(term) ||
      p.contacto?.toLowerCase().includes(term) ||
      p.email?.toLowerCase().includes(term)
    );
    setFilteredProveedores(filtered);
  }, [searchTerm, proveedores]);

  const handleCreateNew = () => {
    setSelectedProveedor(null);
    setShowModal(true);
  };

  const handleEdit = async (proveedor) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/proveedores/edit/${proveedor.id}`, {
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setSelectedProveedor(data.data);
        setShowModal(true);
      } else {
        console.error('Error cargando proveedor para editar:', data);
      }
    } catch (err) {
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedProveedor(null);
  };

  const handleSaved = () => {
    fetchProveedores();
    handleCloseModal();
  };

  return (
    <div className="proveedores-page">
      <div className="proveedores-header">
        <h1>Proveedores</h1>
        <button className="btn-create" onClick={handleCreateNew}>
          ➕ Crear Nuevo Proveedor
        </button>
      </div>

      {/* Buscador */}
      <div className="search-bar">
        <div className="search-input-wrapper">
          <input
            type="text"
            className="search-input"
            placeholder="Buscar por nombre, RUT, contacto o correo..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* Tabla */}
      <div className="table-area">
        <div className="table-header">
          <h2>
            Lista de Proveedores
            {filteredProveedores.length > 0 && (
              <span className="table-count">
                {filteredProveedores.length}
              </span>
            )}
          </h2>
          {loading && <span className="loading">Cargando...</span>}
        </div>
        
        <ProveedoresTable 
          proveedores={filteredProveedores} 
          onEdit={handleEdit} 
        />
      </div>

      {/* Modal */}
      {showModal && (
        <ProveedorForm
          proveedor={selectedProveedor}
          onClose={handleCloseModal}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
};

export default ProveedoresPage;