import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import NewScan from './pages/NewScan';
import ScanResult from './pages/ScanResult';
import VulnDetail from './pages/VulnDetail';

const theme = createTheme({
  palette: {
    primary: { main: '#1a237e' },
    background: { default: '#f5f5f5' },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  shape: { borderRadius: 8 },
});

const queryClient = new QueryClient();

const App: React.FC = () => {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/new-scan" element={<NewScan />} />
              <Route path="/scans/:scanId" element={<ScanResult />} />
              <Route path="/scans/:scanId/vulns/:vulnId" element={<VulnDetail />} />
            </Routes>
          </Layout>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
};

export default App;
