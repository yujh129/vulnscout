import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Chip,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { fetchScan, fetchResults } from '../api/scans';
import SeverityBadge from '../components/SeverityBadge';

const ScanResult: React.FC = () => {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const { data: scan } = useQuery({
    queryKey: ['scan', scanId],
    queryFn: () => fetchScan(scanId!),
    enabled: !!scanId,
  });

  const { data: vulns } = useQuery({
    queryKey: ['results', scanId],
    queryFn: () => fetchResults(scanId!),
    enabled: !!scanId,
  });

  if (!scan || !vulns) {
    return <Typography>{t('common.loading')}</Typography>;
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={600}>
            {t('scan.results')}
          </Typography>
          <Typography color="text.secondary">
            {scan.source_path} — {scan.scanned_files}/{scan.total_files} files
          </Typography>
        </Box>
        <Chip
          label={scan.status}
          color={scan.status === 'done' ? 'success' : scan.status === 'failed' ? 'error' : 'default'}
        />
      </Box>

      <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
            {scan.vuln_count_critical > 0 && (
              <Box><SeverityBadge severity="critical" /> <strong>{scan.vuln_count_critical}</strong></Box>
            )}
            {scan.vuln_count_high > 0 && (
              <Box><SeverityBadge severity="high" /> <strong>{scan.vuln_count_high}</strong></Box>
            )}
            {scan.vuln_count_medium > 0 && (
              <Box><SeverityBadge severity="medium" /> <strong>{scan.vuln_count_medium}</strong></Box>
            )}
            {scan.vuln_count_low > 0 && (
              <Box><SeverityBadge severity="low" /> <strong>{scan.vuln_count_low}</strong></Box>
            )}
          </Box>

          <List disablePadding>
            {vulns.map((vuln) => (
              <ListItem key={vuln.id} disablePadding>
                <ListItemButton
                  onClick={() => navigate(`/scans/${scanId}/vulns/${vuln.id}`)}
                >
                  <SeverityBadge severity={vuln.severity} />
                  <ListItemText
                    sx={{ ml: 2 }}
                    primary={vuln.title}
                    secondary={`${vuln.file_path}:${vuln.line_start || '?'}`}
                  />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ScanResult;
