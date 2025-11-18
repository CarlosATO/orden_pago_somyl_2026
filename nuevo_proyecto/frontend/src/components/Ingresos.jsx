import { useState, useEffect } from 'react';
import Select from 'react-select';
import './Ingresos.css';
import { getAuthToken } from '../utils/auth';

function Ingresos() {
  // ========= Estados principales =========
  const [ocSeleccionada, setOcSeleccionada] = useState(null);
  const [ocList, setOcList] = useState([]);
  const [header, setHeader] = useState(null);
  const [lineas, setLineas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mensaje, setMensaje] = useState(null);
  const [estadoRecepcion, setEstadoRecepcion] = useState('pendiente'); // 'pendiente', 'parcial', 'completo'

  // ========= Estados del formulario de ingreso =========
  const [factura, setFactura] = useState('');
  const [guiaRecepcion, setGuiaRecepcion] = useState('');
  const [facPendiente, setFacPendiente] = useState(false);
  const [cantidadesRecibidas, setCantidadesRecibidas] = useState({});

  // ========= Cargar OCs disponibles al montar =========
  useEffect(() => {
    fetchOCsDisponibles();
  }, []);

  // ========= Cargar datos cuando cambia la OC =========
  useEffect(() => {
    if (ocSeleccionada) {
      fetchDatosOC(ocSeleccionada.value);
    }
  }, [ocSeleccionada]);

  // ========= Funciones de API =========
  const fetchOCsDisponibles = async () => {
    try {
      const token = getAuthToken();
      if (!token) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
        return;
      }

      const response = await fetch('/api/ingresos/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          const ocOptions = data.data.oc_list.map(oc => ({ value: oc, label: String(oc) }));
          setOcList(ocOptions);

          // Auto-seleccionar la OC más reciente
          if (data.data.oc_seleccionada) {
            const selected = ocOptions.find(opt => opt.value === data.data.oc_seleccionada);
            if (selected) {
              setOcSeleccionada(selected);
            }
          }
        }
      } else if (response.status === 401) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada. Por favor inicie sesión nuevamente.' });
      }
    } catch (error) {
      console.error('Error al cargar OCs:', error);
      setMensaje({ tipo: 'error', texto: 'Error al cargar órdenes de compra' });
    }
  };

  const fetchDatosOC = async (ocNumero) => {
    setLoading(true);
    try {
      const token = getAuthToken();
      if (!token) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
        return;
      }

      const response = await fetch(`/api/ingresos/?oc=${ocNumero}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          if (data.data.oc_no_encontrada) {
            setMensaje({ tipo: 'error', texto: `OC ${ocNumero} no encontrada` });
            setHeader(null);
            setLineas([]);
          } else {
            setHeader(data.data.header);
            setLineas(data.data.lineas);
            // Inicializar cantidades recibidas en 0
            const initialCantidades = {};
            data.data.lineas.forEach((linea, idx) => {
              initialCantidades[idx] = 0;
            });
            setCantidadesRecibidas(initialCantidades);
            
            // Calcular estado de recepción
            calcularEstadoRecepcion(data.data.lineas);
            
            setMensaje(null);
          }
        }
      } else if (response.status === 401) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
      }
    } catch (error) {
      console.error('Error al cargar datos de OC:', error);
      setMensaje({ tipo: 'error', texto: 'Error al cargar datos de la OC' });
    } finally {
      setLoading(false);
    }
  };

  // ========= Calcular estado de recepción =========
  const calcularEstadoRecepcion = (lineasData) => {
    const totalSolicitado = lineasData.reduce((sum, linea) => sum + linea.solicitado, 0);
    const totalRecibido = lineasData.reduce((sum, linea) => sum + linea.total_recibido, 0);
    
    if (totalRecibido === 0) {
      setEstadoRecepcion('pendiente');
    } else if (totalRecibido >= totalSolicitado) {
      setEstadoRecepcion('completo');
    } else {
      setEstadoRecepcion('parcial');
    }
  };

  const handleGuardarIngreso = async () => {
    // Validaciones
    if (!ocSeleccionada) {
      setMensaje({ tipo: 'error', texto: 'Debe seleccionar una OC' });
      return;
    }

    // Validar que haya al menos una cantidad recibida > 0
    const hayIngresos = Object.values(cantidadesRecibidas).some(cant => cant > 0);
    if (!hayIngresos) {
      setMensaje({ tipo: 'error', texto: 'Debe ingresar al menos una cantidad recibida' });
      return;
    }

    // Confirmar si no hay factura
    if (!factura && !facPendiente && !window.confirm('⚠️ No ha ingresado número de factura. ¿Desea continuar?')) {
      return;
    }

    setLoading(true);
    try {
      const token = getAuthToken();
      if (!token) {
        setMensaje({ tipo: 'error', texto: 'Sesión expirada' });
        return;
      }

      // Preparar líneas con cantidades recibidas
      const lineasConIngresos = lineas
        .map((linea, idx) => ({
          descripcion: linea.descripcion,
          material_id: linea.material_id,
          recibido: cantidadesRecibidas[idx] || 0,
          neto: linea.neto,
          art_corr: linea.art_corr
        }))
        .filter(linea => linea.recibido > 0);

      const payload = {
        oc: ocSeleccionada.value,
        proveedor_id: header.proveedor_id,
        factura: factura.trim(),
        guia_recepcion: guiaRecepcion.trim(),
        fac_pendiente: facPendiente,
        lineas: lineasConIngresos
      };

      console.log('📤 Enviando ingreso:', payload);

      const response = await fetch('/api/ingresos/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setMensaje({ 
          tipo: 'success', 
          texto: data.message + (data.warning ? ` ${data.warning}` : '')
        });
        
        // Limpiar formulario
        setFactura('');
        setGuiaRecepcion('');
        setFacPendiente(false);
        
        // Recargar datos de la OC
        await fetchDatosOC(ocSeleccionada.value);
      } else {
        setMensaje({ tipo: 'error', texto: data.message || 'Error al guardar ingreso' });
      }
    } catch (error) {
      console.error('Error al guardar ingreso:', error);
      setMensaje({ tipo: 'error', texto: 'Error al guardar ingreso' });
    } finally {
      setLoading(false);
    }
  };

  // ========= Manejadores de cambio =========
  const handleCantidadChange = (idx, valor) => {
    const nuevasCantidades = { ...cantidadesRecibidas };
    const valorNumerico = parseInt(valor) || 0;
    
    // Validar que no exceda el pendiente
    if (valorNumerico > lineas[idx].pendiente) {
      setMensaje({ 
        tipo: 'info', 
        texto: `La cantidad no puede exceder el pendiente (${lineas[idx].pendiente})` 
      });
      nuevasCantidades[idx] = lineas[idx].pendiente;
    } else {
      nuevasCantidades[idx] = valorNumerico;
    }
    
    setCantidadesRecibidas(nuevasCantidades);
  };

  // ========= Estilos personalizados para react-select =========
  const customSelectStyles = {
    control: (base) => ({
      ...base,
      minHeight: '38px',
      borderColor: '#d1d5db',
      '&:hover': { borderColor: '#3b82f6' },
      boxShadow: 'none'
    }),
    option: (base, state) => ({
      ...base,
      backgroundColor: state.isFocused ? '#dbeafe' : 'white',
      color: '#1f2937',
      cursor: 'pointer'
    })
  };

  // ========= Cálculos de totales =========
  const calcularTotalIngreso = () => {
    let total = 0;
    lineas.forEach((linea, idx) => {
      const cantidad = cantidadesRecibidas[idx] || 0;
      const subtotal = cantidad * linea.neto;
      total += header?.fac_sin_iva ? subtotal : subtotal * 1.19;
    });
    return total;
  };

  // ========= Renderizado =========
  return (
    <div className="ingresos-container">
      {/* ========= Header con gradiente moderno ========= */}
      <div className="ingresos-header">
        <div className="header-title-group">
          <div className="icon-wrapper">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M20 7H4C2.89543 7 2 7.89543 2 9V19C2 20.1046 2.89543 21 4 21H20C21.1046 21 22 20.1046 22 19V9C22 7.89543 21.1046 7 20 7Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M16 21V5C16 4.46957 15.7893 3.96086 15.4142 3.58579C15.0391 3.21071 14.5304 3 14 3H10C9.46957 3 8.96086 3.21071 8.58579 3.58579C8.21071 3.96086 8 4.46957 8 5V21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <h1>Registro de Ingresos</h1>
        </div>
        {header && (
          <div className={`badge-estado badge-${estadoRecepcion}`}>
            {estadoRecepcion === 'completo' && (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Recibido Completo
              </>
            )}
            {estadoRecepcion === 'parcial' && (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                  <path d="M12 6V12L16 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
                Recepción Parcial
              </>
            )}
            {estadoRecepcion === 'pendiente' && (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                  <path d="M12 8V12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  <circle cx="12" cy="16" r="1" fill="currentColor"/>
                </svg>
                Pendiente
              </>
            )}
          </div>
        )}
      </div>

      {/* ========= Mensajes ========= */}
      {mensaje && (
        <div className={`mensaje mensaje-${mensaje.tipo}`}>
          {mensaje.texto}
        </div>
      )}

      {/* ========= SECCIÓN: Selección de OC ========= */}
      <div className="ingresos-section card-elevated">
        <div className="section-header">
          <svg className="section-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2"/>
            <path d="M21 21L16.65 16.65" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          <h2>Seleccionar Orden de Compra</h2>
        </div>
        <div className="form-grid-oc">
          <div className="form-group">
            <label>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 5H7C5.89543 5 5 5.89543 5 7V19C5 20.1046 5.89543 21 7 21H17C18.1046 21 19 20.1046 19 19V7C19 5.89543 18.1046 5 17 5H15" stroke="currentColor" strokeWidth="2"/>
                <rect x="9" y="3" width="6" height="4" rx="1" stroke="currentColor" strokeWidth="2"/>
              </svg>
              Nº Orden de Compra
            </label>
            <Select
              value={ocSeleccionada}
              onChange={setOcSeleccionada}
              options={ocList}
              placeholder="Buscar o seleccionar OC..."
              isClearable
              isSearchable
              styles={customSelectStyles}
              noOptionsMessage={() => "No hay OCs disponibles"}
            />
          </div>
        </div>
      </div>

      {/* ========= SECCIÓN: Datos de la OC ========= */}
      {header && (
        <>
          <div className="ingresos-section card-elevated">
            <div className="section-header">
              <svg className="section-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 5H7C5.89543 5 5 5.89543 5 7V19C5 20.1046 5.89543 21 7 21H17C18.1046 21 19 20.1046 19 19V7C19 5.89543 18.1046 5 17 5H15" stroke="currentColor" strokeWidth="2"/>
                <rect x="9" y="3" width="6" height="4" rx="1" stroke="currentColor" strokeWidth="2"/>
                <line x1="9" y1="12" x2="15" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <line x1="9" y1="16" x2="15" y2="16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              <h2>Información de la Orden</h2>
            </div>
            <div className="info-grid-modern">
              <div className="info-card">
                <div className="info-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                </div>
                <div className="info-content">
                  <label>Proveedor</label>
                  <span>{header.proveedor_nombre}</span>
                </div>
              </div>
              <div className="info-card">
                <div className="info-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="3" y="4" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="2"/>
                    <line x1="3" y1="10" x2="21" y2="10" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                </div>
                <div className="info-content">
                  <label>RUT</label>
                  <span>{header.rut}</span>
                </div>
              </div>
              <div className="info-card">
                <div className="info-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
                    <line x1="16" y1="2" x2="16" y2="6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    <line x1="8" y1="2" x2="8" y2="6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    <line x1="3" y1="10" x2="21" y2="10" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                </div>
                <div className="info-content">
                  <label>Fecha OC</label>
                  <span>{new Date(header.fecha).toLocaleDateString('es-CL')}</span>
                </div>
              </div>
              <div className="info-card">
                <div className="info-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="12" cy="8" r="3" stroke="currentColor" strokeWidth="2"/>
                    <path d="M4 20C4 16.6863 6.68629 14 10 14H14C17.3137 14 20 16.6863 20 20" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                </div>
                <div className="info-content">
                  <label>Solicitado por</label>
                  <span>{header.solicita}</span>
                </div>
              </div>
              <div className="info-card">
                <div className="info-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M9 7H6C4.89543 7 4 7.89543 4 9V18C4 19.1046 4.89543 20 6 20H18C19.1046 20 20 19.1046 20 18V9C20 7.89543 19.1046 7 18 7H15M9 7V5C9 3.89543 9.89543 3 11 3H13C14.1046 3 15 3.89543 15 5V7M9 7H15" stroke="currentColor" strokeWidth="2"/>
                    <path d="M9 12H15M12 9V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                </div>
                <div className="info-content">
                  <label>Tipo Factura</label>
                  <span className={header.fac_sin_iva ? 'badge-sin-iva' : 'badge-con-iva'}>
                    {header.fac_sin_iva ? 'Sin IVA' : 'Con IVA (19%)'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* ========= SECCIÓN: Datos del Ingreso ========= */}
          <div className="ingresos-section card-elevated">
            <div className="section-header">
              <svg className="section-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M16 13H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M16 17H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M10 9H9H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <h2>Datos del Ingreso</h2>
            </div>
            {estadoRecepcion === 'completo' && (
              <div className="alert alert-info">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                  <path d="M12 16V12M12 8H12.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
                <span>Esta orden de compra ya está completamente recibida. No se pueden registrar más ingresos.</span>
              </div>
            )}
            <div className="form-grid-ingreso">
              <div className="form-group">
                <label>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M9 5H7C5.89543 5 5 5.89543 5 7V19C5 20.1046 5.89543 21 7 21H17C18.1046 21 19 20.1046 19 19V7C19 5.89543 18.1046 5 17 5H15" stroke="currentColor" strokeWidth="2"/>
                    <rect x="9" y="3" width="6" height="4" rx="1" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Nº Factura
                </label>
                <input
                  type="text"
                  value={factura}
                  onChange={(e) => setFactura(e.target.value)}
                  placeholder="Ingrese número de factura"
                  maxLength={50}
                  disabled={estadoRecepcion === 'completo'}
                />
                <small className="field-hint">Puede dejarse vacío para pagos urgentes. Se completará después en "Documentos Pendientes"</small>
              </div>
              <div className="form-group">
                <label>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M20 7H4C2.89543 7 2 7.89543 2 9V19C2 20.1046 2.89543 21 4 21H20C21.1046 21 22 20.1046 22 19V9C22 7.89543 21.1046 7 20 7Z" stroke="currentColor" strokeWidth="2"/>
                    <path d="M16 21V5C16 3.89543 15.7893 3 14.4142 3H9.58579C8.21071 3 8 3.89543 8 5V21" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Guía de Recepción
                </label>
                <input
                  type="text"
                  value={guiaRecepcion}
                  onChange={(e) => setGuiaRecepcion(e.target.value)}
                  placeholder="Ingrese guía (opcional)"
                  maxLength={50}
                  disabled={estadoRecepcion === 'completo'}
                />
                <small className="field-hint">Campo opcional para control interno</small>
              </div>
              <div className="form-group checkbox-group">
                <label className={estadoRecepcion === 'completo' ? 'disabled' : ''}>
                  <input
                    type="checkbox"
                    checked={facPendiente}
                    onChange={(e) => setFacPendiente(e.target.checked)}
                    disabled={estadoRecepcion === 'completo'}
                  />
                  <span>Factura Pendiente</span>
                </label>
                <small className="field-hint">Marque si la factura queda pendiente de recepción</small>
              </div>
            </div>
          </div>

          {/* ========= SECCIÓN: Detalle de Productos ========= */}
          <div className="ingresos-section card-elevated">
            <div className="section-header">
              <svg className="section-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
                <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
                <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
                <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
              </svg>
              <h2>Detalle de Productos</h2>
            </div>
            
            <div className="tabla-ingresos">
              <div className="tabla-header-ingresos">
                <div>CÓDIGO</div>
                <div>DESCRIPCIÓN</div>
                <div>SOLICITADO</div>
                <div>RECIBIDO</div>
                <div>PENDIENTE</div>
                <div>NETO UNIT.</div>
                <div>RECIBIR AHORA</div>
              </div>

              {lineas.map((linea, idx) => (
                <div key={idx} className={`tabla-row-ingresos ${linea.pendiente === 0 ? 'row-completo' : ''}`}>
                  <div className="col-codigo">
                    <span className="mobile-label">Código:</span>
                    {linea.codigo || '-'}
                  </div>
                  <div className="col-descripcion-ing">
                    <span className="mobile-label">Descripción:</span>
                    {linea.descripcion}
                  </div>
                  <div className="col-numero">
                    <span className="mobile-label">Solicitado:</span>
                    <span className="badge-numero">{linea.solicitado}</span>
                  </div>
                  <div className="col-numero">
                    <span className="mobile-label">Recibido:</span>
                    <span className="badge-numero badge-recibido">{linea.total_recibido}</span>
                  </div>
                  <div className="col-numero">
                    <span className="mobile-label">Pendiente:</span>
                    <span className={`badge-pendiente ${linea.pendiente === 0 ? 'completo' : ''}`}>
                      {linea.pendiente}
                    </span>
                  </div>
                  <div className="col-precio">
                    <span className="mobile-label">Neto Unitario:</span>
                    ${linea.neto.toLocaleString('es-CL')}
                  </div>
                  <div className="col-input">
                    <span className="mobile-label">Recibir Ahora:</span>
                    <input
                      type="number"
                      value={cantidadesRecibidas[idx] || 0}
                      onChange={(e) => handleCantidadChange(idx, e.target.value)}
                      min="0"
                      max={linea.pendiente}
                      disabled={linea.pendiente === 0 || estadoRecepcion === 'completo'}
                      placeholder="0"
                      className={cantidadesRecibidas[idx] > 0 ? 'input-con-valor' : ''}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* ========= Total del Ingreso ========= */}
            <div className="totales-container">
              <div className="total-row total-final">
                <span className="total-label">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  TOTAL A INGRESAR
                </span>
                <span className="total-value">
                  ${calcularTotalIngreso().toLocaleString('es-CL')}
                </span>
              </div>
            </div>
          </div>

          {/* ========= Botones de Acción ========= */}
          <div className="acciones-footer">
            <button
              className="btn-guardar"
              onClick={handleGuardarIngreso}
              disabled={loading || lineas.length === 0 || estadoRecepcion === 'completo'}
            >
              <svg className="icon-btn" width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M17 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V7L17 3ZM19 19H5V5H16.17L19 7.83V19ZM12 12C10.34 12 9 13.34 9 15C9 16.66 10.34 18 12 18C13.66 18 15 16.66 15 15C15 13.34 13.66 12 12 12ZM6 6H15V10H6V6Z" fill="currentColor"/>
              </svg>
              {loading ? 'Guardando...' : estadoRecepcion === 'completo' ? 'Orden Completa' : 'Guardar Ingreso'}
            </button>
          </div>
        </>
      )}

      {/* ========= Estado de carga ========= */}
      {loading && !mensaje && (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p>Cargando...</p>
        </div>
      )}
    </div>
  );
}

export default Ingresos;