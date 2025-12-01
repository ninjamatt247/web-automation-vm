import { useState, useEffect } from 'react'
import axios from 'axios'
import { DataGrid, GridToolbar } from '@mui/x-data-grid'
import { Box, Modal, Typography, Paper, Button, IconButton, ThemeProvider, createTheme, Popover, Tooltip, TextField, MenuItem, Select, FormControl, InputLabel, Chip, Divider } from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import MoreVertIcon from '@mui/icons-material/MoreVert'
import CheckIcon from '@mui/icons-material/Check'

// Create dark theme with black background
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
    },
    secondary: {
      main: '#f48fb1',
    },
    background: {
      default: '#000000',
      paper: '#1a1a1a',
    },
    text: {
      primary: '#ffffff',
      secondary: '#b0b0b0',
    },
  },
  components: {
    MuiDataGrid: {
      styleOverrides: {
        root: {
          border: '1px solid #333',
          backgroundColor: '#000000',
          '& .MuiDataGrid-cell': {
            borderBottom: '1px solid #333',
            fontSize: '0.875rem',
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
          },
          '& .MuiDataGrid-columnHeaders': {
            backgroundColor: '#1a1a1a',
            fontSize: '0.875rem',
            fontWeight: 600,
            borderBottom: '2px solid #90caf9',
          },
          '& .MuiDataGrid-columnHeaderTitle': {
            fontWeight: 600,
          },
          '& .MuiDataGrid-row': {
            '&:hover': {
              backgroundColor: '#1a1a1a',
            },
            '&.Mui-selected': {
              backgroundColor: '#2a2a2a',
              '&:hover': {
                backgroundColor: '#333333',
              },
            },
          },
          '& .MuiDataGrid-footerContainer': {
            backgroundColor: '#1a1a1a',
            borderTop: '2px solid #90caf9',
          },
          '& .MuiCheckbox-root': {
            color: '#90caf9',
          },
          '& .MuiDataGrid-iconSeparator': {
            color: '#333',
          },
        },
      },
    },
  },
})

