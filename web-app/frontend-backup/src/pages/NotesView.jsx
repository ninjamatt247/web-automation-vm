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

function NotesView() {
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
  const [syncingFreed, setSyncingFreed] = useState(false)
  const [syncMessage, setSyncMessage] = useState(null)
  const [noteLimit, setNoteLimit] = useState(1000)

  useEffect(() => {
    fetchNotes()
  }, [noteLimit])

  const fetchNotes = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`/api/notes?limit=${noteLimit}`)
      setNotes(response.data.notes || [])
      setError(null)
    } catch (err) {
      setError('Failed to load notes')
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

    // Check if it's in mm/dd/yy format
    const match = dateStr.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2})/)
    if (match) {
      const [, month, day, year] = match
      const fullYear = parseInt(year) < 50 ? `20${year}` : `19${year}`
      return new Date(`${fullYear}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`)
    }

    // Try parsing as standard date
    const date = new Date(dateStr)
    return isNaN(date.getTime()) ? null : date
  }

  const handleRunFreedSync = async () => {
    try {
      setSyncingFreed(true)
      setSyncMessage(null)
      const response = await axios.post('/api/fetch-from-freed', { days: 7 })
      setSyncMessage({
        type: 'success',
        text: response.data.message || 'Successfully synced notes from Freed.ai'
      })
      // Refresh notes after sync
      setTimeout(() => {
        fetchNotes()
      }, 3000)
    } catch (err) {
      setSyncMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to sync from Freed.ai'
      })
      console.error(err)
    } finally {
      setSyncingFreed(false)
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

    const visitDate = parseVisitDate(note.visit_date)
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

        // Try to parse the date - it might be in format "11/29/25 3:45PM" or ISO format
        const dateStr = params.row.visit_date
        let date

        // Check if it's already in mm/dd/yy format
        if (dateStr.match(/^\d{1,2}\/\d{1,2}\/\d{2}/)) {
          // Extract just the date part (before any time)
          const datePart = dateStr.split(' ')[0]
          return datePart
        }

        // Try to parse as ISO or other standard format
        date = new Date(dateStr)
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
      field: 'description',
      headerName: 'Description',
      flex: 2,
      minWidth: 250,
      renderCell: (params) => {
        const description = params.row.description || 'No description'
        const fullNote = params.row.note_text || params.row.full_text || params.row.orig_note || params.row.original_note || ''
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
            {description}
          </div>
        )
      },
    },
    {
      field: 'synced',
      headerName: 'Synced',
      width: 100,
      renderCell: (params) => {
        const syncDate = params.row.synced
        if (syncDate) {
          return (
            <Tooltip title={syncDate} arrow>
              <CheckIcon sx={{ color: '#4caf50', fontSize: '1.2rem' }} />
            </Tooltip>
          )
        }
        return <CloseIcon sx={{ color: '#f44336', fontSize: '1.2rem' }} />
      },
    },
    {
      field: 'tags',
      headerName: 'Tags',
      width: 150,
      renderCell: (params) => {
        const tags = params.row.tags
        if (!tags) return '-'

        try {
          const tagArray = typeof tags === 'string' ? JSON.parse(tags) : tags
          if (Array.isArray(tagArray) && tagArray.length > 0) {
            return (
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                {tagArray.slice(0, 2).map((tag, idx) => (
                  <Chip
                    key={idx}
                    label={tag}
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: '0.7rem',
                      bgcolor: '#667eea',
                      color: 'white',
                    }}
                  />
                ))}
                {tagArray.length > 2 && (
                  <Chip
                    label={`+${tagArray.length - 2}`}
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: '0.7rem',
                      bgcolor: '#555',
                      color: 'white',
                    }}
                  />
                )}
              </Box>
            )
          }
        } catch (e) {
          return '-'
        }
        return '-'
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
      headerName: 'Created Date',
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
      field: 'sent_to_ai_date',
      headerName: 'Sent to AI',
      flex: 1,
      minWidth: 150,
      renderCell: (params) => params.row.sent_to_ai_date || '-',
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
      <h1 className="page-title">Freed Notes ({filteredNotes.length})</h1>

      {notes.length === 0 && !loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
          <p>No processed notes found.</p>
          <button
            className="btn btn-primary"
            style={{ marginTop: '1rem' }}
            onClick={() => window.location.href = '/process'}
          >
            Process Your First Note
          </button>
        </div>
      ) : (
        <ThemeProvider theme={darkTheme}>
          {/* Sync Message */}
          {syncMessage && (
            <Box sx={{
              mb: 2,
              p: 2,
              bgcolor: syncMessage.type === 'success' ? '#1b5e20' : '#b71c1c',
              borderRadius: 1,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <Typography>{syncMessage.text}</Typography>
              <IconButton
                size="small"
                onClick={() => setSyncMessage(null)}
                sx={{ color: 'white' }}
              >
                <CloseIcon />
              </IconButton>
            </Box>
          )}

          {/* Search and Sync Actions */}
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
                onClick={handleRunFreedSync}
                disabled={syncingFreed}
                sx={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #5568d3 0%, #65408b 100%)',
                  },
                  height: 56,
                  px: 3,
                }}
              >
                {syncingFreed ? (
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
                    Run Freed Sync
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
                  Note Details
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
                      {selectedNote.visit_date || '-'}
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
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Note Length
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.note_length ? `${selectedNote.note_length.toLocaleString()} characters` : '-'}
                    </Typography>
                  </Box>
                </Box>

                {/* Tags */}
                {selectedNote.tags && (() => {
                  try {
                    const tagArray = typeof selectedNote.tags === 'string' ? JSON.parse(selectedNote.tags) : selectedNote.tags
                    if (Array.isArray(tagArray) && tagArray.length > 0) {
                      return (
                        <Box sx={{ mt: 2 }}>
                          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                            Tags
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                            {tagArray.map((tag, idx) => (
                              <Chip
                                key={idx}
                                label={tag}
                                size="small"
                                sx={{
                                  bgcolor: '#667eea',
                                  color: 'white',
                                }}
                              />
                            ))}
                          </Box>
                        </Box>
                      )
                    }
                  } catch (e) {
                    return null
                  }
                  return null
                })()}
              </Paper>

              {/* Description */}
              {selectedNote.description && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" gutterBottom sx={{ color: '#667eea' }}>
                    Description
                  </Typography>
                  <Paper elevation={0} sx={{ p: 2, bgcolor: '#f8f9fa' }}>
                    <Typography variant="body1">
                      {selectedNote.description}
                    </Typography>
                  </Paper>
                </Box>
              )}

              {/* Full Note Text */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" gutterBottom sx={{ color: '#667eea' }}>
                  Full Note Text
                </Typography>
                <Paper elevation={0} sx={{ p: 2, bgcolor: '#f8f9fa', maxHeight: 300, overflow: 'auto' }}>
                  <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                    {selectedNote.full_text || selectedNote.note_text || selectedNote.original_note || 'No note text available'}
                  </Typography>
                </Paper>
              </Box>

              {/* Sections */}
              {selectedNote.sections && (() => {
                try {
                  const sectionsObj = typeof selectedNote.sections === 'string' ? JSON.parse(selectedNote.sections) : selectedNote.sections
                  if (sectionsObj && Object.keys(sectionsObj).length > 0) {
                    return (
                      <Box sx={{ mb: 3 }}>
                        <Typography variant="h6" gutterBottom sx={{ color: '#667eea' }}>
                          Note Sections
                        </Typography>
                        <Paper elevation={0} sx={{ p: 2, bgcolor: '#f8f9fa' }}>
                          {Object.entries(sectionsObj).map(([key, value]) => (
                            <Box key={key} sx={{ mb: 2 }}>
                              <Typography variant="subtitle2" color="text.secondary" sx={{ textTransform: 'capitalize' }}>
                                {key.replace(/_/g, ' ')}
                              </Typography>
                              <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', mt: 0.5 }}>
                                {value || '-'}
                              </Typography>
                            </Box>
                          ))}
                        </Paper>
                      </Box>
                    )
                  }
                } catch (e) {
                  return null
                }
                return null
              })()}

              {/* Cleaned Note (if exists) */}
              {selectedNote.cleaned_note && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" gutterBottom sx={{ color: '#667eea' }}>
                    Cleaned Note (APSO Format)
                  </Typography>
                  <Paper elevation={0} sx={{ p: 2, bgcolor: '#f8f9fa', maxHeight: 300, overflow: 'auto' }}>
                    <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                      {selectedNote.cleaned_note}
                    </Typography>
                  </Paper>
                </Box>
              )}

              {/* Processing Information */}
              <Paper elevation={0} sx={{ p: 2, mb: 3, bgcolor: '#f0f0f0' }}>
                <Typography variant="h6" gutterBottom sx={{ color: '#667eea' }}>
                  Processing Information
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Processing Status
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.processing_status || '-'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      AI Enhanced
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.ai_enhanced ? 'Yes' : 'No'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Sent to AI Date
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.sent_to_ai_date || '-'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Uploaded to Osmind
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.uploaded_to_osmind ? 'Yes' : 'No'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Synced
                    </Typography>
                    <Typography variant="body1">
                      {selectedNote.synced || '-'}
                    </Typography>
                  </Box>
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

export default NotesView
