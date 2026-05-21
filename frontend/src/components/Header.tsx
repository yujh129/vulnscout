import React, { useEffect, useState } from 'react';
import { AppBar, Toolbar, Typography, Button, Box, ToggleButton, ToggleButtonGroup, Select, MenuItem, Chip, FormControl } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';

interface ModelInfo { current: { provider: string; model: string }; local: { name: string; downloaded: boolean }[]; cloud: { name: string }[] }

const Header: React.FC = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [switching, setSwitching] = useState(false);

  useEffect(() => { api.get('/models').then(r => setModelInfo(r.data)).catch(() => {}); }, []);

  const handleModelChange = async (modelName: string) => {
    if (modelName === modelInfo?.current.model) return;
    setSwitching(true);
    try { await api.post('/models/switch', { model_name: modelName }); const res = await api.get('/models'); setModelInfo(res.data); } catch (e) { console.error(e); }
    setSwitching(false);
  };

  return (
    <AppBar position="static" elevation={0}>
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ cursor: 'pointer', fontWeight: 700 }} onClick={() => navigate('/')}>{t('app.title')}</Typography>
        <Typography variant="body2" sx={{ ml: 1, opacity: 0.7 }}>{t('app.subtitle')}</Typography>
        <Box sx={{ ml: 4, display: 'flex', gap: 1 }}>
          <Button color="inherit" onClick={() => navigate('/')}>{t('nav.dashboard')}</Button>
          <Button color="inherit" onClick={() => navigate('/new-scan')}>{t('nav.newScan')}</Button>
        </Box>
        <Box sx={{ flexGrow: 1 }} />
        {modelInfo && (
          <FormControl size="small" sx={{ minWidth: 180, mr: 2 }}>
            <Select value={modelInfo.current.model} onChange={e => handleModelChange(e.target.value)} disabled={switching}
              sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' }, '& .MuiSvgIcon-root': { color: 'white' }, fontSize: 13 }}>
              <MenuItem disabled sx={{ opacity: 0.6, fontSize: 11 }}>— Local (Ollama) —</MenuItem>
              {modelInfo.local.map(m => <MenuItem key={m.name} value={m.name}>{m.name}{m.downloaded && <Chip label="ready" size="small" color="success" sx={{ ml: 1, height: 18, fontSize: 10 }} />}</MenuItem>)}
              <MenuItem disabled sx={{ opacity: 0.6, fontSize: 11 }}>— Cloud API —</MenuItem>
              {modelInfo.cloud.map(m => <MenuItem key={m.name} value={m.name}>{m.name}</MenuItem>)}
            </Select>
          </FormControl>
        )}
        <ToggleButtonGroup value={i18n.language?.startsWith('zh') ? 'zh' : 'en'} exclusive onChange={(_, v) => v && i18n.changeLanguage(v)} size="small"
          sx={{ '& .MuiToggleButton-root': { color: 'white', borderColor: 'rgba(255,255,255,0.3)', '&.Mui-selected': { color: 'white', bgcolor: 'rgba(255,255,255,0.15)' } }}}>
          <ToggleButton value="en">EN</ToggleButton>
          <ToggleButton value="zh">中</ToggleButton>
        </ToggleButtonGroup>
      </Toolbar>
    </AppBar>
  );
};
export default Header;
