import React, { createContext, useContext, useState, ReactNode } from 'react';

interface SymbolContextType {
  symbol: string;
  interval: string;
  setSymbol: (symbol: string) => void;
  setInterval: (interval: string) => void;
}

const SymbolContext = createContext<SymbolContextType | undefined>(undefined);

export const SymbolProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [interval, setInterval] = useState('5m');

  return (
    <SymbolContext.Provider value={{ symbol, interval, setSymbol, setInterval }}>
      {children}
    </SymbolContext.Provider>
  );
};

export const useSymbol = () => {
  const context = useContext(SymbolContext);
  if (!context) {
    throw new Error('useSymbol must be used within a SymbolProvider');
  }
  return context;
};