function OsmindNotesView() {
  const [notes, setNotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedNote, setSelectedNote] = useState(null)
  const [popoverAnchor, setPopoverAnchor] = useState(null)
  const [popoverContent, setPopoverContent] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [datePreset, setDatePreset] = useState('all')
  const [patientSearch, setPatientSearch] = useState('')
  const [noteLimit, setNoteLimit] = useState(1000)
  const [syncingOsmind, setSyncingOsmind] = useState(false)
  const [syncMessage, setSyncMessage] = useState(null)

  useEffect(() => {
    fetchNotes()
  }, [noteLimit])

  const fetchNotes = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`/api/osmind-notes?limit=${noteLimit}`)
      setNotes(response.data.notes || [])
      setError(null)
    } catch (err) {
      setError('Failed to load Osmind notes')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getDateRangeForPreset = (preset) => {
    const now = new Date()
    const year = now.getFullYear()
    const month = now.getMonth()
    const date = now.getDate()
    const day = now.getDay()

    switch (preset) {
      case 'this_week': {
        const weekStart = new Date(year, month, date - day)
        const weekEnd = new Date(year, month, date - day + 6)
        return { start: weekStart, end: weekEnd }
      }
      case 'last_week': {
        const weekStart = new Date(year, month, date - day - 7)
        const weekEnd = new Date(year, month, date - day - 1)
        return { start: weekStart, end: weekEnd }
      }
      case 'mtd': {
        const monthStart = new Date(year, month, 1)
        return { start: monthStart, end: now }
      }
      case 'last_month': {
        const lastMonthStart = new Date(year, month - 1, 1)
        const lastMonthEnd = new Date(year, month, 0)
        return { start: lastMonthStart, end: lastMonthEnd }
      }
      case 'qtd': {
        const quarter = Math.floor(month / 3)
        const quarterStart = new Date(year, quarter * 3, 1)
        return { start: quarterStart, end: now }
      }
      case 'ytd': {
        const yearStart = new Date(year, 0, 1)
        return { start: yearStart, end: now }
      }
      default:
        return null
    }
  }

  const handlePresetChange = (event) => {
    const preset = event.target.value
    setDatePreset(preset)

    if (preset === 'all') {
      setStartDate('')
      setEndDate('')
    } else if (preset === 'custom') {
      // Keep current dates
    } else {
      const range = getDateRangeForPreset(preset)
      if (range) {
        setStartDate(range.start.toISOString().split('T')[0])
        setEndDate(range.end.toISOString().split('T')[0])
      }
    }
  }

  const parseVisitDate = (dateStr) => {
    if (!dateStr) return null

    // Try parsing as ISO date string first
    const date = new Date(dateStr)
    return isNaN(date.getTime()) ? null : date
  }

  const handleRunOsmindSync = async () => {
    try {
      setSyncingOsmind(true)
      setSyncMessage(null)
      const response = await axios.post('/api/fetch-from-osmind', { days: 7 })
      setSyncMessage({
        type: 'success',
        text: response.data.message || 'Successfully started Osmind sync'
      })
      // Refresh notes after sync completes
      setTimeout(() => {
        fetchNotes()
      }, 15000) // Give it 15 seconds for headless sync
    } catch (err) {
      setSyncMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to start Osmind sync'
      })
      console.error(err)
    } finally {
      setSyncingOsmind(false)
    }
  }

  const filteredNotes = notes.filter((note) => {
    // Filter by patient search
    if (patientSearch) {
      const searchLower = patientSearch.toLowerCase()
      const patientNameMatch = note.patient_name?.toLowerCase().includes(searchLower)
      if (!patientNameMatch) return false
    }

    // Filter by date range
    if (!startDate && !endDate) return true

    const visitDate = parseVisitDate(note.visit_date || note.created_at)
    if (!visitDate) return false

    const start = startDate ? new Date(startDate) : null
    const end = endDate ? new Date(endDate) : null

    if (start && visitDate < start) return false
    if (end) {
      const endOfDay = new Date(end)
      endOfDay.setHours(23, 59, 59, 999)
      if (visitDate > endOfDay) return false
    }

    return true
  })

  const columns = [
    {
      field: 'patient_name',
      headerName: 'Patient Name',
      flex: 1,
      minWidth: 150,
    },
    {
      field: 'visit_date',
      headerName: 'Visit Date',
      width: 110,
      renderCell: (params) => {
        if (!params.row.visit_date) return '-'

        const dateStr = params.row.visit_date
        const date = new Date(dateStr)
        if (!isNaN(date.getTime())) {
          const month = String(date.getMonth() + 1).padStart(2, '0')
          const day = String(date.getDate()).padStart(2, '0')
          const year = String(date.getFullYear()).slice(-2)
          return `${month}/${day}/${year}`
        }

        return dateStr
      },
    },
    {
      field: 'note_type',
      headerName: 'Note Type',
      width: 120,
      renderCell: (params) => params.row.note_type || '-',
    },
    {
      field: 'full_text',
      headerName: 'Note Preview',
      flex: 2,
      minWidth: 300,
      renderCell: (params) => {
        const fullNote = params.row.full_text || params.row.note_text || ''
        const preview = fullNote.substring(0, 100) + (fullNote.length > 100 ? '...' : '')
        return (
          <div
            style={{
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              color: '#ffffff',
              fontSize: '0.875rem',
              width: '100%',
              cursor: 'pointer',
            }}
            onMouseEnter={(event) => {
              setPopoverAnchor(event.currentTarget)
              setPopoverContent(fullNote || 'No note text available')
            }}
            onMouseLeave={() => {
              setPopoverAnchor(null)
              setPopoverContent('')
            }}
          >
            {preview || 'No note text'}
          </div>
        )
      },
    },
    {
      field: 'rendering_provider_name',
      headerName: 'Provider',
      width: 150,
      renderCell: (params) => params.row.rendering_provider_name || '-',
    },
    {
      field: 'location_name',
      headerName: 'Location',
      width: 150,
      renderCell: (params) => params.row.location_name || '-',
    },
    {
      field: 'is_signed',
      headerName: 'Signed',
      width: 80,
      renderCell: (params) => {
        if (params.row.is_signed) {
          return (
            <Tooltip title="Note is signed" arrow>
              <CheckIcon sx={{ color: '#4caf50', fontSize: '1.2rem' }} />
            </Tooltip>
          )
        }
        return <CloseIcon sx={{ color: '#f44336', fontSize: '1.2rem' }} />
      },
    },
    {
      field: 'note_length',
      headerName: 'Length',
      width: 90,
      renderCell: (params) => {
        const length = params.row.note_length || 0
        return length > 0 ? length.toLocaleString() : '-'
      },
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 110,
      renderCell: (params) => {
        if (!params.row.created_at) return '-'
        const date = new Date(params.row.created_at)
        const month = String(date.getMonth() + 1).padStart(2, '0')
        const day = String(date.getDate()).padStart(2, '0')
        const year = String(date.getFullYear()).slice(-2)
        return `${month}/${day}/${year}`
      },
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 80,
      sortable: false,
      renderCell: (params) => (
        <IconButton
          size="small"
          onClick={() => setSelectedNote(params.row)}
          sx={{ color: '#90caf9' }}
        >
          <MoreVertIcon />
        </IconButton>
      ),
    },
  ]

  if (error) {
    return (
      <div className="page">
        <div className="error">{error}</div>
      </div>
    )
  }

  return (
    <div className="page page-full-width">
      <h1 className="page-title">Osmind Notes ({filteredNotes.length})</h1>

      {notes.length === 0 && !loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
          <p>No Osmind notes found.</p>
          <p style={{ marginTop: '1rem', fontSize: '0.9rem' }}>
            Run Osmind sync to fetch notes from the EHR system.
          </p>
        </div>
      ) : (
        <ThemeProvider theme={darkTheme}>
          {/* Sync Message */}
          {syncMessage && (
            <Box
              sx={{
                mb: 2,
                p: 2,
                bgcolor: syncMessage.type === 'success' ? '#1b5e20' : '#b71c1c',
                color: '#ffffff',
                borderRadius: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {syncMessage.type === 'success' ? (
                  <CheckIcon sx={{ fontSize: '1.2rem' }} />
                ) : (
                  <CloseIcon sx={{ fontSize: '1.2rem' }} />
                )}
                <Typography>{syncMessage.text}</Typography>
              </Box>
              <IconButton
                size="small"
                onClick={() => setSyncMessage(null)}
                sx={{ color: '#ffffff' }}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            </Box>
          )}

          {/* Search and Filter Actions */}
          <Box sx={{ mb: 2, p: 2, bgcolor: '#1a1a1a', borderRadius: 1 }}>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap', mb: 2 }}>
              <TextField
                label="Search Patients"
                placeholder="Enter patient name..."
                value={patientSearch}
                onChange={(e) => setPatientSearch(e.target.value)}
                sx={{ minWidth: 250, flex: 1 }}
                InputProps={{
                  startAdornment: (
                    <Box sx={{ mr: 1, display: 'flex', alignItems: 'center' }}>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="11" cy="11" r="8"/>
                        <path d="m21 21-4.35-4.35"/>
                      </svg>
                    </Box>
                  ),
                }}
              />

              <FormControl sx={{ minWidth: 150 }}>
                <InputLabel>Show Notes</InputLabel>
                <Select
                  value={noteLimit}
                  onChange={(e) => setNoteLimit(e.target.value)}
                  label="Show Notes"
                  sx={{ height: 56 }}
                >
                  <MenuItem value={100}>Last 100</MenuItem>
                  <MenuItem value={250}>Last 250</MenuItem>
                  <MenuItem value={500}>Last 500</MenuItem>
                  <MenuItem value={1000}>Last 1000</MenuItem>
                  <MenuItem value={0}>All Notes</MenuItem>
                </Select>
              </FormControl>

              <Button
                variant="contained"
                onClick={handleRunOsmindSync}
                disabled={syncingOsmind}
                sx={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #5568d3 0%, #65408b 100%)',
                  },
                  height: 56,
                  px: 3,
                }}
              >
                {syncingOsmind ? (
                  <>
                    <Box component="span" sx={{ mr: 1, display: 'flex', alignItems: 'center' }}>
                      <svg className="spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10"/>
                      </svg>
                    </Box>
                    Syncing...
                  </>
                ) : (
                  <>
                    <Box component="span" sx={{ mr: 1, display: 'flex', alignItems: 'center' }}>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                      </svg>
                    </Box>
                    Run Osmind Sync
                  </>
                )}
              </Button>

              {patientSearch && (
                <Button
                  variant="outlined"
                  onClick={() => setPatientSearch('')}
                  sx={{ height: 56 }}
                >
                  Clear Search
                </Button>
              )}
            </Box>

            {/* Date Filters */}
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
              <FormControl sx={{ minWidth: 150 }}>
                <InputLabel id="date-preset-label">Date Range</InputLabel>
                <Select
                  labelId="date-preset-label"
                  value={datePreset}
                  label="Date Range"
                  onChange={handlePresetChange}
                >
                  <MenuItem value="all">All Time</MenuItem>
                  <MenuItem value="this_week">This Week</MenuItem>
                  <MenuItem value="last_week">Last Week</MenuItem>
                  <MenuItem value="mtd">Month to Date</MenuItem>
                  <MenuItem value="last_month">Last Month</MenuItem>
                  <MenuItem value="qtd">Quarter to Date</MenuItem>
                  <MenuItem value="ytd">Year to Date</MenuItem>
                  <MenuItem value="custom">Custom Range</MenuItem>
                </Select>
              </FormControl>

              <TextField
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value)
                  setDatePreset('custom')
                }}
                InputLabelProps={{ shrink: true }}
                sx={{ minWidth: 150 }}
              />

              <TextField
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => {
                  setEndDate(e.target.value)
                  setDatePreset('custom')
                }}
                InputLabelProps={{ shrink: true }}
                sx={{ minWidth: 150 }}
              />

              {(startDate || endDate) && (
                <Button
                  variant="outlined"
                  onClick={() => {
                    setStartDate('')
                    setEndDate('')
                    setDatePreset('all')
                  }}
                  sx={{ height: 56 }}
                >
                  Clear Date Filters
                </Button>
              )}
            </Box>
          </Box>

          <Box sx={{ height: 'calc(100vh - 300px)', width: '100%' }}>
            <DataGrid
              rows={filteredNotes}
              columns={columns}
              pageSize={25}
              rowsPerPageOptions={[10, 25, 50, 100]}
              checkboxSelection
              disableSelectionOnClick
              loading={loading}
              slots={{
                toolbar: GridToolbar,
              }}
              slotProps={{
                toolbar: {
                  showQuickFilter: true,
                  quickFilterProps: { debounceMs: 500 },
                },
              }}
            />
          </Box>
        </ThemeProvider>
      )}

      {/* Note Detail Modal */}
      <Modal
        open={!!selectedNote}
        onClose={() => setSelectedNote(null)}
        aria-labelledby="note-detail-modal"
      >
        <Box sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '80%',
          maxWidth: 900,
          maxHeight: '90vh',
          overflow: 'auto',
          bgcolor: 'background.paper',
          boxShadow: 24,
          borderRadius: 2,
          p: 4,
        }}>
          {selectedNote && (
            <>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h5" component="h2">
                  Osmind Note Details
                </Typography>
                <IconButton onClick={() => setSelectedNote(null)}>
                  <CloseIcon />
                </IconButton>
              </Box>

              {/* Patient Information */}
              <Paper elevation={0} sx={{ p: 2, mb: 3, bgcolor: '#f8f9fa' }}>
                <Typography variant="h6" gutterBottom sx={{ color: '#667eea' }}>
                  Patient Information
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Patient Name
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                      {selectedNote.patient_name}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Visit Date
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.visit_date ? new Date(selectedNote.visit_date).toLocaleDateString() : '-'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Note Type
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.note_type || '-'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Note Length
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.note_length ? `${selectedNote.note_length.toLocaleString()} characters` : '-'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Provider
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.rendering_provider_name || '-'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Location
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.location_name || '-'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Is Signed
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.is_signed ? 'Yes' : 'No'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Created At
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.created_at ? new Date(selectedNote.created_at).toLocaleString() : '-'}
                    </Typography>
                  </Box>
                </Box>
              </Paper>

              {/* Full Note Text */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" gutterBottom sx={{ color: '#667eea' }}>
                  Full Note Text
                </Typography>
                <Paper elevation={0} sx={{ p: 2, bgcolor: '#f8f9fa', maxHeight: 400, overflow: 'auto' }}>
                  <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                    {selectedNote.full_text || selectedNote.note_text || 'No note text available'}
                  </Typography>
                </Paper>
              </Box>

              {/* Osmind Metadata */}
              <Paper elevation={0} sx={{ p: 2, mb: 3, bgcolor: '#f0f0f0' }}>
                <Typography variant="h6" gutterBottom sx={{ color: '#667eea' }}>
                  Osmind Metadata
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Osmind Note ID
                    </Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      {selectedNote.osmind_note_id || '-'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Osmind Patient ID
                    </Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      {selectedNote.osmind_patient_id || '-'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Sync Source
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.sync_source || '-'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Last Synced
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.last_synced_at ? new Date(selectedNote.last_synced_at).toLocaleString() : '-'}
                    </Typography>
                  </Box>
                  {selectedNote.first_signed_at && (
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary">
                        First Signed At
                      </Typography>
                      <Typography variant="body1">
                        {new Date(selectedNote.first_signed_at).toLocaleString()}
                      </Typography>
                    </Box>
                  )}
                </Box>
              </Paper>

              <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                  variant="contained"
                  onClick={() => setSelectedNote(null)}
                  sx={{
                    textTransform: 'none',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  }}
                >
                  Close
                </Button>
              </Box>
            </>
          )}
        </Box>
      </Modal>

      {/* Note Preview Popover */}
      <Popover
        open={Boolean(popoverAnchor)}
        anchorEl={popoverAnchor}
        onClose={() => setPopoverAnchor(null)}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'left',
        }}
        sx={{
          pointerEvents: 'none',
        }}
        disableRestoreFocus
      >
        <Paper
          sx={{
            p: 2,
            maxWidth: 600,
            maxHeight: 400,
            overflow: 'auto',
            bgcolor: '#1a1a1a',
            color: '#ffffff',
          }}
        >
          <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
            {popoverContent}
          </Typography>
        </Paper>
      </Popover>
    </div>
  )
}

export default OsmindNotesView
