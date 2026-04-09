import React, { useEffect, useState } from 'react';
import { useSymbol } from '../context/SymbolContext';
import { getLatestDecision, FusedDecisionDTO } from '../api/decisionApi';
import { getOptionsSignal, OptionSignalOut } from '../api/optionsApi';
import { getLatestSentiment, NewsSentimentOut } from '../api/sentimentApi';
import TopBar from '../components/TopBar';
import { TrendingUp, TrendingDown, Minus, Info, MessageSquare, Activity } from 'lucide-react';

const DashboardPage: React.FC = () => {
  const { symbol, interval } = useSymbol();
  const [decision, setDecision] = useState<FusedDecisionDTO | null>(null);
  const [options, setOptions] = useState<OptionSignalOut | null>(null);
  const [sentiment, setSentiment] = useState<NewsSentimentOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [decisionData, optionsData, sentimentData] = await Promise.all([
          getLatestDecision(symbol, interval).catch(() => null),
          getOptionsSignal(symbol).catch(() => null),
          getLatestSentiment(5).catch(() => []),
        ]);
        setDecision(decisionData);
        setOptions(optionsData);
        setSentiment(sentimentData);
      } catch (err) {
        setError('Failed to fetch dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const poll = window.setInterval(fetchData, 30000); // Poll every 30s
    return () => clearInterval(poll);
  }, [symbol, interval]);

  const getDecisionClass = (label: string) => {
    const l = label.toLowerCase();
    if (l.includes('strong_bullish')) return 'decision-strong-bullish';
    if (l.includes('bullish')) return 'decision-bullish';
    if (l.includes('strong_bearish')) return 'decision-strong-bearish';
    if (l.includes('bearish')) return 'decision-bearish';
    return 'decision-neutral';
  };

  if (loading && !decision) return <div>Loading dashboard...</div>;

  return (
    <div>
      <TopBar />
      {error && <div className="card" style={{ color: 'var(--danger)' }}>{error}</div>}
      
      <div className="grid">
        {/* Decision Panel */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
            <h3 style={{ margin: 0 }}>Fused Decision</h3>
            {decision && (
              <span className={`decision-badge ${getDecisionClass(decision.decision_label)}`}>
                {decision.decision_label}
              </span>
            )}
          </div>
          {decision ? (
            <div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${decision.decision_score * 100}%` }}></div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                <span>Confidence Score</span>
                <span>{(decision.decision_score * 100).toFixed(1)}%</span>
              </div>
              
              <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="label" style={{ margin: 0 }}>Price Signal</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    {decision.price_direction === 'BULLISH' ? <TrendingUp size={14} color="#00ff88" /> : decision.price_direction === 'BEARISH' ? <TrendingDown size={14} color="#ff4d4d" /> : <Minus size={14} />}
                    {decision.price_direction} ({(decision.price_confidence * 100).toFixed(0)}%)
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="label" style={{ margin: 0 }}>RL Action</span>
                  <span>{decision.rl_action} ({(decision.rl_confidence * 100).toFixed(0)}%)</span>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-secondary)' }}>No decision data for {symbol} {interval}</div>
          )}
        </div>

        {/* Options Signal Card */}
        <div className="card">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={20} color="var(--accent)" /> Options Intel
          </h3>
          {options ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="label">Signal</span>
                <span className={`decision-badge ${getDecisionClass(options.signal_label)}`}>{options.signal_label}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="label">PCR (Put/Call Ratio)</span>
                <span style={{ fontWeight: 600 }}>{options.pcr.toFixed(3)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="label">Max Pain Strike</span>
                <span style={{ fontWeight: 600 }}>${options.max_pain_strike.toLocaleString()}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                <span>C: {options.call_oi_total.toLocaleString()}</span>
                <span>P: {options.put_oi_total.toLocaleString()}</span>
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-secondary)' }}>No options data available</div>
          )}
        </div>

        {/* Sentiment Meter */}
        <div className="card">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MessageSquare size={20} color="#ffcc00" /> Market Sentiment
          </h3>
          {decision && (
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span className="label">Aggregate Sentiment</span>
                <span style={{ color: decision.sentiment_label === 'POSITIVE' ? '#00ff88' : decision.sentiment_label === 'NEGATIVE' ? '#ff4d4d' : '#a0a0a0', fontWeight: 700 }}>
                  {decision.sentiment_label}
                </span>
              </div>
              <div className="progress-bar" style={{ backgroundColor: 'rgba(160,160,160,0.1)' }}>
                <div className="progress-fill" style={{ 
                  backgroundColor: decision.sentiment_score > 0 ? '#00ff88' : '#ff4d4d',
                  marginLeft: decision.sentiment_score > 0 ? '50%' : `${50 - Math.abs(decision.sentiment_score) * 50}%`,
                  width: `${Math.abs(decision.sentiment_score) * 50}%`
                }}></div>
              </div>
            </div>
          )}
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <span className="label">Latest Headlines</span>
            {sentiment.map((s, idx) => (
              <div key={idx} style={{ padding: '8px', borderLeft: `3px solid ${s.sentiment_label === 'POSITIVE' ? '#00ff88' : s.sentiment_label === 'NEGATIVE' ? '#ff4d4d' : '#a0a0a0'}`, backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '0 4px 4px 0' }}>
                <div style={{ fontSize: '0.85rem' }}>News Item #{s.news_id}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Score: {s.sentiment_score.toFixed(2)} | {s.sentiment_label}</div>
              </div>
            ))}
            {sentiment.length === 0 && <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>No news scored yet</div>}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
