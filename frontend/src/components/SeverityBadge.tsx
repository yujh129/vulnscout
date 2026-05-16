import React from 'react';
import { Chip } from '@mui/material';
import { useTranslation } from 'react-i18next';

interface SeverityBadgeProps {
  severity: 'critical' | 'high' | 'medium' | 'low';
}

const severityColors: Record<string, 'error' | 'warning' | 'info' | 'default'> = {
  critical: 'error',
  high: 'warning',
  medium: 'info',
  low: 'default',
};

const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity }) => {
  const { t } = useTranslation();
  const label = t(`severity.${severity}`, severity);
  return (
    <Chip
      label={label}
      color={severityColors[severity] || 'default'}
      size="small"
      variant="filled"
    />
  );
};

export default SeverityBadge;
