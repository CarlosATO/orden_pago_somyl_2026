import { useState } from 'react';
import './Login.css';

const Login = ({ onLoginSuccess }) => {
  const [correo, setCorreo] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [infoMessage, setInfoMessage] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      console.log('Intentando login con:', { correo });
      
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ correo, password }),
      });

      console.log('Response status:', response.status);
      console.log('Response headers:', response.headers);

      const data = await response.json();
      console.log('Response data:', data);

      if (!response.ok) {
        throw new Error(data.message || 'Error al iniciar sesión');
      }

      // Si el login es exitoso, guardamos el token
      console.log('✅ Token recibido:', data.token ? `${data.token.substring(0, 20)}...` : 'NO HAY TOKEN');
      
      if (!data.token) {
        throw new Error('No se recibió token del servidor');
      }
      
      localStorage.setItem('authToken', data.token);
      if (rememberMe) {
        localStorage.setItem('rememberMe', 'true');
      }
      
      // Verificar que se guardó correctamente
      const savedToken = localStorage.getItem('authToken');
      console.log('✅ Token guardado correctamente:', savedToken ? 'SÍ' : 'NO');
      console.log('✅ Login exitoso, redirigiendo...');
      
      // Llamamos a la función del componente padre para actualizar el estado
      onLoginSuccess();

    } catch (err) {
      console.error('Error en login:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-left">
        <h1>Bienvenido<br/>Gestion compras</h1>
        <p>Plataforma para la gestión y seguimiento en tiempo real de sus órdenes de compra. Manteniendo  el control de sus adquisiciones y generando  reportes detallados.</p>
        <div className="social-icons">
          {/* Contact icon - links to the creator site. Update `contactUrl` if you want a different target. */}
          {
            /* default contact URL - change as needed */
          }
          <a
            className="contact-link"
            href="https://datix.cl"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Contacto del autor"
          >
            <i className="fa-solid fa-address-card" aria-hidden="true"></i>
          </a>
        </div>
      </div>

      <div className="login-box">
        <h2>Sign in</h2>
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label htmlFor="correo">Email Address</label>
            <input
              type="email"
              id="correo"
              value={correo}
              onChange={(e) => setCorreo(e.target.value)}
              required
              placeholder="tu.correo@ejemplo.com"
            />
          </div>
          <div className="input-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="********"
            />
          </div>
          
          <div className="remember-me">
            <input
              type="checkbox"
              id="remember"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            />
            <label htmlFor="remember">Remember Me</label>
          </div>

          {error && <p className="error-message">{error}</p>}
          
          <button type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign in now'}
          </button>
          
          <p className="forgot-password">
            <a href="#" onClick={(e) => { e.preventDefault(); setInfoMessage('solicite el acceso a su jefatura directa'); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
              Lost your password?
            </a>
          </p>
          {infoMessage && (
            <p className="info-message">{infoMessage}</p>
          )}
          
          <p className="terms">
            By clicking on "Sign in now" you agree to <a href="#">Terms of Service</a> | <a href="#">Privacy Policy</a>
          </p>
        </form>
      </div>
    </div>
  );
};

export default Login;