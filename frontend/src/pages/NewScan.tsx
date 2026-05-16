import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Tabs,
  Tab,
  Divider,
} from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { createScan, createScanFromZip } from '../api/scans';

const NewScan: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);
  const [localPath, setLocalPath] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [loading, setLoading] = useState(false);

  const handleStartScan = async () => {
    setLoading(true);
    try {
      let scan;
      if (tab === 0) {
        scan = await createScan('local', localPath);
      } else if (tab === 1) {
        scan = await createScan('url', githubUrl);
      } else {
        const fileInput = document.getElementById('zip-file-input') as HTMLInputElement;
        const file = fileInput?.files?.[0];
        if (file) {
          scan = await createScanFromZip(file);
        } else {
          return;
        }
      }
      navigate(`/scans/${scan.id}`);
    } catch (err) {
      console.error('Scan failed:', err);
      alert('Failed to start scan. Check the input and try again.');
    } finally {
      setLoading(false);
    }
  };

  const canStart = tab === 0 ? localPath : tab === 1 ? githubUrl : true;

  return (
    <Box sx={{ maxWidth: 700, mx: 'auto' }}>
      <Typography variant="h4" fontWeight={600} sx={{ mb: 3 }}>
        {t('scan.new')}
      </Typography>

      <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
        <CardContent>
          <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
            <Tab label="Local Directory" />
            <Tab label="GitHub URL" />
            <Tab label="Upload ZIP" />
          </Tabs>

          <Divider sx={{ mb: 3 }} />

          {tab === 0 && (
            <TextField
              fullWidth
              label={t('scan.localPath')}
              placeholder="/home/user/projects/my-app"
              value={localPath}
              onChange={(e) => setLocalPath(e.target.value)}
              helperText="Enter the absolute path to a local directory"
            />
          )}

          {tab === 1 && (
            <TextField
              fullWidth
              label={t('scan.githubUrl')}
              placeholder="https://github.com/username/repository"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              helperText="Enter a public GitHub repository URL"
            />
          )}

          {tab === 2 && (
            <Box>
              <Button
                variant="outlined"
                component="label"
                fullWidth
                sx={{ py: 4, borderStyle: 'dashed' }}
              >
                {t('scan.uploadZip')}
                <input id="zip-file-input" type="file" accept=".zip" hidden />
              </Button>
            </Box>
          )}

          <Box sx={{ mt: 3, textAlign: 'right' }}>
            <Button
              variant="contained"
              size="large"
              onClick={handleStartScan}
              disabled={!canStart || loading}
            >
              {loading ? t('scan.running') : t('scan.start')}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default NewScan;
