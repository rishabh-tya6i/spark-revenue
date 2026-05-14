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

  const asNumber = (value: any): number | null => {
    if (typeof value === 'number') return Number.isFinite(value) ? value : null;
    const num = Number(value);
    return Number.isFinite(num) ? num : null;
  };

  const formatPercent = (value: any, digits: number = 0): string => {
    const num = asNumber(value);
    if (num === null) return 'N/A';
    return `${(num * 100).toFixed(digits)}%`;
  };

  const formatFixed = (value: any, digits: number = 2): string => {
    const num = asNumber(value);
    return num === null ? 'N/A' : num.toFixed(digits);
  };

  const renderDecisionSection = () => {
    if (!decision) {
      return <EmptyState message={`No fused decision available for ${symbol} ${interval}`} />;
    }

    const decisionScore = asNumber(decision.decision_score) ?? 0;

    return (
      <div className="flex-col gap-md">
        <div className="flex justify-between items-center">
          <span className="text-xs text-muted text-mono uppercase">DECISION LABEL</span>
          <StatusBadge type="decision" status={decision.decision_label} />
        </div>

        <div className="flex-col gap-sm">
          <div className="flex justify-between text-muted text-mono uppercase" style={{ fontSize: '0.85rem' }}>
            <span>Confidence Score</span>
            <span>{formatPercent(decision.decision_score, 1)}</span>
          </div>
          <div className="progress-bar" style={{ height: '6px' }}>
            <div className="progress-fill" style={{ width: `${decisionScore * 100}%`, backgroundColor: 'var(--primary)' }}></div>
          </div>
        </div>

        <KeyValueGrid>
          <KeyValueItem 
            label="Price Signal" 
            value={
              <div className="flex items-center gap-sm">
                {decision.price_direction === 'BULLISH' ? <TrendingUp size={16} color="var(--success)" /> : decision.price_direction === 'BEARISH' ? <TrendingDown size={16} color="var(--danger)" /> : <Minus size={16} />}
                <span>{decision.price_direction}</span>
              </div>
            } 
          />
          <KeyValueItem label="Price Confidence" value={formatPercent(decision.price_confidence, 0)} />
          <KeyValueItem label="RL Action" value={decision.rl_action} />
          <KeyValueItem label="RL Confidence" value={formatPercent(decision.rl_confidence, 0)} />
        </KeyValueGrid>
      </div>
    );
  };

  const renderOptionsSection = () => {
    if (!options) {
      return <EmptyState message="No options intel available" />;
    }

    return (
      <div className="flex-col gap-md">
        <div className="flex justify-between items-center">
          <span className="text-xs text-muted text-mono uppercase">OPTION SIGNAL</span>
          <StatusBadge type="decision" status={options.signal_label} />
        </div>

        <KeyValueGrid>
          <KeyValueItem label="PCR (PUT/CALL)" value={formatFixed(options.pcr, 3)} />
          <KeyValueItem label="MAX PAIN STRIKE" value={asNumber(options.max_pain_strike) === null ? 'N/A' : `$${options.max_pain_strike.toLocaleString()}`} />
          <KeyValueItem label="CALL OI TOTAL" value={asNumber(options.call_oi_total) === null ? 'N/A' : options.call_oi_total.toLocaleString()} />
          <KeyValueItem label="PUT OI TOTAL" value={asNumber(options.put_oi_total) === null ? 'N/A' : options.put_oi_total.toLocaleString()} />
        </KeyValueGrid>
      </div>
    );
  };

  const renderSentimentSection = () => {
    const sentimentScore = decision ? asNumber(decision.sentiment_score) : null;
    return (
      <div className="flex-col gap-md">
        {decision && (
          <div className="glass-panel p-md">
            <div className="flex justify-between items-center mb-md">
              <span className="text-xs text-muted text-mono uppercase">AGGREGATE SENTIMENT</span>
              <span className="text-mono" style={{ color: decision.sentiment_label === 'POSITIVE' ? 'var(--success)' : decision.sentiment_label === 'NEGATIVE' ? 'var(--danger)' : 'var(--muted)', fontWeight: 700 }}>
                {decision.sentiment_label}
              </span>
            </div>
            <div className="progress-bar" style={{ backgroundColor: 'rgba(255,255,255,0.05)', height: '8px' }}>
              <div className="progress-fill" style={{ 
                backgroundColor: (sentimentScore ?? 0) > 0 ? 'var(--success)' : 'var(--danger)',
                marginLeft: (sentimentScore ?? 0) > 0 ? '50%' : `${50 - Math.abs(sentimentScore ?? 0) * 50}%`,
                width: `${Math.abs(sentimentScore ?? 0) * 50}%`
              }}></div>
            </div>
            <div className="text-xs text-muted text-mono" style={{ marginTop: '8px', textAlign: 'center' }}>
              SCORE: {formatFixed(decision.sentiment_score, 2)}
            </div>
          </div>
        )}

        <div className="flex-col gap-md">
          <span className="text-xs text-muted text-mono uppercase">LATEST HEADLINES</span>
          {sentiment.length > 0 ? (
            sentiment.map((s, idx) => (
              <div key={idx} className="p-sm" style={{ 
                borderLeft: `4px solid ${s.sentiment_label === 'POSITIVE' ? 'var(--success)' : s.sentiment_label === 'NEGATIVE' ? 'var(--danger)' : 'var(--muted)'}`, 
                backgroundColor: 'rgba(255,255,255,0.02)', 
                borderRadius: '0 4px 4px 0' 
              }}>
                <div style={{ fontSize: '0.85rem' }} className="text-mono mb-xs">{`NEWS ITEM #${s.news_id}`}</div>
                <div style={{ fontSize: '0.75rem' }} className="text-muted text-mono">
                  {`SCORE: ${formatFixed(s.sentiment_score, 2)} | ${s.sentiment_label}`}
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
        <Card className="text-danger mb-lg">
          {error}
        </Card>
      )}

      <div className="grid gap-lg" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))' }}>
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
