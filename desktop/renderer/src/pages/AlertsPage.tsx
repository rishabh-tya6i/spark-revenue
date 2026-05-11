import React, { useEffect, useState } from 'react';
import { getRecentAlerts, AlertDTO } from '../api/alertsApi';
import { Bell, Filter, Clock, Tag } from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';

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
    <PageContainer title="System Alerts">
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-surface)', padding: '6px 16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', width: '300px' }}>
          <Filter size={16} className="text-muted" />
          <input 
            type="text" 
            placeholder="Filter alerts..." 
            value={filter} 
            onChange={(e) => setFilter(e.target.value)}
            style={{ border: 'none', background: 'transparent', padding: '4px', width: '100%' }}
          />
        </div>
      </div>

      {error && <Card className="text-danger" style={{ marginBottom: '24px' }}>{error}</Card>}
      
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {loading && alerts.length === 0 ? (
          <div style={{ padding: '48px', textAlign: 'center' }} className="text-muted">Loading signals from archive...</div>
        ) : filteredAlerts.length > 0 ? (
          <div className="alerts-list">
            {filteredAlerts.map((alert) => (
              <div key={alert.id} className="alert-item" style={{ borderBottom: '1px solid var(--border)', padding: '20px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <div className="alert-meta" style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }} className="text-xs text-muted text-mono">
                      <Tag size={12} /> {alert.symbol} ({alert.interval})
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }} className="text-xs text-muted text-mono">
                      <Clock size={12} /> {new Date(alert.timestamp).toLocaleString()}
                    </span>
                    <Badge variant={alert.alert_type.includes('HIGH_CONFIDENCE') ? 'success' : 'danger'}>
                      {alert.alert_type}
                    </Badge>
                  </div>
                  <div className="alert-message" style={{ fontSize: '1rem', fontWeight: 500 }}>
                    {alert.message}
                  </div>
                </div>
                <div style={{ paddingLeft: '32px', textAlign: 'right', minWidth: '100px' }}>
                  <div className="text-xs text-muted text-mono">IMPORTANCE</div>
                  <div className="text-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: alert.importance > 0.8 ? 'var(--primary)' : 'var(--foreground)' }}>
                    {(alert.importance * 100).toFixed(0)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '64px', textAlign: 'center' }} className="text-muted">
            <Bell size={48} style={{ opacity: 0.1, marginBottom: '16px', margin: '0 auto' }} />
            <p>No signals detected matching current filters</p>
          </div>
        )}
      </Card>
    </PageContainer>
  );
};

export default AlertsPage;
