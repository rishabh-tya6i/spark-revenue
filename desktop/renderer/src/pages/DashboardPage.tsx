import React, { useEffect, useState, useCallback } from 'react';
import { useSymbol } from '../context/SymbolContext';
import { getLatestDecision, FusedDecisionDTO } from '../api/decisionApi';
import { getOptionsSignal, OptionSignalOut } from '../api/optionsApi';
import { getLatestSentiment, NewsSentimentOut } from '../api/sentimentApi';
import { TrendingUp, TrendingDown, Minus, MessageSquare, Activity, Zap, Loader2 } from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import Card from '../components/ui/Card';
import { KeyValueGrid, KeyValueItem } from '../components/data/KeyValueGrid';
import { StatusBadge } from '../components/data/StatusBadge';
import { SectionHeader } from '../components/data/SectionHeader';
import { EmptyState } from '../components/data/EmptyState';

const DashboardPage: React.FC = () => {
  const { symbol, interval } = useSymbol();
  const [decision, setDecision] = useState<FusedDecisionDTO | null>(null);
  const [options, setOptions] = useState<OptionSignalOut | null>(null);
  const [sentiment, setSentiment] = useState<NewsSentimentOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
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
      setError('Failed to fetch signal monitoring data');
    } finally {
      setLoading(false);
    }
  }, [symbol, interval]);

  useEffect(() => {
    fetchData();
    const poll = window.setInterval(fetchData, 30000); // Poll every 30s
    return () => clearInterval(poll);
  }, [fetchData]);

  const renderDecisionSection = () => {
    if (!decision) {
      return <EmptyState message={`No fused decision available for ${symbol} ${interval}`} />;
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="text-xs text-muted text-mono uppercase">DECISION LABEL</span>
          <StatusBadge type="decision" status={decision.decision_label} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }} className="text-muted text-mono uppercase">
            <span>Confidence Score</span>
            <span>{(decision.decision_score * 100).toFixed(1)}%</span>
          </div>
          <div className="progress-bar" style={{ height: '6px' }}>
            <div className="progress-fill" style={{ width: `${decision.decision_score * 100}%`, backgroundColor: 'var(--primary)' }}></div>
          </div>
        </div>

        <KeyValueGrid>
          <KeyValueItem 
            label="Price Signal" 
            value={
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {decision.price_direction === 'BULLISH' ? <TrendingUp size={16} color="var(--success)" /> : decision.price_direction === 'BEARISH' ? <TrendingDown size={16} color="var(--danger)" /> : <Minus size={16} />}
                <span>{decision.price_direction}</span>
              </div>
            } 
          />
          <KeyValueItem label="Price Confidence" value={`${(decision.price_confidence * 100).toFixed(0)}%`} />
          <KeyValueItem label="RL Action" value={decision.rl_action} />
          <KeyValueItem label="RL Confidence" value={`${(decision.rl_confidence * 100).toFixed(0)}%`} />
        </KeyValueGrid>
      </div>
    );
  };

  const renderOptionsSection = () => {
    if (!options) {
      return <EmptyState message="No options intel available" />;
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="text-xs text-muted text-mono uppercase">OPTION SIGNAL</span>
          <StatusBadge type="decision" status={options.signal_label} />
        </div>

        <KeyValueGrid>
          <KeyValueItem label="PCR (PUT/CALL)" value={options.pcr.toFixed(3)} />
          <KeyValueItem label="MAX PAIN STRIKE" value={`$${options.max_pain_strike.toLocaleString()}`} />
          <KeyValueItem label="CALL OI TOTAL" value={options.call_oi_total.toLocaleString()} />
          <KeyValueItem label="PUT OI TOTAL" value={options.put_oi_total.toLocaleString()} />
        </KeyValueGrid>
      </div>
    );
  };

  const renderSentimentSection = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {decision && (
          <div className="glass-panel" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span className="text-xs text-muted text-mono uppercase">AGGREGATE SENTIMENT</span>
              <span className="text-mono" style={{ color: decision.sentiment_label === 'POSITIVE' ? 'var(--success)' : decision.sentiment_label === 'NEGATIVE' ? 'var(--danger)' : 'var(--muted)', fontWeight: 700 }}>
                {decision.sentiment_label}
              </span>
            </div>
            <div className="progress-bar" style={{ backgroundColor: 'rgba(255,255,255,0.05)', height: '8px' }}>
              <div className="progress-fill" style={{ 
                backgroundColor: decision.sentiment_score > 0 ? 'var(--success)' : 'var(--danger)',
                marginLeft: decision.sentiment_score > 0 ? '50%' : `${50 - Math.abs(decision.sentiment_score) * 50}%`,
                width: `${Math.abs(decision.sentiment_score) * 50}%`
              }}></div>
            </div>
            <div className="text-xs text-muted text-mono" style={{ marginTop: '8px', textAlign: 'center' }}>
              SCORE: {decision.sentiment_score.toFixed(2)}
            </div>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <span className="text-xs text-muted text-mono uppercase">LATEST HEADLINES</span>
          {sentiment.length > 0 ? (
            sentiment.map((s, idx) => (
              <div key={idx} style={{ 
                padding: '12px', 
                borderLeft: `4px solid ${s.sentiment_label === 'POSITIVE' ? 'var(--success)' : s.sentiment_label === 'NEGATIVE' ? 'var(--danger)' : 'var(--muted)'}`, 
                backgroundColor: 'rgba(255,255,255,0.02)', 
                borderRadius: '0 4px 4px 0' 
              }}>
                <div style={{ fontSize: '0.85rem', marginBottom: '4px' }} className="text-mono">{`NEWS ITEM #${s.news_id}`}</div>
                <div style={{ fontSize: '0.75rem' }} className="text-muted text-mono">
                  {`SCORE: ${s.sentiment_score.toFixed(2)} | ${s.sentiment_label}`}
                </div>
              </div>
            ))
          ) : (
            <div className="text-muted text-sm italic">No headlines found</div>
          )}
        </div>
      </div>
    );
  };

  if (loading && !decision && !options) {
    return (
      <PageContainer title="Signal Monitoring">
        <EmptyState message="Fetching market signals..." icon={<Loader2 className="animate-spin" size={40} />} />
      </PageContainer>
    );
  }

  return (
    <PageContainer title="Signal Monitoring">
      {error && (
        <Card className="text-danger" style={{ marginBottom: '24px' }}>
          {error}
        </Card>
      )}

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '24px' }}>
        {/* Fused Decision */}
        <Card>
          <SectionHeader 
            title="Fused Decision" 
            icon={<Zap size={20} color="var(--tertiary)" />} 
            onRefresh={fetchData} 
            loading={loading} 
          />
          {renderDecisionSection()}
        </Card>

        {/* Options Intel */}
        <Card>
          <SectionHeader 
            title="Options Intel" 
            icon={<Activity size={20} color="var(--primary)" />} 
          />
          {renderOptionsSection()}
        </Card>

        {/* Sentiment */}
        <Card>
          <SectionHeader 
            title="Market Sentiment" 
            icon={<MessageSquare size={20} color="var(--secondary)" />} 
          />
          {renderSentimentSection()}
        </Card>
      </div>
    </PageContainer>
  );
};

export default DashboardPage;
