import React, { useEffect, useState } from 'react';
import { useSymbol } from '../context/SymbolContext';
import { getLatestDecision, FusedDecisionDTO } from '../api/decisionApi';
import { getOptionsSignal, OptionSignalOut } from '../api/optionsApi';
import { getLatestSentiment, NewsSentimentOut } from '../api/sentimentApi';
import { TrendingUp, TrendingDown, Minus, MessageSquare, Activity } from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';

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

  const getBadgeVariant = (label: string): 'primary' | 'success' | 'danger' | 'muted' => {
    const l = label.toLowerCase();
    if (l.includes('bullish')) return 'success';
    if (l.includes('bearish')) return 'danger';
    if (l.includes('neutral')) return 'muted';
    return 'primary';
  };

  if (loading && !decision) return <PageContainer title="Overview"><div>Loading dashboard...</div></PageContainer>;

  return (
    <PageContainer title="Overview">
      {error && <Card className="text-danger" style={{ marginBottom: '24px' }}>{error}</Card>}
      
      <div className="grid">
        {/* Decision Panel */}
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
            <h3 style={{ margin: 0 }}>Fused Decision</h3>
            {decision && (
              <Badge variant={getBadgeVariant(decision.decision_label)}>
                {decision.decision_label}
              </Badge>
            )}
          </div>
          {decision ? (
            <div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${decision.decision_score * 100}%`, backgroundColor: 'var(--primary)' }}></div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }} className="text-muted text-mono">
                <span>Confidence Score</span>
                <span>{(decision.decision_score * 100).toFixed(1)}%</span>
              </div>
              
              <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-xs text-muted text-mono">Price Signal</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }} className="text-mono">
                    {decision.price_direction === 'BULLISH' ? <TrendingUp size={14} color="var(--success)" /> : decision.price_direction === 'BEARISH' ? <TrendingDown size={14} color="var(--danger)" /> : <Minus size={14} />}
                    {decision.price_direction} ({(decision.price_confidence * 100).toFixed(0)}%)
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-xs text-muted text-mono">RL Action</span>
                  <span className="text-mono">{decision.rl_action} ({(decision.rl_confidence * 100).toFixed(0)}%)</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-muted">No decision data for {symbol} {interval}</div>
          )}
        </Card>

        {/* Options Signal Card */}
        <Card>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Activity size={20} color="var(--primary)" /> Options Intel
          </h3>
          {options ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">Signal</span>
                <Badge variant={getBadgeVariant(options.signal_label)}>{options.signal_label}</Badge>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">PCR (Put/Call Ratio)</span>
                <span className="text-mono" style={{ fontWeight: 600 }}>{options.pcr.toFixed(3)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-xs text-muted text-mono">Max Pain Strike</span>
                <span className="text-mono" style={{ fontWeight: 600 }}>${options.max_pain_strike.toLocaleString()}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }} className="text-muted text-mono">
                <span>C: {options.call_oi_total.toLocaleString()}</span>
                <span>P: {options.put_oi_total.toLocaleString()}</span>
              </div>
            </div>
          ) : (
            <div className="text-muted">No options data available</div>
          )}
        </Card>

        {/* Sentiment Meter */}
        <Card>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <MessageSquare size={20} color="var(--tertiary)" /> Market Sentiment
          </h3>
          {decision && (
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span className="text-xs text-muted text-mono">Aggregate Sentiment</span>
                <span className="text-mono" style={{ color: decision.sentiment_label === 'POSITIVE' ? 'var(--success)' : decision.sentiment_label === 'NEGATIVE' ? 'var(--danger)' : 'var(--muted)', fontWeight: 700 }}>
                  {decision.sentiment_label}
                </span>
              </div>
              <div className="progress-bar" style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}>
                <div className="progress-fill" style={{ 
                  backgroundColor: decision.sentiment_score > 0 ? 'var(--success)' : 'var(--danger)',
                  marginLeft: decision.sentiment_score > 0 ? '50%' : `${50 - Math.abs(decision.sentiment_score) * 50}%`,
                  width: `${Math.abs(decision.sentiment_score) * 50}%`
                }}></div>
              </div>
            </div>
          )}
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <span className="text-xs text-muted text-mono">Latest Headlines</span>
            {sentiment.map((s, idx) => (
              <div key={idx} style={{ padding: '8px', borderLeft: `3px solid ${s.sentiment_label === 'POSITIVE' ? 'var(--success)' : s.sentiment_label === 'NEGATIVE' ? 'var(--danger)' : 'var(--muted)'}`, backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '0 4px 4px 0' }}>
                <div style={{ fontSize: '0.85rem' }} className="text-mono">News Item #{s.news_id}</div>
                <div style={{ fontSize: '0.75rem' }} className="text-muted text-mono">Score: {s.sentiment_score.toFixed(2)} | {s.sentiment_label}</div>
              </div>
            ))}
            {sentiment.length === 0 && <div style={{ fontSize: '0.85rem' }} className="text-muted">No news scored yet</div>}
          </div>
        </Card>
      </div>
    </PageContainer>
  );
};

export default DashboardPage;
