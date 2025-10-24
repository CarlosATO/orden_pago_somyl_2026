import React from 'react';
import './Proveedores.css';

const ProveedoresTable = ({ proveedores, onEdit }) => {
  if (!proveedores || proveedores.length === 0) {
    return <div>No hay proveedores disponibles.</div>;
  }

  return (
    <table className="proveedores-table">
      <thead>
        <tr>
          <th>Razón Social</th>
          <th>RUT</th>
          <th>Teléfono</th>
          <th>Contacto</th>
          <th>Correo</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody>
        {proveedores.map((p) => (
          <tr key={p.id}>
            <td>{p.nombre}</td>
            <td>{p.rut}</td>
            <td>{p.telefono || '-'}</td>
            <td>{p.contacto || '-'}</td>
            <td>{p.email || '-'}</td>
            <td>
              <button onClick={() => onEdit(p)}>Editar</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default ProveedoresTable;
