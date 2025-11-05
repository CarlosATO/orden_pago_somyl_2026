// frontend/src/components/GastosDirectos.jsx

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import API_BASE_URL from '../config/api';
import * as XLSX from 'xlsx';
import './GastosDirectos.css';
import { getAuthToken } from '../utils/auth';

const API_URL = API_BASE_URL;

function GastosDirectos() {
  // Estados principales
  const [proyectos, setProyectos] = useState([]);
  const [items, setItems] = useState([]);
  const [proyectoSeleccionado, setProyectoSeleccionado] = useState('');
  const [gastosExistentes, setGastosExistentes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mensaje, setMensaje] = useState({ tipo: '', texto: '' });

  // Estados del formulario
  const [formData, setFormData] = useState({
    item_id: '',
    descripcion: '',
    mes: '',
    monto: '',
    fecha: new Date().toISOString().split('T')[0]
  });

  // Estados para Excel
  const [archivoExcel, setArchivoExcel] = useState(null);
  const [datosValidados, setDatosValidados] = useState(null);
  const [erroresExcel, setErroresExcel] = useState([]);
  const [mostrarModalExcel, setMostrarModalExcel] = useState(false);

  const meses = [
    { num: 1, nombre: 'Enero' },
    { num: 2, nombre: 'Febrero' },
    { num: 3, nombre: 'Marzo' },
    { num: 4, nombre: 'Abril' },
    { num: 5, nombre: 'Mayo' },
    { num: 6, nombre: 'Junio' },
    { num: 7, nombre: 'Julio' },
    { num: 8, nombre: 'Agosto' },
    { num: 9, nombre: 'Septiembre' },
    { num: 10, nombre: 'Octubre' },
    { num: 11, nombre: 'Noviembre' },
    { num: 12, nombre: 'Diciembre' }
  ];

  // Cargar datos iniciales
  useEffect(() => {
    cargarProyectos();
    cargarItems();
  }, []);

  // Cargar gastos cuando se selecciona un proyecto
  useEffect(() => {
    if (proyectoSeleccionado) {
      cargarGastos();
    } else {
      setGastosExistentes([]);
    }
  }, [proyectoSeleccionado]);

  const cargarProyectos = async () => {
    try {
      const token = getAuthToken();
      const response = await axios.get(`${API_URL}/proyectos/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.data.success) {
        setProyectos(response.data.data || []); // Cambiado de .proyectos a .data
      }
    } catch (error) {
      console.error('Error al cargar proyectos:', error);
      mostrarMensaje('error', 'Error al cargar proyectos');
      setProyectos([]); // Asegurar que siempre sea un array
    }
  };

  const cargarItems = async () => {
    try {
      const token = getAuthToken();
      const response = await axios.get(`${API_URL}/items/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.data.success) {
        setItems(response.data.items);
      }
    } catch (error) {
      mostrarMensaje('error', 'Error al cargar items');
    }
  };

  const cargarGastos = async () => {
    try {
      setLoading(true);
      const token = getAuthToken();
      const response = await axios.get(
        `${API_URL}/gastos_directos/todos?proyecto_id=${proyectoSeleccionado}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (response.data.success) {
        setGastosExistentes(response.data.data);
      }
    } catch (error) {
      mostrarMensaje('error', 'Error al cargar gastos');
    } finally {
      setLoading(false);
    }
  };

  const mostrarMensaje = (tipo, texto) => {
    setMensaje({ tipo, texto });
    setTimeout(() => setMensaje({ tipo: '', texto: '' }), 5000);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const formatearMonto = (e) => {
    let valor = e.target.value.replace(/\D/g, '');
    if (valor) {
      valor = parseInt(valor).toLocaleString('es-CL');
    }
    setFormData(prev => ({ ...prev, monto: valor }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!proyectoSeleccionado) {
      mostrarMensaje('error', 'Debe seleccionar un proyecto');
      return;
    }

    if (!formData.item_id || !formData.mes || !formData.monto) {
      mostrarMensaje('error', 'Complete todos los campos obligatorios');
      return;
    }

    try {
      setLoading(true);
      const token = getAuthToken();
      
      const payload = {
        proyecto_id: parseInt(proyectoSeleccionado),
        item_id: parseInt(formData.item_id),
        descripcion: formData.descripcion,
        mes: parseInt(formData.mes),
        monto: parseInt(formData.monto.replace(/\D/g, '')),
        fecha: formData.fecha
      };

      const response = await axios.post(
        `${API_URL}/gastos_directos/new`,
        payload,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data.success) {
        mostrarMensaje('success', 'Gasto creado exitosamente');
        limpiarFormulario();
        cargarGastos();
      }
    } catch (error) {
      mostrarMensaje('error', error.response?.data?.message || 'Error al crear gasto');
    } finally {
      setLoading(false);
    }
  };

  const eliminarGasto = async (gastoId) => {
    if (!confirm('¿Está seguro de eliminar este gasto?')) return;

    try {
      setLoading(true);
      const token = getAuthToken();
      const response = await axios.delete(
        `${API_URL}/gastos_directos/${gastoId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data.success) {
        mostrarMensaje('success', 'Gasto eliminado exitosamente');
        cargarGastos();
      }
    } catch (error) {
      mostrarMensaje('error', 'Error al eliminar gasto');
    } finally {
      setLoading(false);
    }
  };

  const limpiarFormulario = () => {
    setFormData({
      item_id: '',
      descripcion: '',
      mes: '',
      monto: '',
      fecha: new Date().toISOString().split('T')[0]
    });
  };

  // ==================== FUNCIONES EXCEL ====================

  const descargarPlantilla = async () => {
    try {
      setLoading(true);
      const token = getAuthToken();
      const response = await axios.get(
        `${API_URL}/gastos_directos/plantilla-excel`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `plantilla_gastos_directos_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      mostrarMensaje('success', 'Plantilla descargada exitosamente');
    } catch (error) {
      mostrarMensaje('error', 'Error al descargar plantilla');
    } finally {
      setLoading(false);
    }
  };

  const handleArchivoExcel = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        mostrarMensaje('error', 'El archivo debe ser Excel (.xlsx o .xls)');
        e.target.value = '';
        return;
      }
      setArchivoExcel(file);
    }
  };

  const validarExcel = async () => {
    if (!archivoExcel) {
      mostrarMensaje('error', 'Debe seleccionar un archivo');
      return;
    }

    try {
      setLoading(true);
      const token = getAuthToken();
      const formData = new FormData();
      formData.append('file', archivoExcel);

      const response = await axios.post(
        `${API_URL}/gastos_directos/validar-excel`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      if (response.data.success) {
        setDatosValidados(response.data.datos_validos);
        setErroresExcel(response.data.errores);
        setMostrarModalExcel(true);
        
        if (response.data.total_errores > 0) {
          mostrarMensaje('warning', `Se encontraron ${response.data.total_errores} errores en el archivo`);
        } else {
          mostrarMensaje('success', `${response.data.total_validos} registros válidos listos para importar`);
        }
      }
    } catch (error) {
      mostrarMensaje('error', error.response?.data?.message || 'Error al validar archivo');
    } finally {
      setLoading(false);
    }
  };

  const importarExcel = async () => {
    if (!datosValidados || datosValidados.length === 0) {
      mostrarMensaje('error', 'No hay datos válidos para importar');
      return;
    }

    try {
      setLoading(true);
      const token = getAuthToken();
      
      const response = await axios.post(
        `${API_URL}/gastos_directos/importar-excel`,
        { gastos: datosValidados },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data.success) {
        mostrarMensaje('success', response.data.message);
        cerrarModalExcel();
        if (proyectoSeleccionado) {
          cargarGastos();
        }
      }
    } catch (error) {
      mostrarMensaje('error', error.response?.data?.message || 'Error al importar datos');
    } finally {
      setLoading(false);
    }
  };

  const exportarExcel = async () => {
    if (!proyectoSeleccionado) {
      mostrarMensaje('error', 'Debe seleccionar un proyecto');
      return;
    }

    try {
      setLoading(true);
      const token = getAuthToken();
      const response = await axios.get(
        `${API_URL}/gastos_directos/exportar-excel/${proyectoSeleccionado}`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const proyecto = proyectos.find(p => p.id == proyectoSeleccionado);
      link.setAttribute('download', `gastos_${proyecto?.proyecto || 'proyecto'}_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      mostrarMensaje('success', 'Gastos exportados exitosamente');
    } catch (error) {
      mostrarMensaje('error', error.response?.data?.message || 'Error al exportar');
    } finally {
      setLoading(false);
    }
  };

  const cerrarModalExcel = () => {
    setMostrarModalExcel(false);
    setDatosValidados(null);
    setErroresExcel([]);
    setArchivoExcel(null);
    document.getElementById('archivoExcel').value = '';
  };

  const obtenerNombreMes = (numMes) => {
    const mes = meses.find(m => m.num === numMes);
    return mes ? mes.nombre : numMes;
  };

  const obtenerNombreItem = (itemId) => {
    const item = items.find(i => i.id === itemId);
    return item ? item.tipo : itemId;
  };

  // ==================== RENDER ====================

  return (
    <div className="gastos-directos-container">
      <div className="gastos-header">
        <h1>📊 Gastos Directos</h1>
        <div className="header-actions">
          <button 
            className="btn-plantilla"
            onClick={descargarPlantilla}
            disabled={loading}
          >
            📥 Descargar Plantilla Excel
          </button>
        </div>
      </div>

      {/* Mensajes */}
      {mensaje.texto && (
        <div className={`alert alert-${mensaje.tipo}`}>
          {mensaje.texto}
        </div>
      )}

      {/* Selección de Proyecto */}
      <div className="proyecto-selector">
        <label htmlFor="proyecto">Proyecto:</label>
        <select
          id="proyecto"
          value={proyectoSeleccionado}
          onChange={(e) => setProyectoSeleccionado(e.target.value)}
          className="form-control"
        >
          <option value="">-- Seleccione un proyecto --</option>
          {proyectos.map(p => (
            <option key={p.id} value={p.id}>{p.proyecto}</option>
          ))}
        </select>
      </div>

      {proyectoSeleccionado && (
        <>
          {/* Pestañas */}
          <div className="tabs">
            <button className="tab active">Formulario Individual</button>
            <button 
              className="tab"
              onClick={() => document.getElementById('importar-section').scrollIntoView({ behavior: 'smooth' })}
            >
              Importar Excel
            </button>
          </div>

          {/* Formulario Individual */}
          <div className="form-section">
            <h3>Agregar Gasto Individual</h3>
            <form onSubmit={handleSubmit} className="gasto-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Item *</label>
                  <select
                    name="item_id"
                    value={formData.item_id}
                    onChange={handleInputChange}
                    required
                    className="form-control"
                  >
                    <option value="">Seleccione...</option>
                    {items.map(item => (
                      <option key={item.id} value={item.id}>{item.tipo}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Mes *</label>
                  <select
                    name="mes"
                    value={formData.mes}
                    onChange={handleInputChange}
                    required
                    className="form-control"
                  >
                    <option value="">Seleccione...</option>
                    {meses.map(m => (
                      <option key={m.num} value={m.num}>{m.nombre}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Monto *</label>
                  <input
                    type="text"
                    name="monto"
                    value={formData.monto}
                    onChange={formatearMonto}
                    placeholder="$ 0"
                    required
                    className="form-control"
                  />
                </div>

                <div className="form-group">
                  <label>Fecha *</label>
                  <input
                    type="date"
                    name="fecha"
                    value={formData.fecha}
                    onChange={handleInputChange}
                    required
                    className="form-control"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Descripción</label>
                <input
                  type="text"
                  name="descripcion"
                  value={formData.descripcion}
                  onChange={handleInputChange}
                  placeholder="Descripción del gasto (opcional)"
                  className="form-control"
                  maxLength={200}
                />
              </div>

              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? '⏳ Guardando...' : '💾 Guardar Gasto'}
                </button>
                <button type="button" className="btn-secondary" onClick={limpiarFormulario}>
                  🗑️ Limpiar
                </button>
              </div>
            </form>
          </div>

          {/* Sección Importar Excel */}
          <div id="importar-section" className="import-section">
            <h3>📤 Importar desde Excel</h3>
            <div className="import-form">
              <div className="form-group">
                <label>Seleccionar archivo Excel:</label>
                <input
                  type="file"
                  id="archivoExcel"
                  accept=".xlsx,.xls"
                  onChange={handleArchivoExcel}
                  className="form-control"
                />
              </div>
              <div className="import-actions">
                <button 
                  className="btn-primary"
                  onClick={validarExcel}
                  disabled={!archivoExcel || loading}
                >
                  🔍 Validar Archivo
                </button>
                <button 
                  className="btn-export"
                  onClick={exportarExcel}
                  disabled={loading || gastosExistentes.length === 0}
                >
                  📤 Exportar Gastos Actuales
                </button>
              </div>
            </div>
          </div>

          {/* Tabla de Gastos Existentes */}
          <div className="gastos-table-section">
            <h3>Gastos Registrados ({gastosExistentes.length})</h3>
            {loading ? (
              <div className="loading">⏳ Cargando gastos...</div>
            ) : gastosExistentes.length === 0 ? (
              <div className="empty-state">
                <p>📭 No hay gastos registrados para este proyecto</p>
                <small>Agregue gastos usando el formulario o importe desde Excel</small>
              </div>
            ) : (
              <div className="table-responsive">
                <table className="gastos-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Item</th>
                      <th>Descripción</th>
                      <th>Mes</th>
                      <th>Monto</th>
                      <th>Fecha</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gastosExistentes.map(gasto => (
                      <tr key={gasto.id}>
                        <td>{gasto.id}</td>
                        <td>{gasto.item_nombre || obtenerNombreItem(gasto.item_id)}</td>
                        <td>{gasto.descripcion || '-'}</td>
                        <td>{obtenerNombreMes(gasto.mes)}</td>
                        <td className="monto">$ {parseInt(gasto.monto).toLocaleString('es-CL')}</td>
                        <td>{new Date(gasto.fecha).toLocaleDateString('es-CL')}</td>
                        <td>
                          <button
                            className="btn-delete"
                            onClick={() => eliminarGasto(gasto.id)}
                            disabled={loading}
                            title="Eliminar gasto"
                          >
                            🗑️
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan="4"><strong>TOTAL</strong></td>
                      <td className="monto"><strong>
                        $ {gastosExistentes.reduce((sum, g) => sum + parseInt(g.monto), 0).toLocaleString('es-CL')}
                      </strong></td>
                      <td colSpan="2"></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* Modal de Validación Excel */}
      {mostrarModalExcel && (
        <div className="modal-overlay" onClick={cerrarModalExcel}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📋 Validación de Archivo Excel</h2>
              <button className="modal-close" onClick={cerrarModalExcel}>✕</button>
            </div>
            
            <div className="modal-body">
              {/* Resumen */}
              <div className="validation-summary">
                <div className="summary-card success">
                  <h4>✅ Registros Válidos</h4>
                  <p className="summary-number">{datosValidados?.length || 0}</p>
                </div>
                <div className="summary-card error">
                  <h4>❌ Errores</h4>
                  <p className="summary-number">{erroresExcel?.length || 0}</p>
                </div>
              </div>

              {/* Errores */}
              {erroresExcel.length > 0 && (
                <div className="errores-section">
                  <h3>⚠️ Errores Encontrados</h3>
                  <div className="errores-list">
                    {erroresExcel.map((error, idx) => (
                      <div key={idx} className="error-item">
                        <strong>Fila {error.fila}:</strong>
                        <ul>
                          {error.errores.map((err, i) => (
                            <li key={i}>{err}</li>
                          ))}
                        </ul>
                        <pre>{JSON.stringify(error.datos, null, 2)}</pre>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Preview de datos válidos */}
              {datosValidados && datosValidados.length > 0 && (
                <div className="preview-section">
                  <h3>📋 Preview de Datos a Importar</h3>
                  <div className="table-responsive">
                    <table className="preview-table">
                      <thead>
                        <tr>
                          <th>Proyecto</th>
                          <th>Item</th>
                          <th>Descripción</th>
                          <th>Mes</th>
                          <th>Monto</th>
                          <th>Fecha</th>
                        </tr>
                      </thead>
                      <tbody>
                        {datosValidados.slice(0, 10).map((dato, idx) => (
                          <tr key={idx}>
                            <td>{dato.proyecto_id}</td>
                            <td>{dato.item_id}</td>
                            <td>{dato.descripcion || '-'}</td>
                            <td>{obtenerNombreMes(dato.mes)}</td>
                            <td>$ {parseInt(dato.monto).toLocaleString('es-CL')}</td>
                            <td>{new Date(dato.fecha).toLocaleDateString('es-CL')}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {datosValidados.length > 10 && (
                      <p className="preview-note">
                        ... y {datosValidados.length - 10} registros más
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button className="btn-secondary" onClick={cerrarModalExcel}>
                Cancelar
              </button>
              {datosValidados && datosValidados.length > 0 && erroresExcel.length === 0 && (
                <button 
                  className="btn-primary"
                  onClick={importarExcel}
                  disabled={loading}
                >
                  {loading ? '⏳ Importando...' : '✅ Importar Datos'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default GastosDirectos;