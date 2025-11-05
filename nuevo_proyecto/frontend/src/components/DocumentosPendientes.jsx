import { useState, useEffect } from 'react';
import './DocumentosPendientes.css';
import { getAuthToken } from '../utils/auth';

function DocumentosPendientes() {
  const [filas, setFilas] = useState([]);
  const [stats, setStats] = useState({
    total_pendientes: 0,
    total_monto: 0,
    proveedores_unicos: 0,
    ordenes_unicas: 0
  });
  const [loading, setLoading] = useState(false);
  const [mensaje, setMensaje] = useState(null);
  const [filtroProveedor, setFiltroProveedor] = useState('');
  const [filtroOrden, setFiltroOrden] = useState('');
  const [facturasInput, setFacturasInput] = useState({});

  useEffect(() => {
    fetchPendientes();
  }, []);

  useEffect(() => {
    if (mensaje) {
      const timer = setTimeout(() => setMensaje(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [mensaje]);

  const fetchPendientes = async () => {
    setLoading(true);
    try {
      const token = getAuthToken();
      if (!token) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
        return;
      }

      const response = await fetch('/api/documentos-pendientes/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setFilas(data.data.filas);
          setStats(data.data.stats);
        } else {
          setMensaje({ tipo: 'error', texto: data.message || 'Error al cargar datos' });
        }
      } else if (response.status === 401) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
      } else {
        setMensaje({ tipo: 'error', texto: 'Error al cargar documentos' });
      }
    } catch (error) {
      console.error('Error:', error);
      setMensaje({ tipo: 'error', texto: 'Error de conexión' });
    } finally {
      setLoading(false);
    }
  };

  const handleActualizar = async (id) => {
    const factura = facturasInput[id];
    
    if (!factura || factura.trim() === '') {
      setMensaje({ tipo: 'error', texto: 'Ingrese número de documento' });
      return;
    }

    setLoading(true);
    try {
      const token = getAuthToken();
      const response = await fetch('/api/documentos-pendientes/update', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ id, factura: factura.trim() })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setMensaje({ tipo: 'success', texto: data.message });
        setFacturasInput(prev => ({ ...prev, [id]: '' }));
        await fetchPendientes();
      } else {
        setMensaje({ tipo: 'error', texto: data.message || 'Error al actualizar' });
      }
    } catch (error) {
      console.error('Error:', error);
      setMensaje({ tipo: 'error', texto: 'Error de conexión' });
    } finally {
      setLoading(false);
    }
  };

  const handleFacturaChange = (id, valor) => {
    setFacturasInput(prev => ({ ...prev, [id]: valor }));
  };

  const limpiarFiltros = () => {
    setFiltroProveedor('');
    setFiltroOrden('');
  };

  const filasFiltradas = filas.filter(fila => {
    const matchProveedor = !filtroProveedor || 
      fila.proveedor_nombre.toLowerCase().includes(filtroProveedor.toLowerCase());
    const matchOrden = !filtroOrden || 
      fila.orden_numero.toString().includes(filtroOrden);
    return matchProveedor && matchOrden;
  });

  // Paginación en cliente: mostrar X filas por página
  const [page, setPage] = useState(1);
  const perPage = 50; // Mostrar 50 líneas por página
  const totalPages = Math.max(1, Math.ceil(filasFiltradas.length / perPage));

  // Resetear página cuando cambian los filtros / datos
  useEffect(() => {
    setPage(1);
  }, [filtroProveedor, filtroOrden, filas.length]);

  const filasPagina = filasFiltradas.slice((page - 1) * perPage, page * perPage);

  const formatMonto = (monto) => {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(monto);
  };

  return (
    <div className="pendientes-container">
      <div className="pendientes-header">
        <div className="header-title-group">
          <div className="icon-wrapper">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" strokeWidth="2"/>
              <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2"/>
              <path d="M12 18V12M12 12L9 15M12 12L15 15" stroke="currentColor" strokeWidth="2"/>
            </svg>
          </div>
          <h1>Documentos Pendientes</h1>
        </div>
        <button className="btn-limpiar-filtros-header" onClick={limpiarFiltros}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          Limpiar Filtros
        </button>
      </div>

      {mensaje && (
        <div className={`mensaje mensaje-${mensaje.tipo}`}>
          {mensaje.texto}
        </div>
      )}

      <div className="stats-grid-simple">
        <div className="stat-card">
          <div className="stat-icon stat-pendientes">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M9 5H7C5.89543 5 5 5.89543 5 7V19C5 20.1046 5.89543 21 7 21H17C18.1046 21 19 20.1046 19 19V7C19 5.89543 18.1046 5 17 5H15" stroke="currentColor" strokeWidth="2"/>
              <rect x="9" y="3" width="6" height="4" rx="1" stroke="currentColor" strokeWidth="2"/>
            </svg>
          </div>
          <div className="stat-content">
            <div className="stat-value">{stats.total_pendientes}</div>
            <div className="stat-label">Órdenes Pendientes</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-monto">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
              <path d="M12 6V18M9 9H13.5C14.6046 9 15.5 9.89543 15.5 11C15.5 12.1046 14.6046 13 13.5 13H9" stroke="currentColor" strokeWidth="2"/>
            </svg>
          </div>
          <div className="stat-content">
            <div className="stat-value">{formatMonto(stats.total_monto)}</div>
            <div className="stat-label">Monto Total</div>
          </div>
        </div>
      </div>

      <div className="filtros-section">
        <div className="filtro-group">
          <label>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2"/>
              <path d="M21 21L16.65 16.65" stroke="currentColor" strokeWidth="2"/>
            </svg>
            Buscar Proveedor
          </label>
          <input
            type="text"
            value={filtroProveedor}
            onChange={(e) => setFiltroProveedor(e.target.value)}
            placeholder="Filtrar por proveedor..."
          />
        </div>
        <div className="filtro-group">
          <label>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M9 5H7C5.89543 5 5 5.89543 5 7V19C5 20.1046 5.89543 21 7 21H17C18.1046 21 19 20.1046 19 19V7C19 5.89543 18.1046 5 17 5H15" stroke="currentColor" strokeWidth="2"/>
              <rect x="9" y="3" width="6" height="4" rx="1" stroke="currentColor" strokeWidth="2"/>
            </svg>
            Buscar O.Pago
          </label>
          <input
            type="text"
            value={filtroOrden}
            onChange={(e) => setFiltroOrden(e.target.value)}
            placeholder="Filtrar por orden..."
          />
        </div>
        <div className="filtro-info">
          Mostrando {Math.min((page - 1) * perPage + 1, filasFiltradas.length || 0)} - {Math.min(page * perPage, filasFiltradas.length)} de {filasFiltradas.length}
        </div>
      </div>

      <div className="tabla-container">
        {loading && filas.length === 0 ? (
          <div className="loading-overlay">
            <div className="spinner"></div>
            <p>Cargando documentos...</p>
          </div>
        ) : filasFiltradas.length === 0 ? (
          <div className="empty-state">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
              <path d="M9 11L12 14L22 4" stroke="currentColor" strokeWidth="2"/>
              <path d="M21 12V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 2.58579C3.96086 2.21071 4.46957 2 5 2H16" stroke="currentColor" strokeWidth="2"/>
            </svg>
            <h3>¡Todo al día!</h3>
            <p>No hay documentos pendientes</p>
          </div>
        ) : (
          <>
          <div className="table-scroll">
            <table className="tabla-pendientes">
              <thead>
                <tr>
                  <th>OC</th>
                  <th>O.Pago</th>
                  <th>Proveedor</th>
                  <th>Material</th>
                  <th className="text-center">Cant.</th>
                  <th>Detalle</th>
                  <th className="text-end">Monto</th>
                  <th className="text-center">Fecha OP</th>
                  <th className="text-center">Estado</th>
                  <th>Nº Documento</th>
                  <th className="text-center">Acción</th>
                </tr>
              </thead>
              <tbody>
                {filasPagina.map((fila) => (
                  <tr key={fila.id}>
                    <td><span className="badge-oc">{fila.orden_compra}</span></td>
                    <td><span className="badge-orden">{fila.orden_numero}</span></td>
                    <td><div className="proveedor-cell">{fila.proveedor_nombre}</div></td>
                    <td><div className="material-cell" title={fila.material_nombre}>{fila.material_nombre}</div></td>
                    <td className="text-center"><span className="cantidad-badge">{fila.cantidad}</span></td>
                    <td><div className="detalle-cell" title={fila.detalle_compra}>{fila.detalle_compra || '-'}</div></td>
                    <td className="text-end monto-cell">{formatMonto(fila.monto_neto_oc)}</td>
                    <td className="text-center">{fila.fecha_op || '-'}</td>
                    <td className="text-center">
                      {fila.fac_compra && <span className="badge-fac-compra">Fac. Compra</span>}
                    </td>
                    <td>
                      <input
                        type="text"
                        className="factura-input"
                        placeholder="Nº Doc..."
                        value={facturasInput[fila.id] || ''}
                        onChange={(e) => handleFacturaChange(fila.id, e.target.value)}
                        disabled={loading}
                      />
                    </td>
                    <td className="text-center">
                      <button
                        className="btn-guardar"
                        onClick={() => handleActualizar(fila.id)}
                        disabled={loading || !facturasInput[fila.id]}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                          <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="2"/>
                        </svg>
                        Guardar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>

            {/* Paginación */}
            <div className="paginacion" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem'}}>
              <div className="paginacion-info" style={{color: '#64748b', fontSize: '0.875rem'}}>
                Mostrando {((page - 1) * perPage) + 1} - {Math.min(page * perPage, filasFiltradas.length)} de {filasFiltradas.length}
              </div>
              <div className="paginacion-botones">
                <button className="btn-guardar" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{marginRight: '0.5rem'}}>
                  Anterior
                </button>
                <span className="page-info" style={{margin: '0 0.5rem', color: '#475569'}}>Página {page} de {totalPages}</span>
                <button className="btn-guardar" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} style={{marginLeft: '0.5rem'}}>
                  Siguiente
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default DocumentosPendientes;