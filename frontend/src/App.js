import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Login from './login/Login';
import Usuarios from './usuarios/Usuarios';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/usuarios" element={<Usuarios />} />
        {/* Agrega aquí más rutas según los módulos */}
      </Routes>
    </Router>
  );
}

export default App;
