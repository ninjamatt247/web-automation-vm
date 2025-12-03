'use client';

import { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Tabs,
  Tab,
  Paper,
  TextField,
  Button,
  Alert,
  Snackbar,
  CircularProgress,
  Chip,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  Divider
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SaveIcon from '@mui/icons-material/Save';
import RefreshIcon from '@mui/icons-material/Refresh';
import SettingsIcon from '@mui/icons-material/Settings';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Settings state
  const [initialPrompt, setInitialPrompt] = useState('');
  const [verificationPrompt, setVerificationPrompt] = useState('');
  const [requirements, setRequirements] = useState<any>({
    critical: [],
    high: [],
    medium: [],
    low: []
  });
  const [triggers, setTriggers] = useState<string[]>([]);
  const [stats, setStats] = useState<any>(null);

  // UI state
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'warning' });
  const [hasChanges, setHasChanges] = useState(false);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      // Load full settings
      const response = await fetch('http://localhost:8000/api/settings/full');
      if (!response.ok) throw new Error('Failed to load settings');

      const data = await response.json();
      setInitialPrompt(data.initial_prompt);
      setVerificationPrompt(data.verification_prompt);
      setRequirements(data.requirements);
      setTriggers(data.human_intervention_triggers);

      // Load stats
      const statsResponse = await fetch('http://localhost:8000/api/settings/stats');
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }

      setHasChanges(false);
      setSnackbar({ open: true, message: 'Settings loaded successfully', severity: 'success' });
    } catch (error) {
      console.error('Error loading settings:', error);
      setSnackbar({ open: true, message: 'Failed to load settings', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const savePrompts = async () => {
    setSaving(true);
    try {
      const response = await fetch('http://localhost:8000/api/settings/prompts', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initial_prompt: initialPrompt,
          verification_prompt: verificationPrompt
        })
      });

      if (!response.ok) throw new Error('Failed to save prompts');

      const result = await response.json();
      setSnackbar({ open: true, message: 'Prompts saved successfully!', severity: 'success' });
      setHasChanges(false);
    } catch (error) {
      console.error('Error saving prompts:', error);
      setSnackbar({ open: true, message: 'Failed to save prompts', severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const saveRequirements = async () => {
    setSaving(true);
    try {
      const response = await fetch('http://localhost:8000/api/settings/requirements', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requirements)
      });

      if (!response.ok) throw new Error('Failed to save requirements');

      const result = await response.json();

      if (result.validation_errors && result.validation_errors.length > 0) {
        setSnackbar({
          open: true,
          message: `Saved with warnings: ${result.validation_errors.join(', ')}`,
          severity: 'warning'
        });
      } else {
        setSnackbar({ open: true, message: 'Requirements saved successfully!', severity: 'success' });
      }

      setHasChanges(false);
    } catch (error) {
      console.error('Error saving requirements:', error);
      setSnackbar({ open: true, message: 'Failed to save requirements', severity: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, textAlign: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading settings...</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <SettingsIcon sx={{ fontSize: 40, mr: 2 }} />
        <Typography variant="h4" component="h1">
          AI Processing Settings
        </Typography>
        <Box sx={{ flexGrow: 1 }} />
        <IconButton onClick={loadSettings} title="Reload settings">
          <RefreshIcon />
        </IconButton>
      </Box>

      {/* Stats Cards */}
      {stats && (
        <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
          <Paper sx={{ p: 2, flex: 1 }}>
            <Typography variant="h6">{stats.total_requirements}</Typography>
            <Typography variant="body2" color="text.secondary">Total Requirements</Typography>
          </Paper>
          <Paper sx={{ p: 2, flex: 1 }}>
            <Typography variant="h6">{stats.by_priority.CRITICAL}</Typography>
            <Typography variant="body2" color="text.secondary">Critical Checks</Typography>
          </Paper>
          <Paper sx={{ p: 2, flex: 1 }}>
            <Typography variant="h6">{stats.intervention_triggers}</Typography>
            <Typography variant="body2" color="text.secondary">Intervention Triggers</Typography>
          </Paper>
        </Box>
      )}

      {/* Change Indicator */}
      {hasChanges && (
        <Alert severity="info" sx={{ mb: 2 }}>
          You have unsaved changes. Remember to save before leaving this page.
        </Alert>
      )}

      {/* Tabs */}
      <Paper sx={{ width: '100%' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="settings tabs">
          <Tab label="Prompts" />
          <Tab label="Requirements" />
          <Tab label="Intervention Triggers" />
          <Tab label="Statistics" />
        </Tabs>

        {/* Tab 1: Prompts */}
        <TabPanel value={tabValue} index={0}>
          <Typography variant="h6" gutterBottom>
            AI Prompts Configuration
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Configure the prompts used for the multi-step note processing system.
          </Typography>

          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              Initial Strict Prompt
            </Typography>
            <Typography variant="caption" color="text.secondary" paragraph>
              This prompt is used in Step 1 to perform initial cleaning and formatting.
            </Typography>
            <TextField
              fullWidth
              multiline
              rows={12}
              value={initialPrompt}
              onChange={(e) => {
                setInitialPrompt(e.target.value);
                setHasChanges(true);
              }}
              variant="outlined"
              sx={{ fontFamily: 'monospace' }}
            />
          </Box>

          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              Verification & Cleanup Prompt
            </Typography>
            <Typography variant="caption" color="text.secondary" paragraph>
              This prompt is used in Step 2 to verify and correct the output from Step 1.
            </Typography>
            <TextField
              fullWidth
              multiline
              rows={12}
              value={verificationPrompt}
              onChange={(e) => {
                setVerificationPrompt(e.target.value);
                setHasChanges(true);
              }}
              variant="outlined"
              sx={{ fontFamily: 'monospace' }}
            />
          </Box>

          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={savePrompts}
              disabled={saving || !hasChanges}
            >
              {saving ? 'Saving...' : 'Save Prompts'}
            </Button>
            <Button
              variant="outlined"
              onClick={loadSettings}
              disabled={saving}
            >
              Reset Changes
            </Button>
          </Box>
        </TabPanel>

        {/* Tab 2: Requirements */}
        <TabPanel value={tabValue} index={1}>
          <Typography variant="h6" gutterBottom>
            Validation Requirements
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Configure the validation checks performed in Step 3. Requirements are organized by priority level.
          </Typography>

          {['critical', 'high', 'medium', 'low'].map((priority) => (
            <Accordion key={priority} defaultExpanded={priority === 'critical'}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip
                    label={priority.toUpperCase()}
                    color={priority === 'critical' ? 'error' : priority === 'high' ? 'warning' : 'default'}
                    size="small"
                  />
                  <Typography>
                    {requirements[priority]?.length || 0} Requirements
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <List>
                  {requirements[priority]?.map((req: any, index: number) => (
                    <ListItem key={index}>
                      <ListItemText
                        primary={req.name}
                        secondary={
                          <>
                            <Typography variant="caption" display="block">
                              ID: {req.id}
                            </Typography>
                            <Typography variant="caption" display="block">
                              {req.description}
                            </Typography>
                            <Typography variant="caption" display="block" color="error">
                              Error: {req.error_message}
                            </Typography>
                          </>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
                {requirements[priority]?.length === 0 && (
                  <Typography variant="body2" color="text.secondary" align="center">
                    No requirements defined for this priority level
                  </Typography>
                )}
              </AccordionDetails>
            </Accordion>
          ))}

          <Alert severity="info" sx={{ mt: 2 }}>
            <Typography variant="body2">
              To modify requirements, edit the <code>config/prompts_config.yaml</code> file directly or use the API.
            </Typography>
          </Alert>
        </TabPanel>

        {/* Tab 3: Intervention Triggers */}
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h6" gutterBottom>
            Human Intervention Triggers
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Conditions that automatically flag a note for human review.
          </Typography>

          <Paper variant="outlined" sx={{ p: 2 }}>
            {triggers.map((trigger, index) => (
              <Box key={index} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <WarningIcon color="warning" sx={{ mr: 1 }} />
                <Typography>{trigger}</Typography>
              </Box>
            ))}
          </Paper>

          <Alert severity="info" sx={{ mt: 2 }}>
            <Typography variant="body2">
              Intervention triggers are currently read-only. Edit <code>config/prompts_config.yaml</code> to modify.
            </Typography>
          </Alert>
        </TabPanel>

        {/* Tab 4: Statistics */}
        <TabPanel value={tabValue} index={3}>
          <Typography variant="h6" gutterBottom>
            Configuration Statistics
          </Typography>

          {stats && (
            <List>
              <ListItem>
                <ListItemText
                  primary="Total Requirements"
                  secondary={stats.total_requirements}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText
                  primary="Requirements by Priority"
                  secondary={
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" display="block">
                        CRITICAL: {stats.by_priority.CRITICAL}
                      </Typography>
                      <Typography variant="caption" display="block">
                        HIGH: {stats.by_priority.HIGH}
                      </Typography>
                      <Typography variant="caption" display="block">
                        MEDIUM: {stats.by_priority.MEDIUM}
                      </Typography>
                      <Typography variant="caption" display="block">
                        LOW: {stats.by_priority.LOW}
                      </Typography>
                    </Box>
                  }
                  secondaryTypographyProps={{ component: 'div' }}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText
                  primary="Initial Prompt Length"
                  secondary={`${stats.prompts.initial_length} characters`}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Verification Prompt Length"
                  secondary={`${stats.prompts.verification_length} characters`}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText
                  primary="Intervention Triggers"
                  secondary={stats.intervention_triggers}
                />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText
                  primary="Configuration File"
                  secondary={stats.config_path}
                />
              </ListItem>
            </List>
          )}
        </TabPanel>
      </Paper>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
}
