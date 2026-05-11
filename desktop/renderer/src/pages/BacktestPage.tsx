import React, { useState } from 'react';
import { useSymbol } from '../context/SymbolContext';
import { runBacktest, BacktestRunOut, BacktestMetricsOut } from '../api/backtestApi';
import { Play, TrendingUp } from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import { EmptyState } from '../components/data/EmptyState';

const BacktestPage: React.FC = () => {
  const { symbol, interval } = useSymbol();
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2023-12-31');
  const [initialCapital, setInitialCapital] = useState(10000);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ run: BacktestRunOut; metrics: BacktestMetricsOut } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunBacktest = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runBacktest({
        strategy_name: 'rule_based',
        symbol,
        interval,
        start_ts: new Date(startDate).toISOString(),
        end_ts: new Date(endDate).toISOString(),
        initial_capital: initialCapital,
      });
      setResult(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Backtest failed to run');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer title="Backtest">
      <div className="grid gap-lg items-start" style={{ gridTemplateColumns: '350px 1fr' }}>
        <Card>
          <h3 className="mb-md">Configure Run</h3>
          <div className="flex-col gap-md">
            <div>
              <span className="text-xs text-muted text-mono mb-sm" style={{ display: 'block' }}>START DATE</span>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="w-full" />
            </div>
            <div>
              <span className="text-xs text-muted text-mono mb-sm" style={{ display: 'block' }}>END DATE</span>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="w-full" />
            </div>
            <div>
              <span className="text-xs text-muted text-mono mb-sm" style={{ display: 'block' }}>INITIAL CAPITAL (USD)</span>
              <input type="number" value={initialCapital} onChange={(e) => setInitialCapital(Number(e.target.value))} className="w-full" />
            </div>
            <Button variant="primary" onClick={handleRunBacktest} disabled={loading} className="w-full mt-sm">
              {loading ? 'Processing...' : <><Play size={18} /> Execute Strategy</>}
            </Button>
          </div>
        </Card>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {error && <Card className="text-danger">{error}</Card>}
          
          {result ? (
            <Card variant="glass">
              <div className="flex justify-between items-center mb-lg">
                <div className="flex items-center gap-md">
                  <h3 className="m-0">Result Analysis</h3>
                  <Badge variant={result.run.status === 'COMPLETED' ? 'success' : 'primary'}>{result.run.status}</Badge>
                </div>
                <span className="mono-metadata">RUN_ID: {result.run.id}</span>
              </div>

              <div className="grid grid-4 gap-md">
                <div className="glass-panel p-md">
                  <span className="text-xs text-muted text-mono">FINAL CAPITAL</span>
                  <div className="text-mono" style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '4px', color: (result.run.final_capital || 0) >= result.run.initial_capital ? 'var(--success)' : 'var(--danger)' }}>
                    ${result.run.final_capital?.toLocaleString() || 'N/A'}
                  </div>
                </div>
                <div className="glass-panel p-md">
                  <span className="text-xs text-muted text-mono">TOTAL RETURN</span>
                  <div className="text-mono" style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '4px' }}>
                    {result.run.final_capital ? (((result.run.final_capital - result.run.initial_capital) / result.run.initial_capital) * 100).toFixed(2) : 0}%
                  </div>
                </div>
                <div className="glass-panel p-md">
                  <span className="text-xs text-muted text-mono">WIN RATE</span>
                  <div className="text-mono" style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '4px' }}>
                    {(result.metrics.metrics.win_rate * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="glass-panel p-md">
                  <span className="text-xs text-muted text-mono">SHARPE RATIO</span>
                  <div className="text-mono" style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '4px' }}>
                    {result.metrics.metrics.sharpe.toFixed(2)}
                  </div>
                </div>
              </div>

              <div style={{ marginTop: '32px' }}>
                <span className="text-xs text-muted text-mono">EQUITY PERFORMANCE</span>
                <div style={{ width: '100%', height: '240px', backgroundColor: 'rgba(247,147,26,0.03)', border: '1px dashed var(--primary)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', marginTop: '12px' }}>
                  <div className="text-center">
                    <TrendingUp size={48} style={{ opacity: 0.2, marginBottom: '12px', color: 'var(--primary)' }} />
                    <p className="text-sm">Historical Equity Visualization Coming in v2</p>
                  </div>
                </div>
              </div>
            </Card>
          ) : !loading && !error && (
            <Card variant="glass" className="flex items-center justify-center h-full" style={{ minHeight: '300px' }}>
              <EmptyState message="Configure and run a backtest to see results" icon={<Play size={48} strokeWidth={1} style={{ opacity: 0.1 }} />} />
            </Card>
          )}
        </div>
      </div>
    </PageContainer>
  );
};

export default BacktestPage;
