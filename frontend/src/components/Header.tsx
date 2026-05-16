import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

const Header: React.FC = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  const handleLanguageChange = (
    _: React.MouseEvent<HTMLElement>,
    newLang: string | null,
  ) => {
    if (newLang) {
      i18n.changeLanguage(newLang);
    }
  };

  return (
    <AppBar position="static" elevation={0}>
      <Toolbar>
        <Typography
          variant="h6"
          component="div"
          sx={{ cursor: 'pointer', fontWeight: 700 }}
          onClick={() => navigate('/')}
        >
          {t('app.title')}
        </Typography>
        <Typography variant="body2" sx={{ ml: 1, opacity: 0.7 }}>
          {t('app.subtitle')}
        </Typography>

        <Box sx={{ ml: 4, display: 'flex', gap: 1 }}>
          <Button color="inherit" onClick={() => navigate('/')}>
            {t('nav.dashboard')}
          </Button>
          <Button color="inherit" onClick={() => navigate('/new-scan')}>
            {t('nav.newScan')}
          </Button>
        </Box>

        <Box sx={{ flexGrow: 1 }} />

        <ToggleButtonGroup
          value={i18n.language?.startsWith('zh') ? 'zh' : 'en'}
          exclusive
          onChange={handleLanguageChange}
          size="small"
          sx={{
            '& .MuiToggleButton-root': {
              color: 'white',
              borderColor: 'rgba(255,255,255,0.3)',
              '&.Mui-selected': {
                color: 'white',
                bgcolor: 'rgba(255,255,255,0.15)',
              },
            },
          }}
        >
          <ToggleButton value="en">EN</ToggleButton>
          <ToggleButton value="zh">中</ToggleButton>
        </ToggleButtonGroup>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
