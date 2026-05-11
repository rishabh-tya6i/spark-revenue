import React from 'react';

interface KeyValueItemProps {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  valueColor?: string;
}

export const KeyValueItem: React.FC<KeyValueItemProps> = ({ label, value, mono = true, valueColor }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
    <div className="text-xs text-muted text-mono uppercase">{label}</div>
    <div 
      className={mono ? 'text-mono' : ''} 
      style={{ fontSize: '1.1rem', color: valueColor || 'var(--text-main)' }}
    >
      {value}
    </div>
  </div>
);

interface KeyValueGridProps {
  children: React.ReactNode;
  cols?: number;
}

export const KeyValueGrid: React.FC<KeyValueGridProps> = ({ children, cols = 2 }) => (
  <div style={{ 
    display: 'grid', 
    gridTemplateColumns: `repeat(${cols}, 1fr)`, 
    gap: '16px' 
  }}>
    {children}
  </div>
);
