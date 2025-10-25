import React from 'react';
import './Materiales.css';

const MaterialesTable = ({ materiales, onEdit }) => {
  if (!materiales || materiales.length === 0) {
    return (
      <div className="materiales-table-wrapper">
        <div className="empty-state">
          No hay materiales disponibles. ¡Crea el primero!
        </div>
      </div>
    );
  }

  return (
    <div className="materiales-table-wrapper">
      <table className="materiales-table">
        <thead>
          <tr>
            <th>Código</th>
            <th>Material</th>
            <th>Tipo</th>
            <th>Item</th>
            <th style={{ textAlign: 'center', width: '120px' }}>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {materiales.map((m) => (
            <tr key={m.id}>
              <td><strong>{m.cod}</strong></td>
              <td>{m.material}</td>
              <td>{m.tipo || '-'}</td>
              <td>{m.item}</td>
              <td style={{ textAlign: 'center' }}>
                <button onClick={() => onEdit(m)}>
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

export default MaterialesTable;
