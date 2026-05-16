import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Chip,
} from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchScans } from '../api/scans';
import SeverityBadge from '../components/SeverityBadge';

const Dashboard: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: scans, isLoading } = useQuery({
    queryKey: ['scans'],
    queryFn: fetchScans,
  });

  const totalVulns = scans?.reduce(
    (sum, s) => sum + s.vuln_count_critical + s.vuln_count_high + s.vuln_count_medium + s.vuln_count_low,
    0,
  ) ?? 0;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4" fontWeight={600}>
          {t('dashboard.title')}
        </Typography>
        <Button variant="contained" onClick={() => navigate('/new-scan')}>
          {t('scan.new')}
        </Button>
      </Box>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={4}>
          <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
            <CardContent>
              <Typography variant="h3" fontWeight={700}>
                {scans?.length ?? 0}
              </Typography>
              <Typography color="text.secondary">{t('dashboard.totalScans')}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
            <CardContent>
              <Typography variant="h3" fontWeight={700}>
                {totalVulns}
              </Typography>
              <Typography color="text.secondary">{t('dashboard.totalVulnerabilities')}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
            <CardContent>
              <Typography variant="h3" fontWeight={700}>
                {scans?.filter(s => s.status === 'done').length ?? 0}
              </Typography>
              <Typography color="text.secondary">{t('dashboard.totalScans')}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Typography variant="h5" fontWeight={600} sx={{ mb: 2 }}>
        {t('dashboard.recentScans')}
      </Typography>

      {isLoading && <Typography>{t('common.loading')}</Typography>}
      {!isLoading && (!scans || scans.length === 0) && (
        <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">{t('dashboard.noScans')}</Typography>
        </Card>
      )}
      {scans && scans.length > 0 && (
        <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>{t('vuln.file')}</TableCell>
                <TableCell>Language</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>{t('vuln.severity')}</TableCell>
                <TableCell>Date</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {scans.map((scan) => (
                <TableRow
                  key={scan.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/scans/${scan.id}`)}
                >
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: 12 }}>
                      {scan.id.slice(0, 8)}
                    </Typography>
                  </TableCell>
                  <TableCell>{scan.source_path}</TableCell>
                  <TableCell>{scan.language || '-'}</TableCell>
                  <TableCell>
                    <Chip
                      label={scan.status}
                      color={scan.status === 'done' ? 'success' : scan.status === 'failed' ? 'error' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      {scan.vuln_count_critical > 0 && <SeverityBadge severity="critical" />}
                      {scan.vuln_count_high > 0 && <SeverityBadge severity="high" />}
                    </Box>
                  </TableCell>
                  <TableCell>
                    {new Date(scan.created_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default Dashboard;
