import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Button,
  Stack,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { fetchVulnerability, fetchPatches } from '../api/scans';
import SeverityBadge from '../components/SeverityBadge';
import DiffViewer from '../components/DiffViewer';

const VulnDetail: React.FC = () => {
  const { scanId, vulnId } = useParams<{ scanId: string; vulnId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const { data: vuln } = useQuery({
    queryKey: ['vuln', vulnId],
    queryFn: () => fetchVulnerability(scanId!, vulnId!),
    enabled: !!scanId && !!vulnId,
  });

  const { data: patches } = useQuery({
    queryKey: ['patches', vulnId],
    queryFn: () => fetchPatches(scanId!, vulnId!),
    enabled: !!scanId && !!vulnId,
  });

  if (!vuln) return <Typography>{t('common.loading')}</Typography>;

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto' }}>
      <Button sx={{ mb: 2 }} onClick={() => navigate(`/scans/${scanId}`)}>
        &larr; {t('common.back')}
      </Button>

      <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
            <SeverityBadge severity={vuln.severity} />
            {vuln.cwe_id && <Chip label={vuln.cwe_id} size="small" variant="outlined" />}
          </Stack>

          <Typography variant="h5" fontWeight={600} sx={{ mb: 2 }}>
            {vuln.title}
          </Typography>

          <Typography color="text.secondary" sx={{ mb: 1 }}>
            {t('vuln.file')}: <strong>{vuln.file_path}</strong>
            {vuln.line_start && (
              <> | {t('vuln.line')}: <strong>{vuln.line_start}{vuln.line_end ? `-${vuln.line_end}` : ''}</strong></>
            )}
          </Typography>

          {vuln.description && (
            <Typography sx={{ mt: 2 }}>{vuln.description}</Typography>
          )}
        </CardContent>
      </Card>

      {vuln.vulnerable_code && (
        <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', mb: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
              Vulnerable Code
            </Typography>
            <Box
              component="pre"
              sx={{
                p: 2,
                bgcolor: 'grey.100',
                borderRadius: 1,
                overflow: 'auto',
                fontSize: 13,
                fontFamily: 'monospace',
              }}
            >
              {vuln.vulnerable_code}
            </Box>
          </CardContent>
        </Card>
      )}

      {patches && patches.length > 0 && (
        <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
          <CardContent>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
              {t('vuln.fix')}
            </Typography>
            {patches.map((patch) => (
              <Box key={patch.id}>
                <DiffViewer diff={patch.diff_content || ''} />
                <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                  <Button variant="contained" size="small">
                    {t('vuln.apply')}
                  </Button>
                  <Button variant="outlined" size="small" color="error">
                    {t('vuln.reject')}
                  </Button>
                </Box>
              </Box>
            ))}
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default VulnDetail;
