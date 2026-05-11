import React from 'react';
import Badge, { BadgeVariant } from '../ui/Badge';
import { 
  getRunStatusVariant, 
  getDispatchStatusVariant, 
  getReadinessVariant, 
  getStalenessVariant 
} from '../../utils/statusUtils';

interface StatusBadgeProps {
  type: 'run' | 'dispatch' | 'readiness' | 'staleness';
  status: string | boolean | number | undefined;
  label?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, status, label }) => {
  let variant: BadgeVariant = 'muted';
  const displayLabel = label || (typeof status === 'string' ? status.toUpperCase() : String(status).toUpperCase());

  switch (type) {
    case 'run':
      variant = getRunStatusVariant(status as string);
      break;
    case 'dispatch':
      variant = getDispatchStatusVariant(status as string);
      break;
    case 'readiness':
      variant = getReadinessVariant(!!status);
      break;
    case 'staleness':
      variant = getStalenessVariant(!!status);
      break;
  }

  return <Badge variant={variant}>{displayLabel}</Badge>;
};
