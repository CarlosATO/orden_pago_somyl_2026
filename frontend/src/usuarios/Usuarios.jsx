// Componente principal de Usuarios
import React, { useEffect, useState } from 'react';

const Usuarios = () => {
  const [usuarios, setUsuarios] = useState([]);

  useEffect(() => {
    fetch('http://localhost:5006/usuarios/api/listado', { credentials: 'include' })
      .then(res => res.json())
      .then(data => setUsuarios(data));
  }, []);

  return (
    <div>
      <h1>Gestión de Usuarios</h1>
      <pre>{JSON.stringify(usuarios, null, 2)}</pre>
    </div>
  );
};

export default Usuarios;
