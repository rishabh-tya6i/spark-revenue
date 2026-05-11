import React, { useEffect, useState } from 'react';
import { useSymbol } from '../context/SymbolContext';
import { getOperationalState, OperationalStateSnapshot, OrchestrationRun } from '../api/orchestrationApi';
import PageContainer from '../components/layout/PageContainer';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { RefreshCw, Globe, Shield, Activity, Zap, History, AlertCircle } from 'lucide-react';

const OverviewPage: React.FC = () => {
  const { interval } = useSymbol();
  const [state, setState] = useState<OperationalStateSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchState = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getOperationalState(undefined, interval);
      setState(data);
    } catch (err) {
      setError('Failed to fetch operational state');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchState();
  }, [interval]);

  if (loading && !state) {
    return (
      <PageContainer title="Operator Overview">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }} className="text-muted">
          <RefreshCw className="animate-spin" size={20} />
          <span>Synchronizing state...</span>
        </div>
      </PageContainer>
    );
  }

  const renderRunBadge = (run: OrchestrationRun | null) => {
    if (!run) return <Badge variant="muted">NO RUN</Badge>;
    const variant = run.status === 'COMPLETED' ? 'success' : run.status === 'FAILED' ? 'danger' : 'primary';
    return <Badge variant={variant}>{run.status}</Badge>;
  };

  return (
    <PageContainer title="Operator Overview">
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '24px' }}>
        <Button variant="outline" size="sm" onClick={fetchState} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} style={{ marginRight: '8px' }} />
          Manual Refresh
        </Button>
      </div>

      {error && <Card className="text-danger" style={{ marginBottom: '24px' }}><AlertCircle size={18} /> {error}</Card>}

      {state && (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '24px' }}>
          
          {/* Universe & Readiness */}
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
              <Globe size={20} color="var(--primary)" />
              <h3 style={{ margin: 0 }}>Universe & Readiness</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">MODE / INTERVAL</span>
                <span className="text-mono">{state.mode.toUpperCase()} / {state.interval}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">SELECTED SYMBOLS</span>
                <span className="text-mono">{state.symbols.length} symbols</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">INFERENCE READY</span>
                <Badge variant={state.inference_ready_symbols.length === state.symbols.length ? 'success' : 'primary'}>
                  {state.inference_ready_symbols.length} / {state.symbols.length}
                </Badge>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">EXECUTION READY</span>
                <Badge variant={state.execution_ready_symbols.length > 0 ? 'success' : 'muted'}>
                  {state.execution_ready_symbols.length} actionable
                </Badge>
              </div>
              <div style={{ marginTop: '8px', padding: '12px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-sm)' }}>
                <div className="text-xs text-muted text-mono" style={{ marginBottom: '8px' }}>ACTIVE SYMBOLS</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {state.symbols.map(s => (
                    <span key={s} className="text-mono text-xs" style={{ padding: '2px 6px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '2px' }}>{s}</span>
                  ))}
                </div>
              </div>
            </div>
          </Card>

          {/* Model Availability */}
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
              <Shield size={20} color="var(--primary)" />
              <h3 style={{ margin: 0 }}>Model Availability</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">PRICE MODELS</span>
                <Badge variant={state.models.missing_price_model.length === 0 ? 'success' : 'danger'}>
                  {state.models.price_model_available.length} Available
                </Badge>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">RL AGENTS</span>
                <Badge variant={state.models.missing_rl_agent.length === 0 ? 'success' : 'danger'}>
                  {state.models.rl_agent_available.length} Available
                </Badge>
              </div>
              {state.models.missing_price_model.length > 0 && (
                <div style={{ color: 'var(--danger)', fontSize: '0.75rem' }} className="text-mono">
                  MISSING PRICE: {state.models.missing_price_model.join(', ')}
                </div>
              )}
              {state.models.missing_rl_agent.length > 0 && (
                <div style={{ color: 'var(--danger)', fontSize: '0.75rem' }} className="text-mono">
                  MISSING RL: {state.models.missing_rl_agent.join(', ')}
                </div>
              )}
            </div>
          </Card>

          {/* Decisions & Execution */}
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
              <Zap size={20} color="var(--tertiary)" />
              <h3 style={{ margin: 0 }}>Decisions & Execution</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">ACTIONABLE DECISIONS</span>
                <Badge variant="success">{state.decisions.actionable.length}</Badge>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">HOLD / NEUTRAL</span>
                <Badge variant="muted">{state.decisions.hold.length}</Badge>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderTop: '1px solid var(--border)' }}>
                <span className="text-xs text-muted text-mono">OPEN POSITIONS</span>
                <Badge variant={state.execution_state.open_positions.length > 0 ? 'primary' : 'muted'}>
                  {state.execution_state.open_positions.length} active
                </Badge>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">ORDER ACTIVITY</span>
                <span className="text-mono text-sm">{state.execution_state.has_orders.length} symbols with orders</span>
              </div>
            </div>
          </Card>

          {/* Safety & Guardrails */}
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
              <Activity size={20} color="var(--secondary)" />
              <h3 style={{ margin: 0 }}>Safety Context</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">EXECUTION GUARD</span>
                <Badge variant={state.execution_guardrails.execution_enabled ? 'success' : 'danger'}>
                  {state.execution_guardrails.execution_enabled ? 'ENABLED' : 'LOCKED'}
                </Badge>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">ALLOWED ACTIONS</span>
                <span className="text-mono text-xs">{state.execution_guardrails.allowed_actions.join(', ')}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderTop: '1px solid var(--border)' }}>
                <span className="text-xs text-muted text-mono">STALENESS CHECK</span>
                <Badge variant={state.execution_staleness.fresh_candidates.length === state.symbols.length ? 'success' : 'warning'}>
                  {state.execution_staleness.fresh_candidates.length} / {state.symbols.length} Fresh
                </Badge>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">ACTIVE OVERRIDES</span>
                <Badge variant={state.execution_overrides.active_symbols.length > 0 ? 'warning' : 'muted'}>
                  {state.execution_overrides.active_symbols.length} manual
                </Badge>
              </div>
            </div>
          </Card>

          {/* Latest Runs */}
          <Card style={{ gridColumn: 'span 2' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
              <History size={20} color="var(--primary)" />
              <h3 style={{ margin: 0 }}>Latest Orchestration Runs</h3>
            </div>
            <div className="grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              {(['train', 'inference', 'execution', 'cycle'] as const).map(type => {
                const run = state.latest_runs[type];
                return (
                  <div key={type} style={{ padding: '16px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                    <div className="text-xs text-muted text-mono" style={{ marginBottom: '12px' }}>{type.toUpperCase()}</div>
                    {run ? (
                      <div>
                        <div style={{ marginBottom: '8px' }}>{renderRunBadge(run)}</div>
                        <div className="text-mono text-xs" style={{ marginBottom: '4px' }}>ID: {run.id}</div>
                        <div className="text-muted" style={{ fontSize: '0.7rem' }}>{new Date(run.created_ts).toLocaleString()}</div>
                      </div>
                    ) : (
                      <div className="text-muted text-xs">No recent history</div>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>

        </div>
      )}
    </PageContainer>
  );
};

export default OverviewPage;
