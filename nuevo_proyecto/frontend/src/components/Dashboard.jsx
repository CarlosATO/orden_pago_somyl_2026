import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './Dashboard.css';

function Dashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:5001/api/dashboard/', {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.data.success) {
        setDashboardData(response.data.data);
        console.log('Dashboard data:', response.data.data);
      }
    } catch (err) {
      console.error('Error al cargar dashboard:', err);
      setError('Error al cargar los datos del dashboard');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    if (!value && value !== 0) return '$0';
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatNumber = (value) => {
    if (!value && value !== 0) return '0';
    return new Intl.NumberFormat('es-CL').format(value);
  };

  const getEstadoBadge = (estado) => {
    const badges = {
      'riesgo': { icon: '🔴', text: 'Riesgo', class: 'badge-riesgo' },
      'alerta': { icon: '🟡', text: 'Alerta', class: 'badge-alerta' },
      'ok': { icon: '🟢', text: 'OK', class: 'badge-ok' }
    };
    return badges[estado] || badges['ok'];
  };

  if (loading) {
    return (
      <div className="content">
        <div className="loading-dashboard">
          <i className="fas fa-spinner fa-spin"></i>
          <p>Cargando Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="content">
        <div className="error-dashboard">
          <i className="fas fa-exclamation-triangle"></i>
          <p>{error}</p>
          <button onClick={fetchDashboardData} className="btn-retry">
            <i className="fas fa-redo"></i> Reintentar
          </button>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return <div className="content">No hay datos disponibles</div>;
  }

  const { kpis, top_proveedores, top_proyectos, oc_sin_recepcionar, evolucion_deuda, distribucion_deuda, ejecucion_presupuestaria } = dashboardData;

  return (
    <div className="content dashboard-container">
      <div className="dashboard-header">
        <h1><i className="fas fa-chart-line"></i> Dashboard - Gestión de Compras</h1>
        <button onClick={fetchDashboardData} className="btn-refresh">
          <i className="fas fa-sync-alt"></i> Actualizar
        </button>
      </div>

      {/* SECCIÓN 1: KPIs PRINCIPALES */}
      <div className="kpis-grid">
        {/* Montos Pendientes de Pago */}
        <div className="kpi-card kpi-danger">
          <div className="kpi-icon">
            <i className="fas fa-hand-holding-usd"></i>
          </div>
          <div className="kpi-content">
            <h3>Montos Pendientes de Pago</h3>
            <div className="kpi-detail" style={{marginTop: '10px', gap: '12px'}}>
              <div style={{padding: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '6px'}}>
                <span style={{fontSize: '0.85em', opacity: 0.9}}>💵 Pendientes</span>
                <div style={{fontSize: '1.3em', fontWeight: 'bold', marginTop: '4px'}}>
                  {formatCurrency(kpis.monto_pendiente || 0)}
                </div>
                <span style={{fontSize: '0.75em', opacity: 0.8}}>{kpis.pendientes || 0} órdenes</span>
              </div>
              <div style={{padding: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '6px'}}>
                <span style={{fontSize: '0.85em', opacity: 0.9}}>💳 Saldo de Abonos</span>
                <div style={{fontSize: '1.3em', fontWeight: 'bold', marginTop: '4px'}}>
                  {formatCurrency(kpis.saldo_abonos || 0)}
                </div>
                <span style={{fontSize: '0.75em', opacity: 0.8}}>{kpis.con_abonos || 0} órdenes</span>
              </div>
              <div style={{padding: '10px', background: 'rgba(255,255,255,0.15)', borderRadius: '6px', borderTop: '2px solid rgba(255,255,255,0.3)'}}>
                <span style={{fontSize: '0.9em', fontWeight: 'bold'}}>🎯 TOTAL GENERAL</span>
                <div style={{fontSize: '1.6em', fontWeight: 'bold', marginTop: '4px'}}>
                  {formatCurrency(kpis.total_general || 0)}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Saldo Presupuestario */}
        <div className={`kpi-card ${kpis.saldo_presupuestario_total < 0 ? 'kpi-danger' : 'kpi-success'}`}>
          <div className="kpi-icon">
            <i className="fas fa-balance-scale"></i>
          </div>
          <div className="kpi-content">
            <h3>Saldo Presupuestario Total</h3>
            <div className="kpi-value">{formatCurrency(kpis.saldo_presupuestario_total)}</div>
            <div className="kpi-detail">
              <span><i className="fas fa-exclamation-triangle"></i> Proyectos en riesgo: {kpis.proyectos_en_riesgo}</span>
            </div>
          </div>
        </div>

        {/* Documentos Pendientes */}
        <div className="kpi-card kpi-warning">
          <div className="kpi-icon">
            <i className="fas fa-bell"></i>
          </div>
          <div className="kpi-content">
            <h3>Documentos Pendientes</h3>
            <div className="kpi-value">{kpis.documentos_pendientes}</div>
            <div className="kpi-detail">
              <span><i className="fas fa-file-invoice-dollar"></i> Facturas: {kpis.facturas_pendientes}</span>
              <span><i className="fas fa-truck-loading"></i> OC antiguas: {kpis.oc_antiguas}</span>
              <span><i className="fas fa-clock"></i> Pagos vencidos: {kpis.pagos_vencidos}</span>
            </div>
          </div>
        </div>

        {/* OC Mes Actual */}
        <div className="kpi-card kpi-info">
          <div className="kpi-icon">
            <i className="fas fa-shopping-cart"></i>
          </div>
          <div className="kpi-content">
            <h3>Órdenes de Compra (Mes)</h3>
            <div className="kpi-value">{kpis.oc_mes_actual}</div>
            <div className="kpi-detail">
              <span><i className="fas fa-dollar-sign"></i> Monto: {formatCurrency(kpis.monto_oc_mes)}</span>
              <span><i className="fas fa-check-circle"></i> Recepciones: {kpis.recepciones_mes}</span>
            </div>
          </div>
        </div>
      </div>

      {/* SECCIÓN 2: TOP RANKINGS */}
      <div className="rankings-grid">
        {/* Top 5 Proveedores */}
        <div className="ranking-card">
          <div className="ranking-header">
            <h2><i className="fas fa-trophy"></i> Top 5 Proveedores - Mayor Deuda</h2>
          </div>
          <div className="ranking-table-container">
            {top_proveedores && top_proveedores.length > 0 ? (
              <table className="ranking-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Proveedor</th>
                    <th>Deuda</th>
                    <th>N° OP</th>
                    <th>Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {top_proveedores.map((prov, index) => (
                    <tr key={index}>
                      <td className="rank-number">{index + 1}</td>
                      <td className="proveedor-name">{prov.proveedor}</td>
                      <td className="deuda-amount">{formatCurrency(prov.deuda)}</td>
                      <td className="op-count">{prov.num_op} OP</td>
                      <td>
                        <button 
                          className="btn-ver-detalle"
                          onClick={() => navigate('/ordenes-pago')}
                          title="Ver detalle en Órdenes de Pago"
                        >
                          <i className="fas fa-eye"></i>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="no-data">No hay datos de proveedores</p>
            )}
          </div>
        </div>

        {/* Top 5 Proyectos Críticos */}
        <div className="ranking-card">
          <div className="ranking-header">
            <h2><i className="fas fa-project-diagram"></i> Top 5 Proyectos - Situación Crítica</h2>
          </div>
          <div className="ranking-table-container">
            {top_proyectos && top_proyectos.length > 0 ? (
              <table className="ranking-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Proyecto</th>
                    <th>Monto Total</th>
                    <th>Deuda</th>
                    <th>Saldo Ppto.</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {top_proyectos.map((proy, index) => {
                    const estadoBadge = getEstadoBadge(proy.estado);
                    return (
                      <tr key={index}>
                        <td className="rank-number">{index + 1}</td>
                        <td className="proyecto-name">{proy.proyecto}</td>
                        <td className="monto-total">{formatCurrency(proy.monto_total)}</td>
                        <td className="deuda-amount">{formatCurrency(proy.deuda)}</td>
                        <td className={proy.saldo_presupuesto < 0 ? 'saldo-negativo' : 'saldo-positivo'}>
                          {formatCurrency(proy.saldo_presupuesto)}
                        </td>
                        <td>
                          <span className={`estado-badge ${estadoBadge.class}`}>
                            {estadoBadge.icon} {estadoBadge.text}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                  <tr className="totales-row">
                    <td colSpan="2" className="totales-label">TOTALES</td>
                    <td className="totales-value">
                      {formatCurrency(top_proyectos.reduce((sum, p) => sum + (p.monto_total || 0), 0))}
                    </td>
                    <td className="totales-value">
                      {formatCurrency(top_proyectos.reduce((sum, p) => sum + (p.deuda || 0), 0))}
                    </td>
                    <td colSpan="2"></td>
                  </tr>
                </tbody>
              </table>
            ) : (
              <p className="no-data">No hay datos de proyectos</p>
            )}
          </div>
        </div>
      </div>

      {/* SECCIÓN 3: ÓRDENES SIN RECEPCIONAR */}
      {oc_sin_recepcionar && oc_sin_recepcionar.length > 0 && (
        <div className="oc-pendientes-section">
          <div className="section-header">
            <h2><i className="fas fa-clock"></i> Órdenes de Compra sin Recepcionar (+15 días)</h2>
            <span className="badge-count">{oc_sin_recepcionar.length} órdenes</span>
          </div>
          <div className="oc-pendientes-grid">
            {oc_sin_recepcionar.slice(0, 6).map((oc, index) => (
              <div key={index} className="oc-pendiente-card">
                <div className="oc-header">
                  <span className="oc-numero">OC #{oc.numero_orden}</span>
                  <span className={`oc-dias ${oc.dias_pendiente > 30 ? 'dias-critico' : 'dias-alerta'}`}>
                    {oc.dias_pendiente} días
                  </span>
                </div>
                <div className="oc-body">
                  <p><strong>Proveedor:</strong> {oc.proveedor}</p>
                  <p><strong>Proyecto:</strong> {oc.proyecto}</p>
                  <p><strong>Monto:</strong> {formatCurrency(oc.monto_total)}</p>
                </div>
                <button 
                  className="btn-recepcionar"
                  onClick={() => navigate('/ingresos')}
                >
                  <i className="fas fa-truck-loading"></i> Recepcionar
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECCIÓN 4: GRÁFICOS */}
      <div className="charts-section">
        {/* Evolución Deuda */}
        {evolucion_deuda && evolucion_deuda.length > 0 && (
          <div className="chart-card chart-full">
            <div className="chart-header">
              <h2><i className="fas fa-chart-line"></i> Evolución de Deuda (Últimos 6 meses)</h2>
            </div>
            <div className="chart-body">
              <div className="simple-line-chart">
                {evolucion_deuda.map((item, index) => {
                  const maxDeuda = Math.max(...evolucion_deuda.map(d => d.deuda));
                  const height = (item.deuda / maxDeuda) * 100;
                  
                  return (
                    <div key={index} className="chart-bar-container">
                      <div 
                        className="chart-bar"
                        style={{ height: `${height}%` }}
                        title={formatCurrency(item.deuda)}
                      >
                        <span className="bar-value">{formatCurrency(item.deuda)}</span>
                      </div>
                      <span className="bar-label">{item.mes}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Ejecución Presupuestaria */}
        {ejecucion_presupuestaria && ejecucion_presupuestaria.length > 0 && (
          <div className="chart-card chart-full">
            <div className="chart-header">
              <h2><i className="fas fa-chart-bar"></i> Ejecución Presupuestaria por Proyecto</h2>
            </div>
            <div className="chart-body">
              <div className="budget-bars">
                {ejecucion_presupuestaria.slice(0, 8).map((proyecto, index) => (
                  <div key={index} className="budget-bar-row">
                    <div className="budget-proyecto-name">{proyecto.proyecto}</div>
                    <div className="budget-bar-container">
                      <div 
                        className="budget-bar budget-bar-presupuesto"
                        style={{ width: '100%' }}
                      >
                        <span className="budget-label">Ppto: {formatCurrency(proyecto.presupuesto)}</span>
                      </div>
                      <div 
                        className={`budget-bar budget-bar-real ${proyecto.porcentaje_ejecutado > 100 ? 'over-budget' : ''}`}
                        style={{ width: `${Math.min(proyecto.porcentaje_ejecutado, 100)}%` }}
                      >
                        <span className="budget-label">Real: {formatCurrency(proyecto.real)} ({proyecto.porcentaje_ejecutado}%)</span>
                      </div>
                    </div>
                    <div className={`budget-saldo ${proyecto.saldo < 0 ? 'saldo-negativo' : 'saldo-positivo'}`}>
                      {formatCurrency(proyecto.saldo)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* SECCIÓN 5: ACCESOS RÁPIDOS */}
      <div className="quick-actions-section">
        <h2><i className="fas fa-bolt"></i> Accesos Rápidos</h2>
        <div className="quick-actions-grid">
          <button className="quick-action-btn btn-primary" onClick={() => navigate('/ordenes')}>
            <i className="fas fa-shopping-cart"></i>
            <span>Nueva Orden de Compra</span>
          </button>
          <button className="quick-action-btn btn-success" onClick={() => navigate('/ordenes-pago')}>
            <i className="fas fa-dollar-sign"></i>
            <span>Nueva Orden de Pago</span>
          </button>
          <button className="quick-action-btn btn-info" onClick={() => navigate('/ingresos')}>
            <i className="fas fa-truck-loading"></i>
            <span>Recepcionar Material</span>
          </button>
          <button className="quick-action-btn btn-warning" onClick={() => navigate('/estado-presupuesto')}>
            <i className="fas fa-chart-pie"></i>
            <span>Estado Presupuesto</span>
          </button>
          <button className="quick-action-btn btn-secondary" onClick={() => navigate('/documentos-pendientes')}>
            <i className="fas fa-file-alt"></i>
            <span>Documentos Pendientes</span>
          </button>
          <button className="quick-action-btn btn-dark" onClick={() => navigate('/ordenes')}>
            <i className="fas fa-search"></i>
            <span>Buscar Órdenes</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
