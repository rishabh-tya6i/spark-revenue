import React, { useEffect, useState } from 'react';
import { useSymbol } from '../context/SymbolContext';
import { getOperationalState, OperationalStateSnapshot } from '../api/orchestrationApi';
import PageContainer from '../components/layout/PageContainer';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import { Globe, Shield, Activity, Zap, History, AlertCircle, Loader2 } from 'lucide-react';
import { KeyValueGrid, KeyValueItem } from '../components/data/KeyValueGrid';
import { StatusBadge } from '../components/data/StatusBadge';
import { SectionHeader } from '../components/data/SectionHeader';
import { EmptyState } from '../components/data/EmptyState';

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
        <EmptyState message="Synchronizing state..." icon={<Loader2 className="animate-spin" size={40} />} />
      </PageContainer>
    );
  }

  return (
    <PageContainer title="Operator Overview">
      {error && (
        <Card className="text-danger" style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <AlertCircle size={18} /> {error}
        </Card>
      )}

      {state && (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '24px' }}>
          
          {/* Universe & Readiness */}
          <Card>
            <SectionHeader title="Universe & Readiness" icon={<Globe size={20} color="var(--primary)" />} onRefresh={fetchState} loading={loading} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <KeyValueGrid>
                <KeyValueItem label="Mode / Interval" value={`${state.mode.toUpperCase()} / ${state.interval}`} />
                <KeyValueItem label="Selected" value={`${state.symbols.length} Symbols`} />
              </KeyValueGrid>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="text-xs text-muted text-mono">INFERENCE READY</span>
                  <Badge data-testid="inference-readiness" variant={state.inference_ready_symbols.length === state.symbols.length ? 'success' : 'primary'}>
                    {`${state.inference_ready_symbols.length} / ${state.symbols.length}`}
                  </Badge>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="text-xs text-muted text-mono">EXECUTION READY</span>
                  <Badge data-testid="execution-readiness" variant={state.execution_ready_symbols.length > 0 ? 'success' : 'muted'}>
                    {`${state.execution_ready_symbols.length} Actionable`}
                  </Badge>
                </div>
              </div>

              <div className="glass-panel" style={{ padding: '12px' }}>
                <div className="text-xs text-muted text-mono" style={{ marginBottom: '8px' }}>ACTIVE UNIVERSE</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {state.symbols.map(s => (
                    <span key={s} className="text-mono text-xs glass-panel" style={{ padding: '2px 6px', borderRadius: '4px' }}>{s}</span>
                  ))}
                </div>
              </div>
            </div>
          </Card>

          {/* Model Availability */}
          <Card>
            <SectionHeader title="Model Availability" icon={<Shield size={20} color="var(--primary)" />} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <KeyValueGrid>
                <KeyValueItem 
                  label="Price Models" 
                  value={<StatusBadge type="readiness" status={state.models.missing_price_model.length === 0} label={`${state.models.price_model_available.length} Available`} />} 
                />
                <KeyValueItem 
                  label="RL Agents" 
                  value={<StatusBadge type="readiness" status={state.models.missing_rl_agent.length === 0} label={`${state.models.rl_agent_available.length} Available`} />} 
                />
              </KeyValueGrid>

              {(state.models.missing_price_model.length > 0 || state.models.missing_rl_agent.length > 0) && (
                <div className="glass-panel text-danger" style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {state.models.missing_price_model.length > 0 && (
                    <div className="text-xs text-mono">MISSING PRICE: {state.models.missing_price_model.join(', ')}</div>
                  )}
                  {state.models.missing_rl_agent.length > 0 && (
                    <div className="text-xs text-mono">MISSING RL: {state.models.missing_rl_agent.join(', ')}</div>
                  )}
                </div>
              )}
            </div>
          </Card>

          {/* Decisions & Execution */}
          <Card>
            <SectionHeader title="Decisions & Execution" icon={<Zap size={20} color="var(--tertiary)" />} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <KeyValueGrid>
                <KeyValueItem label="Actionable" value={state.decisions.actionable.length} valueColor="var(--success)" />
                <KeyValueItem label="Neutral/Hold" value={state.decisions.hold.length} valueColor="var(--muted)" />
              </KeyValueGrid>
              <KeyValueGrid>
                <KeyValueItem label="Open Positions" value={state.execution_state.open_positions.length} valueColor={state.execution_state.open_positions.length > 0 ? 'var(--primary)' : 'var(--muted)'} />
                <KeyValueItem label="Active Orders" value={state.execution_state.has_orders.length} />
              </KeyValueGrid>
            </div>
          </Card>

          {/* Safety & Guardrails */}
          <Card>
            <SectionHeader title="Safety Context" icon={<Activity size={20} color="var(--secondary)" />} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="text-xs text-muted text-mono">EXECUTION GUARD</span>
                <StatusBadge type="readiness" status={state.execution_guardrails.execution_enabled} label={state.execution_guardrails.execution_enabled ? 'ENABLED' : 'LOCKED'} />
              </div>
              
              <KeyValueGrid>
                <KeyValueItem label="Allowed Actions" value={state.execution_guardrails.allowed_actions.join(', ') || 'NONE'} />
                <KeyValueItem 
                  label="Fresh Candidates" 
                  value={<StatusBadge type="staleness" status={state.execution_staleness.fresh_candidates.length !== state.symbols.length} label={`${state.execution_staleness.fresh_candidates.length} / ${state.symbols.length}`} />} 
                />
              </KeyValueGrid>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="text-xs text-muted text-mono">ACTIVE OVERRIDES</span>
                <Badge variant={state.execution_overrides.active_symbols.length > 0 ? 'warning' : 'muted'}>
                  {state.execution_overrides.active_symbols.length} manual
                </Badge>
              </div>
            </div>
          </Card>

          {/* Latest Runs */}
          <Card style={{ gridColumn: 'span 2' }}>
            <SectionHeader title="Latest Orchestration Runs" icon={<History size={20} color="var(--primary)" />} />
            <div className="grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              {(['train', 'inference', 'execution', 'cycle'] as const).map(type => {
                const run = state.latest_runs[type];
                return (
                  <div key={type} className="glass-panel" style={{ padding: '16px' }}>
                    <div className="text-xs text-muted text-mono" style={{ marginBottom: '12px' }}>{type.toUpperCase()}</div>
                    {run ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <StatusBadge type="run" status={run.status} />
                        <div className="text-mono text-xs">ID: {run.id}</div>
                        <div className="text-muted text-xs">{new Date(run.created_ts).toLocaleString(undefined, { hour: '2-digit', minute: '2-digit' })}</div>
                      </div>
                    ) : (
                      <div className="text-muted text-xs italic">No recent history</div>
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
