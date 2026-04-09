import React, { useState } from 'react';
import { useSymbol } from '../context/SymbolContext';
import { runBacktest, BacktestRunOut, BacktestMetricsOut } from '../api/backtestApi';
import TopBar from '../components/TopBar';
import { Play, TrendingUp, DollarSign, Activity, Percent } from 'lucide-react';

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
    <div>
      <TopBar />
      <div className="grid">
        <div className="card">
          <h3>Configure Backtest</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <span className="label">Start Date</span>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={{ width: '100%' }} />
            </div>
            <div>
              <span className="label">End Date</span>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={{ width: '100%' }} />
            </div>
            <div>
              <span className="label">Initial Capital ($)</span>
              <input type="number" value={initialCapital} onChange={(e) => setInitialCapital(Number(e.target.value))} style={{ width: '100%' }} />
            </div>
            <button className="primary" onClick={handleRunBacktest} disabled={loading} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
              {loading ? 'Running...' : <><Play size={18} /> Run Backtest</>}
            </button>
          </div>
        </div>

        {result && (
          <div className="card" style={{ gridColumn: 'span 2' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px' }}>
              <h3 style={{ margin: 0 }}>Results: {result.run.status}</h3>
              <span className="label">Run ID: {result.run.id}</span>
            </div>

            <div className="grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              <div className="card" style={{ marginBottom: 0, padding: '16px', background: 'rgba(255,255,255,0.03)' }}>
                <span className="label">Final Capital</span>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: (result.run.final_capital || 0) >= result.run.initial_capital ? '#00ff88' : '#ff4d4d' }}>
                  ${result.run.final_capital?.toLocaleString() || 'N/A'}
                </div>
              </div>
              <div className="card" style={{ marginBottom: 0, padding: '16px', background: 'rgba(255,255,255,0.03)' }}>
                <span className="label">Total Return</span>
                <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>
                  {result.run.final_capital ? (((result.run.final_capital - result.run.initial_capital) / result.run.initial_capital) * 100).toFixed(2) : 0}%
                </div>
              </div>
              <div className="card" style={{ marginBottom: 0, padding: '16px', background: 'rgba(255,255,255,0.03)' }}>
                <span className="label">Win Rate</span>
                <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>
                  {(result.metrics.metrics.win_rate * 100).toFixed(1)}%
                </div>
              </div>
              <div className="card" style={{ marginBottom: 0, padding: '16px', background: 'rgba(255,255,255,0.03)' }}>
                <span className="label">Sharpe Ratio</span>
                <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>
                  {result.metrics.metrics.sharpe.toFixed(2)}
                </div>
              </div>
            </div>

            <div style={{ marginTop: '32px' }}>
              <span className="label">Equity Curve (v1 Placeholder)</span>
              <div style={{ width: '100%', height: '200px', backgroundColor: 'rgba(0,255,136,0.05)', border: '1px dashed var(--accent)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                <div style={{ textAlign: 'center' }}>
                  <TrendingUp size={48} style={{ opacity: 0.3, marginBottom: '12px' }} />
                  <p>Historical Equity Visualization Coming in v2</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {error && <div className="card" style={{ color: 'var(--danger)', gridColumn: 'span 2' }}>{error}</div>}
      </div>
    </div>
  );
};

export default BacktestPage;
