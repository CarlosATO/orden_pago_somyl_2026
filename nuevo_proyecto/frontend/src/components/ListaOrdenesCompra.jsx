// frontend/src/components/ListaOrdenesCompra.jsx

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import API_BASE_URL from '../config/api';
import { getAuthToken } from '../utils/auth';
import DetalleOrdenModal from './DetalleOrdenModal';
import './ListaOrdenesCompra.css';

function ListaOrdenesCompra() {
  const navigate = useNavigate();
  const [ordenes, setOrdenes] = useState([]);
  const [ordenesFiltradas, setOrdenesFiltradas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mensaje, setMensaje] = useState(null);
  
  // Filtros
  const [filtroTexto, setFiltroTexto] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('Todas');
  
  // Modal
  const [ordenSeleccionada, setOrdenSeleccionada] = useState(null);
  const [mostrarModal, setMostrarModal] = useState(false);

  useEffect(() => {
    cargarOrdenes();
  }, []);

  useEffect(() => {
    aplicarFiltros();
  }, [ordenes, filtroTexto, filtroEstado]);

  const cargarOrdenes = async () => {
    setLoading(true);
    try {
      const token = getAuthToken();
      if (!token) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
        setLoading(false);
        return;
      }

      const response = await axios.get(`${API_BASE_URL}/lista-ordenes/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.data.success) {
        setOrdenes(response.data.data);
      } else {
        setMensaje({ tipo: 'error', texto: response.data.message || 'Error al cargar órdenes' });
      }
    } catch (error) {
      console.error('Error:', error);
      if (error.response?.status === 401) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada. Por favor inicia sesión nuevamente.' });
      } else {
        setMensaje({ tipo: 'error', texto: 'Error de conexión' });
      }
    } finally {
      setLoading(false);
    }
  };

  const aplicarFiltros = () => {
    let resultado = [...ordenes];
    
    // Filtro por texto (busca en N° OC, Proveedor, Proyecto)
    if (filtroTexto) {
      const textoLower = filtroTexto.toLowerCase();
      resultado = resultado.filter(orden => 
        orden.orden_compra.toString().includes(textoLower) ||
        orden.proveedor.toLowerCase().includes(textoLower) ||
        orden.proyecto.toLowerCase().includes(textoLower)
      );
    }
    
    // Filtro por estado
    if (filtroEstado !== 'Todas') {
      resultado = resultado.filter(orden => orden.estado === filtroEstado);
    }
    
    setOrdenesFiltradas(resultado);
  };

  const handleNuevaOrden = () => {
    navigate('/adquisiciones/crear-orden');
  };

  const handleVerDetalle = async (oc_numero) => {
    try {
      const token = getAuthToken();
      if (!token) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
        return;
      }

      const response = await axios.get(`${API_BASE_URL}/lista-ordenes/${oc_numero}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.data.success) {
        setOrdenSeleccionada(response.data.data);
        setMostrarModal(true);
      } else {
        setMensaje({ tipo: 'error', texto: 'Error al cargar detalle' });
      }
    } catch (error) {
      console.error('Error:', error);
      setMensaje({ tipo: 'error', texto: 'Error de conexión' });
    }
  };

  const handleEditarOrden = (orden) => {
    // Navegar a OrdenCompra con los datos de la orden
    navigate('/adquisiciones/crear-orden', { state: { ordenData: orden } });
  };

  const formatearMonto = (monto) => {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP'
    }).format(monto);
  };

  const formatearFecha = (fecha) => {
    if (!fecha) return '-';
    return new Date(fecha).toLocaleDateString('es-CL');
  };

  const getEstadoClass = (estado) => {
    switch(estado) {
      case 'Recibida': return 'estado-recibida';
      case 'Pendiente': return 'estado-pendiente';
      case 'Parcial': return 'estado-parcial';
      default: return '';
    }
  };

  if (loading) {
    return (
      <div className="lista-ordenes-container">
        <div className="loading">Cargando órdenes de compra...</div>
      </div>
    );
  }

  return (
    <div className="lista-ordenes-container">
      {/* HEADER */}
      <div className="lista-ordenes-header">
        <div className="header-titulo">
          <h1>📦 Órdenes de Compra</h1>
          <span className="total-registros">{ordenesFiltradas.length} órdenes</span>
        </div>
        <button className="btn-nuevo" onClick={handleNuevaOrden}>
          + Nuevo
        </button>
      </div>

      {mensaje && (
        <div className={`mensaje mensaje-${mensaje.tipo}`}>
          {mensaje.texto}
        </div>
      )}

      {/* FILTROS */}
      <div className="filtros-container">
        <div className="filtro-grupo">
          <input
            type="text"
            placeholder="🔍 Buscar por N° OC, Proveedor o Proyecto..."
            value={filtroTexto}
            onChange={(e) => setFiltroTexto(e.target.value)}
            className="filtro-input"
          />
        </div>
        
        <div className="filtro-grupo">
          <select
            value={filtroEstado}
            onChange={(e) => setFiltroEstado(e.target.value)}
            className="filtro-select"
          >
            <option value="Todas">Todos los estados</option>
            <option value="Pendiente">Pendiente</option>
            <option value="Parcial">Parcial</option>
            <option value="Recibida">Recibida</option>
          </select>
        </div>
      </div>

      {/* TABLA */}
      <div className="tabla-container">
        <table className="tabla-ordenes">
          <thead>
            <tr>
              <th>FECHA</th>
              <th>N° O.C.</th>
              <th>PROVEEDOR</th>
              <th>ESTADO</th>
              <th>PROYECTO</th>
              <th>MONTO</th>
            </tr>
          </thead>
          <tbody>
            {ordenesFiltradas.length === 0 ? (
              <tr>
                <td colSpan="6" className="sin-datos">
                  No se encontraron órdenes de compra
                </td>
              </tr>
            ) : (
              ordenesFiltradas.map((orden) => (
                <tr 
                  key={orden.orden_compra}
                  onClick={() => handleVerDetalle(orden.orden_compra)}
                  className="fila-clickable"
                >
                  <td>{formatearFecha(orden.fecha)}</td>
                  <td className="numero-oc">{orden.orden_compra}</td>
                  <td>{orden.proveedor}</td>
                  <td>
                    <span className={`estado-badge ${getEstadoClass(orden.estado)}`}>
                      {orden.estado}
                    </span>
                  </td>
                  <td>{orden.proyecto}</td>
                  <td className="monto">{formatearMonto(orden.total)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* MODAL DE DETALLE */}
      {mostrarModal && (
        <DetalleOrdenModal
          orden={ordenSeleccionada}
          onClose={() => {
            setMostrarModal(false);
            setOrdenSeleccionada(null);
          }}
          onEditar={handleEditarOrden}
        />
      )}
    </div>
  );
}

export default ListaOrdenesCompra;