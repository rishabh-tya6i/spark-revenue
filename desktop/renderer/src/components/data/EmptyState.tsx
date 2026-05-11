import React from 'react';
import { AlertCircle, HelpCircle } from 'lucide-react';

interface EmptyStateProps {
  message: string;
  icon?: React.ReactNode;
  type?: 'info' | 'error';
}

export const EmptyState: React.FC<EmptyStateProps> = ({ message, icon, type = 'info' }) => (
  <div style={{ 
    display: 'flex', 
    flexDirection: 'column', 
    alignItems: 'center', 
    justifyContent: 'center', 
    padding: '40px',
    color: 'var(--text-muted)',
    textAlign: 'center',
    gap: '12px'
  }}>
    {icon || (type === 'error' ? <AlertCircle size={40} strokeWidth={1.5} /> : <HelpCircle size={40} strokeWidth={1.5} />)}
    <p className="text-sm">{message}</p>
  </div>
);
