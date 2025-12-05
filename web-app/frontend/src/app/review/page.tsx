'use client';

import { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  LinearProgress,
  Alert,
  IconButton,
  Tooltip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
} from '@mui/material';
import {
  CheckCircle,
  Cancel,
  HourglassEmpty,
  CloudUpload,
  Refresh,
  Visibility,
  Edit,
  Warning,
  Print,
  PrintOutlined,
} from '@mui/icons-material';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface BatchRun {
  id: number;
  batch_id: string;
  start_date: string;
  end_date: string;
  total_notes: number;
  processed_notes: number;
  success_count: number;
  needs_review_count: number;
  failed_count: number;
  status: string;
  created_at: string;
  completed_at?: string;
}

interface ProcessingResult {
  id: number;
  patient_name: string;
  visit_date: string;
  processing_status: string;
  requires_human_intervention: boolean;
  human_intervention_reasons?: string;
  review_status: string;
  upload_status: string;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  critical_failures: number;
  final_cleaned_note?: string;
}

interface DashboardSummary {
  review_status: Record<string, number>;
  upload_status: Record<string, number>;
  quality_metrics: {
    total_notes: number;
    needs_intervention: number;
    critical_failures: number;
    avg_pass_rate: number;
  };
}

interface NoteDetail {
  id: number;
  patient_name: string;
  visit_date: string;
  raw_note: string;
  step1_note?: string;
  step2_note?: string;
  final_cleaned_note?: string;
  processing_status: string;
  validation_checks: Array<{
    id: string;
    name: string;
    priority: string;
    passed: boolean;
    message: string;
    details: string;
  }>;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  processing_attempts: number;
}

