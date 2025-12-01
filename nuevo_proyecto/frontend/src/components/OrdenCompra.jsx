import { useState, useEffect } from 'react';
import Select from 'react-select';
import AsyncSelect from 'react-select/async';
import './OrdenCompra.css';
import { getAuthToken } from '../utils/auth';

function OrdenCompra() {
  // ========= Estados del formulario =========
  const [numeroOC, setNumeroOC] = useState('');
  const [proveedor, setProveedor] = useState(null);
  const [rutProveedor, setRutProveedor] = useState('');
  const [tipoEntrega, setTipoEntrega] = useState(null);
  const [plazoPago, setPlazoPago] = useState(null);
  const [incluirIVA, setIncluirIVA] = useState(true);
  const [proyecto, setProyecto] = useState(null);
  const [solicitadoPor, setSolicitadoPor] = useState(null);
    const [observaciones, setObservaciones] = useState('');

  // ========= Estados de las líneas de productos =========
  const [lineas, setLineas] = useState([
    { id: 1, material: null, descripcion: '', cantidad: 0, netoUnitario: 0, total: 0 }
  ]);

  // ========= Estados para carga y mensajes =========
  const [loading, setLoading] = useState(false);
  const [mensaje, setMensaje] = useState(null);

  // ========= Opciones fijas para selects simples =========
  const tiposEntregaOptions = [
    { value: '30 DÍAS', label: '30 DÍAS' },
    { value: '45 DÍAS', label: '45 DÍAS' },
    { value: '60 DÍAS', label: '60 DÍAS' },
    { value: '90 DÍAS', label: '90 DÍAS' },
    { value: 'INMEDIATO', label: 'INMEDIATO' },
    { value: 'OTROS', label: 'OTROS' },
  ];

  const plazosPagoOptions = [
  { value: '7 días', label: '7 días' },
  { value: '15 días', label: '15 días' },
  { value: '30 días', label: '30 días' },
  { value: '60 días', label: '60 días' },
  { value: '90 días', label: '90 días' },
  { value: 'Contado', label: 'Contado' }
  ];

  // ========= Obtener próximo número de OC =========
  useEffect(() => {
    fetchProximoNumeroOC();
  }, []);

  const fetchProximoNumeroOC = async () => {
    try {
      const token = getAuthToken();
      
      if (!token) {
        console.error('❌ No hay token de autenticación. Por favor inicia sesión nuevamente.');
        setMensaje({ tipo: 'error', texto: 'Sesión expirada. Por favor inicia sesión nuevamente.' });
        return;
      }
      
      console.log('🔍 Obteniendo próximo número de OC...');
      console.log('🔑 Token presente:', token ? 'SÍ' : 'NO');
      
      const response = await fetch('/api/ordenes/helpers/next-number', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      console.log('📡 Response status:', response.status);
      
      if (response.status === 401) {
        console.error('❌ Token inválido o expirado');
        const errorData = await response.json();
        console.error('❌ Error completo:', errorData);
        setMensaje({ tipo: 'error', texto: `Error de autenticación: ${errorData.message || 'Token inválido'}` });
        return;
      }
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Próximo número de OC:', data.next_number);
        setNumeroOC(data.next_number || '');
      } else {
        console.error('❌ Error al obtener número de OC:', response.status);
        const errorData = await response.text();
        console.error('Error data:', errorData);
      }
    } catch (error) {
      console.error('❌ Error al obtener número de OC:', error);
    }
  };

  // ========= Función para buscar con autocompletado =========
  const loadOptions = async (inputValue, resource) => {
    try {
      const token = getAuthToken();
      
      if (!token) {
        console.error('❌ No hay token de autenticación');
        return [];
      }
      
      // Normalizar inputValue (puede ser undefined, null, o string vacío)
      const searchTerm = inputValue ? inputValue.trim() : '';
      
      console.log(`🔍 Buscando ${resource}:`, {
        inputValue: inputValue,
        searchTerm: searchTerm,
        length: searchTerm.length
      });

      // Si no hay término de búsqueda o es muy corto, pedimos los primeros 10 items
      // Si hay término de búsqueda, filtramos por ese término
      const query = searchTerm.length >= 2
        ? `?term=${encodeURIComponent(searchTerm)}`
        : `?limit=10`;
      
      const url = `/api/ordenes/helpers/autocomplete/${resource}${query}`;
      console.log(`📡 URL completa:`, url);

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      console.log(`📡 Response ${resource}:`, response.status);

      if (response.status === 401) {
        console.error('❌ Token inválido o expirado al buscar', resource);
        const errorData = await response.json();
        console.error('❌ Error completo:', errorData);
        return [];
      }

      if (response.ok) {
        const data = await response.json();
        console.log(`✅ Resultados ${resource}:`, {
          cantidad: data.results?.length || 0,
          primeros: data.results?.slice(0, 3)
        });
        return data.results || [];
      } else {
        const errorText = await response.text();
        console.error(`❌ Error ${response.status} en ${resource}:`, errorText);
        return [];
      }
    } catch (error) {
      console.error(`❌ Error al buscar ${resource}:`, error);
      return [];
    }
  };

  // ========= Handlers de autocompletado =========
  const handleProveedorSearch = (inputValue, callback) => {
    console.log('🔍 handleProveedorSearch llamado con:', inputValue);
    return loadOptions(inputValue, 'proveedores');
  };

  const handleProyectoSearch = (inputValue, callback) => {
    console.log('🔍 handleProyectoSearch llamado con:', inputValue);
    return loadOptions(inputValue, 'proyectos');
  };

  const handleTrabajadorSearch = (inputValue, callback) => {
    console.log('🔍 handleTrabajadorSearch llamado con:', inputValue);
    return loadOptions(inputValue, 'trabajadores');
  };

  const handleMaterialSearch = (inputValue, callback) => {
    console.log('🔍 handleMaterialSearch llamado con:', inputValue);
    return loadOptions(inputValue, 'materiales');
  };

  // ========= Cambio de proveedor =========
  const handleProveedorChange = async (selectedOption) => {
    setProveedor(selectedOption);
    if (selectedOption) {
      // El RUT ahora viene directamente en el objeto selectedOption desde el backend
      if (selectedOption.rut) {
        setRutProveedor(selectedOption.rut);
      } else {
        // Fallback: buscar RUT del proveedor si no viene en el objeto
        try {
          const token = getAuthToken();
          const response = await fetch(`/api/proveedores/${selectedOption.value}`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          if (response.ok) {
            const data = await response.json();
            setRutProveedor(data.rut || '');
          }
        } catch (error) {
          console.error('Error al obtener RUT:', error);
          setRutProveedor('');
        }
      }
    } else {
      setRutProveedor('');
    }
  };

  // ========= Generar PDF =========
  const handleGenerarPDF = async () => {
    try {
      const token = getAuthToken();
      
      if (!token) {
        setMensaje({ tipo: 'error', texto: 'No hay sesión activa' });
        return;
      }

      // Preparar datos básicos para el PDF de prueba
      const datosPDF = {
        numero_oc: numeroOC,
        proveedor: {
          id: proveedor?.value || null,
          nombre: proveedor?.label || 'Proveedor no seleccionado',
          rut: rutProveedor || 'Sin RUT'
        },
        fecha: new Date().toISOString().split('T')[0],
        tipo_entrega: tipoEntrega?.label || tipoEntrega?.value || '',
        plazo_pago: plazoPago?.label || plazoPago?.value || '',
        proyecto: proyecto?.label || proyecto?.value || '',
        solicitado_por: solicitadoPor?.label || solicitadoPor?.value || '',
        observaciones: observaciones || '',
        productos: lineas
          .filter(linea => (linea.material || linea.descripcion) && (linea.cantidad && Number(linea.cantidad) > 0))
          .map(linea => ({
            codigo: linea.material?.value || '',
            descripcion: linea.material?.label || linea.descripcion,
            cantidad: Number(linea.cantidad) || 0,
            precio: Number(linea.netoUnitario) || 0,
            total: Number(linea.total) || (Number(linea.cantidad || 0) * Number(linea.netoUnitario || 0))
          })),
        subtotal: Number(calcularSumaNeto()) || 0,
        iva: Number(calcularIVA()) || 0,
        total: Number(calcularTotal()) || 0
      };

      console.log('📄 Generando PDF con datos:', datosPDF);

      const response = await fetch('/api/generar-pdf-orden-compra', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(datosPDF)
      });

      if (response.ok) {
        // Descargar el PDF
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `OrdenCompra_${numeroOC}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        setMensaje({ tipo: 'success', texto: '✅ PDF generado exitosamente' });
      } else {
        const error = await response.json();
        setMensaje({ tipo: 'error', texto: `Error: ${error.error || 'No se pudo generar el PDF'}` });
      }
    } catch (error) {
      console.error('Error al generar PDF:', error);
      setMensaje({ tipo: 'error', texto: 'Error al generar el PDF' });
    }
  };

  // ========= Gestión de líneas de productos =========
  const agregarLinea = () => {
    const nuevaLinea = {
      id: Date.now(),
      material: null,
      descripcion: '',
      cantidad: 0,
      netoUnitario: 0,
      total: 0
    };
    setLineas([...lineas, nuevaLinea]);
  };

  const eliminarLinea = (id) => {
    if (lineas.length > 1) {
      setLineas(lineas.filter(linea => linea.id !== id));
    }
  };

  const actualizarLinea = (id, campo, valor) => {
    setLineas(lineas.map(linea => {
      if (linea.id === id) {
        const lineaActualizada = { ...linea, [campo]: valor };

        // Si cambia material, actualizar descripción y obtener último precio
        if (campo === 'material' && valor) {
          lineaActualizada.descripcion = valor.label;
          // Obtener último precio del material
          fetchUltimoPrecio(valor.value, id);
        }

        // Calcular total si cambia cantidad o neto
        if (campo === 'cantidad' || campo === 'netoUnitario') {
          const cantidad = campo === 'cantidad' ? parseFloat(valor) || 0 : parseFloat(linea.cantidad) || 0;
          const neto = campo === 'netoUnitario' ? parseFloat(valor) || 0 : parseFloat(linea.netoUnitario) || 0;
          lineaActualizada.total = cantidad * neto;
        }

        return lineaActualizada;
      }
      return linea;
    }));
  };

  // ========= Obtener último precio de un material =========
  const fetchUltimoPrecio = async (codigo, lineaId) => {
    try {
      const token = getAuthToken();
      console.log(`🔍 Obteniendo último precio para material código: ${codigo}`);
      
      const response = await fetch(`/api/ordenes/helpers/material/${codigo}/ultimo-precio`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.precio > 0) {
          console.log(`✅ Último precio: $${data.precio.toLocaleString('es-CL')} (fecha: ${data.fecha || 'N/A'})`);
          
          // Actualizar el precio unitario de la línea
          setLineas(prevLineas => prevLineas.map(linea => {
            if (linea.id === lineaId) {
              const precio = parseFloat(data.precio) || 0;
              return {
                ...linea,
                netoUnitario: precio,
                total: linea.cantidad * precio
              };
            }
            return linea;
          }));
        } else {
          console.log('ℹ️ No hay precio previo registrado para este material');
        }
      } else {
        console.warn('⚠️ No se pudo obtener el último precio');
      }
    } catch (error) {
      console.error('❌ Error al obtener último precio:', error);
    }
  };

  // ========= Cálculo del total =========
  const calcularSumaNeto = () => {
    const suma = lineas.reduce((acc, linea) => acc + (linea.total || 0), 0);
    return suma.toFixed(0);
  };

  const calcularIVA = () => {
    if (!incluirIVA) return 0;
    const neto = parseFloat(calcularSumaNeto());
    return (neto * 0.19).toFixed(0);
  };

  const calcularTotal = () => {
    const neto = parseFloat(calcularSumaNeto());
    const iva = parseFloat(calcularIVA());
    return (neto + iva).toFixed(0);
  };

  // ========= Guardar orden de compra =========
  const handleGuardar = async () => {
    // Validaciones
    if (!proveedor) {
      setMensaje({ tipo: 'error', texto: 'Debe seleccionar un proveedor' });
      return;
    }

    if (!proyecto) {
      setMensaje({ tipo: 'error', texto: 'Debe seleccionar un proyecto' });
      return;
    }

    if (lineas.length === 0 || lineas.every(l => !l.cantidad || l.cantidad <= 0)) {
      setMensaje({ tipo: 'error', texto: 'Debe agregar al menos una línea con cantidad' });
      return;
    }

    setLoading(true);
    setMensaje(null);

    try {
      const token = getAuthToken(); // Usar 'authToken' en lugar de 'token'
      
      const payload = {
        header: {
          proveedor_id: proveedor.value,
          tipo_entrega: tipoEntrega?.value,
          plazo_pago: plazoPago?.value,
          sin_iva: !incluirIVA,
          proyecto_id: proyecto.value,
          solicitado_por: solicitadoPor?.value
        },
        lineas: lineas.filter(l => l.cantidad > 0).map(l => ({
          codigo: l.material?.value || '',
          descripcion: l.descripcion,
          cantidad: l.cantidad,
          neto: l.netoUnitario,
          total: l.total
        }))
      };

      const response = await fetch('/api/ordenes/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setMensaje({ tipo: 'success', texto: `✅ ${data.message}` });
        
        // Limpiar formulario sin recargar la página
        setTimeout(() => {
          // Resetear todos los estados
          setProveedor(null);
          setRutProveedor('');
          setTipoEntrega(null);
          setPlazoPago(null);
          setIncluirIVA(true);
          setProyecto(null);
          setSolicitadoPor(null);
          setObservaciones('');
          setLineas([{ id: Date.now(), material: null, descripcion: '', cantidad: 0, netoUnitario: 0, total: 0 }]);
          
          // Obtener nuevo número de OC
          fetchProximoNumeroOC();
          
          // Limpiar mensaje después de 3 segundos
          setTimeout(() => setMensaje(null), 3000);
        }, 1500);
      } else {
        setMensaje({ tipo: 'error', texto: `❌ ${data.message || 'Error al guardar'}` });
      }
    } catch (error) {
      console.error('Error al guardar OC:', error);
      setMensaje({ tipo: 'error', texto: '❌ Error de conexión al guardar la orden' });
    } finally {
      setLoading(false);
    }
  };

  // ========= Estilos personalizados para react-select =========
  const customSelectStyles = {
    container: (provided) => ({
      ...provided,
      width: '100%', // Asegurar que tome el 100% del contenedor padre (grid cell)
    }),
    control: (provided) => ({
      ...provided,
      width: '100%', // Control también al 100%
      minHeight: '42px',
      borderColor: '#ddd',
      boxShadow: 'none',
      '&:hover': {
        borderColor: '#aaa'
      }
    }),
    menu: (provided) => ({
      ...provided,
      zIndex: 9999,
      maxHeight: '300px', // Altura máxima del menú
      width: '100%', // Menú también al 100%
    }),
    menuList: (provided) => ({
      ...provided,
      maxHeight: '300px', // Lista de opciones
      paddingTop: '4px',
      paddingBottom: '4px'
    }),
    option: (provided, state) => ({
      ...provided,
      padding: '12px 16px', // Más espacio para cada opción
      fontSize: '0.95rem',
      backgroundColor: state.isSelected 
        ? '#3b82f6' 
        : state.isFocused 
        ? '#e0f2fe' 
        : 'white',
      color: state.isSelected ? 'white' : '#1f2937',
      cursor: 'pointer',
      '&:active': {
        backgroundColor: '#2563eb'
      }
    })
  };

  return (
    <div className="orden-compra-container">
      <div className="orden-compra-header">
        <h1>📄 Datos de la Orden de Compra</h1>
      </div>

      {mensaje && (
        <div className={`mensaje mensaje-${mensaje.tipo}`}>
          {mensaje.texto}
        </div>
      )}

      {/* ========= SECCIÓN: Datos del Encabezado ========= */}
      <div className="orden-section">
        {/* Primera fila: N°OC, Proveedor, RUT */}
        <div className="form-grid">
          <div className="form-group">
            <label>N° OC:</label>
            <input 
              type="text" 
              value={numeroOC} 
              readOnly 
              className="input-readonly"
            />
          </div>

          <div className="form-group">
            <label>Proveedor:</label>
            <AsyncSelect
              value={proveedor}
              onChange={handleProveedorChange}
              loadOptions={handleProveedorSearch}
              placeholder="Seleccione un proveedor..."
              isClearable
              isSearchable
              styles={customSelectStyles}
              noOptionsMessage={() => "Escriba para buscar..."}
              loadingMessage={() => "Buscando..."}
              cacheOptions
              defaultOptions={true}
            />
          </div>

          <div className="form-group">
            <label>RUT:</label>
            <input 
              type="text" 
              value={rutProveedor} 
              readOnly 
              placeholder="RUT del proveedor"
              className="input-readonly"
            />
          </div>
        </div>

        {/* Segunda fila: Tipo de entrega, Plazo Pago, Checkbox IVA */}
        <div className="form-grid-secondary">
          <div className="form-group">
            <label>Tipo de entrega:</label>
            <Select
              value={tipoEntrega}
              onChange={setTipoEntrega}
              options={tiposEntregaOptions}
              placeholder="Seleccione tipo de entrega..."
              isClearable
              styles={customSelectStyles}
            />
          </div>

          <div className="form-group">
            <label>Plazo de pago:</label>
            <Select
              value={plazoPago}
              onChange={setPlazoPago}
              options={plazosPagoOptions}
              placeholder="Seleccione plazo de pago..."
              isClearable
              styles={customSelectStyles}
            />
          </div>

          <div className="checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={incluirIVA}
                onChange={(e) => setIncluirIVA(e.target.checked)}
              />
              ✓ Incluir IVA (19%)
            </label>
          </div>
        </div>

        {/* Tercera fila: Proyecto, Solicitado Por */}
        <div className="form-grid-third">
          <div className="form-group">
            <label>Proyecto:</label>
            <AsyncSelect
              value={proyecto}
              onChange={setProyecto}
              loadOptions={handleProyectoSearch}
              placeholder="Seleccione un proyecto..."
              isClearable
              isSearchable
              styles={customSelectStyles}
              noOptionsMessage={() => "Escriba para buscar..."}
              cacheOptions
              defaultOptions={true}
            />
          </div>

          <div className="form-group">
            <label>Solicitado por:</label>
            <AsyncSelect
              value={solicitadoPor}
              onChange={setSolicitadoPor}
              loadOptions={handleTrabajadorSearch}
              placeholder="Seleccione un trabajador..."
              isClearable
              isSearchable
              styles={customSelectStyles}
              noOptionsMessage={() => "Escriba para buscar..."}
              cacheOptions
              defaultOptions={true}
            />
          </div>
        </div>
      </div>

      {/* ========= SECCIÓN: Detalle de Productos ========= */}
      <div className="orden-section">
        <h2>📋 Detalle de Productos</h2>
        
        <div className="tabla-productos">
          <div className="tabla-header">
            <div className="col-descripcion">DESCRIPCIÓN</div>
            <div className="col-cantidad">CANTIDAD</div>
            <div className="col-neto">NETO UNITARIO</div>
            <div className="col-total">TOTAL</div>
            <div className="col-acciones">ACCIONES</div>
          </div>

          {lineas.map((linea) => (
            <div className="tabla-row">
              <div className="col-descripcion">
                <AsyncSelect
                  value={linea.material}
                  onChange={(val) => actualizarLinea(linea.id, 'material', val)}
                  loadOptions={handleMaterialSearch}
                  placeholder="Buscar material..."
                  isClearable
                  isSearchable
                  styles={customSelectStyles}
                  noOptionsMessage={() => "Escriba para buscar..."}
                  cacheOptions
                  defaultOptions={true}
                />
              </div>

              <div className="col-cantidad">
                <input
                  type="number"
                  value={linea.cantidad}
                  onChange={(e) => actualizarLinea(linea.id, 'cantidad', e.target.value)}
                  min="0"
                  placeholder="0"
                />
              </div>

              <div className="col-neto">
                <input
                  type="number"
                  value={linea.netoUnitario}
                  onChange={(e) => actualizarLinea(linea.id, 'netoUnitario', e.target.value)}
                  min="0"
                  placeholder="$0"
                />
              </div>

              <div className="col-total">
                <input
                  type="text"
                  value={`$${linea.total.toLocaleString('es-CL')}`}
                  readOnly
                  className="input-readonly"
                />
              </div>

              <div className="col-acciones">
                <button
                  className="btn-eliminar"
                  onClick={() => eliminarLinea(linea.id)}
                  disabled={lineas.length === 1}
                  title="Eliminar línea"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>

        <button className="btn-agregar-linea" onClick={agregarLinea}>
          ➕ Agregar Línea
        </button>

        {/* ========= Totales ========= */}
        <div className="totales-container">
          <div className="total-row">
            <span className="total-label">SUMA NETO:</span>
            <span className="total-value">${parseFloat(calcularSumaNeto()).toLocaleString('es-CL')}</span>
          </div>
          {incluirIVA && (
            <div className="total-row">
              <span className="total-label">IVA (19%):</span>
              <span className="total-value">${parseFloat(calcularIVA()).toLocaleString('es-CL')}</span>
            </div>
          )}
          <div className="total-row total-final">
            <span className="total-label">TOTAL:</span>
            <span className="total-value">${parseFloat(calcularTotal()).toLocaleString('es-CL')}</span>
          </div>
        </div>
      </div>

      {/* ========= SECCIÓN: Observaciones ========= */}
      <div className="orden-section observaciones-section">
        <div className="observaciones-header">
          <svg className="icon-observaciones" width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M7 8H17M7 12H17M7 16H11M3 4H21V16H13L7 20V16H3V4Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <h2>Observaciones</h2>
        </div>
        <textarea
          value={observaciones}
          onChange={(e) => setObservaciones(e.target.value)}
          placeholder="Ingrese observaciones adicionales..."
          maxLength={500}
        />
      </div>

      {/* ========= Botones de acción ========= */}
      <div className="acciones-footer">
        <button 
          className="btn-pdf"
          onClick={handleGenerarPDF}
          disabled={!numeroOC}
        >
          <svg className="icon-btn" width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M7 18H17V16H7V18Z" fill="currentColor"/>
            <path d="M17 14H7V12H17V14Z" fill="currentColor"/>
            <path d="M7 10H11V8H7V10Z" fill="currentColor"/>
            <path fillRule="evenodd" clipRule="evenodd" d="M6 2C4.34315 2 3 3.34315 3 5V19C3 20.6569 4.34315 22 6 22H18C19.6569 22 21 20.6569 21 19V9C21 5.13401 17.866 2 14 2H6ZM6 4H13V9H19V19C19 19.5523 18.5523 20 18 20H6C5.44772 20 5 19.5523 5 19V5C5 4.44772 5.44772 4 6 4ZM15 4.10002C16.6113 4.4271 17.9413 5.52906 18.584 7H15V4.10002Z" fill="currentColor"/>
          </svg>
          Generar PDF
        </button>
        <button 
          className="btn-guardar"
          onClick={handleGuardar}
          disabled={loading}
        >
          <svg className="icon-btn" width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M17 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V7L17 3ZM19 19H5V5H16.17L19 7.83V19ZM12 12C10.34 12 9 13.34 9 15C9 16.66 10.34 18 12 18C13.66 18 15 16.66 15 15C15 13.34 13.66 12 12 12ZM6 6H15V10H6V6Z" fill="currentColor"/>
          </svg>
          {loading ? 'Guardando...' : 'Guardar Orden de Compra'}
        </button>
      </div>
    </div>
  );
}

export default OrdenCompra;
