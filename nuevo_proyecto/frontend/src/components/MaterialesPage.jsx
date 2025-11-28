import React, { useEffect, useState } from 'react';
import MaterialForm from './MaterialForm';
import MaterialesTable from './MaterialesTable';
import './Materiales.css';
import { getAuthToken } from '../utils/auth';

const MaterialesPage = () => {
  const [materiales, setMateriales] = useState([]);
  const [filteredMateriales, setFilteredMateriales] = useState([]);
  const [items, setItems] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTipo, setFilterTipo] = useState('');
  const [filterItem, setFilterItem] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const token = getAuthToken();

  const fetchMateriales = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/materiales/api/todos', {
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setMateriales(data.data || []);
        setFilteredMateriales(data.data || []);
      } else {
        console.error('Error cargando materiales:', data);
      }
    } catch (err) {
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchItems = async () => {
    try {
      const res = await fetch('/api/materiales/api/items', {
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setItems(data.data || []);
      }
    } catch (err) {
      console.error('Error cargando items:', err);
    }
  };

  useEffect(() => {
    fetchMateriales();
    fetchItems();
  }, []);

  // Filtrar materiales según búsqueda y filtros
  useEffect(() => {
    let filtered = [...materiales];

    // Aplicar búsqueda - FIX: usar String() para evitar errores
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(m => 
        String(m.cod || '').toLowerCase().includes(term) ||
        String(m.material || '').toLowerCase().includes(term) ||
        String(m.tipo || '').toLowerCase().includes(term) ||
        String(m.item || '').toLowerCase().includes(term)
      );
    }

    // Aplicar filtro de tipo
    if (filterTipo) {
      filtered = filtered.filter(m => String(m.tipo || '').toLowerCase() === filterTipo.toLowerCase());
    }

    // Aplicar filtro de item
    if (filterItem) {
      filtered = filtered.filter(m => String(m.item || '').toLowerCase() === filterItem.toLowerCase());
    }

    setFilteredMateriales(filtered);
  }, [searchTerm, filterTipo, filterItem, materiales]);

  const handleCreateNew = () => {
    setSelectedMaterial(null);
    setShowModal(true);
  };

  const handleEdit = (material) => {
    setSelectedMaterial(material);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedMaterial(null);
  };

  const handleSaved = () => {
    fetchMateriales();
    handleCloseModal();
  };

  // Obtener opciones únicas de tipo para filtro
  const tipoOptions = [...new Set(materiales.map(m => m.tipo).filter(Boolean))];

  return (
    <div className="materiales-page">
      <div className="materiales-header">
        <h1>Materiales</h1>
        <button className="btn-create" onClick={handleCreateNew}>
          ➕ Crear Nuevo Material
        </button>
      </div>

      {/* Buscador y Filtros (ahora vertical) */}
      <div className="search-filter-bar vertical">
        <div className="search-input-wrapper">
          <input
            type="text"
            className="search-input"
            placeholder="Buscar por código, material, tipo o item..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="filters-row">
          <select
            className="filter-select"
            value={filterTipo}
            onChange={(e) => setFilterTipo(e.target.value)}
          >
            <option value="">Todos los tipos</option>
            {tipoOptions.map((tipo, idx) => (
              <option key={idx} value={tipo}>
                {tipo}
              </option>
            ))}
          </select>
          <select
            className="filter-select"
            value={filterItem}
            onChange={(e) => setFilterItem(e.target.value)}
          >
            <option value="">Todos los items</option>
            {items.map((it, idx) => (
              <option key={idx} value={it.tipo}>
                {it.tipo}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabla */}
      <div className="table-area">
        <div className="table-header">
          <h2>
            Lista de Materiales
            {filteredMateriales.length > 0 && (
              <span className="table-count">
                {filteredMateriales.length}
              </span>
            )}
          </h2>
          {loading && <span className="loading">Cargando...</span>}
        </div>
        
        <MaterialesTable 
          materiales={filteredMateriales} 
          onEdit={handleEdit} 
        />
      </div>

      {/* Modal */}
      {showModal && (
        <MaterialForm
          material={selectedMaterial}
          items={items}
          onClose={handleCloseModal}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
};

export default MaterialesPage;
