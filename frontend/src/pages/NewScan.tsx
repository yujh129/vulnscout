import React, { useState } from 'react';
import { Box, Typography, Card, CardContent, TextField, Button, Tabs, Tab, Divider } from '@mui/material';
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
      if (tab === 0) scan = await createScan('local', localPath);
      else if (tab === 1) scan = await createScan('url', githubUrl);
      else { const inp = document.getElementById('zip-file-input') as HTMLInputElement; if (inp?.files?.[0]) scan = await createScanFromZip(inp.files[0]); else return; }
      navigate(`/scans/${scan.id}`);
    } catch { alert('Failed to start scan.'); } finally { setLoading(false); }
  };

  return (
    <Box sx={{ maxWidth: 700, mx: 'auto' }}>
      <Typography variant="h4" fontWeight={600} sx={{ mb: 3 }}>{t('scan.new')}</Typography>
      <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
        <CardContent>
          <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
            <Tab label="Local Directory" /><Tab label="GitHub URL" /><Tab label="Upload ZIP" />
          </Tabs>
          <Divider sx={{ mb: 3 }} />
          {tab === 0 && <TextField fullWidth label={t('scan.localPath')} placeholder="/home/user/projects/my-app" value={localPath} onChange={e => setLocalPath(e.target.value)} />}
          {tab === 1 && <TextField fullWidth label={t('scan.githubUrl')} placeholder="https://github.com/username/repository" value={githubUrl} onChange={e => setGithubUrl(e.target.value)} />}
          {tab === 2 && <Button variant="outlined" component="label" fullWidth sx={{ py: 4, borderStyle: 'dashed' }}>{t('scan.uploadZip')}<input id="zip-file-input" type="file" accept=".zip" hidden /></Button>}
          <Box sx={{ mt: 3, textAlign: 'right' }}>
            <Button variant="contained" size="large" onClick={handleStartScan} disabled={loading || (tab === 0 ? !localPath : tab === 1 ? !githubUrl : false)}>
              {loading ? t('scan.running') : t('scan.start')}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};
export default NewScan;
