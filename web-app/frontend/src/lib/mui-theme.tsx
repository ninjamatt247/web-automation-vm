'use client';

import { createTheme, ThemeProvider } from '@mui/material/styles';
import { useTheme } from 'next-themes';
import { useMemo } from 'react';

export function CustomMuiThemeProvider({ children }: { children: React.ReactNode }) {
  const { theme } = useTheme();

  const muiTheme = useMemo(
    () =>
      createTheme({
        palette: {
          mode: theme === 'dark' ? 'dark' : 'light',
          primary: {
            main: theme === 'dark' ? '#9D83E7' : '#6366f1',
          },
          secondary: {
            main: theme === 'dark' ? '#E74548' : '#ec4899',
          },
          background: {
            default: theme === 'dark' ? '#0a0a0a' : '#ffffff',
            paper: theme === 'dark' ? '#171717' : '#f9fafb',
          },
          text: {
            primary: theme === 'dark' ? '#fafafa' : '#0a0a0a',
            secondary: theme === 'dark' ? '#a1a1aa' : '#71717a',
          },
        },
        components: {
          MuiPaper: {
            styleOverrides: {
              root: {
                backgroundImage: 'none',
              },
            },
          },
          MuiTextField: {
            styleOverrides: {
              root: {
                '& .MuiOutlinedInput-root': {
                  '& fieldset': {
                    borderColor: theme === 'dark' ? '#27272a' : '#e4e4e7',
                  },
                  '&:hover fieldset': {
                    borderColor: theme === 'dark' ? '#3f3f46' : '#d4d4d8',
                  },
                  '&.Mui-focused fieldset': {
                    borderColor: theme === 'dark' ? '#9D83E7' : '#6366f1',
                  },
                },
              },
            },
          },
          MuiTabs: {
            styleOverrides: {
              root: {
                borderBottom: `1px solid ${theme === 'dark' ? '#27272a' : '#e4e4e7'}`,
              },
            },
          },
          MuiTab: {
            styleOverrides: {
              root: {
                color: theme === 'dark' ? '#a1a1aa' : '#71717a',
                '&.Mui-selected': {
                  color: theme === 'dark' ? '#fafafa' : '#0a0a0a',
                },
              },
            },
          },
          MuiAccordion: {
            styleOverrides: {
              root: {
                border: `1px solid ${theme === 'dark' ? '#27272a' : '#e4e4e7'}`,
                '&:before': {
                  display: 'none',
                },
              },
            },
          },
        },
      }),
    [theme]
  );

  return <ThemeProvider theme={muiTheme}>{children}</ThemeProvider>;
}
