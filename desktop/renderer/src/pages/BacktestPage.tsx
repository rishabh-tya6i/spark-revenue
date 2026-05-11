import React, { useState } from 'react';
import { useSymbol } from '../context/SymbolContext';
import { runBacktest, BacktestRunOut, BacktestMetricsOut } from '../api/backtestApi';
import { Play, TrendingUp } from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';

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
      <div className="grid" style={{ gridTemplateColumns: '350px 1fr', alignItems: 'start' }}>
        <Card>
          <h3 style={{ marginBottom: '20px' }}>Configure Run</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <span className="text-xs text-muted text-mono" style={{ display: 'block', marginBottom: '8px' }}>START DATE</span>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={{ width: '100%' }} />
            </div>
            <div>
              <span className="text-xs text-muted text-mono" style={{ display: 'block', marginBottom: '8px' }}>END DATE</span>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={{ width: '100%' }} />
            </div>
            <div>
              <span className="text-xs text-muted text-mono" style={{ display: 'block', marginBottom: '8px' }}>INITIAL CAPITAL (USD)</span>
              <input type="number" value={initialCapital} onChange={(e) => setInitialCapital(Number(e.target.value))} style={{ width: '100%' }} />
            </div>
            <Button variant="primary" onClick={handleRunBacktest} disabled={loading} style={{ width: '100%', marginTop: '8px' }}>
              {loading ? 'Processing...' : <><Play size={18} /> Execute Strategy</>}
            </Button>
          </div>
        </Card>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {error && <Card className="text-danger">{error}</Card>}
          
          {result ? (
            <Card variant="glass">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <h3 style={{ margin: 0 }}>Result Analysis</h3>
                  <Badge variant={result.run.status === 'COMPLETED' ? 'success' : 'primary'}>{result.run.status}</Badge>
                </div>
                <span className="text-xs text-muted text-mono">RUN_ID: {result.run.id}</span>
              </div>

              <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px' }}>
                <div className="card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
                  <span className="text-xs text-muted text-mono">FINAL CAPITAL</span>
                  <div className="text-mono" style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '4px', color: (result.run.final_capital || 0) >= result.run.initial_capital ? 'var(--success)' : 'var(--danger)' }}>
                    ${result.run.final_capital?.toLocaleString() || 'N/A'}
                  </div>
                </div>
                <div className="card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
                  <span className="text-xs text-muted text-mono">TOTAL RETURN</span>
                  <div className="text-mono" style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '4px' }}>
                    {result.run.final_capital ? (((result.run.final_capital - result.run.initial_capital) / result.run.initial_capital) * 100).toFixed(2) : 0}%
                  </div>
                </div>
                <div className="card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
                  <span className="text-xs text-muted text-mono">WIN RATE</span>
                  <div className="text-mono" style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '4px' }}>
                    {(result.metrics.metrics.win_rate * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
                  <span className="text-xs text-muted text-mono">SHARPE RATIO</span>
                  <div className="text-mono" style={{ fontSize: '1.4rem', fontWeight: 700, marginTop: '4px' }}>
                    {result.metrics.metrics.sharpe.toFixed(2)}
                  </div>
                </div>
              </div>

              <div style={{ marginTop: '32px' }}>
                <span className="text-xs text-muted text-mono">EQUITY PERFORMANCE</span>
                <div style={{ width: '100%', height: '240px', backgroundColor: 'rgba(247,147,26,0.03)', border: '1px dashed var(--primary)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', marginTop: '12px' }}>
                  <div style={{ textAlign: 'center' }}>
                    <TrendingUp size={48} style={{ opacity: 0.2, marginBottom: '12px', color: 'var(--primary)' }} />
                    <p className="text-sm">Historical Equity Visualization Coming in v2</p>
                  </div>
                </div>
              </div>
            </Card>
          ) : !loading && !error && (
            <Card variant="glass" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '300px' }}>
              <div style={{ textAlign: 'center' }} className="text-muted">
                <Play size={48} style={{ opacity: 0.1, marginBottom: '16px' }} />
                <p>Configure and run a backtest to see results</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </PageContainer>
  );
};

export default BacktestPage;