export default function ReviewPage() {
  const [batches, setBatches] = useState<BatchRun[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<string | null>(null);
  const [pendingNotes, setPendingNotes] = useState<ProcessingResult[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedNote, setSelectedNote] = useState<ProcessingResult | null>(null);
  const [noteDetail, setNoteDetail] = useState<NoteDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [reviewNotes, setReviewNotes] = useState('');
  const [reviewStatus, setReviewStatus] = useState('approved');

  // Fetch recent batches
  const fetchBatches = async () => {
    try {
      const response = await fetch(`${API_URL}/api/review/batches?limit=10`);
      const data = await response.json();
      setBatches(data.batches || []);

      // Auto-select most recent batch if exists
      if (data.batches && data.batches.length > 0 && !selectedBatch) {
        setSelectedBatch(data.batches[0].batch_id);
      }
    } catch (error) {
      console.error('Failed to fetch batches:', error);
    }
  };

  // Fetch pending notes for selected batch
  const fetchPendingNotes = async () => {
    if (!selectedBatch) return;

    try {
      const response = await fetch(
        `${API_URL}/api/review/pending?batch_id=${selectedBatch}&limit=100`
      );
      const data = await response.json();
      setPendingNotes(data.results || []);
    } catch (error) {
      console.error('Failed to fetch pending notes:', error);
    }
  };

  // Fetch dashboard summary
  const fetchSummary = async () => {
    if (!selectedBatch) return;

    try {
      const response = await fetch(
        `${API_URL}/api/review/dashboard/summary?batch_id=${selectedBatch}`
      );
      const data = await response.json();
      setSummary(data);
    } catch (error) {
      console.error('Failed to fetch summary:', error);
    }
  };

  // Load data on mount and when batch changes
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await fetchBatches();
      setLoading(false);
    };
    loadData();
  }, []);

  useEffect(() => {
    if (selectedBatch) {
      fetchPendingNotes();
      fetchSummary();
    }
  }, [selectedBatch]);

  // Fetch detailed note information
  const fetchNoteDetail = async (resultId: number) => {
    setLoadingDetail(true);
    try {
      const response = await fetch(`${API_URL}/api/review/note/${resultId}`);
      const data = await response.json();
      setNoteDetail(data);
    } catch (error) {
      console.error('Failed to fetch note detail:', error);
    } finally {
      setLoadingDetail(false);
    }
  };

  // Handle reprocessing a note
  const handleReprocess = async () => {
    if (!selectedNote) return;

    setReprocessing(true);
    try {
      const response = await fetch(`${API_URL}/api/review/reprocess`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          result_id: selectedNote.id,
          max_attempts: 3,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        // Reload note detail to show updated version
        await fetchNoteDetail(selectedNote.id);
        // Refresh pending notes list
        await fetchPendingNotes();
        await fetchSummary();
        alert(`Note reprocessed successfully! Now passing ${result.passed_checks}/${result.total_checks} checks.`);
      } else {
        const error = await response.json();
        alert(`Failed to reprocess note: ${error.detail}`);
      }
    } catch (error) {
      console.error('Failed to reprocess note:', error);
      alert('Failed to reprocess note. Please try again.');
    } finally {
      setReprocessing(false);
    }
  };

  // Handle opening review dialog - fetch note details
  const handleOpenReview = async (note: ProcessingResult) => {
    setSelectedNote(note);
    setReviewDialogOpen(true);
    setReviewNotes('');
    setReviewStatus('approved');
    // Fetch detailed note information
    await fetchNoteDetail(note.id);
  };

  // Handle review submission
  const handleReviewSubmit = async () => {
    if (!selectedNote) return;

    try {
      const response = await fetch(`${API_URL}/api/review/update-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          result_id: selectedNote.id,
          review_status: reviewStatus,
          review_notes: reviewNotes,
          reviewed_by: 'User', // TODO: Replace with actual user
        }),
      });

      if (response.ok) {
        // Refresh data
        await fetchPendingNotes();
        await fetchSummary();
        setReviewDialogOpen(false);
        setSelectedNote(null);
        setNoteDetail(null);
        setReviewNotes('');
      }
    } catch (error) {
      console.error('Failed to submit review:', error);
    }
  };

  // Get status color
  const getStatusColor = (status: string): 'success' | 'warning' | 'error' | 'default' => {
    switch (status) {
      case 'approved':
      case 'success':
        return 'success';
      case 'pending':
        return 'warning';
      case 'rejected':
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  // Print individual note
  const handlePrintNote = () => {
    if (!noteDetail) return;

    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    const printContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Note - ${noteDetail.patient_name} - ${noteDetail.visit_date}</title>
          <style>
            body {
              font-family: Arial, sans-serif;
              margin: 20px;
              line-height: 1.6;
            }
            h1 {
              color: #1976d2;
              border-bottom: 2px solid #1976d2;
              padding-bottom: 10px;
            }
            h2 {
              color: #333;
              margin-top: 30px;
              border-bottom: 1px solid #ddd;
              padding-bottom: 5px;
            }
            .section {
              margin: 20px 0;
            }
            .note-box {
              border: 1px solid #ddd;
              padding: 15px;
              background-color: #f9f9f9;
              white-space: pre-wrap;
              font-family: 'Courier New', monospace;
              font-size: 12px;
              max-height: none;
              overflow: visible;
            }
            .metadata {
              background-color: #e3f2fd;
              padding: 10px;
              border-left: 4px solid #1976d2;
              margin: 10px 0;
            }
            .validation-checks {
              margin-top: 20px;
            }
            table {
              width: 100%;
              border-collapse: collapse;
              margin-top: 10px;
            }
            th, td {
              border: 1px solid #ddd;
              padding: 8px;
              text-align: left;
            }
            th {
              background-color: #f5f5f5;
              font-weight: bold;
            }
            .priority-critical {
              color: #d32f2f;
              font-weight: bold;
            }
            .priority-high {
              color: #f57c00;
              font-weight: bold;
            }
            .priority-medium {
              color: #fbc02d;
            }
            @media print {
              body {
                margin: 0;
                padding: 15px;
              }
              .note-box {
                page-break-inside: avoid;
              }
            }
          </style>
        </head>
        <body>
          <h1>Medical Note</h1>

          <div class="metadata">
            <strong>Patient:</strong> ${noteDetail.patient_name}<br>
            <strong>Visit Date:</strong> ${noteDetail.visit_date}<br>
            <strong>Processing Status:</strong> ${noteDetail.processing_status}<br>
            <strong>Quality Score:</strong> ${noteDetail.passed_checks}/${noteDetail.total_checks} checks passed<br>
            <strong>Processing Attempts:</strong> ${noteDetail.processing_attempts || 1}
          </div>

          <div class="section">
            <h2>Original Freed Note</h2>
            <div class="note-box">${noteDetail.raw_note || 'No original note available'}</div>
          </div>

          <div class="section">
            <h2>AI-Processed Note (ASOP Format)</h2>
            <div class="note-box">${noteDetail.final_cleaned_note || 'No processed note available'}</div>
          </div>

          ${noteDetail.validation_checks && noteDetail.validation_checks.filter(c => !c.passed).length > 0 ? `
          <div class="section validation-checks">
            <h2>Failed Validation Checks</h2>
            <table>
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>Check Name</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                ${noteDetail.validation_checks.filter(c => !c.passed).map(check => `
                  <tr>
                    <td class="priority-${check.priority.toLowerCase()}">${check.priority}</td>
                    <td>${check.name}</td>
                    <td>${check.details || check.message}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
          ` : ''}

          <div class="section">
            <p style="color: #666; font-size: 12px; margin-top: 30px;">
              Printed on: ${new Date().toLocaleString()}<br>
              Generated by: ASOP Note Review System
            </p>
          </div>

          <script>
            window.onload = function() {
              window.print();
            };
          </script>
        </body>
      </html>
    `;

    printWindow.document.write(printContent);
    printWindow.document.close();
  };

  // Print all pending notes in batch
  const handlePrintAllNotes = () => {
    if (pendingNotes.length === 0) return;

    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    const printContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Batch Notes - ${selectedBatch}</title>
          <style>
            body {
              font-family: Arial, sans-serif;
              margin: 20px;
              line-height: 1.6;
            }
            h1 {
              color: #1976d2;
              border-bottom: 2px solid #1976d2;
              padding-bottom: 10px;
            }
            h2 {
              color: #333;
              margin-top: 30px;
              border-bottom: 1px solid #ddd;
              padding-bottom: 5px;
              page-break-before: always;
            }
            h2:first-of-type {
              page-break-before: auto;
            }
            .batch-header {
              background-color: #e3f2fd;
              padding: 15px;
              border-left: 4px solid #1976d2;
              margin: 20px 0;
            }
            .note-section {
              margin: 30px 0;
              page-break-inside: avoid;
            }
            .metadata {
              background-color: #f5f5f5;
              padding: 10px;
              border-left: 4px solid #1976d2;
              margin: 10px 0;
            }
            .quality-badge {
              display: inline-block;
              padding: 4px 8px;
              border-radius: 4px;
              font-weight: bold;
              margin-left: 10px;
            }
            .quality-success {
              background-color: #c8e6c9;
              color: #2e7d32;
            }
            .quality-warning {
              background-color: #fff9c4;
              color: #f57f17;
            }
            .quality-error {
              background-color: #ffcdd2;
              color: #c62828;
            }
            table {
              width: 100%;
              border-collapse: collapse;
              margin: 15px 0;
            }
            th, td {
              border: 1px solid #ddd;
              padding: 8px;
              text-align: left;
            }
            th {
              background-color: #f5f5f5;
              font-weight: bold;
            }
            @media print {
              body {
                margin: 0;
                padding: 15px;
              }
              .note-section {
                page-break-inside: avoid;
              }
            }
          </style>
        </head>
        <body>
          <h1>Batch Review Summary</h1>

          <div class="batch-header">
            <strong>Batch ID:</strong> ${selectedBatch || 'N/A'}<br>
            <strong>Total Notes:</strong> ${pendingNotes.length}<br>
            <strong>Generated:</strong> ${new Date().toLocaleString()}
          </div>

          <table>
            <thead>
              <tr>
                <th>Patient</th>
                <th>Visit Date</th>
                <th>Status</th>
                <th>Quality Score</th>
                <th>Critical Issues</th>
              </tr>
            </thead>
            <tbody>
              ${pendingNotes.map(note => `
                <tr>
                  <td>${note.patient_name}</td>
                  <td>${note.visit_date}</td>
                  <td>${note.review_status}</td>
                  <td>${note.passed_checks}/${note.total_checks}</td>
                  <td>${note.critical_failures > 0 ? `${note.critical_failures} critical` : 'None'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>

          ${pendingNotes.map(note => `
            <div class="note-section">
              <h2>${note.patient_name} - ${note.visit_date}
                <span class="quality-badge quality-${note.critical_failures > 0 ? 'error' : note.passed_checks === note.total_checks ? 'success' : 'warning'}">
                  ${note.passed_checks}/${note.total_checks} checks
                </span>
              </h2>

              <div class="metadata">
                <strong>Review Status:</strong> ${note.review_status}<br>
                <strong>Processing Status:</strong> ${note.processing_status}<br>
                ${note.requires_human_intervention ? `<strong style="color: #f57c00;">⚠ Requires Human Intervention</strong><br>` : ''}
                ${note.human_intervention_reasons ? `<strong>Reason:</strong> ${note.human_intervention_reasons}<br>` : ''}
                ${note.critical_failures > 0 ? `<strong style="color: #d32f2f;">Critical Failures:</strong> ${note.critical_failures}<br>` : ''}
              </div>
            </div>
          `).join('')}

          <div style="margin-top: 40px; padding-top: 20px; border-top: 2px solid #ddd;">
            <p style="color: #666; font-size: 12px;">
              Printed on: ${new Date().toLocaleString()}<br>
              Generated by: ASOP Note Review System<br>
              Batch: ${selectedBatch || 'N/A'}
            </p>
          </div>

          <script>
            window.onload = function() {
              window.print();
            };
          </script>
        </body>
      </html>
    `;

    printWindow.document.write(printContent);
    printWindow.document.close();
  };

  if (loading) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <LinearProgress />
        <Typography sx={{ mt: 2 }}>Loading review dashboard...</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Note Review Dashboard
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Review and approve ASOP-converted notes before upload to Osmind
        </Typography>
      </Box>

      {/* Batch Selector */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Select Batch</InputLabel>
                <Select
                  value={selectedBatch || ''}
                  onChange={(e) => setSelectedBatch(e.target.value)}
                  label="Select Batch"
                >
                  {batches.map((batch) => (
                    <MenuItem key={batch.batch_id} value={batch.batch_id}>
                      {batch.batch_id} ({batch.start_date} to {batch.end_date}) - {batch.total_notes} notes
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  variant="outlined"
                  startIcon={<Refresh />}
                  onClick={() => {
                    fetchBatches();
                    fetchPendingNotes();
                    fetchSummary();
                  }}
                >
                  Refresh
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<PrintOutlined />}
                  onClick={handlePrintAllNotes}
                  disabled={pendingNotes.length === 0}
                >
                  Print All Notes
                </Button>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      {summary && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Total Notes
                </Typography>
                <Typography variant="h4">
                  {summary.quality_metrics.total_notes}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Pending Review
                </Typography>
                <Typography variant="h4" color="warning.main">
                  {summary.review_status.pending || 0}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Approved
                </Typography>
                <Typography variant="h4" color="success.main">
                  {summary.review_status.approved || 0}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Avg Pass Rate
                </Typography>
                <Typography variant="h4">
                  {(summary.quality_metrics.avg_pass_rate * 100).toFixed(0)}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Pending Notes Table */}
      {pendingNotes.length > 0 ? (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Notes Pending Review ({pendingNotes.length})
            </Typography>
            <TableContainer component={Paper} sx={{ mt: 2 }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Patient</TableCell>
                    <TableCell>Visit Date</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Quality</TableCell>
                    <TableCell>Issues</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pendingNotes.map((note) => (
                    <TableRow key={note.id} hover>
                      <TableCell>{note.patient_name}</TableCell>
                      <TableCell>{note.visit_date}</TableCell>
                      <TableCell>
                        <Chip
                          label={note.review_status}
                          color={getStatusColor(note.review_status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2">
                            {note.passed_checks}/{note.total_checks}
                          </Typography>
                          <LinearProgress
                            variant="determinate"
                            value={(note.passed_checks / note.total_checks) * 100}
                            sx={{ width: 60 }}
                            color={
                              note.critical_failures > 0
                                ? 'error'
                                : note.passed_checks === note.total_checks
                                ? 'success'
                                : 'warning'
                            }
                          />
                        </Box>
                      </TableCell>
                      <TableCell>
                        {note.requires_human_intervention && (
                          <Tooltip title={note.human_intervention_reasons || 'Needs review'}>
                            <Warning color="warning" fontSize="small" />
                          </Tooltip>
                        )}
                        {note.critical_failures > 0 && (
                          <Chip
                            label={`${note.critical_failures} critical`}
                            color="error"
                            size="small"
                          />
                        )}
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Review Note">
                          <IconButton
                            size="small"
                            onClick={() => handleOpenReview(note)}
                          >
                            <Edit />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      ) : (
        <Alert severity="info">
          {selectedBatch
            ? 'No notes pending review in this batch.'
            : 'Select a batch to view pending notes.'}
        </Alert>
      )}

      {/* Review Dialog */}
      <Dialog
        open={reviewDialogOpen}
        onClose={() => setReviewDialogOpen(false)}
        maxWidth="xl"
        fullWidth
      >
        <DialogTitle>Review Note - {selectedNote?.patient_name}</DialogTitle>
        <DialogContent>
          {selectedNote && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Visit Date: {selectedNote.visit_date}
              </Typography>
              <Typography variant="subtitle2" gutterBottom>
                Quality: {selectedNote.passed_checks}/{selectedNote.total_checks} checks passed
              </Typography>
              {selectedNote.human_intervention_reasons && (
                <Alert severity="warning" sx={{ my: 2 }}>
                  {selectedNote.human_intervention_reasons}
                </Alert>
              )}

              {/* Note Comparison - Side by Side */}
              <Box sx={{ mt: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Note Comparison
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1" gutterBottom color="primary">
                          Original Freed Note
                        </Typography>
                        <Box
                          sx={{
                            maxHeight: 400,
                            overflow: 'auto',
                            whiteSpace: 'pre-wrap',
                            fontFamily: 'monospace',
                            fontSize: '0.85rem',
                            bgcolor: 'background.default',
                            p: 2,
                            borderRadius: 1,
                            border: 1,
                            borderColor: 'divider'
                          }}
                        >
                          {loadingDetail ? 'Loading...' : noteDetail?.raw_note || 'No original note available'}
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1" gutterBottom color="secondary">
                          AI-Processed Note (ASOP Format)
                        </Typography>
                        <Box
                          sx={{
                            maxHeight: 400,
                            overflow: 'auto',
                            whiteSpace: 'pre-wrap',
                            fontFamily: 'monospace',
                            fontSize: '0.85rem',
                            bgcolor: 'background.default',
                            p: 2,
                            borderRadius: 1,
                            border: 1,
                            borderColor: 'divider'
                          }}
                        >
                          {loadingDetail ? 'Loading...' : noteDetail?.final_cleaned_note || 'No processed note available'}
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </Box>

              {/* Validation Checks */}
              <Box sx={{ mt: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Failing Validation Checks
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Priority</TableCell>
                        <TableCell>Check Name</TableCell>
                        <TableCell>Details</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {loadingDetail ? (
                        <TableRow>
                          <TableCell colSpan={3} align="center">
                            Loading validation checks...
                          </TableCell>
                        </TableRow>
                      ) : noteDetail?.validation_checks?.filter(check => !check.passed).length > 0 ? (
                        noteDetail.validation_checks.filter(check => !check.passed).map((check) => (
                          <TableRow key={check.id}>
                            <TableCell>
                              <Chip
                                label={check.priority}
                                size="small"
                                color={check.priority === 'CRITICAL' ? 'error' : check.priority === 'HIGH' ? 'warning' : 'default'}
                              />
                            </TableCell>
                            <TableCell>{check.name}</TableCell>
                            <TableCell>{check.details || check.message}</TableCell>
                          </TableRow>
                        ))
                      ) : (
                        <TableRow>
                          <TableCell colSpan={3} align="center">
                            All checks passed!
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>

              {/* Re-processing Section */}
              <Box sx={{ mt: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Re-process with AI
                </Typography>
                <Button
                  variant="contained"
                  color="secondary"
                  startIcon={<Refresh />}
                  sx={{ mr: 2 }}
                  onClick={handleReprocess}
                  disabled={reprocessing || loadingDetail}
                >
                  {reprocessing ? 'Re-processing...' : 'Re-process Note'}
                </Button>
                <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                  Note: This will send the original note back through the AI processing pipeline with updated prompts.
                </Typography>
              </Box>

              <FormControl fullWidth sx={{ mt: 3, mb: 2 }}>
                <InputLabel>Review Decision</InputLabel>
                <Select
                  value={reviewStatus}
                  onChange={(e) => setReviewStatus(e.target.value)}
                  label="Review Decision"
                >
                  <MenuItem value="approved">Approve</MenuItem>
                  <MenuItem value="needs_revision">Needs Revision</MenuItem>
                  <MenuItem value="rejected">Reject</MenuItem>
                </Select>
              </FormControl>

              <TextField
                fullWidth
                multiline
                rows={4}
                label="Review Notes"
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Add notes about your review decision..."
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            startIcon={<Print />}
            onClick={handlePrintNote}
            disabled={!noteDetail}
          >
            Print Note
          </Button>
          <Box sx={{ flex: 1 }} />
          <Button onClick={() => setReviewDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleReviewSubmit} variant="contained" color="primary">
            Submit Review
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
