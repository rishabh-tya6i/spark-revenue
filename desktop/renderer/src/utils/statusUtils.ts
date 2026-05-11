import { BadgeVariant } from '../components/ui/Badge';

/**
 * Maps backend orchestration statuses to UI badge variants.
 */
export const getRunStatusVariant = (status: string | undefined): BadgeVariant => {
  if (!status) return 'muted';
  const s = status.toLowerCase();
  if (s === 'completed' || s === 'success') return 'success';
  if (s === 'failed') return 'danger';
  if (s === 'skipped') return 'muted';
  return 'muted';
};

/**
 * Maps dispatch statuses to UI badge variants.
 */
export const getDispatchStatusVariant = (status: string | undefined): BadgeVariant => {
  if (!status) return 'muted';
  const s = status.toLowerCase();
  if (s === 'executed' || s === 'success') return 'success';
  if (s === 'failed') return 'danger';
  if (s === 'skipped') return 'muted';
  return 'muted';
};

/**
 * Maps readiness and decision states to UI badge variants.
 */
export const getReadinessVariant = (ready: boolean | undefined): BadgeVariant => {
  return ready ? 'success' : 'danger';
};

/**
 * Maps staleness states to UI badge variants.
 */
export const getStalenessVariant = (stale: boolean | undefined): BadgeVariant => {
  return stale ? 'danger' : 'success';
};

/**
 * Maps decision labels to UI badge variants.
 */
export const getDecisionVariant = (label: string | undefined): BadgeVariant => {
  if (!label) return 'muted';
  const l = label.toLowerCase();
  if (l.includes('bullish')) return 'success';
  if (l.includes('bearish')) return 'danger';
  if (l.includes('neutral')) return 'muted';
  return 'primary';
};
