// Helper pequeño para centralizar el manejo del token de autenticación
// Usa sessionStorage para que se borre automáticamente al cerrar la pestaña/navegador
const TOKEN_KEY = 'authToken';

export function getAuthToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch (e) {
    console.error('Error al leer authToken:', e);
    return null;
  }
}

export function setAuthToken(token) {
  try {
    if (token) {
      sessionStorage.setItem(TOKEN_KEY, token);
      // Guardar también la fecha de creación para validar expiración
      sessionStorage.setItem('tokenCreatedAt', Date.now().toString());
    } else {
      sessionStorage.removeItem(TOKEN_KEY);
      sessionStorage.removeItem('tokenCreatedAt');
    }
  } catch (e) {
    console.error('Error al guardar authToken:', e);
  }
}

export function removeAuthToken() {
  try {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem('tokenCreatedAt');
    // NO removemos rememberMe y rememberedEmail porque esos SÍ deben persistir
    // localStorage.removeItem('rememberMe');
    // localStorage.removeItem('rememberedEmail');
  } catch (e) {
    console.error('Error al remover authToken:', e);
  }
}

/**
 * Valida si el token existe y no ha expirado
 * @returns {boolean} true si el token es válido
 */
export function isTokenValid() {
  const token = getAuthToken();
  
  if (!token) {
    return false;
  }
  
  // Verificar expiración (opcional: 24 horas)
  const tokenCreatedAt = sessionStorage.getItem('tokenCreatedAt');
  if (tokenCreatedAt) {
    const tokenAge = Date.now() - parseInt(tokenCreatedAt);
    const maxAge = 24 * 60 * 60 * 1000; // 24 horas en milisegundos
    
    if (tokenAge > maxAge) {
      console.warn('Token expirado');
      removeAuthToken();
      return false;
    }
  }
  
  return true;
}

/**
 * Decodifica el payload del JWT (sin validar firma)
 * Solo para leer información del usuario
 */
export function decodeToken(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    console.error('Error decodificando token:', e);
    return null;
  }
}

export default { getAuthToken, setAuthToken, removeAuthToken, isTokenValid, decodeToken };

/**
 * Obtiene la información del usuario actual desde el token
 * @returns {object|null} Objeto con datos del usuario o null si no hay token
 */
export function getCurrentUser() {
  const token = getAuthToken();
  if (!token) return null;
  
  const payload = decodeToken(token);
  if (!payload) return null;
  
  // El token incluye: sub (user_id), email, nombre, etc.
  return {
    id: payload.sub,
    email: payload.email,
    nombre: payload.nombre || payload.email?.split('@')[0] || 'Usuario'
  };
}
