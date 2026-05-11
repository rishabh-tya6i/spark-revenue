import React, { useEffect, useState, useCallback } from 'react';
import { 
  getOrchestrationRuns, 
  getOrchestrationRun, 
  OrchestrationRun 
} from '../api/orchestrationApi';
import PageContainer from '../components/layout/PageContainer';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { 
  History, 
  RefreshCw, 
  Filter, 
  ChevronRight, 
  Clock, 
  Database, 
  Cpu, 
  Zap, 
  RotateCcw,
  AlertCircle
} from 'lucide-react';
import { StatusBadge } from '../components/data/StatusBadge';
import { EmptyState } from '../components/data/EmptyState';
import { KeyValueGrid, KeyValueItem } from '../components/data/KeyValueGrid';

const SummaryRenderer: React.FC<{ data: any }> = ({ data }) => {
  if (!data || typeof data !== 'object') return <span>{String(data)}</span>;

  if (Array.isArray(data)) {
    return (
      <div className="flex flex-wrap gap-xs">
        {data.map((item, i) => (
          <span key={i} className="glass-panel text-xs text-mono p-xs" style={{ borderRadius: '4px' }}>
            {typeof item === 'object' ? <SummaryRenderer data={item} /> : String(item)}
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className="flex-col gap-sm">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="flex-col gap-xs">
          <div className="text-xs text-muted text-mono uppercase">{key.replace(/_/g, ' ')}</div>
          <div style={{ paddingLeft: '8px', borderLeft: '1px solid var(--border-subtle)' }}>
            {typeof value === 'object' ? <SummaryRenderer data={value} /> : <span className="text-sm text-mono">{String(value)}</span>}
          </div>
        </div>
      ))}
    </div>
  );
};

const RunsPage: React.FC = () => {
  const [runs, setRuns] = useState<OrchestrationRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<OrchestrationRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [filter, setFilter] = useState<string>('');
  const [limit, setLimit] = useState<number>(50);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getOrchestrationRuns(filter || undefined, limit);
      setRuns(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch runs');
    } finally {
      setLoading(false);
    }
  }, [filter, limit]);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  const handleSelectRun = async (run: OrchestrationRun) => {
    setSelectedRun(run);
    setDetailLoading(true);
    setDetailError(null);
    try {
      const fullRun = await getOrchestrationRun(run.id);
      setSelectedRun(fullRun);
    } catch (err: any) {
      setDetailError(err.message || 'Failed to fetch run details');
      console.error('Failed to fetch run detail', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const getRunTypeIcon = (type: string) => {
    switch (type) {
      case 'train': return <Database size={16} />;
      case 'inference': return <Cpu size={16} />;
      case 'execution': return <Zap size={16} />;
      case 'cycle': return <RotateCcw size={16} />;
      default: return <History size={16} />;
    }
  };

  return (
    <PageContainer title="Orchestration Runs">
      <div className="flex-col gap-md" style={{ height: 'calc(100vh - 180px)' }}>
        
        {/* Toolbar */}
        <div className="flex justify-between items-center">
          <div className="flex gap-md items-center">
            <div className="glass-panel flex items-center gap-sm p-xs" style={{ borderRadius: 'var(--radius-md)' }}>
              <Filter size={16} className="text-muted" />
              <select 
                className="input-void" 
                style={{ border: 'none', padding: '4px', background: 'transparent' }}
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                aria-label="Filter by type"
              >
                <option value="">ALL TYPES</option>
                <option value="train">TRAIN</option>
                <option value="inference">INFERENCE</option>
                <option value="execution">EXECUTION</option>
                <option value="cycle">CYCLE</option>
              </select>
            </div>
            <select 
              className="input-void"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              style={{ width: '80px' }}
            >
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
          <Button variant="outline" onClick={fetchRuns} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            <span style={{ marginLeft: '8px' }}>Refresh</span>
          </Button>
        </div>

        {error && (
          <div className="glass-panel text-danger" style={{ padding: '12px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertCircle size={20} />
            {error}
          </div>
        )}

        {/* Main Split Layout */}
        <div className="flex gap-lg flex-1" style={{ minHeight: 0 }}>
          
          {/* Left: Run List */}
          <Card className="flex-col" style={{ flex: 2, padding: 0, overflow: 'hidden' }}>
            <div className="table-container flex-1 overflow-auto">
              <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead className="sticky-header">
                  <tr>
                    <th>ID</th>
                    <th>TYPE</th>
                    <th>STATUS</th>
                    <th>UNIVERSE</th>
                    <th>COUNTS</th>
                    <th>CREATED</th>
                    <th style={{ width: '40px' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map(run => (
                    <tr 
                      key={run.id} 
                      onClick={() => handleSelectRun(run)}
                      data-testid={`run-row-${run.id}`}
                      style={{ 
                        cursor: 'pointer',
                        backgroundColor: selectedRun?.id === run.id ? 'rgba(245, 158, 11, 0.1)' : 'transparent',
                        borderLeft: selectedRun?.id === run.id ? '3px solid var(--primary)' : '3px solid transparent'
                      }}
                    >
                      <td className="text-mono text-xs">{run.id}</td>
                      <td>
                        <div className="flex items-center gap-sm">
                          <span className="text-muted">{getRunTypeIcon(run.run_type)}</span>
                          <span className="text-xs text-mono uppercase">{run.run_type}</span>
                        </div>
                      </td>
                      <td><StatusBadge type="run" status={run.status} /></td>
                      <td>
                        <div className="text-xs text-mono">
                          {run.mode} <span className="text-muted">/</span> {run.interval}
                        </div>
                      </td>
                      <td>
                        <div className="flex gap-xs">
                          <Badge variant="primary" title="Ready">{run.ready_symbols_count}</Badge>
                          <Badge variant="success" title="Success">{run.success_count}</Badge>
                          {run.failed_count > 0 && <Badge variant="danger" title="Failed">{run.failed_count}</Badge>}
                        </div>
                      </td>
                      <td className="text-xs text-muted">
                        {new Date(run.created_ts).toLocaleString(undefined, { 
                          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' 
                        })}
                      </td>
                      <td><ChevronRight size={14} className="text-muted" /></td>
                    </tr>
                  ))}
                  {!loading && runs.length === 0 && (
                    <tr><td colSpan={7}><EmptyState message="No orchestration runs found." /></td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Right: Detail Panel */}
          <Card className="flex-col" style={{ flex: 1.5, overflow: 'hidden' }}>
            {!selectedRun ? (
              <EmptyState message="Select a run to view details" icon={<History size={48} strokeWidth={1} style={{ opacity: 0.5 }} />} />
            ) : (
              <div className="flex-col gap-lg p-xs" style={{ flex: 1, overflow: 'auto' }}>
                <div className="flex justify-between items-start">
                  <div>
                    <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>Run #{selectedRun.id}</h3>
                    <div className="text-xs text-muted text-mono uppercase" style={{ marginTop: '4px' }}>
                      {selectedRun.run_type} | {selectedRun.mode} | {selectedRun.interval}
                    </div>
                  </div>
                  <StatusBadge type="run" status={selectedRun.status} />
                </div>

                {selectedRun.reason && (
                  <div className="glass-panel p-sm" style={{ borderLeft: '4px solid var(--danger)' }}>
                    <div className="text-xs text-muted text-mono mb-xs">FAILURE REASON</div>
                    <div className="text-sm">{selectedRun.reason}</div>
                  </div>
                )}

                <KeyValueGrid cols={2}>
                  <KeyValueItem label="Selected Symbols" value={selectedRun.selected_symbols_count} />
                  <KeyValueItem label="Ready Symbols" value={selectedRun.ready_symbols_count} />
                  <KeyValueItem label="Success / Skipped" value={`${selectedRun.success_count} / ${selectedRun.skipped_count}`} valueColor="var(--success)" />
                  <KeyValueItem label="Failed" value={selectedRun.failed_count} valueColor={selectedRun.failed_count > 0 ? 'var(--danger)' : undefined} />
                </KeyValueGrid>

                <div>
                  <div className="text-xs text-muted text-mono mb-md flex items-center gap-sm">
                    <Clock size={14} /> EXECUTION SUMMARY
                  </div>
                  <div className="glass-panel p-md">
                    {detailLoading ? (
                      <div className="text-center py-8"><RefreshCw className="animate-spin text-muted" /></div>
                    ) : (
                      <SummaryRenderer data={selectedRun.summary} />
                    )}
                  </div>
                </div>

                {detailError && (
                  <div className="glass-panel text-danger" style={{ padding: '12px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <AlertCircle size={20} />
                    {detailError}
                  </div>
                )}

                <div className="text-xs text-muted text-mono" style={{ marginTop: 'auto', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
                  CREATED AT: {new Date(selectedRun.created_ts).toISOString()}
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </PageContainer>
  );
};

export default RunsPage;
