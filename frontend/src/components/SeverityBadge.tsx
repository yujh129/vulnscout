import React from 'react';
import { Chip } from '@mui/material';
import { useTranslation } from 'react-i18next';
interface Props { severity: 'critical'|'high'|'medium'|'low' }
const colors: Record<string, 'error'|'warning'|'info'|'default'> = { critical: 'error', high: 'warning', medium: 'info', low: 'default' };
const SeverityBadge: React.FC<Props> = ({ severity }) => {
  const { t } = useTranslation();
  return <Chip label={t(`severity.${severity}`, severity)} color={colors[severity] || 'default'} size="small" variant="filled" />;
};
export default SeverityBadge;
