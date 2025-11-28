import React, { useEffect, useState } from 'react';
import ProyectoForm from './ProyectoForm';
import ProyectosTable from './ProyectosTable';
import './Proyectos.css';
import { getAuthToken } from '../utils/auth';

const ProyectosPage = () => {
  const [proyectos, setProyectos] = useState([]);
  const [filteredProyectos, setFilteredProyectos] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [selectedProyecto, setSelectedProyecto] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ total: 0, conVenta: 0, sinVenta: 0 });
  
  const token = getAuthToken();

  const fetchProyectos = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/proyectos/api/activos', {
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      const data = await res.json();
      if (res.ok && data.success) {
        const proyectosData = data.data || [];
        setProyectos(proyectosData);
        setFilteredProyectos(proyectosData);
        
        // Calcular estadísticas
        const total = proyectosData.length;
        const conVenta = proyectosData.filter(p => p.venta).length;
        const sinVenta = total - conVenta;
        setStats({ total, conVenta, sinVenta });
      } else {
        console.error('Error cargando proyectos:', data);
      }
    } catch (err) {
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProyectos();
  }, []);

  // Filtrar proyectos según búsqueda y filtro
  useEffect(() => {
    let filtered = [...proyectos];

    // Aplicar búsqueda
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(p => 
        (typeof p.proyecto === 'string' && p.proyecto.toLowerCase().includes(term)) ||
        (typeof p.venta === 'string' && p.venta.toLowerCase().includes(term)) ||
        (typeof p.observacion === 'string' && p.observacion.toLowerCase().includes(term))
      );
    }

    // Aplicar filtro
    if (filter === 'con_venta') {
      filtered = filtered.filter(p => p.venta);
    } else if (filter === 'sin_venta') {
      filtered = filtered.filter(p => !p.venta);
    }

    setFilteredProyectos(filtered);
  }, [searchTerm, filter, proyectos]);

  const handleCreateNew = () => {
    setSelectedProyecto(null);
    setShowModal(true);
  };

  const handleEdit = (proyecto) => {
    setSelectedProyecto(proyecto);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedProyecto(null);
  };

  const handleSaved = () => {
    fetchProyectos();
    handleCloseModal();
  };

  return (
    <div className="proyectos-page">
      <div className="proyectos-header">
        <h1>Proyectos</h1>
        <button className="btn-create" onClick={handleCreateNew}>
          ➕ Crear Nuevo Proyecto
        </button>
      </div>

      {/* Estadísticas */}
      <div className="stats-container">
        <div className="stat-card total">
          <div className="stat-number">{stats.total}</div>
          <div className="stat-label">Total Proyectos</div>
        </div>
        <div className="stat-card con-venta">
          <div className="stat-number">{stats.conVenta}</div>
          <div className="stat-label">Con Venta</div>
        </div>
        <div className="stat-card sin-venta">
          <div className="stat-number">{stats.sinVenta}</div>
          <div className="stat-label">Sin Venta</div>
        </div>
      </div>

      {/* Buscador y Filtros */}
      <div className="search-filter-bar">
        <div className="search-input-wrapper">
          <input
            type="text"
            className="search-input"
            placeholder="Buscar por proyecto, venta u observación..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <select
          className="filter-select"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="">Todos los proyectos</option>
          <option value="con_venta">Con venta</option>
          <option value="sin_venta">Sin venta</option>
        </select>
      </div>

      {/* Tabla */}
      <div className="table-area">
        <div className="table-header">
          <h2>
            Lista de Proyectos
            {filteredProyectos.length > 0 && (
              <span className="table-count">
                {filteredProyectos.length}
              </span>
            )}
          </h2>
          {loading && <span className="loading">Cargando...</span>}
        </div>
        
        <ProyectosTable 
          proyectos={filteredProyectos} 
          onEdit={handleEdit} 
        />
      </div>

      {/* Modal */}
      {showModal && (
        <ProyectoForm
          proyecto={selectedProyecto}
          onClose={handleCloseModal}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
};

export default ProyectosPage;
