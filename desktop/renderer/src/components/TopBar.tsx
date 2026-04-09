import React from 'react';
import { useSymbol } from '../context/SymbolContext';

const TopBar: React.FC = () => {
  const { symbol, interval, setSymbol, setInterval } = useSymbol();

  return (
    <div className="top-bar" style={{ display: 'flex', gap: '16px', marginBottom: '32px', alignItems: 'center' }}>
      <div>
        <span className="label">Symbol</span>
        <input 
          type="text" 
          value={symbol} 
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          placeholder="BTCUSDT"
        />
      </div>
      <div>
        <span className="label">Interval</span>
        <select value={interval} onChange={(e) => setInterval(e.target.value)}>
          <option value="1m">1m</option>
          <option value="5m">5m</option>
          <option value="15m">15m</option>
          <option value="1h">1h</option>
          <option value="1d">1d</option>
        </select>
      </div>
    </div>
  );
};

export default TopBar;
