import React, { useEffect, useMemo, useState } from 'react';
import PageContainer from '../components/layout/PageContainer';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { SectionHeader } from '../components/data/SectionHeader';
import { KeyValueGrid, KeyValueItem } from '../components/data/KeyValueGrid';
import { EmptyState } from '../components/data/EmptyState';
import { AlertCircle, CheckCircle2, KeyRound, RefreshCcw, Download, Brain } from 'lucide-react';

import { useSymbol } from '../context/SymbolContext';
import { clearUpstoxToken, getUpstoxTokenStatus, setUpstoxToken } from '../api/settingsApi';
import { syncInstruments } from '../api/instrumentsApi';
import { backfillOhlc } from '../api/ingestionApi';
import { prepareTrainingData, runTrainTrainable } from '../api/orchestrationApi';

const SetupPage: React.FC = () => {
  const { symbol, interval } = useSymbol();

  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const thirtyDaysAgo = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().slice(0, 10);
  }, []);

  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string | null>>({});
  const [results, setResults] = useState<Record<string, any>>({});

  const [tokenStatus, setTokenStatus] = useState<{ present: boolean; masked: string; source: string } | null>(null);
  const [tokenInput, setTokenInput] = useState('');

  const [segments, setSegments] = useState('NSE_INDEX,BSE_INDEX');

  const [backfillSymbol, setBackfillSymbol] = useState(symbol || 'NIFTY');
  const [backfillStart, setBackfillStart] = useState(thirtyDaysAgo);
  const [backfillEnd, setBackfillEnd] = useState(today);

  const runAction = async (key: string, fn: () => Promise<any>) => {
    setLoading(prev => ({ ...prev, [key]: true }));
    setErrors(prev => ({ ...prev, [key]: null }));
    try {
      const res = await fn();
      setResults(prev => ({ ...prev, [key]: res }));
      return res;
    } catch (err: any) {
      setErrors(prev => ({ ...prev, [key]: err.response?.data?.detail || err.message }));
      return null;
    } finally {
      setLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  const renderError = (msg: string | null) =>
    msg ? (
      <div className="glass-panel text-danger mb-md p-sm flex items-center gap-sm">
        <AlertCircle size={14} /> <span className="text-sm">{msg}</span>
      </div>
    ) : null;

  const refreshTokenStatus = async () => {
    const res = await runAction('token-status', () => getUpstoxTokenStatus());
    if (res) setTokenStatus(res);
  };

  useEffect(() => {
    refreshTokenStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const tokenReady = !!tokenStatus?.present;

  return (
    <PageContainer title="Setup (Step by Step)">
      <div className="grid gap-lg" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))' }}>
        {/* Step 1: Token */}
        <Card className="flex-col">
          <SectionHeader title="Step 1 — Add Upstox Token" icon={<KeyRound size={20} color="var(--primary)" />} />
          <div className="text-sm text-muted mb-md">
            Paste your Upstox access token here. It is saved in Redis (not in `.env`).
          </div>

          {renderError(errors.token)}

          <KeyValueGrid cols={2}>
            <KeyValueItem label="Token Saved" value={tokenReady ? 'YES' : 'NO'} valueColor={tokenReady ? 'var(--success)' : 'var(--danger)'} />
            <KeyValueItem label="Stored In" value={tokenStatus?.source || '...'} />
            <KeyValueItem label="Masked" value={tokenStatus?.masked || '...'} />
            <KeyValueItem label="Tip" value="Token expires; update here anytime." mono={false} />
          </KeyValueGrid>

          <div className="flex-col gap-sm" style={{ marginTop: '16px' }}>
            <label className="text-xs text-muted text-mono uppercase">TOKEN</label>
            <input
              className="input"
              value={tokenInput}
              onChange={e => setTokenInput(e.target.value)}
              placeholder="Paste Upstox token"
            />
            <div className="grid gap-sm" style={{ gridTemplateColumns: '1fr 1fr' }}>
              <Button
                variant="primary"
                disabled={loading.tokenSave || !tokenInput.trim()}
                onClick={async () => {
                  await runAction('token', () => setUpstoxToken(tokenInput));
                  setTokenInput('');
                  await refreshTokenStatus();
                }}
              >
                <CheckCircle2 size={18} />
                <span style={{ marginLeft: '8px' }}>{loading.tokenSave ? 'Saving...' : 'Save Token'}</span>
              </Button>
              <Button
                variant="outline"
                disabled={loading.tokenClear}
                onClick={async () => {
                  await runAction('token', () => clearUpstoxToken());
                  await refreshTokenStatus();
                }}
              >
                <RefreshCcw size={18} />
                <span style={{ marginLeft: '8px' }}>{loading.tokenClear ? 'Clearing...' : 'Remove Token'}</span>
              </Button>
            </div>
          </div>
        </Card>

        {/* Step 2: Instruments */}
        <Card className="flex-col">
          <SectionHeader title="Step 2 — Sync Symbols List" icon={<RefreshCcw size={20} color="var(--secondary)" />} />
          <div className="text-sm text-muted mb-md">
            Downloads the Upstox symbols list and stores it in the database. Needed before fetching NIFTY/SENSEX candles.
          </div>

          {!tokenReady && <EmptyState message="Add token first (Step 1)." />}
          {tokenReady && (
            <>
              {renderError(errors.sync)}
              <label className="text-xs text-muted text-mono uppercase">SEGMENTS</label>
              <input className="input" value={segments} onChange={e => setSegments(e.target.value)} />
              <Button
                variant="primary"
                disabled={loading.sync}
                onClick={() => runAction('sync', () => syncInstruments(segments))}
                style={{ width: '100%', marginTop: '12px' }}
              >
                <RefreshCcw size={18} />
                <span style={{ marginLeft: '8px' }}>{loading.sync ? 'Syncing...' : 'Sync Instruments'}</span>
              </Button>
              {results.sync && (
                <div className="glass-panel mt-md p-md">
                  <KeyValueGrid cols={2}>
                    <KeyValueItem label="Processed" value={results.sync.processed_count ?? 'N/A'} />
                  </KeyValueGrid>
                </div>
              )}
            </>
          )}
        </Card>

        {/* Step 3: Backfill */}
        <Card className="flex-col">
          <SectionHeader title="Step 3 — Download Price Bars" icon={<Download size={20} color="var(--success)" />} />
          <div className="text-sm text-muted mb-md">
            Fetches OHLC bars from Upstox for one symbol (example: NIFTY).
          </div>

          {!tokenReady && <EmptyState message="Add token first (Step 1)." />}
          {tokenReady && (
            <>
              {renderError(errors.backfill)}
              <label className="text-xs text-muted text-mono uppercase">SYMBOL</label>
              <input className="input" value={backfillSymbol} onChange={e => setBackfillSymbol(e.target.value)} />
              <div className="grid gap-sm" style={{ gridTemplateColumns: '1fr 1fr', marginTop: '8px' }}>
                <div>
                  <label className="text-xs text-muted text-mono uppercase">START</label>
                  <input className="input" value={backfillStart} onChange={e => setBackfillStart(e.target.value)} />
                </div>
                <div>
                  <label className="text-xs text-muted text-mono uppercase">END</label>
                  <input className="input" value={backfillEnd} onChange={e => setBackfillEnd(e.target.value)} />
                </div>
              </div>
              <Button
                variant="primary"
                disabled={loading.backfill}
                onClick={() =>
                  runAction('backfill', () =>
                    backfillOhlc({ source: 'upstox', symbol: backfillSymbol, start: backfillStart, end: backfillEnd, interval })
                  )
                }
                style={{ width: '100%', marginTop: '12px' }}
              >
                <Download size={18} />
                <span style={{ marginLeft: '8px' }}>{loading.backfill ? 'Downloading...' : 'Download Bars'}</span>
              </Button>
            </>
          )}
        </Card>

        {/* Step 4: Features */}
        <Card className="flex-col">
          <SectionHeader title="Step 4 — Build Features" icon={<RefreshCcw size={20} color="var(--tertiary)" />} />
          <div className="text-sm text-muted mb-md">
            Builds indicators (RSI, EMA, VWAP) from bars. This step also checks if training is ready.
          </div>
          {renderError(errors.prep)}
          <Button
            variant="primary"
            disabled={loading.prep}
            onClick={() => runAction('prep', () => prepareTrainingData({ interval, lookback_days: 30, sync_first: false }))}
            style={{ width: '100%' }}
          >
            <RefreshCcw size={18} />
            <span style={{ marginLeft: '8px' }}>{loading.prep ? 'Building...' : 'Build Features'}</span>
          </Button>
          {results.prep && (
            <div className="glass-panel mt-md p-md">
              <KeyValueGrid cols={2}>
                <KeyValueItem label="Trainable" value={(results.prep.trainable_symbols || []).join(', ') || 'None'} mono={false} />
                <KeyValueItem label="Interval" value={results.prep.interval || interval} />
              </KeyValueGrid>
            </div>
          )}
        </Card>

        {/* Step 5: Train */}
        <Card className="flex-col">
          <SectionHeader title="Step 5 — Train Models" icon={<Brain size={20} color="var(--primary)" />} />
          <div className="text-sm text-muted mb-md">
            Trains the price model + RL model for symbols that have enough data.
          </div>
          {renderError(errors.train)}
          <Button
            variant="primary"
            disabled={loading.train}
            onClick={() => runAction('train', () => runTrainTrainable({ interval, lookback_days: 30, sync_first: false, epochs: 10 }))}
            style={{ width: '100%' }}
          >
            <Brain size={18} />
            <span style={{ marginLeft: '8px' }}>{loading.train ? 'Training...' : 'Train'}</span>
          </Button>
        </Card>
      </div>
    </PageContainer>
  );
};

export default SetupPage;

