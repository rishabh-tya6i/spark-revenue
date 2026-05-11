import React, { useEffect, useState } from 'react';
import { getRecentAlerts, AlertDTO } from '../api/alertsApi';
import { Bell, Filter, Clock, Tag, Activity } from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import { EmptyState } from '../components/data/EmptyState';

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
      <div className="flex justify-end mb-lg">
        <div className="flex items-center gap-sm bg-surface p-xs glass-panel" style={{ width: '300px' }}>
          <Filter size={16} className="text-muted" />
          <input 
            type="text" 
            placeholder="Filter alerts..." 
            className="input-void"
            style={{ border: 'none', background: 'transparent', padding: '4px', width: '100%' }}
            value={filter} 
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
      </div>

      {error && <Card className="text-danger" style={{ marginBottom: '24px' }}>{error}</Card>}
      
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {loading && alerts.length === 0 ? (
          <EmptyState message="Loading signals from archive..." icon={<Activity className="animate-spin" size={40} />} />
        ) : filteredAlerts.length > 0 ? (
          <div className="alerts-list">
            {filteredAlerts.map((alert) => (
              <div key={alert.id} className="flex justify-between items-center p-lg border-b border-border">
                <div className="flex-1">
                  <div className="flex gap-md items-center mb-sm">
                    <span className="flex items-center gap-xs text-xs text-muted text-mono">
                      <Tag size={12} /> {alert.symbol} ({alert.interval})
                    </span>
                    <span className="flex items-center gap-xs text-xs text-muted text-mono">
                      <Clock size={12} /> {new Date(alert.timestamp).toLocaleString()}
                    </span>
                    <Badge variant={alert.alert_type.includes('HIGH_CONFIDENCE') ? 'success' : 'danger'}>
                      {alert.alert_type}
                    </Badge>
                  </div>
                  <div className="text-lg font-medium">
                    {alert.message}
                  </div>
                </div>
                <div className="flex flex-col items-end min-w-[100px]">
                  <div className="text-xs text-muted text-mono">IMPORTANCE</div>
                  <div className="text-mono text-xl font-bold" style={{ color: alert.importance > 0.8 ? 'var(--primary)' : 'var(--foreground)' }}>
                    {(alert.importance * 100).toFixed(0)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState message="No signals detected matching current filters" icon={<Bell size={48} strokeWidth={1} style={{ opacity: 0.1 }} />} />
        )}
      </Card>
    </PageContainer>
  );
};

export default AlertsPage;
