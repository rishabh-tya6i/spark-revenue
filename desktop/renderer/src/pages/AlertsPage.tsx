import React, { useEffect, useState } from 'react';
import { getRecentAlerts, AlertDTO } from '../api/alertsApi';
import { Bell, Filter, Clock, Tag } from 'lucide-react';

const AlertsPage: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const data = await getRecentAlerts(50);
        setAlerts(data);
      } catch (err) {
        setError('Failed to fetch alerts');
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
    const poll = setInterval(fetchAlerts, 10000); // Poll every 10s
    return () => clearInterval(poll);
  }, []);

  const filteredAlerts = alerts.filter(a => 
    a.symbol.toLowerCase().includes(filter.toLowerCase()) || 
    a.alert_type.toLowerCase().includes(filter.toLowerCase()) ||
    a.message.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <h2 style={{ margin: 0 }}>System Alerts</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-card)', padding: '4px 12px', borderRadius: '8px', border: '1px solid var(--border)' }}>
          <Filter size={16} color="var(--text-secondary)" />
          <input 
            type="text" 
            placeholder="Filter alerts..." 
            value={filter} 
            onChange={(e) => setFilter(e.target.value)}
            style={{ border: 'none', background: 'transparent', padding: '4px' }}
          />
        </div>
      </div>

      {error && <div className="card" style={{ color: 'var(--danger)' }}>{error}</div>}
      
      <div className="card" style={{ padding: 0 }}>
        {loading && alerts.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading alerts...</div>
        ) : filteredAlerts.length > 0 ? (
          <div className="alerts-list">
            {filteredAlerts.map((alert) => (
              <div key={alert.id} className="alert-item">
                <div style={{ flex: 1 }}>
                  <div className="alert-meta" style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Tag size={12} /> {alert.symbol} ({alert.interval})
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={12} /> {new Date(alert.timestamp).toLocaleString()}
                    </span>
                    <span style={{ 
                      padding: '2px 8px', 
                      borderRadius: '4px', 
                      fontSize: '0.7rem', 
                      fontWeight: 700,
                      backgroundColor: alert.alert_type.includes('HIGH_CONFIDENCE') ? 'rgba(0, 255, 136, 0.1)' : 'rgba(255, 77, 77, 0.1)',
                      color: alert.alert_type.includes('HIGH_CONFIDENCE') ? '#00ff88' : '#ff4d4d'
                    }}>
                      {alert.alert_type}
                    </span>
                  </div>
                  <div className="alert-message" style={{ marginTop: '8px', fontSize: '1rem' }}>
                    {alert.message}
                  </div>
                </div>
                <div style={{ paddingLeft: '24px', textAlign: 'right' }}>
                  <div className="label">Importance</div>
                  <div style={{ fontWeight: 700, color: alert.importance > 0.8 ? 'var(--accent)' : 'var(--text-primary)' }}>
                    {(alert.importance * 100).toFixed(0)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <Bell size={48} style={{ opacity: 0.1, marginBottom: '16px' }} />
            <p>No alerts matching your criteria</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AlertsPage;
