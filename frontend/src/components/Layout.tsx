import React from 'react';
import { Box, Container } from '@mui/material';
import Header from './Header';
const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Box sx={{ minHeight: '100vh', bgcolor: 'grey.50' }}><Header /><Container maxWidth="xl" sx={{ py: 3 }}>{children}</Container></Box>
);
export default Layout;
