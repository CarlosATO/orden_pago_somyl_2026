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
    // Redirigir al login, pasando la ubicación actual en el state
    // para poder redirigir de vuelta después del login
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return children;
};

export default ProtectedRoute;
