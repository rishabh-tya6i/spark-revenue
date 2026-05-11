import React, { useEffect, useState, useCallback } from 'react';
import { useSymbol } from '../context/SymbolContext';
import { 
  getExecutionReadiness, 
  getExecutionGuardrails, 
  getExecutionOverrides, 
  setExecutionOverride, 
  clearExecutionOverride, 
  getExecutionDispatches, 
  getExecutionStaleness,
  ReadinessState,
  GuardrailSummary,
  ExecutionOverride,
  DispatchRecord,
  StalenessState
} from '../api/orchestrationApi';
import PageContainer from '../components/layout/PageContainer';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { 
  ShieldCheck, 
  UserCog, 
  Send, 
  Clock, 
  CheckCircle2, 
  Plus,
  Trash2,
  AlertCircle
} from 'lucide-react';
import { SectionHeader } from '../components/data/SectionHeader';
import { StatusBadge } from '../components/data/StatusBadge';
import { KeyValueGrid, KeyValueItem } from '../components/data/KeyValueGrid';
import { EmptyState } from '../components/data/EmptyState';

const ExecutionPage: React.FC = () => {
  const { interval, symbol: contextSymbol } = useSymbol();
  
  // States for each section
  const [readiness, setReadiness] = useState<ReadinessState | null>(null);
  const [guardrails, setGuardrails] = useState<GuardrailSummary | null>(null);
  const [overrides, setOverrides] = useState<ExecutionOverride[]>([]);
  const [dispatches, setDispatches] = useState<DispatchRecord[]>([]);
  const [staleness, setStaleness] = useState<StalenessState | null>(null);
  
  // Loading & Error states
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string | null>>({});

  // Override Form State
  const [newOverride, setNewOverride] = useState({
    symbol: contextSymbol || '',
    action: 'SKIP',
    reason: ''
  });

  const fetchData = useCallback(async (section?: string) => {
    const sections = section ? [section] : ['readiness', 'guardrails', 'overrides', 'dispatches', 'staleness'];
    
    sections.forEach(async (s) => {
      setLoading(prev => ({ ...prev, [s]: true }));
      setErrors(prev => ({ ...prev, [s]: null }));
      try {
        switch (s) {
          case 'readiness':
            const r = await getExecutionReadiness(undefined, interval, true);
            setReadiness(r);
            break;
          case 'guardrails':
            const g = await getExecutionGuardrails(undefined, interval, true);
            setGuardrails(g);
            break;
          case 'overrides':
            const o = await getExecutionOverrides(interval);
            setOverrides(o);
            break;
          case 'dispatches':
            const d = await getExecutionDispatches(undefined, interval);
            setDispatches(d);
            break;
          case 'staleness':
            const st = await getExecutionStaleness(undefined, interval);
            setStaleness(st);
            break;
        }
      } catch (err: any) {
        setErrors(prev => ({ ...prev, [s]: err.message || 'Failed to fetch' }));
      } finally {
        setLoading(prev => ({ ...prev, [s]: false }));
      }
    });
  }, [interval]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAddOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(prev => ({ ...prev, 'overrides-action': true }));
    try {
      await setExecutionOverride({
        symbol: newOverride.symbol,
        interval: interval,
        override_action: newOverride.action,
        reason: newOverride.reason
      });
      setNewOverride({ ...newOverride, symbol: contextSymbol || '', reason: '' });
      fetchData('overrides');
      fetchData('readiness');
      fetchData('guardrails');
    } catch (err: any) {
      alert('Failed to set override: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(prev => ({ ...prev, 'overrides-action': false }));
    }
  };

  const handleClearOverride = async (symbol: string) => {
    setLoading(prev => ({ ...prev, [`clear-${symbol}`]: true }));
    try {
      await clearExecutionOverride(symbol, interval);
      fetchData('overrides');
      fetchData('readiness');
      fetchData('guardrails');
    } catch (err: any) {
      alert('Failed to clear override: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(prev => ({ ...prev, [`clear-${symbol}`]: false }));
    }
  };

  const renderError = (msg: string | null) => msg ? (
    <div className="glass-panel text-danger" style={{ marginBottom: '16px', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
      <AlertCircle size={14} /> <span className="text-sm">{msg}</span>
    </div>
  ) : null;

  return (
    <PageContainer title="Execution Management">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        
        {/* A. Execution Readiness */}
        <Card>
          <SectionHeader title="Execution Readiness" icon={<CheckCircle2 size={20} color="var(--success)" />} onRefresh={() => fetchData('readiness')} loading={loading.readiness} />
          {renderError(errors.readiness)}
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>SYMBOL</th>
                  <th>DECISION</th>
                  <th>RL ACTION</th>
                  <th>STATUS</th>
                  <th>DETAILS</th>
                </tr>
              </thead>
              <tbody>
                {readiness?.details.map(d => (
                  <tr key={d.symbol}>
                    <td className="text-mono">{d.symbol}</td>
                    <td className="text-mono">
                      <span style={{ color: d.decision_label === 'BUY' ? 'var(--success)' : d.decision_label === 'SELL' ? 'var(--danger)' : 'var(--muted)' }}>
                        {d.decision_label}
                      </span>
                      <span className="text-xs text-muted" style={{ marginLeft: '8px' }}>({d.decision_score.toFixed(2)})</span>
                    </td>
                    <td><Badge variant={d.rl_action === 'HOLD' ? 'muted' : 'primary'}>{d.rl_action}</Badge></td>
                    <td><StatusBadge type="readiness" status={d.ready} label={d.ready ? 'READY' : 'NOT READY'} /></td>
                    <td className="text-xs text-muted">
                      {d.override_active && (
                        <div className="text-warning">
                          [OVERRIDE: {d.override_action}] {d.override_stale ? '(STALE)' : ''}
                          {d.override_created_ts && <span style={{ marginLeft: '4px' }}>@{new Date(d.override_created_ts).toLocaleTimeString()}</span>}
                        </div>
                      )}
                      {d.decision_stale && <div className="text-danger">[STALE DECISION] @{d.decision_ts ? new Date(d.decision_ts).toLocaleTimeString() : 'N/A'}</div>}
                      {!d.decision_stale && d.decision_ts && <div>[DECISION] @{new Date(d.decision_ts).toLocaleTimeString()}</div>}
                      {d.reason && <div>{d.reason}</div>}
                    </td>
                  </tr>
                ))}
                {!loading.readiness && readiness?.details.length === 0 && (
                  <tr><td colSpan={5}><EmptyState message="No symbols in current universe." /></td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          
          {/* B. Guardrails */}
          <Card>
            <SectionHeader title="Execution Guardrails" icon={<ShieldCheck size={20} color="var(--primary)" />} onRefresh={() => fetchData('guardrails')} loading={loading.guardrails} />
            {renderError(errors.guardrails)}
            {guardrails && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="text-xs text-muted text-mono">EXECUTION GUARD</span>
                  <StatusBadge type="readiness" status={guardrails.guardrails.execution_enabled} label={guardrails.guardrails.execution_enabled ? 'ENABLED' : 'LOCKED'} />
                </div>
                
                <KeyValueGrid>
                  <KeyValueItem label="Allowed Actions" value={guardrails.guardrails.allowed_actions.join(', ') || 'NONE'} />
                  <KeyValueItem label="Max Per Run" value={guardrails.guardrails.max_symbols_per_run} />
                </KeyValueGrid>

                <KeyValueGrid>
                  <KeyValueItem label="Requested" value={guardrails.guardrails.requested_ready_symbols.length} />
                  <KeyValueItem label="Allowed" value={guardrails.guardrails.allowed_symbols.length} valueColor="var(--success)" />
                </KeyValueGrid>
                
                <div>
                  <div className="text-xs text-muted text-mono" style={{ marginBottom: '8px' }}>BLOCKED SYMBOLS</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {guardrails.guardrails.blocked_symbols.map(({ symbol, reason }) => (
                      <div key={symbol} className="glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px' }}>
                        <span className="text-mono text-sm">{symbol}</span>
                        <span className="text-xs text-danger">{reason}</span>
                      </div>
                    ))}
                    {guardrails.guardrails.blocked_symbols.length === 0 && (
                      <div className="text-xs text-muted italic">No guardrail blocks active.</div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </Card>

          {/* C. Manual Overrides */}
          <Card>
            <SectionHeader title="Manual Overrides" icon={<UserCog size={20} color="var(--tertiary)" />} onRefresh={() => fetchData('overrides')} loading={loading.overrides} />
            {renderError(errors.overrides)}
            
            <form onSubmit={handleAddOverride} style={{ marginBottom: '20px', display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '12px', alignItems: 'flex-end' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label className="text-xs text-muted text-mono">SYMBOL</label>
                <input className="input-void" value={newOverride.symbol} onChange={e => setNewOverride({...newOverride, symbol: e.target.value.toUpperCase()})} placeholder="BTC-USD" required />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label className="text-xs text-muted text-mono">ACTION</label>
                <select className="input-void" value={newOverride.action} onChange={e => setNewOverride({...newOverride, action: e.target.value})}>
                  <option value="SKIP">SKIP</option>
                  <option value="HOLD">HOLD</option>
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                </select>
              </div>
              <Button type="submit" variant="primary" disabled={loading['overrides-action']} aria-label="Add Override">
                <Plus size={16} />
              </Button>
            </form>

            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>SYMBOL</th>
                    <th>ACTION</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {overrides.map(o => (
                    <tr key={o.id}>
                      <td className="text-mono">{o.symbol}</td>
                      <td><Badge variant="warning">{o.override_action}</Badge></td>
                      <td style={{ textAlign: 'right' }}>
                        <Button variant="outline" size="sm" onClick={() => handleClearOverride(o.symbol)} disabled={loading[`clear-${o.symbol}`]} aria-label="Clear Override">
                          <Trash2 size={14} className="text-danger" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {overrides.length === 0 && (
                    <tr><td colSpan={3} className="text-center py-4"><span className="text-muted text-xs italic">No active overrides.</span></td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* D. Dispatch History */}
        <Card>
          <SectionHeader title="Dispatch Ledger" icon={<Send size={20} color="var(--secondary)" />} onRefresh={() => fetchData('dispatches')} loading={loading.dispatches} />
          {renderError(errors.dispatches)}
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>SYMBOL</th>
                  <th>SOURCE</th>
                  <th>ACTION</th>
                  <th>STATUS</th>
                  <th>ORDER ID</th>
                  <th>TIME</th>
                </tr>
              </thead>
              <tbody>
                {dispatches.map(d => (
                  <tr key={d.id}>
                    <td className="text-mono text-xs text-muted">{d.id}</td>
                    <td className="text-mono">{d.symbol}</td>
                    <td className="text-mono text-xs">{d.source_type.toUpperCase()} ({d.source_id})</td>
                    <td><Badge variant="primary">{d.dispatched_action}</Badge></td>
                    <td><StatusBadge type="dispatch" status={d.status} /></td>
                    <td className="text-mono text-xs">{d.order_id || '-'}</td>
                    <td className="text-xs text-muted">{new Date(d.created_ts).toLocaleString()}</td>
                  </tr>
                ))}
                {dispatches.length === 0 && (
                  <tr><td colSpan={7}><EmptyState message="No recent dispatches." /></td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* E. Staleness Inspection */}
        <Card>
          <SectionHeader title="Staleness Inspection" icon={<Clock size={20} color="var(--muted)" />} onRefresh={() => fetchData('staleness')} loading={loading.staleness} />
          {renderError(errors.staleness)}
          <div className="grid" style={{ gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="glass-panel" style={{ padding: '16px' }}>
                <div className="text-xs text-muted text-mono" style={{ marginBottom: '16px' }}>STALENESS SUMMARY</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="text-sm text-muted">STALE DECISIONS</span>
                    <StatusBadge type="staleness" status={staleness?.summary.stale_decision_symbols.length || 0} label={String(staleness?.summary.stale_decision_symbols.length || 0)} />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="text-sm text-muted">STALE OVERRIDES</span>
                    <StatusBadge type="staleness" status={staleness?.summary.stale_override_symbols.length || 0} label={String(staleness?.summary.stale_override_symbols.length || 0)} />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="text-sm text-muted">FRESH CANDIDATES</span>
                    <Badge variant="primary">{staleness?.summary.fresh_candidates.length || 0}</Badge>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>SYMBOL</th>
                    <th>STATE</th>
                    <th>REASON</th>
                  </tr>
                </thead>
                <tbody>
                  {staleness?.details.map(d => (
                    <tr key={d.symbol}>
                      <td className="text-mono">{d.symbol}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <StatusBadge type="staleness" status={d.decision_stale} label={`DECISION: ${d.decision_stale ? 'STALE' : 'FRESH'}`} />
                          {d.override_active && (
                            <StatusBadge type="staleness" status={d.override_stale} label={`OVERRIDE: ${d.override_stale ? 'STALE' : 'FRESH'}`} />
                          )}
                        </div>
                      </td>
                      <td className="text-xs text-muted">
                        {d.decision_stale && <div>Decision stale since {d.decision_ts ? new Date(d.decision_ts).toLocaleString() : 'N/A'}</div>}
                        {d.override_stale && <div>Override stale since {d.override_created_ts ? new Date(d.override_created_ts).toLocaleString() : 'N/A'}</div>}
                        {!d.decision_stale && !d.override_stale && <div className="text-success">All source data is fresh.</div>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Card>
      </div>
    </PageContainer>
  );
};

export default ExecutionPage;
