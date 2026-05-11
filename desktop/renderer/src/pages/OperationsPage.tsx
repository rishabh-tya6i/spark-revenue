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
import Badge from '../components/ui/Badge';
import { Play, Brain, Zap, RotateCcw, Loader2 } from 'lucide-react';

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

  const renderResult = (key: string) => {
    const res = results[key];
    if (!res) return null;

    if (res.error) {
      return (
        <div style={{ marginTop: '16px', padding: '12px', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: 'var(--radius-sm)', color: 'var(--danger)', fontSize: '0.85rem' }}>
          <strong>Error:</strong> {res.error}
        </div>
      );
    }

    return (
      <div style={{ marginTop: '16px', padding: '12px', backgroundColor: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <Badge variant={res.status === 'COMPLETED' ? 'success' : res.status === 'SKIPPED' ? 'muted' : 'primary'}>
            {res.status || 'SUCCESS'}
          </Badge>
          {res.run_record_id && <span className="text-xs text-muted text-mono">RUN: {res.run_record_id}</span>}
        </div>
        
        {res.summary && (
          <div className="text-xs text-mono" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            {Object.entries(res.summary).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-muted">{k.toUpperCase()}</span>
                <span>{String(v)}</span>
              </div>
            ))}
          </div>
        )}
        
        {res.reason && (
          <div className="text-xs text-muted" style={{ marginTop: '8px', fontStyle: 'italic' }}>
            {res.reason}
          </div>
        )}
      </div>
    );
  };

  return (
    <PageContainer title="Operator Console">
      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '24px' }}>
        
        {/* A. Training */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
            <Brain size={20} color="var(--primary)" />
            <h3 style={{ margin: 0 }}>Model Training</h3>
          </div>
          <p className="text-sm text-muted" style={{ marginBottom: '20px' }}>
            Triggers data preparation and training for trainable symbols in the current universe.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="text-xs text-muted text-mono">INTERVAL: {interval}</div>
            <Button 
              variant="primary" 
              onClick={() => executeAction('train', () => runTrainTrainable({ interval, epochs: 10 }))}
              disabled={loading['train']}
            >
              {loading['train'] ? <Loader2 className="animate-spin" size={18} /> : <Play size={18} />}
              Execute Training Flow
            </Button>
          </div>
          {renderResult('train')}
        </Card>

        {/* B. Inference */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
            <Zap size={20} color="var(--tertiary)" />
            <h3 style={{ margin: 0 }}>Universe Inference</h3>
          </div>
          <p className="text-sm text-muted" style={{ marginBottom: '20px' }}>
            Generates new decisions using the latest active models for ready symbols.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="text-xs text-muted text-mono">INTERVAL: {interval}</div>
            <Button 
              variant="primary" 
              onClick={() => executeAction('inference', () => runUniverseInference({ interval }))}
              disabled={loading['inference']}
            >
              {loading['inference'] ? <Loader2 className="animate-spin" size={18} /> : <Play size={18} />}
              Run All Inferences
            </Button>
          </div>
          {renderResult('inference')}
        </Card>

        {/* C. Execution */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
            <Play size={20} color="var(--success)" />
            <h3 style={{ margin: 0 }}>Universe Execution</h3>
          </div>
          <p className="text-sm text-muted" style={{ marginBottom: '20px' }}>
            Dispatches orders based on latest actionable decisions. Respects guardrails.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="text-xs text-muted text-mono">INTERVAL: {interval}</div>
            <Button 
              variant="primary" 
              onClick={() => executeAction('execution', () => runUniverseExecution({ interval, require_actionable: true }))}
              disabled={loading['execution']}
            >
              {loading['execution'] ? <Loader2 className="animate-spin" size={18} /> : <Play size={18} />}
              Dispatch Universe
            </Button>
          </div>
          {renderResult('execution')}
        </Card>

        {/* D. Full Cycle */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
            <RotateCcw size={20} color="var(--secondary)" />
            <h3 style={{ margin: 0 }}>Operational Cycle</h3>
          </div>
          <p className="text-sm text-muted" style={{ marginBottom: '20px' }}>
            Runs Inference → Decision → Execution in a single orchestrated sequence.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="text-xs text-muted text-mono">INTERVAL: {interval}</div>
            <Button 
              variant="primary" 
              onClick={() => executeAction('cycle', () => runOperationalCycle({ interval, require_actionable: true }))}
              disabled={loading['cycle']}
            >
              {loading['cycle'] ? <Loader2 className="animate-spin" size={18} /> : <RotateCcw size={18} />}
              Run Full Cycle
            </Button>
          </div>
          {renderResult('cycle')}
        </Card>

      </div>
    </PageContainer>
  );
};

export default OperationsPage;
