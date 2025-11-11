import { useState, useEffect } from 'react';
import Select from 'react-select';
import AsyncSelect from 'react-select/async';
import './OrdenesPago.css';
import { getAuthToken } from '../utils/auth';

function OrdenesPago() {
  // ========= Estados principales =========
  const [numeroOP, setNumeroOP] = useState('');
  const [proveedor, setProveedor] = useState(null);
  const [proveedorData, setProveedorData] = useState(null);
  const [documentos, setDocumentos] = useState([]);
  const [documentoSeleccionado, setDocumentoSeleccionado] = useState(null);
  const [lineasSeleccionadas, setLineasSeleccionadas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mensaje, setMensaje] = useState(null);

  // ========= Estados del formulario =========
  const [autoriza, setAutoriza] = useState(null);
  const [correoAutoriza, setCorreoAutoriza] = useState('');
  const [fechaFactura, setFechaFactura] = useState('');
  const [vencimiento, setVencimiento] = useState('');
  const [estadoPago, setEstadoPago] = useState('');
  const [detalleCompra, setDetalleCompra] = useState('');
  const [documentoAdjunto1, setDocumentoAdjunto1] = useState(null);
  const [documentoAdjunto2, setDocumentoAdjunto2] = useState(null);

  // ========= Estados de modales =========
  const [mostrarHistorial, setMostrarHistorial] = useState(false);
  const [historial, setHistorial] = useState([]);
  const [historialFilter, setHistorialFilter] = useState('');

  // ========= Estado para generar PDF de orden copiada =========
  const [numeroOrdenOriginal, setNumeroOrdenOriginal] = useState(null);
  const [modoConsulta, setModoConsulta] = useState(false); // true = solo consulta, false = creación
  const [pdfDownloaded, setPdfDownloaded] = useState(false); // true si se descargó el PDF para los datos actuales

  // ========= Cargar próximo número al montar =========
  useEffect(() => {
    fetchProximoNumero();
  }, []);

  const fetchProximoNumero = async () => {
    try {
      const token = getAuthToken();
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
    setDocumentoSeleccionado(null);
    setNumeroOrdenOriginal(null); // Limpiar número de orden original al cambiar proveedor
    setModoConsulta(false); // Desactivar modo consulta

    if (!selectedOption) {
      setProveedorData(null);
      return;
    }

    setLoading(true);
    try {
      const token = getAuthToken();
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
          setPdfDownloaded(false);
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
    setDocumentoSeleccionado({ documento, oc });

    try {
      const token = getAuthToken();
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
          setLineasSeleccionadas(data.data);
          setMensaje({ tipo: 'success', texto: `${data.data.length} línea(s) cargadas` });
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
    // Calcular neto e IVA por línea según fac_sin_iva
    let neto = 0;
    let iva = 0;
    
    lineasSeleccionadas.forEach(linea => {
      const netoLinea = linea.neto_total || 0;
      neto += netoLinea;
      
      // Solo agregar IVA si la OC NO es sin IVA (fac_sin_iva == 0 o false)
      if (!linea.fac_sin_iva) {
        iva += netoLinea * 0.19;
      }
    });
    
    const total = neto + iva;
    return { neto, iva, total };
  };

  // ========= Guardar orden de pago =========
  const handleGuardar = async () => {
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
      const token = getAuthToken();

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
        setLineasSeleccionadas([]);
        setDetalleCompra('');
        setEstadoPago('');
        setNumeroOrdenOriginal(null); // Limpiar número de orden original
        setModoConsulta(false); // Desactivar modo consulta
        setPdfDownloaded(false);
        await fetchProximoNumero();

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
    // Si hay una orden original copiada (modo consulta), usar la ruta por número.
    // En modo creación, enviar los datos actuales al endpoint que genera PDF desde el form
    if (modoConsulta && numeroOrdenOriginal) {
      try {
        const token = getAuthToken();
        const response = await fetch(`/api/ordenes_pago/pdf/${numeroOrdenOriginal}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `orden_pago_${numeroOrdenOriginal}.pdf`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
          setMensaje({ tipo: 'success', texto: `PDF de orden ${numeroOrdenOriginal} generado correctamente` });
          setPdfDownloaded(true);
        } else {
          const data = await response.json();
          setMensaje({ tipo: 'error', texto: data.error || data.message || 'Error al generar PDF' });
        }
      } catch (error) {
        console.error('Error al generar PDF:', error);
        setMensaje({ tipo: 'error', texto: 'Error al generar PDF' });
      }
      return;
    }

    // Modo creación: generar PDF desde los datos del formulario (sin guardar en BD)
    // Validaciones mínimas
    if (!proveedor) {
      setMensaje({ tipo: 'error', texto: 'Debe seleccionar un proveedor antes de generar PDF' });
      return;
    }

    if (lineasSeleccionadas.length === 0) {
      setMensaje({ tipo: 'error', texto: 'Debe seleccionar al menos una línea antes de generar PDF' });
      return;
    }

    try {
      const token = getAuthToken();

      const payload = {
        'orden_compra[]': lineasSeleccionadas.map(l => l.orden_compra || ''),
        'guia_recepcion[]': lineasSeleccionadas.map(l => l.doc_recep || l.documento || ''),
        'descripcion[]': lineasSeleccionadas.map(l => l.descripcion || ''),
        next_num: numeroOP,
        nombre_proveedor: proveedor?.label || '',
        detalle_compra: detalleCompra,
        vencimiento: vencimiento,
        fecha_factura: fechaFactura,
        autoriza_input: autoriza?.label || '',
        autoriza_email: correoAutoriza || '',
        total_neto: totales.neto,
        total_iva: totales.iva,
        total_pagar: totales.total
      };

      const response = await fetch('/api/ordenes_pago/generar-pdf', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
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
        setMensaje({ tipo: 'success', texto: `PDF de orden ${numeroOP} generado correctamente` });
        setPdfDownloaded(true);
      } else {
        const data = await response.json();
        setMensaje({ tipo: 'error', texto: data.error || data.message || 'Error al generar PDF' });
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
      const token = getAuthToken();
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
          setHistorialFilter('');
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
      const token = getAuthToken();
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

          // Guardar el número de orden original para generar PDF
          setNumeroOrdenOriginal(ordenNumero);
          setModoConsulta(true); // Activar modo solo consulta
          setPdfDownloaded(false);
          
          setNumeroOP(copiaData.next_num);
          setProveedor({ value: copiaData.proveedor_id, label: copiaData.proveedor_nombre });
          setAutoriza({ value: copiaData.autoriza_id, label: copiaData.autoriza_nombre });
          setFechaFactura(copiaData.fecha_factura);
          setVencimiento(copiaData.vencimiento);
          setEstadoPago(copiaData.estado_pago);
          setDetalleCompra(copiaData.detalle_compra);
          setLineasSeleccionadas(copiaData.lineas);

          setMostrarHistorial(false);
          setMensaje({ tipo: 'success', texto: `Orden ${ordenNumero} cargada en modo consulta. Puede generar PDF.` });
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
      const token = getAuthToken();
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
      const token = getAuthToken();
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

  // ========= Manejar cambio de autorizador y cargar correo =========
  const handleAutorizaChange = async (selectedOption) => {
    setAutoriza(selectedOption);
    
    if (selectedOption) {
      // Buscar correo del trabajador
      try {
        const token = getAuthToken();
        // ⚠️ Asumimos que este endpoint existe (no estaba en el .py)
        // Si no existe, necesitamos crearlo o buscar el correo de otra forma
        const response = await fetch(`/api/trabajadores/${selectedOption.value}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();
          // Soportar ambos formatos de respuesta: { correo: 'x' } o { success: true, data: { correo: 'x' } }
          const correo = data?.correo || (data?.data && data.data.correo) || '';
          setCorreoAutoriza(correo);
        }
      } catch (error) {
        console.error('Error al cargar correo:', error);
        setCorreoAutoriza('');
      }
    } else {
      setCorreoAutoriza('');
    }
  };

  // ========= Manejar archivos adjuntos =========
  const handleArchivoChange = (fileNumber, event) => {
    const file = event.target.files[0];
    if (fileNumber === 1) {
      setDocumentoAdjunto1(file);
    } else {
      setDocumentoAdjunto2(file);
    }
  };

  const customSelectStyles = {
    control: (base) => ({
      ...base,
      minHeight: '42px',
      borderColor: '#d1d5db',
      '&:hover': { borderColor: '#3b82f6' }
    }),
    // Opciones y textos en azul oscuro para mejor contraste
    option: (base, state) => ({
      ...base,
      color: '#1e3a8a', // azul oscuro
      backgroundColor: state.isFocused ? '#eef2ff' : state.isSelected ? '#e0e7ff' : 'white'
    }),
    singleValue: (base) => ({
      ...base,
      color: '#1e3a8a'
    }),
    placeholder: (base) => ({
      ...base,
      color: '#1e3a8a',
      opacity: 0.9
    }),
    menu: (base) => ({
      ...base,
      zIndex: 9999
    }),
    menuList: (base) => ({
      ...base,
      padding: 0,
      color: '#1e3a8a'
    })
  };

  const totales = calcularTotales();

  // Filtrar historial por término (número, proveedor, fecha, total)
  const filteredHistorial = historial.filter((orden) => {
    const q = historialFilter.trim().toLowerCase();
    if (!q) return true;
    const numero = String(orden.orden_numero || '').toLowerCase();
    const proveedorText = String(orden.proveedor || '').toLowerCase();
    const fecha = String(orden.fecha || '').toLowerCase();
    const total = String(orden.total || '').toLowerCase();
    return (
      numero.includes(q) ||
      proveedorText.includes(q) ||
      fecha.includes(q) ||
      total.includes(q)
    );
  });

  // ========= Renderizado =========
  return (
    <div className="ordenes-pago-page">
      {/* Header */}
      <div className="page-header">
        <div className="header-left">
          <h1 className="page-title">Órdenes de Pago - Apps. Admis</h1>
        </div>
        <div className="header-right">
          <button className="btn-reload" onClick={handleVerHistorial} style={{ marginRight: '10px', background: '#667eea' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" strokeWidth="2"/>
            </svg>
            Ver Historial
          </button>
        </div>
      </div>

      {/* Mensajes */}
      {mensaje && (
        <div className={`alert alert-${mensaje.tipo === 'success' ? 'success' : 'danger'}`}>
          {mensaje.texto}
          <button className="alert-close" onClick={() => setMensaje(null)}>×</button>
        </div>
      )}

      {/* Banner de Modo Consulta (minimal) */}
      {modoConsulta && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '6px 10px',
          borderRadius: '10px',
          marginBottom: '12px',
          background: '#f8fafc',
          border: '1px solid #e6eef8'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#eef2ff',
              color: '#1e3a8a'
            }} aria-hidden>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M7 7h10M7 11h10M7 15h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '13px', color: '#0f172a', fontWeight: 600 }}>Orden #{numeroOrdenOriginal}</span>
              <small style={{ color: '#6b7280', fontSize: '12px' }}>Solo consulta — puede generar PDF</small>
            </div>
          </div>

          {/* Se eliminó el botón 'Nueva' para mantener el banner minimalista */}
        </div>
      )}

      <div className="content-wrapper">
        {/* Selector de Proveedor */}
        <div className="section-card">
          <div className="card-header-icon">
            <div className="icon-circle blue">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="2"/>
                <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2"/>
              </svg>
            </div>
            <div>
              <h2 className="card-title">Proveedor:</h2>
            </div>
          </div>

          <div className="form-row-single">
            <AsyncSelect
              value={proveedor}
              onChange={handleProveedorChange}
              loadOptions={loadProveedores}
              placeholder={modoConsulta ? (proveedor?.label || 'CBASAURE SPA') : 'Busque proveedor'}
              isClearable
              isSearchable
              isDisabled={modoConsulta} // Deshabilitar en modo consulta
              styles={customSelectStyles}
              noOptionsMessage={() => "Escriba para buscar..."}
              defaultOptions
              className="select-full-width"
            />
          </div>
        </div>

        {/* Datos de la Orden */}
        {proveedor && (
          <div className="section-card">
            <div className="card-header-icon">
              <div className="icon-circle blue">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="2"/>
                  <polyline points="14 2 14 8 20 8" stroke="currentColor" strokeWidth="2"/>
                </svg>
              </div>
              <div>
                <h2 className="card-title">Datos de la Orden de Pago</h2>
                <p className="card-subtitle">Información general de la orden</p>
              </div>
            </div>

            <div className="form-grid-three">
              <div className="form-group">
                <label className="form-label">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="8" r="3" stroke="currentColor" strokeWidth="2"/>
                    <path d="M4 20a8 8 0 0 1 16 0" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Autoriza:
                </label>
                <AsyncSelect
                  value={autoriza}
                  onChange={handleAutorizaChange} // ✅ CAMBIO: Usar handler
                  loadOptions={loadTrabajadores}
                  placeholder="Selecciona quien autoriza"
                  isClearable
                  isDisabled={modoConsulta} // Deshabilitar en modo consulta
                  styles={customSelectStyles}
                  noOptionsMessage={() => "Escriba para buscar..."}
                  defaultOptions
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Correo:
                </label>
                <input
                  type="text"
                  className="form-control"
                  value={correoAutoriza} // ✅ CAMBIO: Usar estado correoAutoriza
                  placeholder="Se completa automáticamente"
                  readOnly
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  # Número de Orden:
                </label>
                <input
                  type="text"
                  className="form-control readonly-field"
                  value={numeroOP}
                  readOnly
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Fecha de factura:
                </label>
                <input
                  type="date"
                  className="form-control"
                  value={fechaFactura}
                  onChange={(e) => setFechaFactura(e.target.value)}
                  disabled={modoConsulta}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Vencimiento factura:
                </label>
                <input
                  type="date"
                  className="form-control"
                  value={vencimiento}
                  onChange={(e) => setVencimiento(e.target.value)}
                  disabled={modoConsulta}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <rect x="2" y="5" width="20" height="14" rx="2" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Estado de pago:
                </label>
                <input
                  type="text"
                  className="form-control"
                  value={estadoPago}
                  onChange={(e) => setEstadoPago(e.target.value)}
                  placeholder="Ej: Pendiente, Pagado..."
                />
              </div>
            </div>

            {/* ✅ CAMBIO: Detalle de compra más ancho */}
            <div className="form-row-wide">
              <div className="form-group-detalle">
                <label className="form-label">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Detalle de Compra:
                </label>
                <textarea
                  className="form-control textarea-detalle"
                  value={detalleCompra}
                  onChange={(e) => setDetalleCompra(e.target.value)}
                  disabled={modoConsulta}
                  placeholder="Escribe aquí el detalle de la compra..."
                  rows="4"
                />
              </div>
            </div>

            {/* ✅ AÑADIDO: Sección para adjuntar archivos */}
            <div className="attachments-row">
              <div className="attachment-group">
                <label className="form-label">Adjuntar Documento 1 (Opcional):</label>
                <div className="file-input-wrapper">
                  <input 
                    type="file" 
                    id="doc1" 
                    className="file-input" 
                    onChange={(e) => handleArchivoChange(1, e)} 
                  />
                  <label htmlFor="doc1" className="file-label">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke="currentColor" strokeWidth="2"/>
                      <polyline points="17 8 12 3 7 8" stroke="currentColor" strokeWidth="2"/>
                      <line x1="12" y1="3" x2="12" y2="15" stroke="currentColor" strokeWidth="2"/>
                    </svg>
                    {documentoAdjunto1 ? documentoAdjunto1.name : "Seleccionar archivo..."}
                  </label>
                </div>
              </div>
              
              <div className="attachment-group">
                <label className="form-label">Adjuntar Documento 2 (Opcional):</label>
                <div className="file-input-wrapper">
                  <input 
                    type="file" 
                    id="doc2" 
                    className="file-input" 
                    onChange={(e) => handleArchivoChange(2, e)} 
                  />
                  <label htmlFor="doc2" className="file-label">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke="currentColor" strokeWidth="2"/>
                      <polyline points="17 8 12 3 7 8" stroke="currentColor" strokeWidth="2"/>
                      <line x1="12" y1="3" x2="12" y2="15" stroke="currentColor" strokeWidth="2"/>
                    </svg>
                    {documentoAdjunto2 ? documentoAdjunto2.name : "Seleccionar archivo..."}
                  </label>
                </div>
              </div>
            </div>

            {/* ✅ CAMBIO: Botón de correo alineado y con estilo */}
            <div className="button-row-right">
              <button className="btn-enviar-correo" disabled>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" stroke="currentColor" strokeWidth="2"/>
                  <polyline points="22,6 12,13 2,6" stroke="currentColor" strokeWidth="2"/>
                </svg>
                Enviar correo
              </button>
            </div>
          </div>
        )}

        {/* Documentos Pendientes */}
        {documentos.length > 0 && (
          <div className="section-card">
            <div className="card-header-icon">
              <div className="icon-circle blue">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="2"/>
                </svg>
              </div>
              <div>
                <h2 className="card-title">Documentos Pendientes</h2>
                <p className="card-subtitle">Selecciona los documentos para procesar</p>
                <span className="badge-count">{documentos.length} documento(s)</span>
              </div>
            </div>

            <div className="table-responsive">
              <table className="table-docs">
                <thead>
                  <tr>
                    <th>Acción</th>
                    <th>Documento</th>
                    <th>Orden de Compra</th>
                    <th>$ Total Neto</th>
                  </tr>
                </thead>
                <tbody>
                  {documentos.map((doc, idx) => (
                    <tr key={idx} className={documentoSeleccionado?.oc === doc.orden_compra ? 'selected-row' : ''}>
                      <td>
                        <button
                          className={`btn-select ${documentoSeleccionado?.oc === doc.orden_compra ? 'selected' : ''}`}
                          onClick={() => handleSeleccionarDocumento(doc.documento, doc.orden_compra)}
                        >
                          {documentoSeleccionado?.oc === doc.orden_compra ? (
                            <>
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                                <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2"/>
                              </svg>
                              Seleccionado
                            </>
                          ) : (
                            'Seleccionar'
                          )}
                        </button>
                      </td>
                      <td>
                        {doc.documento === 'SIN_DOCUMENTO' ? (
                          <span className="badge badge-sin-doc">Sin documento</span>
                        ) : (
                          <span className="badge badge-doc">{doc.documento}</span>
                        )}
                      </td>
                      <td>
                        <span className="badge badge-info">{doc.orden_compra}</span>
                      </td>
                      <td className="text-money">${doc.total_neto.toLocaleString('es-CL')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Detalle de Material Seleccionado */}
        {lineasSeleccionadas.length > 0 && (
          <>
            <div className="section-card">
              <div className="card-header-icon">
                <div className="icon-circle green">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path d="M3 3h18v18H3z" stroke="currentColor" strokeWidth="2"/>
                    <path d="M9 9h6v6H9z" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                </div>
                <div>
                  <h2 className="card-title">Detalle de Material Seleccionado</h2>
                  <p className="card-subtitle">Materiales incluidos en la orden de pago</p>
                </div>
              </div>

              <div className="table-responsive">
                <table className="table-lineas">
                  <thead>
                    <tr>
                      <th>Descripción</th>
                      <th className="text-center">Cant.</th>
                      <th className="text-right">$ Precio Unit.</th>
                      <th className="text-right">Total Neto</th>
                      <th className="text-center">OC</th>
                      <th className="text-center">Doc.</th>
                      <th className="text-center">Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lineasSeleccionadas.map((linea) => (
                      <tr key={linea.ingreso_id}>
                        <td className="desc-col">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="icon-inline">
                            <circle cx="12" cy="12" r="10" stroke="#3b82f6" strokeWidth="2"/>
                          </svg>
                          {linea.descripcion}
                        </td>
                        <td className="text-center">
                          <span className="badge badge-number">{linea.cantidad}</span>
                        </td>
                        <td className="text-right text-money">${linea.neto_unitario.toLocaleString('es-CL')}</td>
                        <td className="text-right text-money">${linea.neto_total.toLocaleString('es-CL')}</td>
                        <td className="text-center">
                          <span className="badge badge-info">{linea.orden_compra}</span>
                        </td>
                        <td className="text-center">
                          {linea.documento === 'SIN_DOCUMENTO' ? (
                            <span className="badge badge-sin-doc">Sin doc</span>
                          ) : (
                            <span className="badge badge-doc">{linea.documento}</span>
                          )}
                        </td>
                        <td className="text-center">
                          {!modoConsulta && (
                            <button
                              className="btn-icon btn-delete"
                              onClick={() => eliminarLinea(linea.ingreso_id)}
                              title="Eliminar"
                            >
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                                <path d="M3 6h18M8 6V4h8v2m-4 4v8m-4-4v4m8-4v4" stroke="currentColor" strokeWidth="2"/>
                              </svg>
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="info-notice">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                  <path d="M12 16v-4m0-4h.01" stroke="currentColor" strokeWidth="2"/>
                </svg>
                Los totales calculan IVA (19%) según la configuración de cada orden de compra.
              </div>

              <div className="totales-box">
                <div className="total-row">
                  <span className="total-label">Total Neto:</span>
                  <span className="total-value">${totales.neto.toLocaleString('es-CL')}</span>
                </div>
                <div className="total-row">
                  <span className="total-label">IVA (19%):</span>
                  <span className="total-value">${totales.iva.toLocaleString('es-CL')}</span>
                </div>
                <div className="total-row total-final-row">
                  <span className="total-label-final">Total a Pagar:</span>
                  <span className="total-value-final">${totales.total.toLocaleString('es-CL')}</span>
                </div>
              </div>
            </div>

            {/* Botones de Acción */}
            <div className="actions-footer">
              <button className="btn-action btn-pdf" onClick={handleGenerarPDF}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="2"/>
                </svg>
                {modoConsulta ? `Generar PDF de Orden #${numeroOrdenOriginal}` : 'Generar PDF'}
              </button>
              
              {modoConsulta ? (
                <button 
                  className="btn-action btn-secondary" 
                  disabled
                  style={{ 
                    background: '#6c757d', 
                    cursor: 'not-allowed',
                    opacity: 0.6
                  }}
                  title="Esta orden ya existe. Solo puede consultar y generar PDF."
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path d="M12 15v2m0 0v2m0-2h2m-2 0h-2m9-7a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Orden #{numeroOrdenOriginal} (Solo Consulta)
                </button>
              ) : (
                <button className="btn-action btn-primary" onClick={handleGuardar} disabled={loading || !pdfDownloaded}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path d="M12 5v14m7-7H5" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  {loading ? 'Creando...' : `Crear Orden de Pago #${numeroOP}`}
                </button>
              )}
```
            </div>
          </>
        )}
      </div>

      {/* Modal de Historial */}
      {mostrarHistorial && (
        <div className="modal-overlay" onClick={() => setMostrarHistorial(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '900px' }}>
            <div className="modal-header">
              <h2>Historial de Órdenes de Pago</h2>
              <button className="modal-close" onClick={() => setMostrarHistorial(false)}>×</button>
            </div>
            <div className="modal-body">
              <div style={{ marginBottom: '12px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Buscar por número, proveedor, fecha o total..."
                  value={historialFilter}
                  onChange={(e) => setHistorialFilter(e.target.value)}
                  style={{ flex: 1 }}
                />
                <button
                  onClick={() => setHistorialFilter('')}
                  title="Limpiar búsqueda"
                  aria-label="Limpiar búsqueda"
                  style={{
                    width: '36px',
                    height: '36px',
                    padding: 0,
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: '6px',
                    border: '1px solid #e5e7eb',
                    background: 'white',
                    color: '#374151',
                    cursor: 'pointer'
                  }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
                    <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              </div>

              {filteredHistorial.length === 0 ? (
                <p>No hay órdenes que coincidan</p>
              ) : (
                <div className="table-responsive">
                  <table className="table-docs">
                    <thead>
                      <tr>
                        <th>Orden #</th>
                        <th>Proveedor</th>
                        <th>Fecha</th>
                        <th>Estado Pago</th>
                        <th>Total</th>
                        <th>Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredHistorial.map((orden) => (
                        <tr key={orden.orden_numero}>
                          <td><strong>{orden.orden_numero}</strong></td>
                          <td>{orden.proveedor}</td>
                          <td>{orden.fecha}</td>
                          <td>
                            <span className={`badge ${orden.estado_pago === 'PAGADO' ? 'badge-success' : 'badge-warning'}`}>
                              {orden.estado_pago || 'PENDIENTE'}
                            </span>
                          </td>
                          <td className="text-money">${orden.total.toLocaleString('es-CL')}</td>
                          <td>
                            <button
                              className="btn-action btn-primary"
                              onClick={() => handleCopiarOrden(orden.orden_numero)}
                              style={{ fontSize: '14px', padding: '6px 12px' }}
                            >
                              Cargar para ver PDF
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
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