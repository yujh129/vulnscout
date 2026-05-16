import React from 'react';
import { Box } from '@mui/material';

interface DiffViewerProps {
  diff: string;
}

const DiffViewer: React.FC<DiffViewerProps> = ({ diff }) => {
  const lines = diff.split('\n');

  return (
    <Box
      sx={{
        bgcolor: '#1e1e1e',
        color: '#d4d4d4',
        borderRadius: 1,
        overflow: 'auto',
        fontSize: 13,
        fontFamily: '"Cascadia Code", "Fira Code", monospace',
        lineHeight: 1.5,
      }}
    >
      {lines.map((line, i) => {
        let bg = 'transparent';
        let prefix = ' ';
        if (line.startsWith('+')) {
          bg = 'rgba(0,200,80,0.15)';
          prefix = '+';
        } else if (line.startsWith('-')) {
          bg = 'rgba(200,0,0,0.15)';
          prefix = '-';
        } else if (line.startsWith('@@')) {
          bg = 'rgba(0,100,200,0.2)';
          prefix = '@';
        }
        return (
          <Box
            key={i}
            sx={{
              bgcolor: bg,
              px: 2,
              whiteSpace: 'pre',
              '&:hover': { filter: 'brightness(1.2)' },
            }}
          >
            <span style={{ color: '#666', userSelect: 'none', marginRight: 16, minWidth: 32, display: 'inline-block', textAlign: 'right' }}>
              {i + 1}
            </span>
            <span>{line}</span>
          </Box>
        );
      })}
    </Box>
  );
};

export default DiffViewer;
