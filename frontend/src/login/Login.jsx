// Componente de Login para autenticación de usuarios (estilizado, genérico)
import React, { useState } from 'react';
import './Login.css';

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const response = await fetch("http://localhost:5006/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        credentials: "include",
        body: `email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`,
      });
      if (response.ok) {
        // Redirigir a la raíz o a /usuarios tras login
        window.location.href = '/usuarios';
      } else {
        setError("Credenciales incorrectas o usuario no autorizado.");
      }
    } catch (err) {
      setError("Error de conexión con el servidor.");
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="brand">
          <div className="logo-placeholder" aria-hidden="true"></div>
          <h4 className="module-title">Gestión de Compras</h4>
          <h1 className="brand-title">Acceso al Sistema</h1>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Correo electrónico</span>
            <input
              type="email"
              placeholder="usuario@empresa.cl"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
          </label>

          <label className="field">
            <span>Contraseña</span>
            <input
              type="password"
              placeholder="Contraseña"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </label>

          <button className="btn-primary" type="submit">Ingresar al Sistema</button>

          {error && <div className="error">{error}</div>}
        </form>
      </div>
    </div>
  );
};

export default Login;
