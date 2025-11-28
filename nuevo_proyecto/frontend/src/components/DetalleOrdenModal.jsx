// frontend/src/components/DetalleOrdenModal.jsx

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAuthToken } from '../utils/auth';
import './DetalleOrdenModal.css';

function DetalleOrdenModal({ orden, onClose, onEditar }) {
  const navigate = useNavigate();
  const [generandoPDF, setGenerandoPDF] = useState(false);

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

  const handleModificar = async () => {
    // Validar si tiene ingresos antes de permitir modificar
    try {
      const token = getAuthToken();
      const response = await fetch(`/api/ingresos/historial/${orden.orden_compra}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data && data.data.length > 0) {
          // Tiene ingresos - NO se puede modificar
          alert('⚠️ No se puede modificar esta orden porque ya tiene recepciones registradas.');
          return;
        }
      }
      
      // No tiene ingresos - permitir modificar
      onClose();
      navigate('/adquisiciones/crear-orden', { 
        state: { 
          ordenData: orden,
          modo: 'editar'
        } 
      });
    } catch (error) {
      console.error('Error al validar ingresos:', error);
      alert('Error al validar si la orden puede modificarse');
    }
  };

  const handleIngreso = () => {
    onClose();
    navigate('/ingresos-recepciones', { 
      state: { 
        ocNumero: orden.orden_compra 
      } 
    });
  };

  const handleGenerarPDF = async () => {
    setGenerandoPDF(true);
    try {
      const token = getAuthToken();
      if (!token) {
        alert('Sesión expirada');
        setGenerandoPDF(false);
        return;
      }
      
      // Calcular totales
      const subtotal = orden.lineas.reduce((sum, linea) => sum + (linea.total_linea || 0), 0);
      const iva = orden.sin_iva ? 0 : subtotal * 0.19;
      const total = subtotal + iva;
      
      // Preparar datos para el PDF
      const datosPDF = {
        numero_oc: orden.orden_compra,
        fecha: orden.fecha,
        proveedor: {
          nombre: orden.proveedor_nombre,
          rut: orden.proveedor_rut
        },
        proyecto: orden.proyecto_nombre,
        solicitado_por: orden.solicitante_nombre,
        tipo_entrega: orden.tipo_entrega || '',
        plazo_entrega: orden.plazo_pago || '',
        sin_iva: orden.sin_iva,
        productos: orden.lineas.map(linea => ({
          codigo: linea.codigo,
          descripcion: linea.descripcion,
          cantidad: linea.cantidad_solicitada,
          precio: linea.precio_unitario,
          total: linea.total_linea
        })),
        subtotal: subtotal,
        iva: iva,
        total: total
      };

      const response = await fetch('/api/generar-pdf-orden-compra', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(datosPDF)
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `OrdenCompra_${orden.orden_compra}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        alert('Error al generar PDF');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Error de conexión al generar PDF');
    } finally {
      setGenerandoPDF(false);
    }
  };

  const getEstadoClass = (estado) => {
    switch(estado) {
      case 'Recibida': return 'badge-recibida';
      case 'Pendiente': return 'badge-pendiente';
      case 'Parcial': return 'badge-parcial';
      default: return '';
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-detalle" onClick={(e) => e.stopPropagation()}>
        {/* HEADER */}
        <div className="modal-header">
          <div className="modal-titulo">
            <h2>Orden de Compra #{orden.orden_compra}</h2>
            <span className={`estado-badge ${getEstadoClass(orden.estado_general)}`}>
              {orden.estado_general}
            </span>
          </div>
          <button className="btn-cerrar" onClick={onClose}>✕</button>
        </div>

        {/* ACCIONES */}
        <div className="modal-acciones">
          <button className="btn-accion btn-editar" onClick={handleModificar}>
            ✏️ Modificar
          </button>
          <button 
            className="btn-accion btn-pdf" 
            onClick={handleGenerarPDF}
            disabled={generandoPDF}
          >
            {generandoPDF ? '⏳ Generando...' : '📄 PDF/Imprimir'}
          </button>
          <button className="btn-accion btn-ingreso" onClick={handleIngreso}>
            📦 Ingreso
          </button>
        </div>

        {/* CONTENIDO */}
        <div className="modal-contenido">
          {/* INFO GENERAL */}
          <div className="seccion-info">
            <h3>Información General</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Fecha:</span>
                <span className="info-valor">{formatearFecha(orden.fecha)}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Proveedor:</span>
                <span className="info-valor">{orden.proveedor_nombre}</span>
              </div>
              <div className="info-item">
                <span className="info-label">RUT:</span>
                <span className="info-valor">{orden.proveedor_rut}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Proyecto:</span>
                <span className="info-valor">{orden.proyecto_nombre}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Solicitante:</span>
                <span className="info-valor">{orden.solicitante_nombre}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Tipo Entrega:</span>
                <span className="info-valor">{orden.tipo_entrega || '-'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Plazo Pago:</span>
                <span className="info-valor">{orden.plazo_pago || '-'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Sin IVA:</span>
                <span className="info-valor">{orden.sin_iva ? 'Sí' : 'No'}</span>
              </div>
            </div>
          </div>

          {/* LÍNEAS DE LA ORDEN */}
          <div className="seccion-lineas">
            <h3>Detalle de Productos</h3>
            <div className="tabla-lineas-container">
              <table className="tabla-lineas">
                <thead>
                  <tr>
                    <th>CÓDIGO</th>
                    <th>DESCRIPCIÓN</th>
                    <th>CANT. SOLICITADA</th>
                    <th>CANT. RECIBIDA</th>
                    <th>PRECIO UNIT.</th>
                    <th>TOTAL</th>
                    <th>ESTADO</th>
                  </tr>
                </thead>
                <tbody>
                  {orden.lineas.map((linea) => (
                    <tr key={linea.art_corr}>
                      <td>{linea.codigo}</td>
                      <td>{linea.descripcion}</td>
                      <td className="text-center">{linea.cantidad_solicitada}</td>
                      <td className="text-center">{linea.cantidad_recibida}</td>
                      <td className="text-right">{formatearMonto(linea.precio_unitario)}</td>
                      <td className="text-right">{formatearMonto(linea.total_linea)}</td>
                      <td>
                        <span className={`estado-linea ${linea.estado.toLowerCase()}`}>
                          {linea.estado}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan="5" className="text-right"><strong>TOTAL:</strong></td>
                    <td className="text-right"><strong>{formatearMonto(orden.total_oc)}</strong></td>
                    <td></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DetalleOrdenModal;