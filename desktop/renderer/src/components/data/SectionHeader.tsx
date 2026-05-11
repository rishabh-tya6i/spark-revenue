import React from 'react';
import { RefreshCw } from 'lucide-react';
import Button from '../ui/Button';

interface SectionHeaderProps {
  title: string;
  icon: React.ReactNode;
  onRefresh?: () => void;
  loading?: boolean;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({ title, icon, onRefresh, loading }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
      {icon}
      <h3 style={{ margin: 0 }}>{title}</h3>
    </div>
    {onRefresh && (
      <Button variant="outline" size="sm" onClick={onRefresh} disabled={loading}>
        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
      </Button>
    )}
  </div>
);
