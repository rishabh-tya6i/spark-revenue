import React, { useState } from 'react';
import { useSymbol } from '../context/SymbolContext';
import { 
  runTrainTrainable, 
  runUniverseInference, 
  runUniverseExecution, 
  runOperationalCycle 
} from '../api/orchestrationApi';
import PageContainer from '../components/layout/PageContainer';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { Play, Brain, Zap, RotateCcw, Loader2, AlertCircle } from 'lucide-react';
import { KeyValueGrid, KeyValueItem } from '../components/data/KeyValueGrid';
import { StatusBadge } from '../components/data/StatusBadge';
import { SectionHeader } from '../components/data/SectionHeader';

const ResultRenderer: React.FC<{ res: any }> = ({ res }) => {
  if (!res) return null;

  if (res.error) {
    return (
      <div className="glass-panel text-danger mt-md p-sm flex items-center gap-sm">
        <AlertCircle size={16} />
        <span className="text-sm"><strong>Error:</strong> {res.error}</span>
      </div>
    );
  }

  return (
    <div className="glass-panel mt-md p-md">
      <div className="flex justify-between items-center mb-md">
        <StatusBadge type="run" status={res.status || 'success'} />
        {res.run_record_id && <span className="text-xs text-muted text-mono">RUN ID: {res.run_record_id}</span>}
      </div>
      
      {res.summary && (
        <KeyValueGrid cols={2}>
          {Object.entries(res.summary).map(([k, v]) => (
            <KeyValueItem key={k} label={k.replace(/_/g, ' ')} value={String(v)} />
          ))}
        </KeyValueGrid>
      )}
      
      {res.reason && (
        <div className="text-xs text-muted italic" style={{ marginTop: '12px', borderTop: '1px solid var(--border-subtle)', paddingTop: '8px' }}>
          {res.reason}
        </div>
      )}
    </div>
  );
};

const OperationsPage: React.FC = () => {
  const { interval } = useSymbol();
  const [results, setResults] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  const executeAction = async (key: string, fn: () => Promise<any>) => {
    setLoading(prev => ({ ...prev, [key]: true }));
    try {
      const res = await fn();
      setResults(prev => ({ ...prev, [key]: res }));
    } catch (err: any) {
      setResults(prev => ({ ...prev, [key]: { error: err.response?.data?.detail || err.message } }));
    } finally {
      setLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  const actions = [
    {
      id: 'train',
      title: 'Model Training',
      description: 'Triggers data preparation and training for trainable symbols in the current universe.',
      icon: <Brain size={20} color="var(--primary)" />,
      fn: () => runTrainTrainable({ interval, epochs: 10 })
    },
    {
      id: 'inference',
      title: 'Universe Inference',
      description: 'Generates new decisions using the latest active models for ready symbols.',
      icon: <Zap size={20} color="var(--tertiary)" />,
      fn: () => runUniverseInference({ interval })
    },
    {
      id: 'execution',
      title: 'Universe Execution',
      description: 'Dispatches orders based on latest actionable decisions. Respects guardrails.',
      icon: <Play size={20} color="var(--success)" />,
      fn: () => runUniverseExecution({ interval, require_actionable: true })
    },
    {
      id: 'cycle',
      title: 'Operational Cycle',
      description: 'Runs Inference → Decision → Execution in a single orchestrated sequence.',
      icon: <RotateCcw size={20} color="var(--secondary)" />,
      fn: () => runOperationalCycle({ interval, require_actionable: true })
    }
  ];

  return (
    <PageContainer title="Operator Console">
      <div className="grid gap-lg" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))' }}>
        {actions.map(action => (
          <Card key={action.id} className="flex-col">
            <SectionHeader title={action.title} icon={action.icon} />
            <p className="text-sm text-muted mb-lg flex-1">
              {action.description}
            </p>
            <div className="flex-col gap-md">
              <div className="text-xs text-muted text-mono uppercase">TARGET INTERVAL: {interval}</div>
              <Button 
                variant="primary" 
                onClick={() => executeAction(action.id, action.fn)}
                disabled={loading[action.id]}
                style={{ width: '100%' }}
              >
                {loading[action.id] ? (
                  <Loader2 className="animate-spin" size={18} />
                ) : (
                  action.id === 'cycle' ? <RotateCcw size={18} /> : <Play size={18} />
                )}
                <span style={{ marginLeft: '8px' }}>
                  {loading[action.id] ? 'Executing...' : `Run ${action.title}`}
                </span>
              </Button>
            </div>
            <ResultRenderer res={results[action.id]} />
          </Card>
        ))}
      </div>
    </PageContainer>
  );
};

export default OperationsPage;
