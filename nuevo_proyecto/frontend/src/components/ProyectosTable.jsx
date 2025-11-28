import React from 'react';
import './Proyectos.css';

const ProyectosTable = ({ proyectos, onEdit }) => {
  if (!proyectos || proyectos.length === 0) {
    return (
      <div className="proyectos-table-wrapper">
        <div className="empty-state">
          No hay proyectos disponibles. ¡Crea el primero!
        </div>
      </div>
    );
  }

  return (
    <div className="proyectos-table-wrapper">
      <table className="proyectos-table">
        <thead>
          <tr>
            <th>Proyecto</th>
            <th>Venta</th>
            <th style={{ width: '150px' }}>Estado Venta</th>
            <th>Observación</th>
            <th style={{ textAlign: 'center', width: '120px' }}>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {proyectos.map((p) => (
            <tr key={p.id}>
              <td><strong>{p.proyecto}</strong></td>
              <td>{p.venta || '-'}</td>
              <td>
                <span className={`badge-venta ${p.venta ? 'si' : 'no'}`}>
                  {p.venta ? 'Con Venta' : 'Sin Venta'}
                </span>
              </td>
              <td>{p.observacion || '-'}</td>
              <td style={{ textAlign: 'center' }}>
                <button onClick={() => onEdit(p)}>
                  ✏️ Editar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ProyectosTable;
