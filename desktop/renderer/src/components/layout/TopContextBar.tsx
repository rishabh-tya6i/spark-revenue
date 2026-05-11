import React from 'react';
import { useSymbol } from '../../context/SymbolContext';

const TopContextBar: React.FC = () => {
  const { symbol, interval, setSymbol, setInterval } = useSymbol();

  return (
    <header className="top-bar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="text-xs text-muted text-mono" style={{ textTransform: 'uppercase' }}>Symbol</span>
          <input 
            type="text" 
            value={symbol} 
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            className="text-mono"
            style={{ width: '120px', height: '32px' }}
          />
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="text-xs text-muted text-mono" style={{ textTransform: 'uppercase' }}>Interval</span>
          <select 
            value={interval} 
            onChange={(e) => setInterval(e.target.value)}
            style={{ height: '32px' }}
          >
            <option value="1m">1m</option>
            <option value="5m">5m</option>
            <option value="15m">15m</option>
            <option value="1h">1h</option>
            <option value="1d">1d</option>
          </select>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div className="badge badge-primary">Live Data</div>
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--success)', boxShadow: '0 0 8px var(--success)' }}></div>
      </div>
    </header>
  );
};

export default TopContextBar;
