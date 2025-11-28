import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAuthToken } from '../utils/auth';
import './ChangePassword.css';

const ChangePassword = (props) => {
  // onClose: función opcional para cerrar modal cuando se usa como overlay
  // Si onClose está presente, el componente no hará navigate al dashboard al terminar;
  // en su lugar llamará onClose().
  const { onClose } = props || {};
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState({ type: '', text: '' });
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const validar = () => {
    if (!currentPassword) {
      setMessage({ type: 'error', text: 'Ingrese su contraseña actual' });
      return false;
    }
    if (!newPassword || newPassword.length < 8) {
      setMessage({ type: 'error', text: 'La nueva contraseña debe tener al menos 8 caracteres' });
      return false;
    }
    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: 'Las contraseñas no coinciden' });
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validar()) return;

    setLoading(true);
    try {
      const token = getAuthToken();
      const response = await fetch('/api/usuarios/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setMessage({ type: 'success', text: data.message || 'Contraseña actualizada correctamente' });
        // Si nos pasaron onClose, cerrar modal; si no, navegar al dashboard
        if (onClose && typeof onClose === 'function') {
          setTimeout(() => onClose(), 800);
        } else {
          setTimeout(() => navigate('/dashboard', { replace: true }), 1000);
        }
      } else {
        setMessage({ type: 'error', text: data.message || 'Error al cambiar la contraseña' });
      }
    } catch (err) {
      console.error(err);
      setMessage({ type: 'error', text: 'Error de conexión' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="change-password-page">
      <div className="change-password-card">
        <h2>Cambiar contraseña</h2>
        <p>Si ha ingresado con una contraseña temporal, ingrese esa contraseña en "Actual" y defina su nueva contraseña.</p>

        {message.text && (
          <div className={`message ${message.type}`}>{message.text}</div>
        )}

        <form onSubmit={handleSubmit} className="change-password-form">
          <label>Contraseña actual</label>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder="Contraseña actual"
          />

          <label>Nueva contraseña</label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Nueva contraseña (mínimo 8 caracteres)"
          />

          <label>Confirmar nueva contraseña</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirmar nueva contraseña"
          />

          <div className="actions">
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Guardando...' : 'Guardar nueva contraseña'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ChangePassword;
