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
  StalenessState,
  ReadinessDetail
} from '../api/orchestrationApi';
import PageContainer from '../components/layout/PageContainer';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { 
  RefreshCw, 
  ShieldCheck, 
  UserCog, 
  Send, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  Plus,
  Trash2,
  Table as TableIcon
} from 'lucide-react';

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

  const renderSectionHeader = (title: string, icon: React.ReactNode, sectionKey: string) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {icon}
        <h3 style={{ margin: 0 }}>{title}</h3>
      </div>
      <Button variant="outline" size="sm" onClick={() => fetchData(sectionKey)} disabled={loading[sectionKey]}>
        <RefreshCw size={14} className={loading[sectionKey] ? 'animate-spin' : ''} />
      </Button>
    </div>
  );

  const renderError = (msg: string | null) => msg ? (
    <div className="text-danger text-sm" style={{ marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
      <XCircle size={14} /> {msg}
    </div>
  ) : null;

  return (
    <PageContainer title="Execution Management">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        
        {/* A. Execution Readiness */}
        <Card>
          {renderSectionHeader('Execution Readiness', <CheckCircle2 size={20} color="var(--success)" />, 'readiness')}
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
                    <td>
                      <Badge variant={d.ready ? 'success' : 'danger'}>
                        {d.ready ? 'READY' : 'NOT READY'}
                      </Badge>
                    </td>
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
                  <tr><td colSpan={5} className="text-center text-muted py-4">No symbols in current universe universe.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          
          {/* B. Guardrails */}
          <Card>
            {renderSectionHeader('Execution Guardrails', <ShieldCheck size={20} color="var(--primary)" />, 'guardrails')}
            {renderError(errors.guardrails)}
            {guardrails && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="text-xs text-muted text-mono">EXECUTION GUARD</span>
                  <Badge variant={guardrails.guardrails.execution_enabled ? 'success' : 'danger'}>
                    {guardrails.guardrails.execution_enabled ? 'ENABLED' : 'LOCKED'}
                  </Badge>
                </div>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="glass-panel" style={{ padding: '12px' }}>
                    <div className="text-xs text-muted text-mono">ALLOWED ACTIONS</div>
                    <div className="text-sm text-mono">{guardrails.guardrails.allowed_actions.join(', ') || 'NONE'}</div>
                  </div>
                  <div className="glass-panel" style={{ padding: '12px' }}>
                    <div className="text-xs text-muted text-mono">MAX PER RUN</div>
                    <div className="text-xl text-mono">{guardrails.guardrails.max_symbols_per_run}</div>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="glass-panel" style={{ padding: '12px' }}>
                    <div className="text-xs text-muted text-mono">REQUESTED</div>
                    <div className="text-xl text-mono">{guardrails.guardrails.requested_ready_symbols.length}</div>
                  </div>
                  <div className="glass-panel" style={{ padding: '12px' }}>
                    <div className="text-xs text-muted text-mono">ALLOWED</div>
                    <div className="text-xl text-mono" style={{ color: 'var(--success)' }}>
                      {guardrails.guardrails.allowed_symbols.length}
                    </div>
                  </div>
                </div>
                
                <div>
                  <div className="text-xs text-muted text-mono" style={{ marginBottom: '8px' }}>BLOCKED SYMBOLS</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {guardrails.guardrails.blocked_symbols.map(({ symbol, reason }) => (
                      <div key={symbol} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px', backgroundColor: 'rgba(239, 68, 68, 0.05)', borderRadius: 'var(--radius-sm)' }}>
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
            {renderSectionHeader('Manual Overrides', <UserCog size={20} color="var(--tertiary)" />, 'overrides')}
            {renderError(errors.overrides)}
            
            {/* Form */}
            <form onSubmit={handleAddOverride} style={{ marginBottom: '20px', display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '12px', alignItems: 'flex-end' }}>
              <div>
                <label className="text-xs text-muted text-mono">SYMBOL</label>
                <input 
                  className="input-void" 
                  value={newOverride.symbol} 
                  onChange={e => setNewOverride({...newOverride, symbol: e.target.value.toUpperCase()})}
                  placeholder="BTC-USD"
                  required
                />
              </div>
              <div>
                <label className="text-xs text-muted text-mono">ACTION</label>
                <select 
                  className="input-void" 
                  value={newOverride.action} 
                  onChange={e => setNewOverride({...newOverride, action: e.target.value})}
                >
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
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={() => handleClearOverride(o.symbol)}
                          disabled={loading[`clear-${o.symbol}`]}
                          aria-label="Clear Override"
                        >
                          <Trash2 size={14} className="text-danger" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {overrides.length === 0 && (
                    <tr><td colSpan={3} className="text-center text-muted py-4 text-xs">No active overrides.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

        </div>

        {/* D. Dispatch History */}
        <Card>
          {renderSectionHeader('Dispatch Ledger', <Send size={20} color="var(--secondary)" />, 'dispatches')}
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
                    <td className="text-mono text-xs">
                      {d.source_type.toUpperCase()} ({d.source_id})
                    </td>
                    <td><Badge variant="primary">{d.dispatched_action}</Badge></td>
                    <td>
                      <Badge variant={d.status === 'executed' ? 'success' : d.status === 'failed' ? 'danger' : 'muted'}>
                        {d.status.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="text-mono text-xs">{d.order_id || '-'}</td>
                    <td className="text-xs text-muted">{new Date(d.created_ts).toLocaleString()}</td>
                  </tr>
                ))}
                {dispatches.length === 0 && (
                  <tr><td colSpan={7} className="text-center text-muted py-4">No recent dispatches.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* E. Staleness Inspection */}
        <Card>
          {renderSectionHeader('Staleness Inspection', <Clock size={20} color="var(--muted)" />, 'staleness')}
          {renderError(errors.staleness)}
          <div className="grid" style={{ gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="glass-panel" style={{ padding: '16px' }}>
                <div className="text-xs text-muted text-mono" style={{ marginBottom: '12px' }}>STALENESS SUMMARY</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-sm text-muted">STALE DECISIONS</span>
                    <Badge variant={staleness?.summary.stale_decision_symbols.length ? 'danger' : 'success'}>
                      {staleness?.summary.stale_decision_symbols.length || 0}
                    </Badge>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-sm text-muted">STALE OVERRIDES</span>
                    <Badge variant={staleness?.summary.stale_override_symbols.length ? 'danger' : 'success'}>
                      {staleness?.summary.stale_override_symbols.length || 0}
                    </Badge>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
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
                          <Badge variant={d.decision_stale ? 'danger' : 'success'}>
                            DECISION: {d.decision_stale ? 'STALE' : 'FRESH'}
                          </Badge>
                          {d.override_active && (
                            <Badge variant={d.override_stale ? 'danger' : 'success'}>
                              OVERRIDE: {d.override_stale ? 'STALE' : 'FRESH'}
                            </Badge>
                          )}
                        </div>
                      </td>
                      <td className="text-xs text-muted">
                        {d.decision_stale && <div>Decision stale since {d.decision_ts ? new Date(d.decision_ts).toLocaleString() : 'N/A'}</div>}
                        {d.override_stale && <div>Override stale since {d.override_created_ts ? new Date(d.override_created_ts).toLocaleString() : 'N/A'}</div>}
                        {!d.decision_stale && !d.override_stale && <div>All source data is fresh.</div>}
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
