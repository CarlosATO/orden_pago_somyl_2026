import { useEffect, useState } from 'react';
import './ChartsPresupuesto.css';
import { getAuthToken } from '../utils/auth';

function SimpleBar({ value, max, color, label }) {
  const height = max > 0 ? Math.round((Math.abs(value) / max) * 120) : 0;
  const formatted = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(value);
  const isNegative = Number(value) < 0;

  const rectColor = isNegative ? '#ef4444' : color;

  return (
    <div className="bar-item">
      <div
        className={`bar-rect ${isNegative ? 'bar-negative' : 'bar-positive'}`}
        style={{ height: `${height}px`, background: rectColor }}
        title={label + ': ' + formatted}
      />
      <div className="bar-label">{label}</div>
      {/* Mostrar cifra sólo abajo, en tamaño pequeño */}
      <div className={`bar-value small ${isNegative ? 'negative-number' : ''}`}>{formatted}</div>
    </div>
  );
}

export default function ChartsPresupuesto({ proyectoId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // No cargar nada si no hay proyecto seleccionado
    if (!proyectoId || proyectoId === '') {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    const fetchData = async () => {
      console.log('📊 Cargando gráficos para proyecto:', proyectoId);
      setLoading(true);
      setError(null);
      try {
        const token = getAuthToken();
        let url = '/api/graficos-presupuesto';
        if (proyectoId && proyectoId !== 'todos') url += `?proyecto_id=${proyectoId}`;

        const res = await fetch(url, {
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          }
        });

        if (!res.ok) {
          setError('Error al obtener datos');
          setLoading(false);
          return;
        }

        const payload = await res.json();
        if (payload && payload.success) {
          console.log('✅ Gráficos cargados correctamente');
          setData(payload.data);
        } else {
          setError(payload.message || 'Respuesta inválida');
        }
      } catch (e) {
        console.error('❌ Error al cargar gráficos:', e);
        setError(String(e));
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [proyectoId]);

  if (loading) return <div className="charts-loading">Cargando gráficos...</div>;
  if (error) return <div className="charts-error">{error}</div>;
  if (!data) return null;

  const groupMax = Math.max(data.venta_presupuestada, data.produccion_actual, data.gasto_presupuestado, data.gasto_actual, 1);
  const saldoMax = Math.max(Math.abs(data.saldo_presupuestado), Math.abs(data.saldo_actual), 1);

  return (
    <div className="charts-container">
      <div className="chart-card">
        <h3 className="chart-title">Comparación: Presupuesto inicial VS Actual</h3>
          <div className="bars-row">
          <div className="bars-group">
            <SimpleBar value={data.venta_presupuestada} max={groupMax} color="#2b79ff" label="Venta presupuestada" />
            <SimpleBar value={data.produccion_actual} max={groupMax} color="#34c38f" label="Producción actual" />
          </div>
          <div className="bars-group">
            <SimpleBar value={data.gasto_presupuestado} max={groupMax} color="#ff5b5b" label="Gasto presupuestado" />
            <SimpleBar value={data.gasto_actual} max={groupMax} color="#d6336c" label="Gasto actual" />
          </div>
        </div>
      </div>

      <div className="chart-card">
        <h3 className="chart-title">Comparación de Saldos</h3>
        <div className="bars-row balance-row">
          <div className="balance-item">
            <div className={`balance-rect ${data.saldo_presupuestado >= 0 ? 'positivo' : 'negativo'}`} style={{ height: `${Math.round((Math.abs(data.saldo_presupuestado) / saldoMax) * 120)}px` }}>
            </div>
            <div className="bar-label">Saldo presupuestado</div>
            <div className={`balance-number ${data.saldo_presupuestado < 0 ? 'negative-number' : ''}`}>{new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(data.saldo_presupuestado)}</div>
          </div>

          <div className="balance-item">
            <div className={`balance-rect ${data.saldo_actual >= 0 ? 'positivo' : 'negativo'}`} style={{ height: `${Math.round((Math.abs(data.saldo_actual) / saldoMax) * 120)}px` }}>
            </div>
            <div className="bar-label">Saldo actual</div>
            <div className={`balance-number ${data.saldo_actual < 0 ? 'negative-number' : ''}`}>{new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(data.saldo_actual)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
