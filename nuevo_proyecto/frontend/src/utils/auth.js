// Helper pequeño para centralizar el manejo del token de autenticación
const TOKEN_KEY = 'authToken';

export function getAuthToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch (e) {
    console.error('Error al leer authToken:', e);
    return null;
  }
}

export function setAuthToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch (e) {
    console.error('Error al guardar authToken:', e);
  }
}

export function removeAuthToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch (e) {
    console.error('Error al remover authToken:', e);
  }
}

export default { getAuthToken, setAuthToken, removeAuthToken };
