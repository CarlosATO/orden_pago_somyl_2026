// Configuración de la API
// En producción usa rutas relativas (mismo dominio)
// En desarrollo usa localhost:5001

const API_BASE_URL = import.meta.env.MODE === 'production' 
  ? '/api' 
  : 'http://localhost:5001/api';

export default API_BASE_URL;
