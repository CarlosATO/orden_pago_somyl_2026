import { useState, useEffect } from 'react';
import Select from 'react-select';
import AsyncSelect from 'react-select/async';
import './OrdenesPago.css';

function OrdenesPago() {
  // ========= Estados principales =========
  const [numeroOP, setNumeroOP] = useState('');
  const [proveedor, setProveedor] = useState(null);
  const [proveedorData, setProveedorData] = useState(null);
  const [documentos, setDocumentos] = useState([]);
  const [lineasSeleccionadas, setLineasSeleccionadas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mensaje, setMensaje] = useState(null);

  // ========= Estados del formulario =========
  const [autoriza, setAutoriza] = useState(null);
  const [fechaFactura, setFechaFactura] = useState('');
  const [vencimiento, setVencimiento] = useState('');
  const [estadoPago, setEstadoPago] = useState('');
  const [detalleCompra, setDetalleCompra] = useState('');

  // ========= Estados de modales =========
  const [mostrarHistorial, setMostrarHistorial] = useState(false);
  const [historial, setHistorial] = useState([]);
  const [mostrarCopiar, setMostrarCopiar] = useState(false);

  // ========= Cargar próximo número al montar =========
  useEffect(() => {
    fetchProximoNumero();
  }, []);

  const fetchProximoNumero = async () => {
    try {
      const token = localStorage.getItem('authToken');
      if (!token) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
        return;
      }

      const response = await fetch('/api/ordenes_pago/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setNumeroOP(data.data.next_num);
        }
      }
    } catch (error) {
      console.error('Error al obtener próximo número:', error);
    }
  };

  // ========= Cargar documentos del proveedor =========
  const handleProveedorChange = async (selectedOption) => {
    setProveedor(selectedOption);
    setDocumentos([]);
    setLineasSeleccionadas([]);

    if (!selectedOption) {
      setProveedorData(null);
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(`/api/ordenes_pago/?proveedor_id=${selectedOption.value}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setProveedorData(data.data.proveedor_seleccionado);
          setDocumentos(data.data.documentos);
          setMensaje(null);
        }
      } else if (response.status === 401) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
      }
    } catch (error) {
      console.error('Error al cargar documentos:', error);
      setMensaje({ tipo: 'error', texto: 'Error al cargar documentos' });
    } finally {
      setLoading(false);
    }
  };

  // ========= Seleccionar documento y cargar líneas =========
  const handleSeleccionarDocumento = async (documento, oc) => {
    if (!proveedor) return;

    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      const url = `/api/ordenes_pago/detalle?documento=${encodeURIComponent(documento)}&oc=${oc}&proveedor_id=${proveedor.value}`;

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          // Agregar líneas que no estén ya seleccionadas
          const nuevasLineas = data.data.filter(linea =>
            !lineasSeleccionadas.some(ls => ls.ingreso_id === linea.ingreso_id)
          );

          setLineasSeleccionadas([...lineasSeleccionadas, ...nuevasLineas]);
          setMensaje({ tipo: 'success', texto: `${nuevasLineas.length} línea(s) agregada(s)` });
        }
      }
    } catch (error) {
      console.error('Error al cargar líneas:', error);
      setMensaje({ tipo: 'error', texto: 'Error al cargar líneas del documento' });
    } finally {
      setLoading(false);
    }
  };

  // ========= Eliminar línea seleccionada =========
  const eliminarLinea = (ingresoId) => {
    setLineasSeleccionadas(lineasSeleccionadas.filter(l => l.ingreso_id !== ingresoId));
  };

  // ========= Calcular totales =========
  const calcularTotales = () => {
    const neto = lineasSeleccionadas.reduce((sum, linea) => sum + linea.neto_total, 0);
    const iva = neto * 0.19; // TODO: Verificar si hay líneas sin IVA
    const total = neto + iva;

    return { neto, iva, total };
  };

  // ========= Guardar orden de pago =========
  const handleGuardar = async () => {
    // Validaciones
    if (!proveedor) {
      setMensaje({ tipo: 'error', texto: 'Debe seleccionar un proveedor' });
      return;
    }

    if (!autoriza) {
      setMensaje({ tipo: 'error', texto: 'Debe seleccionar quien autoriza' });
      return;
    }

    if (!fechaFactura || !vencimiento) {
      setMensaje({ tipo: 'error', texto: 'Debe completar fechas de factura y vencimiento' });
      return;
    }

    if (!detalleCompra.trim()) {
      setMensaje({ tipo: 'error', texto: 'El detalle de compra es obligatorio' });
      return;
    }

    if (lineasSeleccionadas.length === 0) {
      setMensaje({ tipo: 'error', texto: 'Debe seleccionar al menos una línea' });
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');

      const payload = {
        orden_numero: numeroOP,
        proveedor_id: proveedor.value,
        proveedor_nombre: proveedor.label,
        autoriza_id: autoriza.value,
        autoriza_nombre: autoriza.label,
        fecha_factura: fechaFactura,
        vencimiento: vencimiento,
        estado_pago: estadoPago,
        detalle_compra: detalleCompra,
        lineas: lineasSeleccionadas
      };

      const response = await fetch('/api/ordenes_pago/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setMensaje({ tipo: 'success', texto: data.message });

        // Limpiar formulario
        setLineasSeleccionadas([]);
        setDetalleCompra('');
        setEstadoPago('');
        await fetchProximoNumero();

        // Recargar documentos del proveedor
        if (proveedor) {
          handleProveedorChange(proveedor);
        }
      } else {
        setMensaje({ tipo: 'error', texto: data.message || 'Error al guardar' });
      }
    } catch (error) {
      console.error('Error al guardar:', error);
      setMensaje({ tipo: 'error', texto: 'Error al guardar la orden de pago' });
    } finally {
      setLoading(false);
    }
  };

  // ========= Generar PDF =========
  const handleGenerarPDF = async () => {
    if (!numeroOP) {
      setMensaje({ tipo: 'error', texto: 'Debe crear la orden primero' });
      return;
    }

    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(`/api/ordenes_pago/pdf/${numeroOP}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `orden_pago_${numeroOP}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        setMensaje({ tipo: 'success', texto: 'PDF generado correctamente' });
      } else {
        const data = await response.json();
        setMensaje({ tipo: 'error', texto: data.message || 'Error al generar PDF' });
      }
    } catch (error) {
      console.error('Error al generar PDF:', error);
      setMensaje({ tipo: 'error', texto: 'Error al generar PDF' });
    }
  };

  // ========= Ver historial =========
  const handleVerHistorial = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch('/api/ordenes_pago/historial', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setHistorial(data.data);
          setMostrarHistorial(true);
        }
      }
    } catch (error) {
      console.error('Error al cargar historial:', error);
    } finally {
      setLoading(false);
    }
  };

  // ========= Copiar orden =========
  const handleCopiarOrden = async (ordenNumero) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(`/api/ordenes_pago/copiar/${ordenNumero}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          const copiaData = data.data;

          // Cargar datos en el formulario
          setNumeroOP(copiaData.next_num);
          setProveedor({ value: copiaData.proveedor_id, label: copiaData.proveedor_nombre });
          setAutoriza({ value: copiaData.autoriza_id, label: copiaData.autoriza_nombre });
          setFechaFactura(copiaData.fecha_factura);
          setVencimiento(copiaData.vencimiento);
          setEstadoPago(copiaData.estado_pago);
          setDetalleCompra(copiaData.detalle_compra);
          setLineasSeleccionadas(copiaData.lineas);

          setMostrarHistorial(false);
          setMensaje({ tipo: 'success', texto: `Orden ${ordenNumero} copiada. Modifique y guarde.` });
        }
      }
    } catch (error) {
      console.error('Error al copiar orden:', error);
      setMensaje({ tipo: 'error', texto: 'Error al copiar la orden' });
    } finally {
      setLoading(false);
    }
  };

  // ========= Búsqueda de proveedores =========
  const loadProveedores = async (inputValue) => {
    try {
      const token = localStorage.getItem('authToken');
      const searchTerm = inputValue ? inputValue.trim() : '';

      const query = searchTerm.length >= 2
        ? `?term=${encodeURIComponent(searchTerm)}`
        : `?limit=10`;

      const response = await fetch(`/api/ordenes/helpers/autocomplete/proveedores${query}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        return data.results || [];
      }
      return [];
    } catch (error) {
      console.error('Error al buscar proveedores:', error);
      return [];
    }
  };

  // ========= Búsqueda de trabajadores =========
  const loadTrabajadores = async (inputValue) => {
    try {
      const token = localStorage.getItem('authToken');
      const searchTerm = inputValue ? inputValue.trim() : '';

      const query = searchTerm.length >= 2
        ? `?term=${encodeURIComponent(searchTerm)}`
        : `?limit=10`;

      const response = await fetch(`/api/ordenes/helpers/autocomplete/trabajadores${query}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        return data.results || [];
      }
      return [];
    } catch (error) {
      console.error('Error al buscar trabajadores:', error);
      return [];
    }
  };

  // ========= Estilos para react-select =========
  const customSelectStyles = {
    control: (base) => ({
      ...base,
      minHeight: '42px',
      borderColor: '#d1d5db',
      '&:hover': { borderColor: '#667eea' },
      boxShadow: 'none'
    }),
    option: (base, state) => ({
      ...base,
      backgroundColor: state.isFocused ? '#dbeafe' : 'white',
      color: '#1f2937',
      cursor: 'pointer'
    })
  };

  const totales = calcularTotales();

  // ========= Renderizado =========
  return (
    <div className="ordenes-pago-container">
      {/* ========= Header ========= */}
      <div className="ordenes-pago-header">
        <div className="header-title-group">
          <div className="icon-wrapper">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="3" y="6" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="2"/>
              <path d="M3 10H21" stroke="currentColor" strokeWidth="2"/>
              <circle cx="7" cy="14" r="1" fill="currentColor"/>
              <path d="M10 14H17" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <h1>Órdenes de Pago</h1>
        </div>
        <div className="header-actions">
          <button className="btn-secondary" onClick={handleVerHistorial}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
              <path d="M12 6V12L16 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            Historial
          </button>
        </div>
      </div>

      {/* ========= Mensajes ========= */}
      {mensaje && (
        <div className={`mensaje mensaje-${mensaje.tipo}`}>
          {mensaje.texto}
          <button className="btn-close-mensaje" onClick={() => setMensaje(null)}>×</button>
        </div>
      )}

      {/* ========= Selección de Proveedor ========= */}
      <div className="ordenes-section card-elevated">
        <div className="section-header">
          <svg className="section-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" strokeWidth="2"/>
            <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2"/>
          </svg>
          <h2>Seleccionar Proveedor</h2>
        </div>
        <div className="form-grid-single">
          <div className="form-group">
            <label>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2"/>
                <path d="M21 21L16.65 16.65" stroke="currentColor" strokeWidth="2"/>
              </svg>
              Proveedor
            </label>
            <AsyncSelect
              value={proveedor}
              onChange={handleProveedorChange}
              loadOptions={loadProveedores}
              placeholder="Buscar proveedor..."
              isClearable
              isSearchable
              styles={customSelectStyles}
              noOptionsMessage={() => "Escriba para buscar..."}
              defaultOptions
            />
          </div>
        </div>

        {proveedorData && (
          <div className="proveedor-info">
            <div className="info-row">
              <span className="info-label">RUT:</span>
              <span>{proveedorData.rut}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Banco:</span>
              <span>{proveedorData.banco || 'N/A'}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Cuenta:</span>
              <span>{proveedorData.cuenta || 'N/A'}</span>
            </div>
          </div>
        )}
      </div>

      {/* ========= Documentos Pendientes ========= */}
      {documentos.length > 0 && (
        <div className="ordenes-section card-elevated">
          <div className="section-header">
            <svg className="section-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" strokeWidth="2"/>
              <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2"/>
            </svg>
            <h2>Documentos Pendientes</h2>
            <span className="badge-count">{documentos.length}</span>
          </div>

          <div className="tabla-documentos">
            <div className="tabla-header-docs">
              <div>DOCUMENTO</div>
              <div>ORDEN COMPRA</div>
              <div>TOTAL NETO</div>
              <div>ACCIONES</div>
            </div>

            {documentos.map((doc, idx) => (
              <div key={idx} className="tabla-row-docs">
                <div className="col-doc">
                  {doc.documento === 'SIN_DOCUMENTO' ? (
                    <span className="badge-sin-doc">Sin documento</span>
                  ) : (
                    <span className="badge-doc">{doc.documento}</span>
                  )}
                </div>
                <div className="col-oc">
                  <span className="badge-oc">{doc.orden_compra}</span>
                </div>
                <div className="col-total">
                  ${doc.total_neto.toLocaleString('es-CL')}
                </div>
                <div className="col-acciones-docs">
                  <button
                    className="btn-seleccionar"
                    onClick={() => handleSeleccionarDocumento(doc.documento, doc.orden_compra)}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                    Seleccionar
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========= Líneas Seleccionadas ========= */}
      {lineasSeleccionadas.length > 0 && (
        <>
          <div className="ordenes-section card-elevated">
            <div className="section-header">
              <svg className="section-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
                <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
                <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
                <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
              </svg>
              <h2>Detalle de Material Seleccionado</h2>
            </div>

            <div className="tabla-lineas">
              <div className="tabla-header-lineas">
                <div>DESCRIPCIÓN</div>
                <div>CANTIDAD</div>
                <div>NETO UNIT.</div>
                <div>TOTAL</div>
                <div>OC</div>
                <div>DOC.</div>
                <div>ACCIONES</div>
              </div>

              {lineasSeleccionadas.map((linea) => (
                <div key={linea.ingreso_id} className="tabla-row-lineas">
                  <div className="col-desc">{linea.descripcion}</div>
                  <div className="col-cant">
                    <span className="badge-numero">{linea.cantidad}</span>
                  </div>
                  <div className="col-precio">${linea.neto_unitario.toLocaleString('es-CL')}</div>
                  <div className="col-precio">${linea.neto_total.toLocaleString('es-CL')}</div>
                  <div className="col-oc">
                    <span className="badge-oc">{linea.orden_compra}</span>
                  </div>
                  <div className="col-doc">
                    {linea.documento === 'SIN_DOCUMENTO' ? (
                      <span className="badge-sin-doc">Sin doc</span>
                    ) : (
                      <span className="badge-doc">{linea.documento}</span>
                    )}
                  </div>
                  <div className="col-acciones-lineas">
                    <button
                      className="btn-eliminar"
                      onClick={() => eliminarLinea(linea.ingreso_id)}
                      title="Eliminar"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M3 6H5H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                        <path d="M19 6V20C19 21 18 22 17 22H7C6 22 5 21 5 20V6" stroke="currentColor" strokeWidth="2"/>
                        <path d="M8 6V4C8 3 9 2 10 2H14C15 2 16 3 16 4V6" stroke="currentColor" strokeWidth="2"/>
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Totales */}
            <div className="totales-container">
              <div className="total-row">
                <span className="total-label">Total Neto:</span>
                <span className="total-value">${totales.neto.toLocaleString('es-CL')}</span>
              </div>
              <div className="total-row">
                <span className="total-label">IVA (19%):</span>
                <span className="total-value">${totales.iva.toLocaleString('es-CL')}</span>
              </div>
              <div className="total-row total-final">
                <span className="total-label">Total a Pagar:</span>
                <span className="total-value">${totales.total.toLocaleString('es-CL')}</span>
              </div>
            </div>
          </div>

          {/* ========= Datos de la Orden ========= */}
          <div className="ordenes-section card-elevated">
            <div className="section-header">
              <svg className="section-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 5H7C5.89543 5 5 5.89543 5 7V19C5 20.1046 5.89543 21 7 21H17C18.1046 21 19 20.1046 19 19V7C19 5.89543 18.1046 5 17 5H15" stroke="currentColor" strokeWidth="2"/>
                <rect x="9" y="3" width="6" height="4" rx="1" stroke="currentColor" strokeWidth="2"/>
              </svg>
              <h2>Datos de la Orden de Pago</h2>
            </div>

            <div className="form-grid-orden">
              <div className="form-group">
                <label>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Nº Orden de Pago
                </label>
                <input type="text" value={numeroOP} readOnly className="input-readonly" />
              </div>

              <div className="form-group">
                <label>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="12" cy="8" r="3" stroke="currentColor" strokeWidth="2"/>
                    <path d="M4 20C4 16.6863 6.68629 14 10 14H14C17.3137 14 20 16.6863 20 20" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Autoriza
                </label>
                <AsyncSelect
                  value={autoriza}
                  onChange={setAutoriza}
                  loadOptions={loadTrabajadores}
                  placeholder="Seleccionar quien autoriza..."
                  isClearable
                  isSearchable
                  styles={customSelectStyles}
                  noOptionsMessage={() => "Escriba para buscar..."}
                  defaultOptions
                />
              </div>

              <div className="form-group">
                <label>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
                    <line x1="16" y1="2" x2="16" y2="6" stroke="currentColor" strokeWidth="2"/>
                    <line x1="8" y1="2" x2="8" y2="6" stroke="currentColor" strokeWidth="2"/>
                    <line x1="3" y1="10" x2="21" y2="10" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Fecha Factura
                </label>
                <input
                  type="date"
                  value={fechaFactura}
                  onChange={(e) => setFechaFactura(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
                    <line x1="16" y1="2" x2="16" y2="6" stroke="currentColor" strokeWidth="2"/>
                    <line x1="8" y1="2" x2="8" y2="6" stroke="currentColor" strokeWidth="2"/>
                    <line x1="3" y1="10" x2="21" y2="10" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Vencimiento
                </label>
                <input
                  type="date"
                  value={vencimiento}
                  onChange={(e) => setVencimiento(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="2" y="5" width="20" height="14" rx="2" stroke="currentColor" strokeWidth="2"/>
                    <line x1="2" y1="10" x2="22" y2="10" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Estado de Pago
                </label>
                <input
                  type="text"
                  value={estadoPago}
                  onChange={(e) => setEstadoPago(e.target.value)}
                  placeholder="Ej: Pendiente, Pagado..."
                />
              </div>

              <div className="form-group form-group-full">
                <label>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Detalle de Compra (obligatorio)
                </label>
                <textarea
                  value={detalleCompra}
                  onChange={(e) => setDetalleCompra(e.target.value)}
                  placeholder="Describa el detalle de la compra..."
                  rows="3"
                  required
                />
              </div>
            </div>
          </div>

          {/* ========= Acciones ========= */}
          <div className="acciones-footer">
            <button
              className="btn-secondary"
              onClick={handleGenerarPDF}
              disabled={!numeroOP}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" strokeWidth="2"/>
              </svg>
              Generar PDF
            </button>
            <button
              className="btn-guardar"
              onClick={handleGuardar}
              disabled={loading}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M19 21H5C3.89543 21 3 20.1046 3 19V5C3 3.89543 3.89543 3 5 3H16L21 8V19C21 20.1046 20.1046 21 19 21Z" stroke="currentColor" strokeWidth="2"/>
                <path d="M7 3V8H15" stroke="currentColor" strokeWidth="2"/>
                <rect x="9" y="13" width="6" height="8" stroke="currentColor" strokeWidth="2"/>
              </svg>
              {loading ? 'Guardando...' : `Crear Orden de Pago #${numeroOP}`}
            </button>
          </div>
        </>
      )}

      {/* ========= Modal Historial ========= */}
      {mostrarHistorial && (
        <div className="modal-overlay" onClick={() => setMostrarHistorial(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Historial de Órdenes de Pago</h3>
              <button className="btn-close-modal" onClick={() => setMostrarHistorial(false)}>×</button>
            </div>
            <div className="modal-body">
              {historial.length === 0 ? (
                <p className="text-center">No hay órdenes registradas</p>
              ) : (
                <div className="tabla-historial">
                  <div className="tabla-header-historial">
                    <div>Nº ORDEN</div>
                    <div>PROVEEDOR</div>
                    <div>FECHA</div>
                    <div>TOTAL</div>
                    <div>ESTADO</div>
                    <div>ACCIONES</div>
                  </div>
                  {historial.map((orden) => (
                    <div key={orden.orden_numero} className="tabla-row-historial">
                      <div className="col-orden">#{orden.orden_numero}</div>
                      <div className="col-prov">{orden.proveedor}</div>
                      <div className="col-fecha">{new Date(orden.fecha).toLocaleDateString('es-CL')}</div>
                      <div className="col-total">${orden.total.toLocaleString('es-CL')}</div>
                      <div className="col-estado">
                        <span className={`badge-estado ${orden.estado_documento}`}>
                          {orden.estado_documento}
                        </span>
                      </div>
                      <div className="col-acciones-historial">
                        <button
                          className="btn-copiar"
                          onClick={() => handleCopiarOrden(orden.orden_numero)}
                          title="Copiar orden"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="2"/>
                            <path d="M5 15H4C2.89543 15 2 14.1046 2 13V4C2 2.89543 2.89543 2 4 2H13C14.1046 2 15 2.89543 15 4V5" stroke="currentColor" strokeWidth="2"/>
                          </svg>
                          Copiar
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========= Loading Overlay ========= */}
      {loading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p>Procesando...</p>
        </div>
      )}
    </div>
  );
}

export default OrdenesPago;