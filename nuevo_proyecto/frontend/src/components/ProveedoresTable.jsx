import React from 'react';
import './Proveedores.css';

const ProveedoresTable = ({ proveedores, onEdit }) => {
  if (!proveedores || proveedores.length === 0) {
    return (
      <div className="proveedores-table-wrapper">
        <div className="empty-state">
          No hay proveedores disponibles. ¡Crea el primero!
        </div>
      </div>
    );
  }

  return (
    <div className="proveedores-table-wrapper">
      <table className="proveedores-table">
        <thead>
          <tr>
            <th>Razón Social</th>
            <th>RUT</th>
            <th>Teléfono</th>
            <th>Contacto</th>
            <th>Correo</th>
            <th style={{ textAlign: 'center', width: '120px' }}>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {proveedores.map((p) => (
            <tr key={p.id}>
              <td><strong>{p.nombre}</strong></td>
              <td>{p.rut}</td>
              <td>{p.telefono || '-'}</td>
              <td>{p.contacto || '-'}</td>
              <td>{p.email || '-'}</td>
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

export default ProveedoresTable;