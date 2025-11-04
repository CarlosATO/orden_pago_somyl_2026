import { Navigate, useLocation } from 'react-router-dom';
import { isTokenValid } from '../utils/auth';

/**
 * Componente para proteger rutas que requieren autenticación.
 * Redirige al login si no hay token válido.
 */
const ProtectedRoute = ({ children }) => {
  const location = useLocation();
  const hasValidToken = isTokenValid();

  if (!hasValidToken) {
    // Guardar la ruta intentada para redirigir después del login
    sessionStorage.setItem('redirectAfterLogin', location.pathname);
    
    // Redirigir al login
    return <Navigate to="/login" replace />;
  }

  return children;
};

export default ProtectedRoute;
